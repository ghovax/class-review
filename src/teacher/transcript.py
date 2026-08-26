"""Consolidated Teacher implementation."""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime
from langgraph.types import Overwrite
from pydantic import BaseModel, Field
from teacher.configuration import GraphRuntime
from teacher.models import TranscriptSegment, TranscriptAssembled
from teacher.state import LessonState
from teacher.support import get_logger, call_chat_model, render_transcript_text, PipelineError
from teacher.xml import extract_element_text, OneOrMany, RequiredText, build_xml_document, parse_xml_with_schema
from typing import Final

"""Transcript graph nodes: terminology, correction fan-out, and transcript assembly."""

"""Establishing the canonical terminology before correction fans out."""


logger = get_logger(__name__)

# What every batch is given when no terminology could be established.
EMPTY_TERMINOLOGY: Final[str] = "<Glossary></Glossary>"

_SYSTEM_TEMPLATE = "transcript/find_terms/system"
_USER_TEMPLATE = "transcript/find_terms/user"
_ROOT_TAG = "Glossary"


async def find_terms(state: LessonState, runtime: Runtime[GraphRuntime]) -> dict[str, object]:
    """Reads the whole machine transcript and settles its terminology."""
    prompts = runtime.context.prompts
    segments = list(state["transcript"].segments)
    transcript_text = render_transcript_text(segments)

    answer = await call_chat_model(
        runtime.context.text_model,
        [
            SystemMessage(
                prompts.render(
                    _SYSTEM_TEMPLATE,
                    {
                        "audio_language": ", ".join(state["transcript"].languages),
                        "language_policy": prompts.render("language_policy"),
                    },
                )
            ),
            HumanMessage(
                prompts.render(
                    _USER_TEMPLATE,
                    {
                        "audio_language": ", ".join(state["transcript"].languages),
                        "transcript_full": transcript_text,
                    },
                )
            ),
        ],
        metadata={"segment_count": len(segments)},
    )

    terminology = _read_terminology(answer.text)
    logger.info(
        "terminology extracted",
        segment_count=len(segments),
        terminology_character_count=len(terminology),
        was_established=terminology != EMPTY_TERMINOLOGY,
    )

    return {"terminology": terminology, "usage_by_model": answer.usage_by_model}


def _read_terminology(answer_text: str) -> str:
    """Isolates the terminology element, falling back to the empty set."""
    try:
        return extract_element_text(answer_text, _ROOT_TAG)
    except Exception:  # noqa: BLE001 - any unusable answer degrades identically
        logger.warning(
            "terminology answer was unusable, correcting without it",
            answer_character_count=len(answer_text),
        )
        return EMPTY_TERMINOLOGY

"""Correcting one batch of the machine transcript."""


logger = get_logger(__name__)

_SYSTEM_TEMPLATE = "transcript/correct_batch/system"
_USER_TEMPLATE = "transcript/correct_batch/user"
_ROOT_TAG = "CorrectedTranscript"


class CorrectionBatch(BaseModel):
    """One batch dispatched to a parallel correction call."""

    batch_index: int
    total_batches: int
    segments: list[TranscriptSegment]
    spoken_language: str
    terminology: str

    model_config = {"arbitrary_types_allowed": True}


class _CorrectedUnit(BaseModel):
    """One rewritten unit the model anchored to a timestamp."""

    timestamp: float = Field(alias="Timestamp", ge=0)
    content: RequiredText = Field(alias="Content")


class _CorrectedTranscript(BaseModel):
    """The element a correction call is expected to answer with."""

    segments: OneOrMany[_CorrectedUnit] = Field(alias="Segment")


