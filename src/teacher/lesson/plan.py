"""Drafting the plan every chapter is then written against."""

from __future__ import annotations

from typing import Annotated

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from teacher.configuration import GraphRuntime
from teacher.errors import PipelineError
from teacher.events import PipelineStage, PlanCreated, StageChanged
from teacher.lesson.windows import split_into_sentences
from teacher.logging_support import get_logger
from teacher.model_calls import call_chat_model
from teacher.models import (
    Concept,
    ConceptDocumentSpan,
    ConceptIntent,
    ExplanationDepth,
    LessonPlan,
    PlannedChapter,
    ProgressionAxis,
    TimeSpan,
)
from teacher.prompt_fragments import render_language_policy
from teacher.state import LessonState
from teacher.xml.documents import build_xml_document
from teacher.xml.schema_definitions import (
    OneOrMany,
    RequiredText,
    case_insensitive_with_fallback,
    parse_xml_with_schema,
)

__all__ = ["plan_lesson"]

logger = get_logger(__name__)

_SYSTEM_TEMPLATE = "lesson/plan_lesson/system"
_USER_TEMPLATE = "lesson/plan_lesson/user"
_NOTATION_TEMPLATE = "mathematics_notation_rules"
_ROOT_TAG = "LessonOutline"


class _DocumentSpanSchema(BaseModel):
    """The document sections one concept draws on."""

    document_index: int = Field(alias="DocumentIndex", ge=0)
    section_indices: OneOrMany[int] = Field(alias="SectionIndex", default_factory=list)


class _DurationSchema(BaseModel):
    """The transcript window selected for one concept."""

    start_seconds: float = Field(alias="Beginning", ge=0)
    end_seconds: float = Field(alias="End", ge=0)


class _ConceptSchema(BaseModel):
    """One concept the plan declared."""

    topic_title: RequiredText = Field(alias="TopicTitle")
    learning_objective: RequiredText = Field(alias="LearningObjective")
    must_advance_by: Annotated[
        ProgressionAxis,
        case_insensitive_with_fallback(ProgressionAxis, ProgressionAxis.MECHANISM),
    ] = Field(alias="MustAdvanceBy")
    intent: Annotated[
        ConceptIntent,
        case_insensitive_with_fallback(ConceptIntent, ConceptIntent.INTRODUCE),
    ] = Field(alias="Intent")
    explanation_depth: Annotated[
        ExplanationDepth,
        case_insensitive_with_fallback(ExplanationDepth, ExplanationDepth.MEDIUM),
    ] = Field(alias="ExplanationDepth")
    rationale: RequiredText = Field(alias="Rationale")
    duration: _DurationSchema = Field(alias="Duration")
    establishes: RequiredText = Field(alias="DoNotRepeat")
    document_spans: OneOrMany[_DocumentSpanSchema] = Field(
        alias="DocumentSpan", default_factory=list
    )


class _ChapterSchema(BaseModel):
    """One chapter the plan declared."""

    title: RequiredText = Field(alias="Title")
    concepts: OneOrMany[_ConceptSchema] = Field(alias="Concept")


class _OutlineSchema(BaseModel):
    """The element an plan call is expected to answer with."""

    title: RequiredText = Field(alias="Title")
    description: RequiredText = Field(alias="Description")
    chapters: OneOrMany[_ChapterSchema] = Field(alias="Chapter")


