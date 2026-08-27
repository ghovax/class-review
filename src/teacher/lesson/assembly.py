"""Assemble the completed lesson."""

from __future__ import annotations

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime
from teacher.configuration import GraphRuntime
from teacher.models import (
    Citation,
    PipelineStage,
    StageChanged,
    LessonAssembled,
    Chapter,
    Lesson,
)
from teacher.state import LessonState
from teacher.support import PipelineError, get_logger, compute_glossary_links

logger = get_logger(__name__)


async def assemble_completed_lesson(
    state: LessonState, runtime: Runtime[GraphRuntime]
) -> dict[str, object]:
    """Assembles the lesson from everything written."""
    del runtime
    plan = state.get("plan")
    if plan is None:
        raise PipelineError.terminal("there is no plan to assemble a lesson from")

    stream_writer = get_stream_writer()
    stream_writer(StageChanged(stage=PipelineStage.ASSEMBLING_LESSON))

    drafts_by_index = {draft.chapter_index: draft for draft in state.get("chapter_drafts", [])}
    missing = sorted(index for index in range(len(plan.chapters)) if index not in drafts_by_index)
    if missing:
        raise PipelineError.terminal(
            "the plan calls for chapters that were never written",
            {
                "missing_chapter_indices": missing,
                "chapter_count": len(plan.chapters),
            },
        )

    glossary = tuple(state.get("glossary", []))
    contents = [drafts_by_index[index].content for index in range(len(plan.chapters))]
    links_per_chapter = compute_glossary_links(contents, glossary)

    chapters = tuple(
        Chapter(
            title=(drafts_by_index[index].title or plan_chapter.title).strip(),
            content=drafts_by_index[index].content,
            concepts=plan_chapter.concepts,
            citations=tuple(
                Citation(
                    number=citation.number,
                    content=citation.content,
                    document_index=citation.document_index,
                    page_number=citation.page_number,
                )
                for citation in drafts_by_index[index].citations
            ),
            glossary_links=links_per_chapter[index],
        )
        for index, plan_chapter in enumerate(plan.chapters)
    )

    lesson = Lesson(
        title=plan.title,
        description=plan.description,
        chapters=chapters,
        glossary=glossary,
    )

    logger.info(
        "lesson assembled",
        lesson_title=lesson.title,
        chapter_count=len(lesson.chapters),
        citation_count=sum(len(chapter.citations) for chapter in lesson.chapters),
        glossary_term_count=len(lesson.glossary),
        linked_occurrence_count=sum(len(chapter.glossary_links) for chapter in lesson.chapters),
    )
    stream_writer(LessonAssembled(title=lesson.title, chapters=lesson.chapters))

    return {"lesson": lesson}
