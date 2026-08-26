"""The single end-to-end generation graph."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy, Send

from teacher.configuration import GraphRuntime
from teacher.documents import (
    DocumentToLoad,
    explain_sections,
    finish_documents,
    load_document,
    map_sections,
    read_page,
)
from teacher.lesson import build_glossary, finish_lesson, plan_lesson, write_chapter
from teacher.support import PipelineError, classify_retryable, get_logger
from teacher.models import TranscriptSegment
from teacher.state import LessonInput, LessonOutput, LessonState
from teacher.transcript import CorrectionBatch, EMPTY_TERMINOLOGY, correct_batch, finish_transcript, find_terms

logger = get_logger(__name__)


def build_batches(
    segments: Sequence[TranscriptSegment], span_seconds: float
) -> list[list[TranscriptSegment]]:
    """Pack ordered transcript segments into bounded correction windows."""

    ordered = sorted(segments, key=lambda item: (item.start_seconds, item.end_seconds))
    if not ordered:
        raise PipelineError.terminal("the transcript has no segments")
    batches: list[list[TranscriptSegment]] = []
    for segment in ordered:
        if not batches or segment.end_seconds - batches[-1][0].start_seconds > span_seconds:
            batches.append([segment])
        else:
            batches[-1].append(segment)
    return batches


def route_after_chapter(
    state: LessonState,
) -> Literal["write_chapter", "build_glossary"]:
    """Loop over chapter writing until the plan is complete."""

    plan = state.get("plan")
    written = len(state.get("chapter_drafts", []))
    if plan is not None and written < len(plan.chapters):
        return "write_chapter"
    logger.info("every chapter written", chapter_count=written)
    return "build_glossary"


def dispatch_documents(state: LessonState) -> list[Send] | str:
    """Send each source to the document importer or continue with none."""

    sources = state.get("sources", [])
    if not sources:
        return "finish_documents"
    return [
        Send(
            "load_document",
            DocumentToLoad(document_index=index, source=source),
        )
        for index, source in enumerate(sources)
    ]


def dispatch_batches(state: LessonState, runtime) -> list[Send]:
    """Send each transcript window for parallel correction."""

    batches = build_batches(state["transcript"].segments, runtime.context.correction_batch_seconds)
    language = ", ".join(state["transcript"].languages)
    terminology = state.get("terminology") or EMPTY_TERMINOLOGY
    return [
        Send(
            "correct_batch",
            CorrectionBatch(
                batch_index=index,
                total_batches=len(batches),
                segments=batch,
                spoken_language=language,
                terminology=terminology,
            ),
        )
        for index, batch in enumerate(batches)
    ]


def define_graph(
    *, model_attempts: int = 3
) -> StateGraph[LessonState, GraphRuntime, LessonInput, LessonOutput]:
    """Build the complete graph without compiling it."""

    retry = RetryPolicy(max_attempts=model_attempts, retry_on=classify_retryable)
    graph = StateGraph(
        LessonState,
        input_schema=LessonInput,
        output_schema=LessonOutput,
        context_schema=GraphRuntime,
    )
    graph.add_node("find_terms", find_terms, retry_policy=retry)
    graph.add_node("correct_batch", correct_batch, input_schema=CorrectionBatch, retry_policy=retry)
    graph.add_node("finish_transcript", finish_transcript, defer=True)
    graph.add_node(
        "load_document",
        load_document,
        input_schema=DocumentToLoad,
        retry_policy=retry,
        destinations=("read_page", "finish_documents"),
    )
    graph.add_node("read_page", read_page)
    graph.add_node("finish_documents", finish_documents, defer=True)
    graph.add_node("map_sections", map_sections, retry_policy=retry)
    graph.add_node("explain_sections", explain_sections, retry_policy=retry)
    graph.add_node("plan_lesson", plan_lesson, retry_policy=retry, defer=True)
    graph.add_node("write_chapter", write_chapter, retry_policy=retry)
    graph.add_node("build_glossary", build_glossary, retry_policy=retry)
    graph.add_node("finish_lesson", finish_lesson)

    graph.add_edge(START, "find_terms")
    graph.add_conditional_edges(START, dispatch_documents, ["load_document", "finish_documents"])
    graph.add_conditional_edges("find_terms", dispatch_batches, ["correct_batch"])
    graph.add_edge("correct_batch", "finish_transcript")
    graph.add_edge("read_page", "finish_documents")
    graph.add_edge("finish_documents", "map_sections")
    graph.add_edge("map_sections", "explain_sections")
    graph.add_edge(["finish_transcript", "explain_sections"], "plan_lesson")
    graph.add_edge("plan_lesson", "write_chapter")
    graph.add_conditional_edges(
        "write_chapter", route_after_chapter, ["write_chapter", "build_glossary"]
    )
    graph.add_edge("build_glossary", "finish_lesson")
    graph.add_edge("finish_lesson", END)
    return graph
