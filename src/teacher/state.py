"""Checkpointed state for the single end-to-end graph."""

from __future__ import annotations

import operator
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, TypedDict

from teacher.models import (
    Citation,
    Document,
    DocumentSource,
    GlossaryEntry,
    LanguageModelUsage,
    Lesson,
    LessonPlan,
    SectionMap,
    SectionNotes,
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
    existing: Mapping[str, LanguageModelUsage],
    incoming: Mapping[str, LanguageModelUsage],
) -> dict[str, LanguageModelUsage]:
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
class ChapterExchange:
    """One chapter request and answer retained for continuity."""

    chapter_index: int
    request: str
    answer: str


@dataclass(frozen=True, slots=True)
class StagedPage:
    """One extracted page before document assembly."""

    document_index: int
    page_number: int
    summary: str
    details: str
    was_extracted: bool


class LessonInput(TypedDict):
    """Material and output language supplied for a run."""

    transcript: Transcript
    sources: list[DocumentSource]
    output_language: str


class LessonOutput(TypedDict):
    """The generated lesson and measured model usage."""

    lesson: Lesson | None
    usage_by_model: Annotated[dict[str, LanguageModelUsage], merge_usage_by_model]


class LessonState(LessonInput, total=False):
    """Every value persisted while the graph runs."""

    terminology: str
    clean_transcript: Annotated[list[TranscriptSegment], operator.add]
    documents: Annotated[list[Document], upsert_by("document_index")]
    staged_pages: Annotated[list[StagedPage], operator.add]
    section_map: SectionMap | None
    section_notes: list[SectionNotes]
    plan: LessonPlan | None
    chapter_drafts: Annotated[list[ChapterDraft], upsert_by("chapter_index")]
    chapter_exchanges: Annotated[list[ChapterExchange], upsert_by("chapter_index")]
    glossary: list[GlossaryEntry]
    lesson: Lesson | None
    usage_by_model: Annotated[dict[str, LanguageModelUsage], merge_usage_by_model]
