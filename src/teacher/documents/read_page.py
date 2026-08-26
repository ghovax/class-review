"""Reading one rendered page."""

from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.runtime import Runtime

from teacher.configuration import GraphRuntime
from teacher.documents.load import PageToRead
from teacher.errors import PipelineError, classify_retryable
from teacher.logging_support import get_logger
from teacher.model_calls import call_chat_model
from teacher.models import LanguageModelUsage
from teacher.state import StagedPage

__all__ = ["read_page"]

logger = get_logger(__name__)

_SYSTEM_TEMPLATE = "documents/read_page/system"
_USER_TEMPLATE = "documents/read_page/user"
_NOTATION_TEMPLATE = "mathematics_notation_rules"

# What a page that could not be read contributes.
_UNREADABLE_SUMMARY = "This page could not be read."
_UNREADABLE_DETAILS = (
    "No content could be extracted from this page. It is recorded so the page numbering "
    "stays continuous, and is not drawn on when the lecture is written."
)


async def read_page(state: PageToRead, runtime: Runtime[GraphRuntime]) -> dict[str, object]:
    """Reads one page, falling back to a placeholder once attempts run out."""
    page = state
    page_model = runtime.context.page_model
    if page_model is None:
        raise PipelineError.terminal("page_model is required when documents are supplied")
    prompts = runtime.context.prompts
    system_prompt = prompts.render(
        _SYSTEM_TEMPLATE,
        {
            "language_policy": prompts.render("language_policy"),
            "mathematics_notation_rules": prompts.render(_NOTATION_TEMPLATE),
        },
    )
    user_prompt = prompts.render(
        _USER_TEMPLATE,
        {
            "document": {
                "file_name": page.file_name,
                "index": page.document_index,
                "page_number": page.page_number,
            }
        },
    )

    accumulated_usage: dict[str, LanguageModelUsage] = {}
    maximum_attempts = max(1, runtime.context.page_attempts)

    for attempt_number in range(1, maximum_attempts + 1):
        try:
            answer = await call_chat_model(
                page_model,
                [
                    SystemMessage(system_prompt),
                    HumanMessage(
                        content=[
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": page.image_data_url},
                            },
                        ]
                    ),
                ],
                metadata={
                    "document_index": page.document_index,
                    "page_number": page.page_number,
                    "attempt_number": attempt_number,
                },
            )
            accumulated_usage = _combine(accumulated_usage, answer.usage_by_model)
            summary, details = _read_sections(answer.text)
        except PipelineError as error:
            accumulated_usage = _combine(accumulated_usage, getattr(error, "usage_by_model", {}))
            if not classify_retryable(error) or attempt_number == maximum_attempts:
                logger.warning(
                    "page could not be read, staging a placeholder",
                    document_index=page.document_index,
                    page_number=page.page_number,
                    attempt_number=attempt_number,
                    error_message=str(error),
                    error_metadata=error.metadata,
                )
                return _staged(page, accumulated_usage, was_extracted=False)
            logger.info(
                "page documents attempt failed, trying again",
                document_index=page.document_index,
                page_number=page.page_number,
                attempt_number=attempt_number,
                error_message=str(error),
            )
            continue

        logger.info(
            "page read",
            document_index=page.document_index,
            page_number=page.page_number,
            attempt_number=attempt_number,
            summary_character_count=len(summary),
            details_character_count=len(details),
        )
        return {
            "staged_pages": [
                StagedPage(
                    document_index=page.document_index,
                    page_number=page.page_number,
                    summary=summary,
                    details=details,
                    was_extracted=True,
                )
            ],
            "usage_by_model": accumulated_usage,
        }

    return _staged(page, accumulated_usage, was_extracted=False)


def _staged(
    page: PageToRead,
    usage: dict[str, LanguageModelUsage],
    *,
    was_extracted: bool,
) -> dict[str, object]:
    """Builds the update for a page that could not be read."""
    return {
        "staged_pages": [
            StagedPage(
                document_index=page.document_index,
                page_number=page.page_number,
                summary=_UNREADABLE_SUMMARY,
                details=_UNREADABLE_DETAILS,
                was_extracted=was_extracted,
            )
        ],
        "usage_by_model": usage,
    }


def _combine(
    accumulated: dict[str, LanguageModelUsage], incoming: Any
) -> dict[str, LanguageModelUsage]:
    """Adds one attempt's usage to what earlier attempts consumed."""
    combined = dict(accumulated)
    for model_name, usage in (incoming or {}).items():
        present = combined.get(model_name)
        combined[model_name] = usage if present is None else present.combined_with(usage)
    return combined


def _read_sections(answer_text: str) -> tuple[str, str]:
    """Splits the answer into its summary and its details."""
    content = answer_text.strip()
    if not content:
        raise PipelineError.retryable("the page documents is empty")

    headings = list(re.finditer(r"^(#{1,6})[ \t]+.+?[ \t]*$", content, re.MULTILINE))
    if len(headings) < 2:
        raise PipelineError.retryable(
            "the page documents carries fewer than two headings",
            {"heading_count": len(headings)},
        )

    depths = [len(match.group(1)) for match in headings]
    shallowest_depth = min(depths)
    section_positions = [match for match, depth in zip(headings, depths, strict=True) if depth == shallowest_depth]
    if len(section_positions) != 2:
        raise PipelineError.retryable(
            "the page documents does not carry exactly two sections",
            {
                "section_count": len(section_positions),
                "shallowest_depth": shallowest_depth,
            },
        )

    summary_start, details_start = section_positions
    summary = content[summary_start.end() : details_start.start()].strip()
    details = content[details_start.end() :].strip()

    if not summary:
        raise PipelineError.retryable("the page documents has an empty summary")
    if not details:
        raise PipelineError.retryable("the page documents has empty details")
    return summary, details
