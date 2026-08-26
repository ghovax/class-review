"""Consolidated Teacher implementation."""
from __future__ import annotations

from dataclasses import dataclass
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
class GraphConfiguration:
    """Models, provider, storage, and bounded graph settings."""

    language_model: ModelConfiguration
    checkpoint_path: Path
    model_provider: ModelProvider
    page_language_model: ModelConfiguration | None = None
    document_reader: DocumentReader | None = None
    prompts: Prompts = Prompts()
    model_attempts: int = 3
    page_attempts: int = 3
    maximum_transcript_seconds_per_request: float = 1800.0
    chapter_context_margin_seconds: float = 45.0
    maximum_chapter_context_seconds: float = 600.0
    zero_duration_seconds: float = 1e-6
    maximum_plan_request_characters: int = 400_000
    maximum_model_index: int = 10_000
    maximum_model_seconds: float = 86_400.0
    transcript_timestamp_decimals: int = 1
    glossary_key_length: int = 10
    recursion_limit: int = 200

    def runtime(self) -> GraphRuntime:
        """Resolve provider models and immutable settings for one run."""

        return GraphRuntime(
            text_model=self.model_provider.create(
                self.language_model,
            ),
            page_model=(
                self.model_provider.create(
                    self.page_language_model,
                )
                if self.page_language_model is not None
                else None
            ),
            document_reader=self.document_reader,
            prompts=self.prompts,
            model_attempts=self.model_attempts,
            page_attempts=self.page_attempts,
            maximum_transcript_seconds_per_request=self.maximum_transcript_seconds_per_request,
            chapter_context_margin_seconds=self.chapter_context_margin_seconds,
            maximum_chapter_context_seconds=self.maximum_chapter_context_seconds,
            zero_duration_seconds=self.zero_duration_seconds,
            maximum_plan_request_characters=self.maximum_plan_request_characters,
            maximum_model_index=self.maximum_model_index,
            maximum_model_seconds=self.maximum_model_seconds,
            transcript_timestamp_decimals=self.transcript_timestamp_decimals,
            glossary_key_length=self.glossary_key_length,
            recursion_limit=self.recursion_limit,
        )

@dataclass(frozen=True, slots=True)
class GraphRuntime:
    """Resolved models and settings passed between graph nodes."""

    text_model: BaseChatModel
    page_model: BaseChatModel | None
    document_reader: DocumentReader | None
    prompts: Prompts
    model_attempts: int
    page_attempts: int
    maximum_transcript_seconds_per_request: float
    chapter_context_margin_seconds: float
    maximum_chapter_context_seconds: float
    zero_duration_seconds: float
    maximum_plan_request_characters: int
    maximum_model_index: int
    maximum_model_seconds: float
    transcript_timestamp_decimals: int
    glossary_key_length: int
    recursion_limit: int

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
