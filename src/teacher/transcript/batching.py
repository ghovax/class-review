"""Deterministic correction batching."""

from __future__ import annotations

from collections.abc import Sequence

from teacher.errors import PipelineError
from teacher.models import TranscriptSegment


def build_batches(
    segments: Sequence[TranscriptSegment], span_seconds: float
) -> list[list[TranscriptSegment]]:
    """Pack ordered transcript segments into bounded time windows."""

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
