"""Writing one chapter, with every chapter written before it in view."""

from __future__ import annotations

from collections.abc import Sequence

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from teacher.configuration import GraphRuntime
from teacher.errors import PipelineError
from teacher.events import (
    ChapterCompleted,
    ChapterStarted,
    PipelineStage,
    StageChanged,
)
from teacher.lesson.windows import ChapterWindow, build_chapter_window
from teacher.logging_support import get_logger
from teacher.lesson.chapter_output import read_chapter_output
from teacher.model_calls import call_chat_model
from teacher.models import (
    Concept,
    Document,
    LessonPlan,
    PlannedChapter,
    SectionMap,
)
from teacher.prompts import Prompts
from teacher.rendering import render_page_entries
from teacher.state import (
    ChapterDraft,
    ChapterExchange,
    LessonState,
)
from teacher.xml import build_xml_document

__all__ = ["write_chapter"]

logger = get_logger(__name__)

_SYSTEM_TEMPLATE = "lesson/write_chapter/system"
_USER_TEMPLATE = "lesson/write_chapter/user"
_NOTATION_TEMPLATE = "mathematics_notation_rules"


async def write_chapter(state: LessonState, runtime: Runtime[GraphRuntime]) -> dict[str, object]:
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

    window = build_chapter_window(
        chapters=plan.chapters,
        chapter_index=chapter_index,
        segments=state.get("clean_transcript", []),
        configuration=runtime.context,
    )
    if not any(slice_.groups for slice_ in window.concept_slices):
        logger.warning(
            "the chapter window holds no transcript",
            chapter_index=chapter_index,
            chapter_title=chapter.title,
            window_start_seconds=window.start_seconds,
            window_end_seconds=window.end_seconds,
        )

    logger.info(
        "chapter writing started",
        chapter_index=chapter_index,
        chapter_title=chapter.title,
        total_chapters=len(plan.chapters),
        concept_count=len(chapter.concepts),
        prior_chapter_count=len(drafts),
        window_start_seconds=window.start_seconds,
        window_end_seconds=window.end_seconds,
    )

    prompts = runtime.context.prompts
    request = prompts.render(
        _USER_TEMPLATE,
        {
            "language": state["output_language"],
            "mathematics_notation_rules": prompts.render(_NOTATION_TEMPLATE),
            "chapter": _build_chapter_variables(
                plan=plan,
                chapter_index=chapter_index,
                window=window,
                documents=state.get("documents", []),
                section_map=state.get("section_map"),
                prompts=prompts,
            ),
            "transcript": {
                "group_count": sum(len(slice_.groups) for slice_ in window.concept_slices),
                "groups_xml": _render_groups(window),
            },
        },
    )

    answer = await call_chat_model(
        runtime.context.text_model,
        [
            SystemMessage(
                prompts.render(
                    _SYSTEM_TEMPLATE,
                    {
                        "language": state["output_language"],
                        "language_policy": prompts.render("language_policy"),
                        "mathematics_notation_rules": prompts.render(_NOTATION_TEMPLATE),
                    },
                )
            ),
            *_thread_prior_answers(state.get("chapter_exchanges", [])),
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
        "chapter_exchanges": [
            ChapterExchange(chapter_index=chapter_index, request=request, answer=answer.text)
        ],
        "usage_by_model": answer.usage_by_model,
    }


def _thread_prior_answers(
    exchanges: Sequence[ChapterExchange],
) -> list[AIMessage]:
    """Threads every earlier chapter's answer forward, and nothing else."""
    return [
        AIMessage(exchange.answer)
        for exchange in sorted(exchanges, key=lambda item: item.chapter_index)
    ]


def _count_prior_citations(drafts: Sequence[ChapterDraft]) -> int:
    """Counts the citations earlier chapters already emitted."""
    return sum(len(draft.citations) for draft in drafts)


def _build_chapter_variables(
    *,
    plan: LessonPlan,
    chapter_index: int,
    window: ChapterWindow,
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
        "start_seconds": round(window.start_seconds, 1),
        "end_seconds": round(window.end_seconds, 1),
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
                entry = render_page_entries(document, section)
                if entry and entry not in rendered:
                    rendered.append(entry)

    return "\n\n".join(rendered)


def _render_groups(window: ChapterWindow) -> str:
    """Renders the transcript this chapter may draw from, grouped by concept."""
    return build_xml_document(
        "ConceptWindows",
        {
            "ConceptWindow": [
                {
                    "ConceptIndex": concept_slice.concept_index,
                    "TopicTitle": concept_slice.topic_title,
                    "Group": [
                        {
                            "Beginning": round(group.start_seconds, 1),
                            "End": round(group.end_seconds, 1),
                            "Content": group.content,
                        }
                        for group in concept_slice.groups
                    ],
                }
                for concept_slice in window.concept_slices
            ]
        },
    )
