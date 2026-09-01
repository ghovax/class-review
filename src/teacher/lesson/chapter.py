"""Write one lesson chapter from a typed outline and context."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import re

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from lxml import etree

from teacher.interfaces import ChatModel
from teacher.lesson.context import ChapterContext, build_chapter_context
from teacher.markdown import compose_markdown
from teacher.models import (
    Chapter,
    ChapterOutline,
    Citation,
    Concept,
    LessonMaterials,
    ReferenceMaterial,
)
from teacher.prompts import Prompts, get_prompts
from teacher.support import ModelAnswer, OperationError, call_chat_model
from teacher.xml import build_xml_document


_MAX_MODEL_ATTEMPTS = 3


@dataclass(frozen=True, slots=True)
class ChapterWriting:
    """A parsed chapter together with the complete call that produced it."""

    chapter: Chapter
    model_answer: ModelAnswer


class ChapterWriter:
    """Writes one chapter from a chapter outline and the lesson materials."""

    def __init__(
        self,
        text_model: ChatModel,
        *,
        prompts: Prompts | None = None,
    ) -> None:
        self.text_model = text_model
        self.prompts = get_prompts(prompts)

    async def write(
        self,
        outline: ChapterOutline,
        materials: LessonMaterials,
        *,
        chapter_index: int = 1,
        total_chapters: int = 1,
        previous_chapter_count: int = 0,
        previous_concept_count: int = 0,
    ) -> Chapter:
        """Write one chapter using only the outline's bounded source context."""
        return (
            await self.write_with_trace(
                outline,
                materials,
                chapter_index=chapter_index,
                total_chapters=total_chapters,
                previous_chapter_count=previous_chapter_count,
                previous_concept_count=previous_concept_count,
            )
        ).chapter

    async def write_with_trace(
        self,
        outline: ChapterOutline,
        materials: LessonMaterials,
        *,
        chapter_index: int = 1,
        total_chapters: int = 1,
        previous_chapter_count: int = 0,
        previous_concept_count: int = 0,
    ) -> ChapterWriting:
        """Write one chapter and return its complete model exchange as well."""
        return await self._write(
            outline,
            materials,
            chapter_index=chapter_index,
            total_chapters=total_chapters,
            previous_chapter_count=previous_chapter_count,
            previous_concept_count=previous_concept_count,
        )

    async def _write(
        self,
        outline: ChapterOutline,
        materials: LessonMaterials,
        *,
        chapter_index: int,
        total_chapters: int,
        previous_chapter_count: int,
        previous_concept_count: int,
        previous_concepts: Sequence[Concept] = (),
        previous_answers: Sequence[ModelAnswer] = (),
        context: ChapterContext | None = None,
    ) -> ChapterWriting:
        """Write one chapter while retaining the complete model exchange."""
        if not 1 <= chapter_index <= total_chapters:
            raise ValueError("chapter_index must be between 1 and total_chapters")
        if previous_chapter_count < 0 or previous_concept_count < 0:
            raise ValueError("previous chapter and concept counts cannot be negative")
        prompts = self.prompts
        chapter_context = context or build_chapter_context(
            chapter=outline, segments=materials.transcript.segments
        )
        variables = {
            "language": materials.language,
            "mathematics_notation_rules": prompts.render(
                "shared_prompts/mathematics_notation_rules"
            ),
            "chapter": {
                "index": chapter_index,
                "total": total_chapters,
                "start_seconds": round(chapter_context.start_seconds, 1),
                "end_seconds": round(chapter_context.end_seconds, 1),
                "concept_count": len(outline.concepts),
                "previous_chapter_count": previous_chapter_count,
                "previous_concept_count": previous_concept_count,
                "chapter_context_xml": _chapter_xml(outline),
                "covered_concepts_xml": _covered_concepts_xml(previous_concepts),
                "do_not_repeat_ledger_xml": _prohibition_ledger_xml(previous_concepts),
                "document_pages_markdown": _chapter_references(outline, materials.references),
            },
            "transcript": {
                "excerpt_count": sum(len(item.excerpts) for item in chapter_context.concept_slices),
                "excerpts_xml": _context_xml(chapter_context),
            },
        }
        system_message = SystemMessage(
            prompts.render(
                "lesson/write_lesson_chapter/system",
                {
                    "language": materials.language,
                    "chapter": {"index": chapter_index, "total": total_chapters},
                    "language_policy": prompts.render("shared_prompts/language_policy"),
                    "mathematics_notation_rules": prompts.render(
                        "shared_prompts/mathematics_notation_rules"
                    ),
                },
            )
        )
        human_message = HumanMessage(prompts.render("lesson/write_lesson_chapter/user", variables))
        messages: list[BaseMessage] = [
            system_message,
            *(_previous_response(answer) for answer in previous_answers),
        ]
        messages.append(human_message)

        for attempt in range(_MAX_MODEL_ATTEMPTS):
            try:
                answer = await call_chat_model(
                    self.text_model,
                    messages,
                    metadata={"chapter_index": chapter_index, "attempt": attempt + 1},
                )
                title, content, citations = _read_chapter(answer.text)
                chapter = Chapter(
                    title or outline.title,
                    content,
                    outline.concepts,
                    tuple(citations),
                )
                return ChapterWriting(chapter=chapter, model_answer=answer)
            except OperationError as error:
                if not error.is_retryable or attempt + 1 >= _MAX_MODEL_ATTEMPTS:
                    raise

        raise AssertionError("chapter writing loop returned without a result")


