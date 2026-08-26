"""Domain types shared across the transcript, documents, and lesson graphs."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


def normalize_sequence_fields[ValueType](cls: type[ValueType]) -> type[ValueType]:
    """Coerces every field declared as a tuple into one, on construction."""
    tuple_field_names = tuple(
        field_definition.name
        for field_definition in dataclasses.fields(cls)  # type: ignore[arg-type]
        if str(field_definition.type).replace(" ", "").startswith("tuple[")
    )
    if not tuple_field_names:
        return cls

    original_init = cls.__init__

    def __init__(self: Any, *arguments: Any, **keyword_arguments: Any) -> None:  # noqa: N807
        """Builds the value, then holds its sequence fields to their type."""
        original_init(self, *arguments, **keyword_arguments)
        for field_name in tuple_field_names:
            value = getattr(self, field_name)
            if not isinstance(value, tuple):
                object.__setattr__(self, field_name, tuple(value))

    cls.__init__ = __init__  # type: ignore[method-assign]
    return cls


__all__ = [
    "Citation",
    "Concept",
    "ConceptDocumentSpan",
    "ConceptIntent",
    "Document",
    "DocumentPage",
    "DocumentSection",
    "DocumentSections",
    "ExplanationDepth",
    "FetchedSource",
    "GlossaryEntry",
    "GlossaryLink",
    "LanguageModelUsage",
    "Lesson",
    "Chapter",
    "LessonPlan",
    "PlannedChapter",
    "ProgressionAxis",
    "Recording",
    "RenderedPage",
    "SectionMap",
    "SectionNotes",
    "DocumentSource",
    "SourceProbe",
    "TimeSpan",
    "TranscribedRecording",
    "TranscriptSegment",
    "Transcript",
    "normalize_sequence_fields",
]


class ConceptIntent(StrEnum):
    """The instructional purpose a concept serves within its chapter."""

    INTRODUCE = "Introduce"
    DEEPEN = "Deepen"
    APPLY = "Apply"
    REVIEW = "Review"


class ProgressionAxis(StrEnum):
    """The axis along which a concept must advance the reader's understanding."""

    MECHANISM = "Mechanism"
    CONSTRAINT = "Constraint"
    TRADEOFF = "Tradeoff"
    EVIDENCE = "Evidence"


class ExplanationDepth(StrEnum):
    """How much elaboration a concept warrants."""

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass(frozen=True, slots=True)
class Recording:
    """One audio recording supplied by the caller."""

    url: str
    index: int
    file_name: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentSource:
    """One supplementary document supplied by the caller."""

    url: str
    file_name: str | None = None


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    """One span of transcribed speech."""

    start_seconds: float
    end_seconds: float
    content: str


@normalize_sequence_fields
@dataclass(frozen=True, slots=True)
class Transcript:
    """A timestamped transcript and the languages spoken in it."""

    segments: tuple[TranscriptSegment, ...]
    languages: tuple[str, ...]


@normalize_sequence_fields
@dataclass(frozen=True, slots=True)
class TranscribedRecording:
    """One recording paired with the segments a transcriber produced for it."""

    url: str
    index: int
    segments: tuple[TranscriptSegment, ...]
    file_name: str | None = None


@dataclass(frozen=True, slots=True)
class FetchedSource:
    """The bytes of a downloaded source, with the metadata the download carried."""

    url: str
    content: bytes
    content_type: str | None = None
    file_name: str | None = None


@dataclass(frozen=True, slots=True)
class SourceProbe:
    """The outcome of checking a source without downloading its body."""

    url: str
    is_reachable: bool
    status_code: int | None = None
    content_type: str | None = None
    file_name: str | None = None


@dataclass(frozen=True, slots=True)
class RenderedPage:
    """One page of a document rendered to an image."""

    page_number: int
    image_data_url: str


@dataclass(frozen=True, slots=True)
class DocumentPage:
    """What was read from one page of a document."""

    page_number: int
    summary: str
    details: str


