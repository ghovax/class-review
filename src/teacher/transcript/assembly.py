"""Assemble corrected transcript segments."""

from __future__ import annotations

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime
from langgraph.types import Overwrite
from teacher.configuration import GraphRuntime
from teacher.models import (
    TranscriptAssembled,
    TranscriptSegment,
)
from teacher.state import LessonState
from teacher.support import get_logger, PipelineError

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