async def correct_batch(
    state: CorrectionBatch, runtime: Runtime[GraphRuntime]
) -> dict[str, object]:
    """Corrects one batch and commits its units to the shared channel."""
    batch = state
    prompts = runtime.context.prompts
    batch_start_seconds = batch.segments[0].start_seconds
    batch_end_seconds = batch.segments[-1].end_seconds

    logger.info(
        "batch correction started",
        batch_index=batch.batch_index,
        total_batches=batch.total_batches,
        segment_count=len(batch.segments),
        batch_start_seconds=batch_start_seconds,
        batch_end_seconds=batch_end_seconds,
    )

    source_document = build_xml_document(
        "Transcript",
        {
            "Segment": [
                {"Timestamp": segment.start_seconds, "Content": segment.content}
                for segment in batch.segments
            ]
        },
    )
    answer = await call_chat_model(
        runtime.context.text_model,
        [
            SystemMessage(
                prompts.render(
                    _SYSTEM_TEMPLATE,
                    {
                        "audio_language": batch.spoken_language,
                        "language_policy": prompts.render("language_policy"),
                    },
                )
            ),
            HumanMessage(
                prompts.render(
                    _USER_TEMPLATE,
                    {
                        "index": batch.batch_index,
                        "audio_language": batch.spoken_language,
                        "batch_start_seconds": batch_start_seconds,
                        "batch_end_seconds": batch_end_seconds,
                        "glossary_xml": batch.terminology,
                        "source_segments_xml": source_document,
                    },
                )
            ),
        ],
        metadata={"batch_index": batch.batch_index},
    )

    corrected = _read_units(
        answer_text=answer.text,
        batch_index=batch.batch_index,
        batch_start_seconds=batch_start_seconds,
        batch_end_seconds=batch_end_seconds,
    )

    logger.info(
        "batch correction completed",
        batch_index=batch.batch_index,
        source_segment_count=len(batch.segments),
        corrected_segment_count=len(corrected),
    )

    return {"clean_transcript": corrected, "usage_by_model": answer.usage_by_model}


def _read_units(
    *,
    answer_text: str,
    batch_index: int,
    batch_start_seconds: float,
    batch_end_seconds: float,
) -> list[TranscriptSegment]:
    """Reads the corrected units, healing timestamps that fall out of order."""
    parsed = parse_xml_with_schema(
        content=answer_text,
        root_tag=_ROOT_TAG,
        schema=_CorrectedTranscript,
        metadata={"batch_index": batch_index},
    )

    clamped = sorted(
        (
            (
                min(max(unit.timestamp, batch_start_seconds), batch_end_seconds),
                unit.content,
            )
            for unit in parsed.segments
        ),
        key=lambda unit: unit[0],
    )

    return [
        TranscriptSegment(
            start_seconds=timestamp,
            end_seconds=(
                clamped[position + 1][0] if position < len(clamped) - 1 else batch_end_seconds
            ),
            content=content,
        )
        for position, (timestamp, content) in enumerate(clamped)
    ]

"""The barrier that turns parallel batch output into one transcript."""


logger = get_logger(__name__)


async def finish_transcript(
    state: LessonState, runtime: Runtime[GraphRuntime]
) -> dict[str, object]:
    """Orders, deduplicates, and re-chains every batch's units into one whole."""
    del runtime
    collected = state.get("clean_transcript", [])
    if not collected:
        raise PipelineError.terminal("correction produced no segments", {"received_count": 0})

    ordered = sorted(
        collected,
        key=lambda segment: (
            segment.start_seconds,
            segment.end_seconds,
            segment.content,
        ),
    )
    deduplicated = _drop_repeats(ordered)
    chained = _chain_ends(deduplicated)

    duration_seconds = chained[-1].end_seconds - chained[0].start_seconds
    logger.info(
        "transcript assembled",
        collected_segment_count=len(collected),
        final_segment_count=len(chained),
        start_seconds=chained[0].start_seconds,
        end_seconds=chained[-1].end_seconds,
        duration_seconds=duration_seconds,
    )

    stream_writer = get_stream_writer()
    stream_writer(
        TranscriptAssembled(segment_count=len(chained), duration_seconds=duration_seconds)
    )

    return {"clean_transcript": Overwrite(value=chained)}


def _drop_repeats(
    ordered_segments: list[TranscriptSegment],
) -> list[TranscriptSegment]:
    """Removes units that repeat both a start time and their text."""
    kept: list[TranscriptSegment] = []
    for segment in ordered_segments:
        previous = kept[-1] if kept else None
        if (
            previous is not None
            and previous.start_seconds == segment.start_seconds
            and previous.content == segment.content
        ):
            continue
        kept.append(segment)
    return kept


def _chain_ends(segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
    """Sets each unit's end to the next unit's start, across the whole timeline."""
    return [
        TranscriptSegment(
            start_seconds=segment.start_seconds,
            end_seconds=max(
                segment.start_seconds,
                (
                    segments[position + 1].start_seconds
                    if position < len(segments) - 1
                    else segment.end_seconds
                ),
            ),
            content=segment.content,
        )
        for position, segment in enumerate(segments)
    ]


