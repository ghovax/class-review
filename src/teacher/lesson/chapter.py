"""Write and parse one lesson chapter."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime
from lxml import etree
from teacher.configuration import GraphRuntime
from teacher.models import (
    Concept,
    PlannedChapter,
    Citation,
    PipelineStage,
    StageChanged,
    LessonPlan,
    ChapterCompleted,
    ChapterStarted,
    Document,
    SectionMap,
)
from teacher.markdown import compose_markdown
from teacher.prompts import Prompts
from teacher.state import ChapterAnswer, ChapterDraft, LessonState
from teacher.documents.read_page import render_section_pages
from teacher.support import PipelineError, get_logger, call_chat_model
from teacher.xml import (
    build_xml_document,
)
import re

from teacher.lesson.context import build_chapter_context
from teacher.lesson.context import ChapterContext

_CITATION_PATTERN: re.Pattern[str] = re.compile(
    r"<Citation>.*?</Citation>", re.DOTALL | re.IGNORECASE
)
_HEADING_PATTERN: re.Pattern[str] = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$", re.MULTILINE)
_CHAPTER_SYSTEM_TEMPLATE = "lesson/write_lesson_chapter/system"
_CHAPTER_USER_TEMPLATE = "lesson/write_lesson_chapter/user"


@dataclass(frozen=True, slots=True)
class ChapterOutput:
    """The chapter prose and citations returned by one model call."""

    title: str | None
    content: str
    section_count: int
    citations: tuple[Citation, ...]


def read_chapter_output(
    *, raw_content: str, chapter_index: int, starting_citation_index: int
) -> ChapterOutput:
    """Remove citation envelopes and the optional outer chapter title line.

    The chapter body remains the model's original text.  Teacher deliberately does
    not build or round-trip a Markdown syntax tree; Markdown is an output format,
    not an internal data model.
    """
    del chapter_index
    content = raw_content.strip()
    if not content:
        raise PipelineError.retryable("chapter output is empty")

    citations: list[Citation] = []

    def replace(match: re.Match[str]) -> str:
        citation = _read_citation(
            match.group(0).strip(), starting_citation_index + len(citations) + 1
        )
        if citation is None:
            return match.group(0)
        citations.append(citation)
        return f" [^{citation.number}] "

    content = _CITATION_PATTERN.sub(replace, content)
    headings = list(_HEADING_PATTERN.finditer(content))
    title: str | None = None
    if headings and headings[0].start() == 0 and len(headings[0].group(1)) == 1:
        title = headings[0].group(2).strip() or None
        content = content[headings[0].end() :].lstrip()

    section_count = sum(
        1 for match in _HEADING_PATTERN.finditer(content) if len(match.group(1)) == 2
    )
    return ChapterOutput(
        title=title,
        content=content.strip(),
        section_count=section_count,
        citations=tuple(citations),
    )


def _read_citation(element_text: str, number: int) -> Citation | None:
    """Read one XML citation envelope without interpreting the surrounding prose."""
    try:
        element = etree.fromstring(
            element_text.strip().strip("`").encode("utf-8"),
            parser=etree.XMLParser(recover=True, resolve_entities=False),
        )
    except etree.XMLSyntaxError:
        return None
    if element is None:
        return None
    content = _child_text(element, "Content")
    document_index = _child_integer(element, "DocumentIndex")
    page_number = _child_integer(element, "Page")
    if not content or document_index is None or page_number is None:
        return None
    return Citation(
        number=number,
        content=content,
        document_index=document_index,
        page_number=page_number,
    )


def _child_text(element: etree._Element, name: str) -> str:
    child = element.find(name)
    return "" if child is None else "".join(str(text) for text in child.itertext()).strip()


def _child_integer(element: etree._Element, name: str) -> int | None:
    try:
        return int(_child_text(element, name))
    except ValueError:
        return None


logger = get_logger(__name__)


async def write_lesson_chapter(
    state: LessonState, runtime: Runtime[GraphRuntime]
) -> dict[str, object]:
    """Writes the next chapter that has not been written yet."""
    plan = state.get("plan")
    if plan is None:
        raise PipelineError.terminal("there is no plan to write chapters from")

    drafts = state.get("chapter_drafts", [])
    chapter_index = len(drafts)
    if chapter_index >= len(plan.chapters):
        raise PipelineError.terminal(
            "the chapter index has run past the plan",
            {"chapter_index": chapter_index, "chapter_count": len(plan.chapters)},
        )

    chapter = plan.chapters[chapter_index]
    stream_writer = get_stream_writer()
    if chapter_index == 0:
        stream_writer(StageChanged(stage=PipelineStage.WRITING_CHAPTERS))
    stream_writer(
        ChapterStarted(
            chapter_index=chapter_index,
            title=chapter.title,
            total_chapters=len(plan.chapters),
        )
    )

    context = build_chapter_context(
        chapters=plan.chapters,
        chapter_index=chapter_index,
        segments=state.get("clean_transcript", []),
        lesson_policy=runtime.context.lesson,
        transcript_policy=runtime.context.transcript,
    )
    if not any(slice_.excerpts for slice_ in context.concept_slices):
        logger.warning(
            "the chapter context holds no transcript",
            chapter_index=chapter_index,
            chapter_title=chapter.title,
            context_start_seconds=context.start_seconds,
            context_end_seconds=context.end_seconds,
        )

    logger.info(
        "chapter writing started",
        chapter_index=chapter_index,
        chapter_title=chapter.title,
        total_chapters=len(plan.chapters),
        concept_count=len(chapter.concepts),
        prior_chapter_count=len(drafts),
        context_start_seconds=context.start_seconds,
        context_end_seconds=context.end_seconds,
    )

    prompts = runtime.context.prompts
    request = prompts.render(
        _CHAPTER_USER_TEMPLATE,
        {
            "language": state["output_language"],
            "mathematics_notation_rules": prompts.render(
                "shared_prompts/mathematics_notation_rules"
            ),
            "chapter": _build_chapter_variables(
                plan=plan,
                chapter_index=chapter_index,
                context=context,
                documents=state.get("documents", []),
                section_map=state.get("section_map"),
                prompts=prompts,
            ),
            "transcript": {
                "excerpt_count": sum(len(slice_.excerpts) for slice_ in context.concept_slices),
                "excerpts_xml": _render_excerpts(context),
            },
        },
    )

    answer = await call_chat_model(
        runtime.context.models.text,
        [
            SystemMessage(
                prompts.render(
                    _CHAPTER_SYSTEM_TEMPLATE,
                    {
                        "language": state["output_language"],
                        "language_policy": prompts.render("shared_prompts/language_policy"),
                        "xml_policy": prompts.render("shared_prompts/xml_policy"),
                        "mathematics_notation_rules": prompts.render(
                            "shared_prompts/mathematics_notation_rules"
                        ),
                    },
                )
            ),
            *_thread_prior_answers(state.get("chapter_answers", [])),
            HumanMessage(request),
        ],
        metadata={"chapter_index": chapter_index},
    )

    parsed = read_chapter_output(
        raw_content=answer.text,
        chapter_index=chapter_index,
        starting_citation_index=_count_prior_citations(drafts),
    )

    logger.info(
        "chapter writing completed",
        chapter_index=chapter_index,
        chapter_title=parsed.title or chapter.title,
        section_count=parsed.section_count,
        citation_count=len(parsed.citations),
        content_character_count=len(parsed.content),
    )
    stream_writer(
        ChapterCompleted(
            chapter_index=chapter_index,
            title=parsed.title or chapter.title,
            citation_count=len(parsed.citations),
            total_chapters=len(plan.chapters),
        )
    )

    return {
        "chapter_drafts": [
            ChapterDraft(
                chapter_index=chapter_index,
                title=parsed.title,
                content=parsed.content,
                citations=parsed.citations,
            )
        ],
        "chapter_answers": [ChapterAnswer(chapter_index=chapter_index, content=answer.text)],
        "usage_by_model": answer.usage_by_model,
    }


def _thread_prior_answers(
    answers: Sequence[ChapterAnswer],
) -> list[AIMessage]:
    """Threads every earlier chapter's answer forward, and nothing else."""
    return [
        AIMessage(answer.content) for answer in sorted(answers, key=lambda item: item.chapter_index)
    ]


