"""Small runtime values shared by Teacher's graph nodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from teacher.prompts import Prompts


@dataclass(frozen=True, slots=True)
class ModelSelection:
    """The models assigned to Teacher's two content modalities."""

    text: BaseChatModel
    vision: BaseChatModel | None = None

    def __post_init__(self) -> None:
        if self.text is None:
            raise ValueError("text model is required")

@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Retry limits for model calls."""

    model_attempts: int = 3
    page_attempts: int = 3


@dataclass(frozen=True, slots=True)
class TranscriptPolicy:
    """Limits and timestamp rules for transcript processing."""

    maximum_request_seconds: float = 1800.0
    zero_duration_seconds: float = 1e-6
    timestamp_decimals: int = 1


@dataclass(frozen=True, slots=True)
class LessonPolicy:
    """Context and validation limits for lesson authoring."""

    chapter_context_margin_seconds: float = 45.0
    maximum_chapter_context_seconds: float = 600.0
    maximum_plan_request_characters: int = 400_000
    maximum_model_index: int = 10_000
    maximum_model_seconds: float = 86_400.0
    glossary_key_length: int = 10


@dataclass(frozen=True, slots=True)
class ExecutionPolicy:
    """Graph execution limits."""

    recursion_limit: int = 200


@dataclass(frozen=True, slots=True)
class GraphRuntime:
    """Resolved values passed to graph nodes."""

    models: ModelSelection
    prompts: Prompts = field(default_factory=Prompts)
    retries: RetryPolicy = field(default_factory=RetryPolicy)
    transcript: TranscriptPolicy = field(default_factory=TranscriptPolicy)
    lesson: LessonPolicy = field(default_factory=LessonPolicy)
    execution: ExecutionPolicy = field(default_factory=ExecutionPolicy)


PERSISTED_TYPES: Final[tuple[tuple[str, str], ...]] = (
    ("teacher.models", "Recording"),
    ("teacher.models", "DocumentSource"),
    ("teacher.models", "TranscriptSegment"),
    ("teacher.models", "Transcript"),
    ("teacher.models", "Terminology"),
    ("teacher.models", "TerminologyTerm"),
    ("teacher.models", "TerminologyHeard"),
    ("teacher.models", "RenderedPage"),
    ("teacher.models", "DocumentPage"),
    ("teacher.models", "Document"),
    ("teacher.models", "DocumentSection"),
    ("teacher.models", "DocumentSections"),
    ("teacher.models", "SectionMap"),
    ("teacher.models", "SectionNotes"),
    ("teacher.models", "TimeSpan"),
    ("teacher.models", "ConceptDocumentSpan"),
    ("teacher.models", "Concept"),
    ("teacher.models", "PlannedChapter"),
    ("teacher.models", "LessonPlan"),
    ("teacher.models", "Citation"),
    ("teacher.models", "GlossaryEntry"),
    ("teacher.models", "GlossaryLink"),
    ("teacher.models", "Chapter"),
    ("teacher.models", "Lesson"),
    ("models_provider.core", "ModelUsage"),
    ("teacher.models", "ConceptIntent"),
    ("teacher.models", "ProgressionAxis"),
    ("teacher.models", "ExplanationDepth"),
    ("teacher.state", "ChapterDraft"),
    ("teacher.state", "ChapterAnswer"),
    ("teacher.state", "DocumentPageReading"),
)


def build_serializer() -> JsonPlusSerializer:
    """Build a serializer that restores every persisted Teacher type."""

    return JsonPlusSerializer(allowed_msgpack_modules=list(PERSISTED_TYPES))


__all__ = [
    "ExecutionPolicy",
    "GraphRuntime",
    "LessonPolicy",
    "ModelSelection",
    "RetryPolicy",
    "TranscriptPolicy",
    "build_serializer",
]
