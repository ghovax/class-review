"""Shared errors, logging, model calls, and lesson helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.messages import BaseMessage
from models_provider import ModelUsage
from teacher.interfaces import ChatModel
from teacher.models import GlossaryEntry, GlossaryLink
from typing import Any, Final, Self, Literal
import logging
import re
import traceback

import structlog


class OperationError(Exception):
    """A failure raised by an operation."""

    def __init__(
        self,
        message: str,
        metadata: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        """Build an operation error carrying structured context."""
        super().__init__(message)
        self.metadata: dict[str, Any] = dict(metadata or {})
        if cause is not None:
            self.__cause__ = cause

    @classmethod
    def retryable(
        cls,
        message: str,
        metadata: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> Self:
        """Builds an error the retry predicate will schedule another attempt for."""
        return cls(message, {**(metadata or {}), "retryable": True}, cause)

    @classmethod
    def terminal(
        cls,
        message: str,
        metadata: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> Self:
        """Builds an error that marks an operation failure as terminal."""
        return cls(message, {**(metadata or {}), "retryable": False}, cause)

    @property
    def is_retryable(self) -> bool:
        """Whether this error was explicitly flagged as transient."""
        return bool(self.metadata.get("retryable", False))


TRANSIENT_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {"ETIMEDOUT", "ECONNRESET", "ECONNREFUSED", "EAI_AGAIN"}
)


def classify_retryable(error: BaseException) -> bool:
    """Decide whether an operation failure is likely transient."""
    if isinstance(error, OperationError):
        return error.is_retryable
    status_code = _read_status_code(error)
    if status_code is not None:
        return status_code == 429 or 500 <= status_code < 600
    error_code = getattr(error, "code", None)
    return isinstance(error_code, str) and error_code in TRANSIENT_ERROR_CODES


def describe_error(error: BaseException) -> dict[str, Any]:
    """Renders an exception as a structured payload for logging."""
    described: dict[str, Any] = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback_frames": [
            {
                "file_name": frame.filename,
                "line_number": frame.lineno,
                "function_name": frame.name,
            }
            for frame in traceback.extract_tb(error.__traceback__)
        ],
    }
    if isinstance(error, OperationError) and error.metadata:
        described["error_metadata"] = error.metadata
    cause = error.__cause__
    if cause is not None:
        described["error_cause"] = describe_error(cause)
    return described


def _read_status_code(error: BaseException) -> int | None:
    """Extracts an HTTP status code from an exception, when it carries one."""
    for attribute_name in ("status_code", "status"):
        candidate = getattr(error, attribute_name, None)
        if isinstance(candidate, int) and candidate > 0:
            return candidate
    response = getattr(error, "response", None)
    candidate = getattr(response, "status_code", None)
    if isinstance(candidate, int) and candidate > 0:
        return candidate
    return None


RenderingStyle = Literal["console", "json"]


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Returns the logger a module should bind its records to."""
    return structlog.stdlib.get_logger(name)


def configure_logging(
    *,
    level: int = logging.INFO,
    rendering: RenderingStyle = "console",
) -> None:
    """Configures structlog and the standard library logging bridge."""
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        timestamper,
        structlog.processors.StackInfoRenderer(),
    ]
    renderer: Any = (
        structlog.dev.ConsoleRenderer()
        if rendering == "console"
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(format="%(message)s", level=level)


@dataclass(frozen=True, slots=True)
class ModelAnswer:
    """One complete model call, including the response beyond visible text.

    ``text`` is the normalized text used by parsers.  ``messages`` and
    ``response`` retain the original request and provider response so callers
    can inspect content blocks, tool calls, response metadata, and any
    reasoning fields the selected model exposes.
    """

    text: str
    messages: tuple[BaseMessage, ...]
    response: Any
    usage_by_model: dict[str, ModelUsage]


async def call_chat_model(
    chat_model: ChatModel,
    messages: Sequence[BaseMessage],
    *,
    metadata: dict[str, Any] | None = None,
) -> ModelAnswer:
    """Call a chat model without throwing away the provider response."""
    request_messages = tuple(messages)
    with get_usage_metadata_callback() as usage_callback:
        response = await chat_model.ainvoke(list(request_messages))

    # LangChain messages expose ``text`` while a small user-supplied model
    # double may only expose ``content``.  Keep the original response either
    # way; this string is only the parser-facing projection.
    trimmed = _response_text(response).strip()
    if not trimmed:
        raise OperationError.retryable("the model returned an empty answer", dict(metadata or {}))

    return ModelAnswer(
        text=trimmed,
        messages=request_messages,
        response=response,
        usage_by_model=_read_usage(usage_callback.usage_metadata),
    )


def _response_text(response: Any) -> str:  # noqa: ANN401
    """Read visible text while leaving the complete response untouched."""
    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text
    content = getattr(response, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, Sequence):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, Mapping):
                value = block.get("text")
                if isinstance(value, str):
                    parts.append(value)
        return "".join(parts)
    return ""


def _read_usage(usage_metadata: Any) -> dict[str, ModelUsage]:  # noqa: ANN401
    """Converts collected usage metadata into the channel's shape."""
    converted: dict[str, ModelUsage] = {}
    for model_name, counts in (usage_metadata or {}).items():
        converted[str(model_name)] = ModelUsage.from_mapping(
            counts if isinstance(counts, Mapping) else {}
        )
    return converted


def compute_glossary_links(
    chapter_contents: Sequence[str], glossary_entries: Sequence[GlossaryEntry]
) -> list[tuple[GlossaryLink, ...]]:
    """Link the first plain-text occurrence of each glossary term."""
    remaining = {entry.key for entry in glossary_entries if entry.short_form.strip()}
    links_per_chapter: list[tuple[GlossaryLink, ...]] = []
    for content in chapter_contents:
        candidates: list[GlossaryLink] = []
        for entry in glossary_entries:
            if entry.key not in remaining:
                continue
            phrase = entry.short_form.strip()
            match = re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", content, re.IGNORECASE)
            if match is None:
                continue
            candidates.append(GlossaryLink(key=entry.key, start=match.start(), end=match.end()))
        chapter_links = _select_non_overlapping_links(content, candidates)
        remaining.difference_update(link.key for link in chapter_links)
        links_per_chapter.append(chapter_links)
    return links_per_chapter


def apply_glossary_links(content: str, links: Sequence[GlossaryLink]) -> str:
    """Link stored character ranges to the glossary section."""
    result = content
    for link in reversed(_select_non_overlapping_links(content, links)):
        text = result[link.start : link.end]
        result = f"{result[: link.start]}[{text}](#glossary){result[link.end :]}"
    return result


def _select_non_overlapping_links(
    content: str, links: Sequence[GlossaryLink]
) -> tuple[GlossaryLink, ...]:
    """Select valid, longest-first links so nested ranges cannot corrupt Markdown."""
    selected: list[GlossaryLink] = []
    for link in sorted(
        links,
        key=lambda item: (-(item.end - item.start), item.start, item.end, item.key),
    ):
        if not 0 <= link.start < link.end <= len(content):
            continue
        if any(link.start < other.end and other.start < link.end for other in selected):
            continue
        selected.append(link)
    return tuple(sorted(selected, key=lambda item: (item.start, item.end, item.key)))
