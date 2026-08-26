"""Correcting one batch of the machine transcript."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from teacher.configuration import GraphRuntime
from teacher.logging_support import get_logger
from teacher.model_calls import call_chat_model
from teacher.models import TranscriptSegment
from teacher.xml import (
    OneOrMany,
    RequiredText,
    build_xml_document,
    parse_xml_with_schema,
)

__all__ = ["CorrectionBatch", "correct_batch"]

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