def _count_prior_citations(drafts: Sequence[ChapterDraft]) -> int:
    """Counts the citations earlier chapters already emitted."""
    return sum(len(draft.citations) for draft in drafts)


def _build_chapter_variables(
    *,
    plan: LessonPlan,
    chapter_index: int,
    context: ChapterContext,
    documents: Sequence[Document],
    section_map: SectionMap | None,
    prompts: Prompts,
) -> dict[str, object]:
    """Assembles what the chapter request says about the chapter."""
    chapter = plan.chapters[chapter_index]
    earlier_chapters = plan.chapters[:chapter_index]
    earlier_concepts = [concept for earlier in earlier_chapters for concept in earlier.concepts]

    return {
        "index": chapter_index,
        "total": len(plan.chapters),
        "start_seconds": round(context.start_seconds, 1),
        "end_seconds": round(context.end_seconds, 1),
        "concept_count": len(chapter.concepts),
        "previous_chapter_count": len(earlier_chapters),
        "previous_concept_count": len(earlier_concepts),
        "chapter_context_xml": _render_chapter_context(chapter),
        "covered_concepts_xml": _render_covered_concepts(earlier_concepts),
        "do_not_repeat_ledger_xml": _render_established_ledger(earlier_concepts),
        "document_pages_markdown": _render_document_material(
            chapter=chapter,
            documents=documents,
            section_map=section_map,
            prompts=prompts,
        ),
    }


