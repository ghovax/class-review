"""Consolidated Teacher implementation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
import dataclasses

"""Domain values, graph input/output contracts, and emitted events."""

"""Domain types shared across the transcript, documents, and lesson graphs."""


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

    def __post_init__(self) -> None:
        if not self.url.strip():
            raise ValueError("recording url cannot be empty")
        if self.index < 0:
            raise ValueError("recording index cannot be negative")


@dataclass(frozen=True, slots=True)
class DocumentSource:
    """One supplementary document supplied as bytes by the caller."""

    content: bytes
    file_name: str | None = None

    @classmethod
    def from_path(cls, path: str | Path, *, file_name: str | None = None) -> "DocumentSource":
        """Read a local document once and keep only its bytes and display name."""
        source_path = Path(path)
        return cls(
            content=source_path.read_bytes(),
            file_name=source_path.name if file_name is None else file_name,
        )

    def __post_init__(self) -> None:
        if not isinstance(self.content, bytes):
            raise TypeError("document source content must be bytes")
        if not self.content:
            raise ValueError("document source content cannot be empty")
        if self.file_name is not None and not self.file_name.strip():
            raise ValueError("document source file name cannot be empty when provided")


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    """One span of transcribed speech."""

    start_seconds: float
    end_seconds: float
    content: str

    def __post_init__(self) -> None:
        if self.start_seconds < 0 or self.end_seconds < 0:
            raise ValueError("transcript timestamps cannot be negative")
        if self.end_seconds < self.start_seconds:
            raise ValueError("transcript end timestamp cannot precede its start")
        if not self.content.strip():
            raise ValueError("transcript segment content cannot be empty")


@normalize_sequence_fields
@dataclass(frozen=True, slots=True)
class TerminologyHeard:
    """Recognized forms associated with one canonical term."""

    variants: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.variants or any(not variant.strip() for variant in self.variants):
            raise ValueError("terminology variants cannot be empty")


@dataclass(frozen=True, slots=True)
class TerminologyTerm:
    """One canonical term and the forms heard in the transcript."""

    canonical: str
    heard: TerminologyHeard
    kind: str

    def __post_init__(self) -> None:
        if not self.canonical.strip():
            raise ValueError("canonical terminology cannot be empty")
        if not self.kind.strip():
            raise ValueError("terminology kind cannot be empty")


@normalize_sequence_fields
@dataclass(frozen=True, slots=True)
class Terminology:
    """The parsed terminology shared by transcript correction."""

    terms: tuple[TerminologyTerm, ...]


@normalize_sequence_fields
@dataclass(frozen=True, slots=True)
class Transcript:
    """A timestamped transcript and the languages spoken in it."""

    segments: tuple[TranscriptSegment, ...]
    languages: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.segments:
            raise ValueError("transcript must contain at least one segment")
        if not self.languages or any(not language.strip() for language in self.languages):
            raise ValueError("transcript must contain at least one language")
        for previous_segment, current_segment in zip(
            self.segments, self.segments[1:], strict=False
        ):
            if current_segment.start_seconds < previous_segment.start_seconds:
                raise ValueError("transcript segments must be ordered by start timestamp")


@dataclass(frozen=True, slots=True)
class RenderedPage:
    """One page of a document rendered to an image."""

    page_number: int
    image_data_url: str


@dataclass(frozen=True, slots=True)
class DocumentPage:
    """What was read from one page of a document."""

    page_number: int
    summary: str | None
    details: str | None


@normalize_sequence_fields
@dataclass(frozen=True, slots=True)
class Document:
    """One source document after every page has been read."""

    document_index: int
    file_name: str
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
    """One term distilled from the completed lecture."""

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
    """One completed chapter."""

    title: str
    content: str
    concepts: tuple[Concept, ...]
    citations: tuple[Citation, ...] = ()
    glossary_links: tuple[GlossaryLink, ...] = ()


@normalize_sequence_fields
@dataclass(frozen=True, slots=True)
class Lesson:
    """The completed artifact."""

    title: str
    description: str
    chapters: tuple[Chapter, ...]
    glossary: tuple[GlossaryEntry, ...] = ()


"""Interfaces for transcript and document input."""


@dataclass(frozen=True, slots=True)
class DocumentPages:
    """Rendered pages produced from one document source."""

    document_index: int
    file_name: str
    pages: tuple[RenderedPage, ...]


@runtime_checkable
class DocumentDecoder(Protocol):
    """Turns document bytes into page images."""

    async def read(self, source: DocumentSource, *, document_index: int) -> DocumentPages: ...


"""Progress events the graphs emit as they run."""


class PipelineStage(StrEnum):
    """The coarse phases a caller reports to a reader waiting on a run."""

    TRANSCRIBING_RECORDINGS = "transcribing_recordings"
    CORRECTING_TRANSCRIPT = "correcting_transcript"
    READING_DOCUMENTS = "reading_documents"
    PLANNING_LESSON = "planning_lesson"
    WRITING_CHAPTERS = "writing_chapters"
    ASSEMBLING_LESSON = "assembling_lesson"


@dataclass(frozen=True, slots=True)
class StageChanged:
    """The run entered a new phase."""

    stage: PipelineStage


@dataclass(frozen=True, slots=True)
class TranscriptAssembled:
    """All transcript corrections settled and the transcript was reassembled."""

    segment_count: int
    duration_seconds: float


@dataclass(frozen=True, slots=True)
class DocumentRead:
    """One source document after reading."""

    document_index: int
    file_name: str
    page_count: int
    unreadable_page_count: int


@dataclass(frozen=True, slots=True)
class PlanCreated:
    """The plan was produced and verified."""

    plan: LessonPlan


@dataclass(frozen=True, slots=True)
class ChapterStarted:
    """A chapter began being written."""

    chapter_index: int
    title: str
    total_chapters: int


@dataclass(frozen=True, slots=True)
class ChapterCompleted:
    """A chapter was written and committed."""

    chapter_index: int
    title: str
    citation_count: int
    total_chapters: int


@dataclass(frozen=True, slots=True)
class GlossaryDistilled:
    """The glossary was distilled from the completed chapters."""

    term_count: int


@dataclass(frozen=True, slots=True)
class LessonAssembled:
    """The lecture was assembled and the run is complete."""

    title: str
    chapters: tuple[Chapter, ...]


# Every event a graph may emit.
type PipelineEvent = (
    StageChanged
    | TranscriptAssembled
    | DocumentRead
    | PlanCreated
    | ChapterStarted
    | ChapterCompleted
    | GlossaryDistilled
    | LessonAssembled
)