async def plan_lesson(state: LessonState, runtime: Runtime[GraphRuntime]) -> dict[str, object]:
    """Drafts the plan the chapters will be written against."""
    segments = state.get("clean_transcript", [])
    if not segments:
        raise PipelineError.terminal(
            "there is no transcript to plan a lesson from", {"segment_count": 0}
        )

    stream_writer = get_stream_writer()
    stream_writer(StageChanged(stage=PipelineStage.PLANNING_LESSON))

    prompts = runtime.context.prompts
    start_seconds = min(segment.start_seconds for segment in segments)
    end_seconds = max(segment.end_seconds for segment in segments)
    duration_seconds = max(0.0, end_seconds - start_seconds)
    documents = state.get("documents", [])

    logger.info(
        "plan drafting started",
        segment_count=len(segments),
        document_count=len(documents),
        duration_seconds=duration_seconds,
    )

    system_prompt = prompts.render(
        _SYSTEM_TEMPLATE,
        {
            "language": state["output_language"],
            "language_policy": render_language_policy(prompts),
            "mathematics_notation_rules": prompts.render(_NOTATION_TEMPLATE),
        },
    )
    user_prompt = prompts.render(
        _USER_TEMPLATE,
        {
            "language": state["output_language"],
            "metadata": {
                "language": state["output_language"],
                "document_count": len(documents),
                "lesson_start_seconds": round(start_seconds, 1),
                "lesson_end_seconds": round(end_seconds, 1),
                "lesson_duration_seconds": round(duration_seconds, 1),
            },
            "transcript_segments_xml": _render_transcript(state, runtime.context),
            "document_section_map_xml": _render_section_map(state),
            "section_explanations_xml": _render_notes(state),
        },
    )
    _check_request_size(
        character_count=len(system_prompt) + len(user_prompt),
        segment_count=len(segments),
        duration_seconds=duration_seconds,
        policy=runtime.context,
    )

    answer = await call_chat_model(
        runtime.context.text_model,
        [SystemMessage(system_prompt), HumanMessage(user_prompt)],
        metadata={"segment_count": len(segments)},
    )

    plan = _read_plan(
        answer.text,
        transcript_start_seconds=start_seconds,
        transcript_end_seconds=end_seconds,
        policy=runtime.context,
    )
    logger.info(
        "plan drafted",
        lecture_title=plan.title,
        chapter_count=len(plan.chapters),
        concept_count=sum(len(chapter.concepts) for chapter in plan.chapters),
    )
    stream_writer(PlanCreated(plan=plan))

    return {"plan": plan, "usage_by_model": answer.usage_by_model}


def _render_transcript(state: LessonState, policy: GraphRuntime) -> str:
    """Renders the transcript with its sentences, for the plan to plan over."""
    clean_transcript = state.get("clean_transcript")
    if clean_transcript is None:
        raise PipelineError.terminal("the corrected transcript is missing")
    return build_xml_document(
        "TranscriptSegments",
        {
            "Segment": [
                {
                    "Beginning": round(segment.start_seconds, policy.transcript_timestamp_decimals),
                    "End": round(segment.end_seconds, policy.transcript_timestamp_decimals),
                    "Sentence": [
                        {
                            "Beginning": round(
                                sentence.start_seconds,
                                policy.transcript_timestamp_decimals,
                            ),
                            "End": round(
                                sentence.end_seconds,
                                policy.transcript_timestamp_decimals,
                            ),
                            "Text": sentence.content,
                        }
                        for sentence in split_into_sentences(segment)
                    ],
                }
                for segment in clean_transcript
            ]
        },
    )


def _render_section_map(state: LessonState) -> str:
    """Renders how the documents divide into sections."""
    section_map = state.get("section_map")
    if section_map is None or not section_map.documents:
        return build_xml_document("DocumentSections", {})
    return build_xml_document(
        "DocumentSections",
        {
            "Document": [
                {
                    "DocumentIndex": entry.document_index,
                    "FileName": entry.file_name,
                    "Section": [
                        {
                            "SectionIndex": section.section_index,
                            "StartPage": section.start_page,
                            "EndPage": section.end_page,
                            "SectionTitle": section.title,
                            "Description": section.description,
                        }
                        for section in entry.sections
                    ],
                }
                for entry in section_map.documents
            ]
        },
    )


def _render_notes(state: LessonState) -> str:
    """Renders the section explanations."""
    notes = state.get("section_notes", [])
    if not notes:
        return build_xml_document("SectionExplanations", {})
    return build_xml_document(
        "SectionExplanations",
        {
            "Section": [
                {
                    "DocumentIndex": note.document_index,
                    "SectionIndex": note.section_index,
                    "Explanation": note.content,
                }
                for note in notes
            ]
        },
    )


