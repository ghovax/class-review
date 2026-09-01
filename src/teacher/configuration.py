"""Configuration shared by independent lesson-writing operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

from langchain_core.messages import BaseMessage

from teacher.prompts import Prompts


class ChatModel(Protocol):
    async def ainvoke(self, messages: Sequence[BaseMessage]) -> Any: ...


@dataclass(frozen=True, slots=True)
class ModelsConfiguration:
    text: ChatModel
    vision: ChatModel | None = None

    def __post_init__(self) -> None:
        if self.text is None:
            raise ValueError("a text model is required")


@dataclass(frozen=True, slots=True)
class RetryConfiguration:
    model_attempts: int = 3
    page_attempts: int = 3


@dataclass(frozen=True, slots=True)
class TranscriptConfiguration:
    maximum_request_seconds: float = 1800.0
    zero_duration_seconds: float = 1e-6
    timestamp_decimals: int = 1


@dataclass(frozen=True, slots=True)
class LessonConfiguration:
    chapter_context_margin_seconds: float = 45.0
    maximum_chapter_context_seconds: float = 600.0
    maximum_plan_request_characters: int = 400_000
    maximum_model_seconds: float = 86_400.0
    glossary_key_length: int = 10


@dataclass(frozen=True, slots=True)
class OperationConfiguration:
    models: ModelsConfiguration
    prompts: Prompts = field(default_factory=Prompts)
    retries: RetryConfiguration = field(default_factory=RetryConfiguration)
    transcript: TranscriptConfiguration = field(default_factory=TranscriptConfiguration)
    lesson: LessonConfiguration = field(default_factory=LessonConfiguration)
