"""Checkpoint serialization for teacher's persisted values."""

from __future__ import annotations

from typing import Final

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

__all__ = ["PERSISTED_TYPES", "build_serializer"]

PERSISTED_TYPES: Final[tuple[tuple[str, str], ...]] = (
    ("teacher.models", "Recording"),
    ("teacher.models", "DocumentSource"),
    ("teacher.models", "TranscriptSegment"),
    ("teacher.models", "Transcript"),
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
    ("teacher.models", "LanguageModelUsage"),
    ("teacher.models", "ConceptIntent"),
    ("teacher.models", "ProgressionAxis"),
    ("teacher.models", "ExplanationDepth"),
    ("teacher.state", "ChapterDraft"),
    ("teacher.state", "ChapterExchange"),
    ("teacher.state", "StagedPage"),
)


def build_serializer() -> JsonPlusSerializer:
    """Build a serializer that restores every persisted teacher type."""

    return JsonPlusSerializer(allowed_msgpack_modules=list(PERSISTED_TYPES))
