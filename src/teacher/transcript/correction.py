"""Correct transcript segments using established terminology."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field
from teacher.configuration import GraphRuntime
from teacher.models import (
    Terminology,
    TranscriptSegment,
)
from teacher.support import get_logger, call_chat_model
from teacher.transcript.terminology import render_terminology_xml
from teacher.xml import OneOrMany, RequiredText, build_xml_document, parse_xml_with_schema

logger = get_logger(__name__)


_CORRECTION_SYSTEM_TEMPLATE = "transcript/correct_transcript/system"


_CORRECTION_USER_TEMPLATE = "transcript/correct_transcript/user"


_CORRECTED_ROOT_TAG = "CorrectedTranscript"


class TranscriptCorrectionInput(BaseModel):
    """Transcript material supplied to one correction call."""

    segments: list[TranscriptSegment]
    spoken_language: str
    terminology: Terminology

    model_config = {"arbitrary_types_allowed": True}


class _CorrectedUnit(BaseModel):
    """One rewritten unit the model anchored to a timestamp."""

    timestamp: float = Field(alias="Timestamp", ge=0)
    content: RequiredText = Field(alias="Content")


class _CorrectedTranscript(BaseModel):
    """The element a correction call is expected to answer with."""

    segments: OneOrMany[_CorrectedUnit] = Field(alias="Segment")


async def correct_transcript(
    state: TranscriptCorrectionInput, runtime: Runtime[GraphRuntime]
) -> dict[str, object]:
    """Corrects supplied transcript material and commits its units."""
    correction = state
    prompts = runtime.context.prompts
    start_seconds = correction.segments[0].start_seconds
    end_seconds = correction.segments[-1].end_seconds

    logger.info(
        "transcript correction started",
        segment_count=len(correction.segments),
        start_seconds=start_seconds,
        end_seconds=end_seconds,
    )

    source_document = build_xml_document(
        "Transcript",
        {
            "Segment": [
                {"Timestamp": segment.start_seconds, "Content": segment.content}
                for segment in correction.segments
            ]
        },
    )
    answer = await call_chat_model(
        runtime.context.models.text,
        [
            SystemMessage(
                prompts.render(
                    _CORRECTION_SYSTEM_TEMPLATE,
                    {
                        "language": correction.spoken_language,
                        "language_policy": prompts.render("shared_prompts/language_policy"),
                        "xml_policy": prompts.render("shared_prompts/xml_policy"),
                    },
                )
            ),
            HumanMessage(
                prompts.render(
                    _CORRECTION_USER_TEMPLATE,
                    {
                        "language": correction.spoken_language,
                        "start_seconds": start_seconds,
                        "end_seconds": end_seconds,
                        "terminology_xml": render_terminology_xml(correction.terminology),
                        "transcript_xml": source_document,
                    },
                )
            ),
        ],
        metadata={"segment_count": len(correction.segments)},
    )

    corrected = _read_units(
        answer_text=answer.text,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
    )

    logger.info(
        "transcript correction completed",
        source_segment_count=len(correction.segments),
        corrected_segment_count=len(corrected),
    )

    return {"clean_transcript": corrected, "usage_by_model": answer.usage_by_model}


def _read_units(
    *,
    answer_text: str,
    start_seconds: float,
    end_seconds: float,
) -> list[TranscriptSegment]:
    """Reads the corrected units, healing timestamps that fall out of order."""
    parsed = parse_xml_with_schema(
        content=answer_text,
        root_tag=_CORRECTED_ROOT_TAG,
        schema=_CorrectedTranscript,
        metadata={"start_seconds": start_seconds, "end_seconds": end_seconds},
    )

    clamped = sorted(
        (
            (
                min(max(unit.timestamp, start_seconds), end_seconds),
                unit.content,
            )
            for unit in parsed.segments
        ),
        key=lambda unit: unit[0],
    )

    return [
        TranscriptSegment(
            start_seconds=timestamp,
            end_seconds=(clamped[position + 1][0] if position < len(clamped) - 1 else end_seconds),
            content=content,
        )
        for position, (timestamp, content) in enumerate(clamped)
    ]