@normalize_sequence_fields
@dataclass(frozen=True, slots=True)
class Document:
    """One source document after every page has been read."""

    document_index: int
    file_name: str
    source_url: str
    pages: tuple[DocumentPage, ...]


@dataclass(frozen=True, slots=True)
class DocumentSection:
    """One semantic section spanning a run of pages within a document."""

    section_index: int
    start_page: int
    end_page: int
    title: str
    description: str


@normalize_sequence_fields
@dataclass(frozen=True, slots=True)
class DocumentSections:
    """The sections belonging to one document."""

    document_index: int
    file_name: str
    sections: tuple[DocumentSection, ...]


@normalize_sequence_fields
@dataclass(frozen=True, slots=True)
class SectionMap:
    """The section breakdown of every document, produced once and then frozen."""

    documents: tuple[DocumentSections, ...]


@dataclass(frozen=True, slots=True)
class SectionNotes:
    """One continuous explanation synthesised from every page in a section."""

    document_index: int
    section_index: int
    content: str


@dataclass(frozen=True, slots=True)
class TimeSpan:
    """A half-open span of the transcript timeline, in seconds."""

    start_seconds: float
    end_seconds: float


@normalize_sequence_fields
@dataclass(frozen=True, slots=True)
class ConceptDocumentSpan:
    """The document sections one concept draws on."""

    document_index: int
    section_indices: tuple[int, ...]


@normalize_sequence_fields
@dataclass(frozen=True, slots=True)
class Concept:
    """One teaching moment within a chapter, the atomic unit of the plan."""

    concept_index: int
    global_index: int
    topic_title: str
    learning_objective: str
    must_advance_by: ProgressionAxis
    intent: ConceptIntent
    explanation_depth: ExplanationDepth
    rationale: str
    transcript_span: TimeSpan
    establishes: str
    document_spans: tuple[ConceptDocumentSpan, ...] = ()


@normalize_sequence_fields
@dataclass(frozen=True, slots=True)
class PlannedChapter:
    """One chapter of the plan, before any prose has been written."""

    title: str
    concepts: tuple[Concept, ...]


@normalize_sequence_fields
@dataclass(frozen=True, slots=True)
class LessonPlan:
    """The plan the lesson branch writes against."""

    title: str
    description: str
    chapters: tuple[PlannedChapter, ...]


@dataclass(frozen=True, slots=True)
class Citation:
    """One inline citation pointing at a page of a source document."""

    number: int
    content: str
    document_index: int
    page_number: int


@dataclass(frozen=True, slots=True)
class GlossaryEntry:
    """One term distilled from the finished lecture."""

    key: str
    short_form: str
    description: str
    long_form: str | None = None


@dataclass(frozen=True, slots=True)
class GlossaryLink:
    """One authoritative in-body glossary link placement."""

    key: str
    start: int
    end: int


@normalize_sequence_fields
@dataclass(frozen=True, slots=True)
class Chapter:
    """One finished chapter."""

    title: str
    content: str
    concepts: tuple[Concept, ...]
    citations: tuple[Citation, ...] = ()
    glossary_links: tuple[GlossaryLink, ...] = ()


@normalize_sequence_fields
@dataclass(frozen=True, slots=True)
class Lesson:
    """The finished artifact."""

    title: str
    description: str
    chapters: tuple[Chapter, ...]
    glossary: tuple[GlossaryEntry, ...] = ()


@dataclass(frozen=True, slots=True)
class LanguageModelUsage:
    """Token counts and spend for one model, summed across a run."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0

    def combined_with(self, other: LanguageModelUsage) -> LanguageModelUsage:
        """Adds another usage record to this one."""
        return LanguageModelUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cached_tokens=self.cached_tokens + other.cached_tokens,
            cache_write_tokens=self.cache_write_tokens + other.cache_write_tokens,
            cost_usd=self.cost_usd + other.cost_usd,
        )
