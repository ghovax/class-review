"""Small settings shared by independent lesson-writing operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from langchain_core.messages import BaseMessage


class ChatModel(Protocol):
    """The small model interface required from a model provider."""

    async def ainvoke(self, messages: Sequence[BaseMessage]) -> Any: ...


@dataclass(frozen=True, slots=True)
class RetryConfiguration:
    """Retry counts for callers that choose to retry operation failures."""

    model_attempts: int = 3
    page_attempts: int = 3


@dataclass(frozen=True, slots=True)
class TranscriptConfiguration:
    """Limits used while revising transcript material."""

    maximum_request_seconds: float = 1800.0
    zero_duration_seconds: float = 1e-6
    timestamp_decimals: int = 1


@dataclass(frozen=True, slots=True)
class LessonConfiguration:
    """Limits used while outlining and writing a lesson."""

    chapter_context_margin_seconds: float = 45.0
    maximum_chapter_context_seconds: float = 600.0
    maximum_plan_request_characters: int = 400_000
    maximum_model_seconds: float = 86_400.0
    glossary_key_length: int = 10
