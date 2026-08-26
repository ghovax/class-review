"""Progress events the graphs emit as they run."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from teacher.models import Chapter, LessonPlan

__all__ = [
    "ChapterCompleted",
    "ChapterStarted",
    "DocumentRead",
    "GlossaryDistilled",
    "LessonAssembled",
    "PlanCreated",
    "PipelineEvent",
    "PipelineStage",
    "StageChanged",
    "TranscriptAssembled",
]


class PipelineStage(StrEnum):
    """The coarse phases a caller reports to a reader waiting on a run."""

    TRANSCRIBING_RECORDINGS = "transcribing_recordings"
    CORRECTING_TRANSCRIPT = "correcting_transcript"
    READING_DOCUMENTS = "reading_documents"
    PLANNING_LESSON = "planning_lesson"
    WRITING_CHAPTERS = "writing_chapters"
    FINISHING_LESSON = "finishing_lesson"


@dataclass(frozen=True, slots=True)
class StageChanged:
    """The run entered a new phase."""

    stage: PipelineStage


@dataclass(frozen=True, slots=True)
class TranscriptAssembled:
    """Every correction batch settled and the transcript was reassembled."""

    segment_count: int
    duration_seconds: float


@dataclass(frozen=True, slots=True)
class DocumentRead:
    """One source document finished being read."""

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
    """The glossary was distilled from the finished chapters."""

    term_count: int


@dataclass(frozen=True, slots=True)
class LessonAssembled:
    """The lecture was assembled and the run is finished."""

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
