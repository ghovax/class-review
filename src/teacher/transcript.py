"""Consolidated Teacher implementation."""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime
from langgraph.types import Overwrite
from pydantic import BaseModel, Field
from teacher.configuration import GraphRuntime
from teacher.models import (
    Terminology,
    TerminologyHeard,
    TerminologyTerm,
    TranscriptAssembled,
    TranscriptSegment,
)
from teacher.state import LessonState
from teacher.support import get_logger, call_chat_model, render_transcript_text, PipelineError
from teacher.xml import OneOrMany, RequiredText, build_xml_document, parse_xml_with_schema
from typing import Final

"""Transcript graph nodes: terminology, correction, and transcript assembly."""

"""Establishing the canonical terminology before transcript correction."""


logger = get_logger(__name__)

# What every correction receives when no terminology could be established.
EMPTY_TERMINOLOGY: Final[Terminology] = Terminology(terms=())

_SYSTEM_TEMPLATE = "transcript/extract_transcript_terminology/system"
_USER_TEMPLATE = "transcript/extract_transcript_terminology/user"


async def extract_transcript_terminology(
    state: LessonState, runtime: Runtime[GraphRuntime]
) -> dict[str, object]:
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
                        "language": ", ".join(state["transcript"].languages),
                        "language_policy": prompts.render("language_policy"),
                    },
                )
            ),
            HumanMessage(
                prompts.render(
                    _USER_TEMPLATE,
                    {
                        "language": ", ".join(state["transcript"].languages),
                        "transcript": transcript_text,
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
        terminology_term_count=len(terminology.terms),
    )

    return {"terminology": terminology, "usage_by_model": answer.usage_by_model}


class _HeardTerminologySchema(BaseModel):
    variants: OneOrMany[RequiredText] = Field(alias="Variant")


class _TerminologyTermSchema(BaseModel):
    canonical: RequiredText = Field(alias="Canonical")
    heard: _HeardTerminologySchema = Field(alias="Heard")
    kind: RequiredText = Field(alias="Kind")


class _TerminologySchema(BaseModel):
    terms: OneOrMany[_TerminologyTermSchema] = Field(alias="Term")


def _read_terminology(answer_text: str) -> Terminology:
    """Parses the model's terminology XML into the typed graph value."""
    try:
        parsed = parse_xml_with_schema(
            content=answer_text,
            root_tag="Terminology",
            schema=_TerminologySchema,
        )
        return Terminology(
            terms=tuple(
                TerminologyTerm(
                    canonical=term.canonical,
                    heard=TerminologyHeard(variants=tuple(term.heard.variants)),
                    kind=term.kind,
                )
                for term in parsed.terms
            )
        )
    except Exception:  # noqa: BLE001 - any unusable answer degrades identically
        logger.warning(
            "terminology answer was unusable, correcting without it",
            answer_character_count=len(answer_text),
        )
        return EMPTY_TERMINOLOGY


def render_terminology_xml(terminology: Terminology) -> str:
    """Render typed terminology only at the prompt boundary."""
    return build_xml_document(
        "Terminology",
        {
            "Term": [
                {
                    "Canonical": term.canonical,
                    "Heard": {"Variant": list(term.heard.variants)},
                    "Kind": term.kind,
                }
                for term in terminology.terms
            ]
        },
    )

"""Correcting one part of the machine transcript."""


logger = get_logger(__name__)

_SYSTEM_TEMPLATE = "transcript/correct_transcript/system"
_USER_TEMPLATE = "transcript/correct_transcript/user"
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
        runtime.context.text_model,
        [
            SystemMessage(
                prompts.render(
                    _SYSTEM_TEMPLATE,
                    {
                        "language": correction.spoken_language,
                        "language_policy": prompts.render("language_policy"),
                    },
                )
            ),
            HumanMessage(
                prompts.render(
                    _USER_TEMPLATE,
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
            end_seconds=(
                clamped[position + 1][0] if position < len(clamped) - 1 else end_seconds
            ),
            content=content,
        )
        for position, (timestamp, content) in enumerate(clamped)
    ]

"""Joining correction results into one transcript."""


logger = get_logger(__name__)


async def assemble_corrected_transcript(
    state: LessonState, runtime: Runtime[GraphRuntime]
) -> dict[str, object]:
    """Orders, deduplicates, and re-chains every correction into one transcript."""
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