def _read_plan(
    answer_text: str,
    *,
    transcript_start_seconds: float,
    transcript_end_seconds: float,
    policy: GraphRuntime,
) -> LessonPlan:
    """Reads the answer into an plan, held to the transcript that exists."""
    parsed = parse_xml_with_schema(content=answer_text, root_tag=_ROOT_TAG, schema=_OutlineSchema)
    if not parsed.chapters:
        raise PipelineError.retryable("the plan declares no chapters")
    _check_asserted_values(parsed, policy)

    global_index = 0
    chapters_list: list[PlannedChapter] = []
    for chapter in parsed.chapters:
        concepts: list[Concept] = []
        for concept_index, concept in enumerate(chapter.concepts):
            concepts.append(
                Concept(
                    concept_index=concept_index,
                    global_index=global_index,
                    topic_title=concept.topic_title,
                    learning_objective=concept.learning_objective,
                    must_advance_by=concept.must_advance_by,
                    intent=concept.intent,
                    explanation_depth=concept.explanation_depth,
                    rationale=concept.rationale,
                    transcript_span=_clamp_span(
                        concept.duration.start_seconds,
                        concept.duration.end_seconds,
                        transcript_start_seconds,
                        transcript_end_seconds,
                    ),
                    establishes=concept.establishes,
                    document_spans=tuple(
                        ConceptDocumentSpan(
                            document_index=span.document_index,
                            section_indices=tuple(span.section_indices),
                        )
                        for span in concept.document_spans
                    ),
                )
            )
            global_index += 1
        chapters_list.append(PlannedChapter(title=chapter.title, concepts=tuple(concepts)))
    chapters = tuple(chapters_list)

    if not any(chapter.concepts for chapter in chapters):
        raise PipelineError.retryable("the plan declares no concepts")

    return LessonPlan(title=parsed.title, description=parsed.description, chapters=chapters)


def _clamp_span(first: float, second: float, lower: float, upper: float) -> TimeSpan:
    """Brings one concept's span inside the recording that exists."""
    start = min(first, second)
    end = max(first, second)
    clamped_start = min(max(start, lower), upper)
    clamped_end = min(max(end, clamped_start), upper)
    if (start, end) != (clamped_start, clamped_end):
        logger.warning(
            "plan named a stretch outside the recording, bringing it inside",
            named_start_seconds=start,
            named_end_seconds=end,
            clamped_start_seconds=clamped_start,
            clamped_end_seconds=clamped_end,
        )
    return TimeSpan(start_seconds=clamped_start, end_seconds=clamped_end)


def _check_request_size(
    *,
    character_count: int,
    segment_count: int,
    duration_seconds: float,
    policy: GraphRuntime,
) -> None:
    """Refuses a request no provider will accept, naming why it grew."""
    logger.info(
        "plan request assembled",
        request_character_count=character_count,
        segment_count=segment_count,
        duration_seconds=round(duration_seconds, 1),
    )
    if character_count <= policy.maximum_plan_request_characters:
        return
    raise PipelineError.terminal(
        "the transcript is too long to draft an plan from in one request",
        {
            "request_character_count": character_count,
            "maximum_request_characters": policy.maximum_plan_request_characters,
            "segment_count": segment_count,
            "duration_seconds": round(duration_seconds, 1),
            "duration_hours": round(duration_seconds / 3600, 2),
        },
    )


def _check_asserted_values(parsed: _OutlineSchema, policy: GraphRuntime) -> None:
    """Holds every number the answer states to a plausible range."""
    for chapter in parsed.chapters:
        for concept in chapter.concepts:
            for label, value, ceiling in (
                (
                    "start_seconds",
                    concept.duration.start_seconds,
                    policy.maximum_model_seconds,
                ),
                (
                    "end_seconds",
                    concept.duration.end_seconds,
                    policy.maximum_model_seconds,
                ),
            ):
                if value > ceiling:
                    raise PipelineError.retryable(
                        "the plan states a value beyond what could be real",
                        {
                            "field_name": label,
                            "stated_value": value,
                            "maximum_value": ceiling,
                            "chapter_title": chapter.title,
                        },
                    )
            for span in concept.document_spans:
                if span.document_index > policy.maximum_model_index:
                    raise PipelineError.retryable(
                        "the plan states a document beyond what could be real",
                        {
                            "stated_value": span.document_index,
                            "maximum_value": policy.maximum_model_index,
                        },
                    )
