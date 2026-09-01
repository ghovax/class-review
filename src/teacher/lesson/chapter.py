"""Write one lesson chapter from a typed outline and context."""

from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from lxml import etree

from teacher.interfaces import ChatModel
from teacher.lesson.context import build_chapter_context
from teacher.markdown import compose_markdown
from teacher.models import Chapter, ChapterOutline, Citation, LessonMaterials, ReferenceMaterial
from teacher.prompts import Prompts, get_prompts
from teacher.support import call_chat_model
from teacher.xml import build_xml_document


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

    async def write(self, outline: ChapterOutline, materials: LessonMaterials) -> Chapter:
        """Write one chapter using only the outline's bounded source context."""
        prompts = self.prompts
        context = build_chapter_context(
            chapter=outline,
            segments=materials.transcript.segments,
        )
        variables = {
            "language": materials.language,
            "mathematics_notation_rules": prompts.render(
                "shared_prompts/mathematics_notation_rules"
            ),
            "chapter": {
                "index": 0,
                "total": 1,
                "start_seconds": round(context.start_seconds, 1),
                "end_seconds": round(context.end_seconds, 1),
                "concept_count": len(outline.concepts),
                "previous_chapter_count": 0,
                "previous_concept_count": 0,
                "chapter_context_xml": _chapter_xml(outline),
                "covered_concepts_xml": build_xml_document("CoveredConcepts", {}),
                "do_not_repeat_ledger_xml": build_xml_document("ProhibitionLedger", {}),
                "document_pages_markdown": _chapter_references(outline, materials.references),
            },
            "transcript": {
                "excerpt_count": sum(len(item.excerpts) for item in context.concept_slices),
                "excerpts_xml": _context_xml(context),
            },
        }
        answer = await call_chat_model(
            self.text_model,
            [
                SystemMessage(
                    prompts.render(
                        "lesson/write_lesson_chapter/system",
                        {
                            "language": materials.language,
                            "language_policy": prompts.render("shared_prompts/language_policy"),
                            "xml_policy": prompts.render("shared_prompts/xml_policy"),
                            "mathematics_notation_rules": prompts.render(
                                "shared_prompts/mathematics_notation_rules"
                            ),
                        },
                    )
                ),
                HumanMessage(prompts.render("lesson/write_lesson_chapter/user", variables)),
            ],
        )
        title, content, citations = _read_chapter(answer.text)
        return Chapter(title or outline.title, content, outline.concepts, tuple(citations))


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
                }
                for item in outline.concepts
            ],
        },
    )


def _context_xml(context: Any) -> str:
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
    wanted = {
        (span.document_index, section)
        for concept in outline.concepts
        for span in concept.document_spans
        for section in span.section_indices
    }
    output = []
    for document in material.documents:
        for section_set in material.sections:
            if section_set.document_index != document.document_index:
                continue
            for section in section_set.sections:
                if (document.document_index, section.section_index) not in wanted:
                    continue
                output.append(f"## {section.title}\n{section.description}")
                output.extend(
                    page.details or ""
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
    return title, body, citations
