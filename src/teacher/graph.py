"""The single end-to-end generation graph."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy, Send

from teacher.configuration import GraphRuntime
from teacher.documents import (
    DocumentPageReadRequest,
    DocumentReadRequest,
    assemble_documents_from_pages,
    explain_document_sections,
    extract_document_page,
    load_document_pages,
    map_document_sections,
)
from teacher.lesson import (
    assemble_completed_lesson,
    build_lesson_glossary,
    plan_lesson_outline,
    write_lesson_chapter,
)
from teacher.support import PipelineError, classify_retryable, get_logger
from teacher.models import TranscriptSegment
from teacher.state import LessonInput, LessonOutput, LessonState
from teacher.transcript import (
    CorrectionBatch,
    EMPTY_TERMINOLOGY,
    assemble_corrected_transcript,
    correct_transcript_batch,
    extract_transcript_terminology,
)

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


def route_after_chapter_writing(
    state: LessonState,
) -> Literal["write_lesson_chapter", "build_lesson_glossary"]:
    """Loop over chapter writing until the plan is complete."""

    plan = state.get("plan")
    written = len(state.get("chapter_drafts", []))
    if plan is not None and written < len(plan.chapters):
        return "write_lesson_chapter"
    logger.info("every chapter written", chapter_count=written)
    return "build_lesson_glossary"


def dispatch_document_reads(state: LessonState) -> list[Send] | str:
    """Send each source to the caller's document reader or continue with none."""

    sources = state.get("sources", [])
    if not sources:
        return "assemble_documents_from_pages"
    return [
        Send(
            "load_document_pages",
            DocumentReadRequest(document_index=index, source=source),
        )
        for index, source in enumerate(sources)
    ]


def dispatch_transcript_corrections(state: LessonState, runtime) -> list[Send]:
    """Send each transcript window for parallel correction."""

    batches = build_batches(state["transcript"].segments, runtime.context.correction_batch_seconds)
    language = ", ".join(state["transcript"].languages)
    terminology = state.get("terminology") or EMPTY_TERMINOLOGY
    return [
        Send(
            "correct_transcript_batch",
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
    graph.add_node("extract_transcript_terminology", extract_transcript_terminology, retry_policy=retry)
    graph.add_node("correct_transcript_batch", correct_transcript_batch, input_schema=CorrectionBatch, retry_policy=retry)
    graph.add_node("assemble_corrected_transcript", assemble_corrected_transcript, defer=True)
    graph.add_node(
        "load_document_pages",
        load_document_pages,
        input_schema=DocumentReadRequest,
        retry_policy=retry,
        destinations=("extract_document_page", "assemble_documents_from_pages"),
    )
    graph.add_node("extract_document_page", extract_document_page, input_schema=DocumentPageReadRequest)
    graph.add_node("assemble_documents_from_pages", assemble_documents_from_pages, defer=True)
    graph.add_node("map_document_sections", map_document_sections, retry_policy=retry)
    graph.add_node("explain_document_sections", explain_document_sections, retry_policy=retry)
    graph.add_node("plan_lesson_outline", plan_lesson_outline, retry_policy=retry, defer=True)
    graph.add_node("write_lesson_chapter", write_lesson_chapter, retry_policy=retry)
    graph.add_node("build_lesson_glossary", build_lesson_glossary, retry_policy=retry)
    graph.add_node("assemble_completed_lesson", assemble_completed_lesson)

    graph.add_edge(START, "extract_transcript_terminology")
    graph.add_conditional_edges(START, dispatch_document_reads, ["load_document_pages", "assemble_documents_from_pages"])
    graph.add_conditional_edges("extract_transcript_terminology", dispatch_transcript_corrections, ["correct_transcript_batch"])
    graph.add_edge("correct_transcript_batch", "assemble_corrected_transcript")
    graph.add_edge("extract_document_page", "assemble_documents_from_pages")
    graph.add_edge("assemble_documents_from_pages", "map_document_sections")
    graph.add_edge("map_document_sections", "explain_document_sections")
    graph.add_edge(["assemble_corrected_transcript", "explain_document_sections"], "plan_lesson_outline")
    graph.add_edge("plan_lesson_outline", "write_lesson_chapter")
    graph.add_conditional_edges(
        "write_lesson_chapter", route_after_chapter_writing, ["write_lesson_chapter", "build_lesson_glossary"]
    )
    graph.add_edge("build_lesson_glossary", "assemble_completed_lesson")
    graph.add_edge("assemble_completed_lesson", END)
    return graph
