"""Checkpointed state for the single end-to-end graph."""

from __future__ import annotations

import operator
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from models_provider import ModelUsage
from typing import Annotated, TypedDict

from teacher.models import (
    Citation,
    Document,
    DocumentSource,
    GlossaryEntry,
    Lesson,
    LessonPlan,
    SectionMap,
    SectionNotes,
    Terminology,
    Transcript,
    TranscriptSegment,
    normalize_sequence_fields,
)


def upsert_by[ItemType](
    index_field: str,
) -> Callable[[Sequence[ItemType], Sequence[ItemType]], list[ItemType]]:
    """Merge parallel graph writes by the field identifying each item."""

    def reduce(existing: Sequence[ItemType], incoming: Sequence[ItemType]) -> list[ItemType]:
        merged = {getattr(item, index_field): item for item in existing}
        for item in incoming:
            merged[getattr(item, index_field)] = item
        return sorted(merged.values(), key=lambda item: getattr(item, index_field))

    return reduce


def merge_usage_by_model(
    existing: Mapping[str, ModelUsage],
    incoming: Mapping[str, ModelUsage],
) -> dict[str, ModelUsage]:
    """Add usage emitted by parallel model calls."""

    merged = dict(existing)
    for model_name, usage in incoming.items():
        present = merged.get(model_name)
        merged[model_name] = usage if present is None else present.combined_with(usage)
    return merged


@normalize_sequence_fields
@dataclass(frozen=True, slots=True)
class ChapterDraft:
    """One generated chapter before final assembly."""

    chapter_index: int
    title: str | None
    content: str
    citations: tuple[Citation, ...]


@dataclass(frozen=True, slots=True)
class ChapterAnswer:
    """One generated chapter answer retained for continuity."""

    chapter_index: int
    content: str


@dataclass(frozen=True, slots=True)
class DocumentPageReading:
    """What one page-reading request produced."""

    document_index: int
    page_number: int
    summary: str | None
    details: str | None


class LessonInput(TypedDict):
    """Material and output language supplied for a run."""

    transcript: Transcript
    sources: list[DocumentSource]
    output_language: str


class LessonOutput(TypedDict):
    """The generated lesson and measured model usage."""

    lesson: Lesson | None
    usage_by_model: Annotated[dict[str, ModelUsage], merge_usage_by_model]


class LessonState(LessonInput, total=False):
    """Every value persisted while the graph runs."""

    terminology: Terminology
    clean_transcript: Annotated[list[TranscriptSegment], operator.add]
    documents: Annotated[list[Document], upsert_by("document_index")]
    page_readings: Annotated[list[DocumentPageReading], operator.add]
    section_map: SectionMap | None
    section_notes: list[SectionNotes]
    plan: LessonPlan | None
    chapter_drafts: Annotated[list[ChapterDraft], upsert_by("chapter_index")]
    chapter_answers: Annotated[list[ChapterAnswer], upsert_by("chapter_index")]
    glossary: list[GlossaryEntry]
    lesson: Lesson | None
    usage_by_model: Annotated[dict[str, ModelUsage], merge_usage_by_model]
