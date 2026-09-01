"""Framework-independent values exchanged by lesson-writing operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import re
from typing import Any, Self


class ConceptIntent(StrEnum):
    INTRODUCE = "Introduce"
    DEEPEN = "Deepen"
    APPLY = "Apply"
    REVIEW = "Review"


class ProgressionAxis(StrEnum):
    MECHANISM = "Mechanism"
    CONSTRAINT = "Constraint"
    TRADEOFF = "Tradeoff"
    EVIDENCE = "Evidence"


class ExplanationDepth(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    start_seconds: float
    end_seconds: float
    content: str

    def __post_init__(self) -> None:
        if self.start_seconds < 0 or self.end_seconds < self.start_seconds:
            raise ValueError("transcript timestamps are invalid")
        if not self.content.strip():
            raise ValueError("transcript segment content cannot be empty")


@dataclass(frozen=True, slots=True)
class Transcript:
    segments: tuple[TranscriptSegment, ...]
    languages: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.segments:
            raise ValueError("transcript must contain at least one segment")
        if not self.languages or any(not language.strip() for language in self.languages):
            raise ValueError("transcript must contain at least one language")
        if any(
            current.start_seconds < previous.start_seconds
            for previous, current in zip(self.segments, self.segments[1:], strict=False)
        ):
            raise ValueError("transcript segments must be ordered")


@dataclass(frozen=True, slots=True)
class ReferenceDocument:
    content: bytes
    file_name: str | None = None

    @classmethod
    def from_path(cls, path: str | Path, *, file_name: str | None = None) -> Self:
        source = Path(path)
        return cls(source.read_bytes(), file_name or source.name)

    def __post_init__(self) -> None:
        if not isinstance(self.content, bytes) or not self.content:
            raise ValueError("reference document content must be non-empty bytes")
        if self.file_name is not None and not self.file_name.strip():
            raise ValueError("reference document file name cannot be blank")


@dataclass(frozen=True, slots=True)
class ReferencePage:
    page_number: int
    summary: str | None
    details: str | None


@dataclass(frozen=True, slots=True)
class Reference:
    document_index: int
    file_name: str
    pages: tuple[ReferencePage, ...]


@dataclass(frozen=True, slots=True)
class ReferenceSection:
    section_index: int
    start_page: int
    end_page: int
    title: str
    description: str


@dataclass(frozen=True, slots=True)
class ReferenceSections:
    document_index: int
    file_name: str
    sections: tuple[ReferenceSection, ...]


@dataclass(frozen=True, slots=True)
class ReferenceNote:
    document_index: int
    section_index: int
    content: str


@dataclass(frozen=True, slots=True)
class ReferenceMaterial:
    documents: tuple[Reference, ...]
    sections: tuple[ReferenceSections, ...] = ()
    notes: tuple[ReferenceNote, ...] = ()


@dataclass(frozen=True, slots=True)
class LessonMaterials:
    transcript: Transcript
    references: ReferenceMaterial
    language: str

    def __post_init__(self) -> None:
        if not self.language.strip():
            raise ValueError("lesson language cannot be empty")


@dataclass(frozen=True, slots=True)
class TimeSpan:
    start_seconds: float
    end_seconds: float


@dataclass(frozen=True, slots=True)
class ConceptDocumentSpan:
    document_index: int
    section_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Concept:
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


@dataclass(frozen=True, slots=True)
class ChapterOutline:
    title: str
    concepts: tuple[Concept, ...]


@dataclass(frozen=True, slots=True)
class LessonOutline:
    title: str
    description: str
    chapters: tuple[ChapterOutline, ...]


@dataclass(frozen=True, slots=True)
class Citation:
    number: int
    content: str
    document_index: int
    page_number: int


@dataclass(frozen=True, slots=True)
class GlossaryEntry:
    key: str
    short_form: str
    description: str
    long_form: str | None = None


@dataclass(frozen=True, slots=True)
class GlossaryLink:
    key: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class Chapter:
    title: str
    content: str
    concepts: tuple[Concept, ...]
    citations: tuple[Citation, ...] = ()
    glossary_links: tuple[GlossaryLink, ...] = ()


@dataclass(frozen=True, slots=True)
class Lesson:
    title: str
    description: str
    chapters: tuple[Chapter, ...]
    glossary: tuple[GlossaryEntry, ...] = ()

    def export(self, format: str, *, metadata: Any = None) -> bytes:
        """Render this lesson as the requested representation."""
        from teacher.outputs import _export_to_bytes

        return _export_to_bytes(self, format=format, metadata=metadata)

    @classmethod
    def from_parts(
        cls,
        *,
        outline: LessonOutline,
        chapters: tuple[Chapter, ...],
        glossary: tuple[GlossaryEntry, ...] = (),
    ) -> Self:
        if len(chapters) != len(outline.chapters):
            raise ValueError("the number of chapters must match the outline")
        for index, (chapter, proposed) in enumerate(zip(chapters, outline.chapters, strict=True)):
            if chapter.concepts != proposed.concepts:
                raise ValueError(f"chapter {index} concepts do not match the outline")
        return cls(
            outline.title,
            outline.description,
            _link_chapters(_number_citations(chapters), glossary),
            glossary,
        )


def _link_chapters(
    chapters: tuple[Chapter, ...], glossary: tuple[GlossaryEntry, ...]
) -> tuple[Chapter, ...]:
    """Link the first occurrence of each glossary term across the lesson."""
    remaining = {entry.key for entry in glossary}
    linked: list[Chapter] = []
    for chapter in chapters:
        links: list[GlossaryLink] = []
        for entry in glossary:
            if entry.key not in remaining:
                continue
            match = re.search(
                rf"(?<!\w){re.escape(entry.short_form)}(?!\w)", chapter.content, re.IGNORECASE
            )
            if match is not None:
                links.append(GlossaryLink(entry.key, match.start(), match.end()))
                remaining.remove(entry.key)
        linked.append(
            Chapter(
                chapter.title, chapter.content, chapter.concepts, chapter.citations, tuple(links)
            )
        )
    return tuple(linked)


def _number_citations(chapters: tuple[Chapter, ...]) -> tuple[Chapter, ...]:
    """Give citations one stable number across all chapters."""
    offset = 0
    result: list[Chapter] = []
    for chapter in chapters:
        numbers = {citation.number: citation.number + offset for citation in chapter.citations}
        content = re.sub(
            r"\[\^([^\]]+)\]",
            lambda match, numbers=numbers: (
                f"[^{numbers.get(int(match.group(1)), match.group(1))}]"
                if match.group(1).isdigit()
                else match.group(0)
            ),
            chapter.content,
        )
        citations = tuple(
            Citation(
                number + offset, citation.content, citation.document_index, citation.page_number
            )
            for number, citation in ((item.number, item) for item in chapter.citations)
        )
        result.append(
            Chapter(chapter.title, content, chapter.concepts, citations, chapter.glossary_links)
        )
        offset += len(citations)
    return tuple(result)


def _number_citations(chapters: tuple[Chapter, ...]) -> tuple[Chapter, ...]:
    """Give citations one stable number across all chapters."""
    offset = 0
    result: list[Chapter] = []
    for chapter in chapters:
        numbers = {citation.number: citation.number + offset for citation in chapter.citations}
        content = re.sub(
            r"\[\^([^\]]+)\]",
            lambda match, numbers=numbers: (
                f"[^{numbers.get(int(match.group(1)), match.group(1))}]"
                if match.group(1).isdigit()
                else match.group(0)
            ),
            chapter.content,
        )
        citations = tuple(
            Citation(
                number + offset, citation.content, citation.document_index, citation.page_number
            )
            for number, citation in ((item.number, item) for item in chapter.citations)
        )
        result.append(
            Chapter(chapter.title, content, chapter.concepts, citations, chapter.glossary_links)
        )
        offset += len(citations)
    return tuple(result)