def _render_chapter_context(chapter: PlannedChapter) -> str:
    """Renders what this chapter is asked to teach."""
    return build_xml_document(
        "ChapterContext",
        {
            "Title": chapter.title,
            "Concept": [
                {
                    "ConceptIndex": concept.concept_index,
                    "GlobalIndex": concept.global_index,
                    "TopicTitle": concept.topic_title,
                    "LearningObjective": concept.learning_objective,
                    "MustAdvanceBy": str(concept.must_advance_by),
                    "Intent": str(concept.intent),
                    "ExplanationDepth": str(concept.explanation_depth),
                    "Rationale": concept.rationale,
                    "Start": round(concept.transcript_span.start_seconds, 1),
                    "End": round(concept.transcript_span.end_seconds, 1),
                    "DocumentSpan": [
                        {
                            "DocumentIndex": span.document_index,
                            "SectionIndex": list(span.section_indices),
                        }
                        for span in concept.document_spans
                    ],
                }
                for concept in chapter.concepts
            ],
        },
    )


def _render_covered_concepts(earlier_concepts: Sequence[Concept]) -> str:
    """Renders what earlier chapters already taught."""
    return build_xml_document(
        "CoveredConcepts",
        {
            "Concept": [
                {
                    "ConceptIndex": concept.concept_index,
                    "GlobalIndex": concept.global_index,
                    "TopicTitle": concept.topic_title,
                    "LearningObjective": concept.learning_objective,
                    "MustAdvanceBy": str(concept.must_advance_by),
                    "Start": round(concept.transcript_span.start_seconds, 1),
                    "End": round(concept.transcript_span.end_seconds, 1),
                }
                for concept in earlier_concepts
            ]
        },
    )


def _render_established_ledger(earlier_concepts: Sequence[Concept]) -> str:
    """Renders everything earlier chapters already established."""
    return build_xml_document(
        "ProhibitionLedger",
        {
            "Established": [
                {
                    "GlobalIndex": concept.global_index,
                    "TopicTitle": concept.topic_title,
                    "Statement": concept.establishes,
                }
                for concept in earlier_concepts
            ]
        },
    )


def _render_document_material(
    *,
    chapter: PlannedChapter,
    documents: Sequence[Document],
    section_map: SectionMap | None,
    prompts: Prompts,
) -> str:
    """Renders the document pages this chapter's concepts point at."""
    if not documents or section_map is None:
        return ""

    documents_by_index = {document.document_index: document for document in documents}
    sections_by_document = {
        entry.document_index: {section.section_index: section for section in entry.sections}
        for entry in section_map.documents
    }

    rendered: list[str] = []
    for concept in chapter.concepts:
        for span in concept.document_spans:
            document = documents_by_index.get(span.document_index)
            sections = sections_by_document.get(span.document_index, {})
            if document is None:
                continue
            for section_index in span.section_indices:
                section = sections.get(section_index)
                if section is None:
                    continue
                entry = render_section_pages(document, section, prompts)
                if entry and entry not in rendered:
                    rendered.append(entry)

    return compose_markdown(rendered)


def _render_excerpts(context: ChapterContext) -> str:
    """Render the transcript this chapter may draw from, arranged by concept."""
    return build_xml_document(
        "ConceptContexts",
        {
            "ConceptContext": [
                {
                    "ConceptIndex": concept_slice.concept_index,
                    "TopicTitle": concept_slice.topic_title,
                    "Excerpt": [
                        {
                            "Beginning": round(excerpt.start_seconds, 1),
                            "End": round(excerpt.end_seconds, 1),
                            "Content": excerpt.content,
                        }
                        for excerpt in concept_slice.excerpts
                    ],
                }
                for concept_slice in context.concept_slices
            ]
        },
    )
