"""Transcript input from local JSON files."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from teacher.models import Recording, Transcript, TranscriptSegment


class JsonTranscriptImporter:
    """Loads each recording URL as a JSON transcript path."""

    async def load(
        self,
        recordings: Sequence[Recording],
        *,
        audio_languages: str | Sequence[str],
    ) -> Transcript:
        languages = _languages(audio_languages, len(recordings))
        payloads = await asyncio.gather(
            *(asyncio.to_thread(_read_json, Path(item.url)) for item in recordings)
        )
        ordered = sorted(zip(recordings, payloads, strict=True), key=lambda item: item[0].index)
        return Transcript(
            segments=_join_recordings([_segments(payload) for _, payload in ordered]),
            languages=tuple(dict.fromkeys(languages)),
        )


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _segments(payload: Any) -> tuple[TranscriptSegment, ...]:
    raw = payload.get("segments", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw, list):
        raise ValueError("transcript JSON must contain a segments list")
    segments = []
    for item in raw:
        start = item.get("start_seconds", item.get("start"))
        end = item.get("end_seconds", item.get("end"))
        content = item.get("content", item.get("text"))
        if not isinstance(start, int | float) or not isinstance(end, int | float):
            raise ValueError("each transcript segment needs numeric start and end")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("each transcript segment needs non-empty text")
        segments.append(TranscriptSegment(float(start), float(end), content.strip()))
    return tuple(segments)


def _languages(value: str | Sequence[str], count: int) -> tuple[str, ...]:
    if isinstance(value, str):
        languages = (value.strip().replace("_", "-").lower(),) * count
    else:
        languages = tuple(item.strip().replace("_", "-").lower() for item in value)
    if len(languages) != count or any(not item for item in languages):
        raise ValueError("audio_languages must provide one language per recording")
    return languages


def _join_recordings(
    recordings: Sequence[Sequence[TranscriptSegment]],
) -> tuple[TranscriptSegment, ...]:
    joined: list[TranscriptSegment] = []
    offset = 0.0
    for segments in recordings:
        for segment in sorted(segments, key=lambda item: item.start_seconds):
            joined.append(
                TranscriptSegment(
                    start_seconds=segment.start_seconds + offset,
                    end_seconds=segment.end_seconds + offset,
                    content=segment.content,
                )
            )
        if segments:
            offset = joined[-1].end_seconds
    return tuple(joined)
