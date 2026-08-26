"""Consolidated Teacher implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from models_provider import ModelConfiguration, ModelProvider
from pathlib import Path
from teacher.models import DocumentReader
from teacher.prompts import Prompts
from typing import Final

"""Graph configuration, resolved runtime values, and checkpoint serialization."""

"""Configuration for one lesson graph."""


@dataclass(frozen=True, slots=True)
class GraphModels:
    """Models and provider used by the graph."""

    language: ModelConfiguration
    provider: ModelProvider
    page: ModelConfiguration | None = None


@dataclass(frozen=True, slots=True)
class GraphInputs:
    """Caller-supplied readers and model-facing prompt resources."""

    document_reader: DocumentReader | None = None
    prompts: Prompts = field(default_factory=Prompts)


@dataclass(frozen=True, slots=True)
class GraphStorage:
    """Persistent storage used by one graph instance."""

    checkpoint_path: Path


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Retry limits for ordinary and document-page model calls."""

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
class ResolvedModels:
    """Provider-created models passed between graph nodes."""

    text: BaseChatModel
    page: BaseChatModel | None


@dataclass(frozen=True, slots=True)
class GraphConfiguration:
    """Structured models, inputs, storage, policies, and execution limits."""

    models: GraphModels
    storage: GraphStorage
    inputs: GraphInputs = field(default_factory=GraphInputs)
    retries: RetryPolicy = field(default_factory=RetryPolicy)
    transcript: TranscriptPolicy = field(default_factory=TranscriptPolicy)
    lesson: LessonPolicy = field(default_factory=LessonPolicy)
    execution: ExecutionPolicy = field(default_factory=ExecutionPolicy)

    def runtime(self) -> GraphRuntime:
        """Resolve provider models and immutable settings for one run."""

        return GraphRuntime(
            models=ResolvedModels(
                text=self.models.provider.create(self.models.language),
                page=(
                    self.models.provider.create(self.models.page)
                    if self.models.page is not None
                    else None
                ),
            ),
            inputs=self.inputs,
            retries=self.retries,
            transcript=self.transcript,
            lesson=self.lesson,
            execution=self.execution,
        )


@dataclass(frozen=True, slots=True)
class GraphRuntime:
    """Resolved models and grouped policies passed between graph nodes."""

    models: ResolvedModels
    inputs: GraphInputs
    retries: RetryPolicy
    transcript: TranscriptPolicy
    lesson: LessonPolicy
    execution: ExecutionPolicy


"""Checkpoint serialization for teacher's persisted values."""


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
    """Build a serializer that restores every persisted teacher type."""

    return JsonPlusSerializer(allowed_msgpack_modules=list(PERSISTED_TYPES))