def _chapter_xml(outline: ChapterOutline) -> str:
    return build_xml_document(
        "ChapterContext",
        {
            "Title": outline.title,
            "Concept": [
                {
                    "ConceptIndex": item.concept_index,
                    "GlobalIndex": item.global_index,
                    "TopicTitle": item.topic_title,
                    "LearningObjective": item.learning_objective,
                    "MustAdvanceBy": item.must_advance_by.value,
                    "Intent": item.intent.value,
                    "ExplanationDepth": item.explanation_depth.value,
                    "Rationale": item.rationale,
                    "Start": item.transcript_span.start_seconds,
                    "End": item.transcript_span.end_seconds,
                    "DoNotRepeat": item.establishes,
                    "DocumentSpan": [
                        {
                            "DocumentIndex": span.document_index,
                            "SectionIndex": list(span.section_indices),
                        }
                        for span in item.document_spans
                    ],
                }
                for item in outline.concepts
            ],
        },
    )


def _covered_concepts_xml(concepts: Sequence[Concept]) -> str:
    """Render the concepts whose material is already owned by earlier chapters."""
    return build_xml_document(
        "CoveredConcepts",
        {
            "Concept": [
                {
                    "ConceptIndex": concept.concept_index,
                    "GlobalIndex": concept.global_index,
                    "TopicTitle": concept.topic_title,
                    "LearningObjective": concept.learning_objective,
                    "MustAdvanceBy": concept.must_advance_by.value,
                    "Start": concept.transcript_span.start_seconds,
                    "End": concept.transcript_span.end_seconds,
                }
                for concept in concepts
            ]
        },
    )


def _prohibition_ledger_xml(concepts: Sequence[Concept]) -> str:
    """Render the claims earlier chapters established and later chapters avoid."""
    return build_xml_document(
        "ProhibitionLedger",
        {
            "Established": [
                {
                    "GlobalIndex": concept.global_index,
                    "TopicTitle": concept.topic_title,
                    "Statement": concept.establishes,
                }
                for concept in concepts
            ]
        },
    )


def _previous_response(answer: ModelAnswer) -> BaseMessage:
    """Carry the original assistant message, including provider metadata, forward."""
    if isinstance(answer.response, BaseMessage):
        return answer.response
    return AIMessage(content=answer.text)


def _context_xml(context: ChapterContext) -> str:
    return build_xml_document(
        "ConceptContexts",
        {
            "ConceptContext": [
                {
                    "ConceptIndex": item.concept_index,
                    "TopicTitle": item.topic_title,
                    "Excerpt": [
                        {
                            "Beginning": excerpt.start_seconds,
                            "End": excerpt.end_seconds,
                            "Content": excerpt.content,
                        }
                        for excerpt in item.excerpts
                    ],
                }
                for item in context.concept_slices
            ]
        },
    )


def _chapter_references(outline: ChapterOutline, material: ReferenceMaterial) -> str:
    documents = {document.document_index: document for document in material.documents}
    sections = {
        document.document_index: {section.section_index: section for section in document.sections}
        for document in material.sections
    }
    notes = {(note.document_index, note.section_index): note.content for note in material.notes}
    wanted = [
        (span.document_index, section_index)
        for concept in outline.concepts
        for span in concept.document_spans
        for section_index in span.section_indices
    ]

    output: list[str] = []
    rendered: set[tuple[int, int]] = set()
    for document_index, section_index in wanted:
        key = (document_index, section_index)
        if key in rendered:
            continue
        rendered.add(key)
        document = documents.get(document_index)
        section = sections.get(document_index, {}).get(section_index)
        if document is None or section is None:
            continue
        output.append(f"## {section.title}\n{section.description}")
        if note := notes.get(key):
            output.append(note)
        output.extend(
            "\n".join(
                part
                for part in (
                    f"### Page {page.page_number}",
                    page.summary or "",
                    page.details or "",
                )
                if part
            )
            for page in document.pages
            if section.start_page <= page.page_number <= section.end_page
        )
    return compose_markdown(output)


def _read_chapter(content: str) -> tuple[str | None, str, list[Citation]]:
    citations: list[Citation] = []

    def replace(match: re.Match[str]) -> str:
        try:
            element = etree.fromstring(
                match.group(0).encode("utf-8"), parser=etree.XMLParser(recover=True)
            )

            def text(name: str) -> str:
                child = element.find(name)
                return (
                    "" if child is None else "".join(str(part) for part in child.itertext()).strip()
                )

            citation = Citation(
                len(citations) + 1, text("Content"), int(text("DocumentIndex")), int(text("Page"))
            )
        except (ValueError, TypeError, etree.XMLSyntaxError):
            return match.group(0)
        citations.append(citation)
        return f" [^{citation.number}] "

    body = re.sub(
        r"<Citation>.*?</Citation>", replace, content.strip(), flags=re.DOTALL | re.IGNORECASE
    )
    match = re.match(r"^#{1}\s+(.+?)\s*$", body, re.MULTILINE)
    title = match.group(1).strip() if match else None
    if match:
        body = body[match.end() :].strip()
    if not body:
        raise OperationError.retryable("chapter output contains no prose")
    return title, body, citations
