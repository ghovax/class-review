"""Transcript input through the bundled Modal endpoints."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Final

import httpx

from teacher.importers.json_file import _join_recordings, _languages
from teacher.models import Recording, Transcript, TranscriptSegment

PARAKEET_LANGUAGES: Final[frozenset[str]] = frozenset(
    {
        "bg",
        "hr",
        "cs",
        "da",
        "nl",
        "en",
        "et",
        "fi",
        "fr",
        "de",
        "el",
        "hu",
        "it",
        "lv",
        "lt",
        "mt",
        "pl",
        "pt",
        "ro",
        "sk",
        "sl",
        "es",
        "sv",
        "ru",
        "uk",
    }
)


@dataclass(frozen=True, slots=True)
class ModalTranscriptImporter:
    """Routes supported languages to Parakeet and the rest to WhisperX."""

    parakeet_url: str
    whisperx_url: str
    proxy_key: str
    proxy_secret: str
    timeout_seconds: float = 3600.0

    async def load(
        self,
        recordings: Sequence[Recording],
        *,
        audio_languages: str | Sequence[str],
    ) -> Transcript:
        if not recordings:
            raise ValueError("recordings cannot be empty")
        languages = _languages(audio_languages, len(recordings))
        indexed = list(zip(recordings, languages, strict=True))
        groups: list[tuple[str, str | None, list[Recording]]] = []
        parakeet = [item for item, language in indexed if language in PARAKEET_LANGUAGES]
        if parakeet:
            groups.append((self.parakeet_url, None, parakeet))
        for language in dict.fromkeys(languages):
            whisper = [
                item
                for item, item_language in indexed
                if item_language == language and language not in PARAKEET_LANGUAGES
            ]
            if whisper:
                groups.append((self.whisperx_url, language, whisper))
        batches = await asyncio.gather(
            *(self._request(url, language, items) for url, language, items in groups)
        )
        by_index = {result[0]: result[1] for batch in batches for result in batch}
        ordered_segments = [
            by_index[item.index] for item in sorted(recordings, key=lambda item: item.index)
        ]
        return Transcript(
            segments=_join_recordings(ordered_segments),
            languages=tuple(dict.fromkeys(languages)),
        )

    async def _request(
        self, url: str, language: str | None, recordings: Sequence[Recording]
    ) -> list[tuple[int, tuple[TranscriptSegment, ...]]]:
        if not url.strip():
            raise ValueError("the selected Modal endpoint URL cannot be empty")
        payload: dict[str, Any] = {
            "items": [{"url": item.url, "index": item.index} for item in recordings]
        }
        if language is not None:
            payload["language"] = language
        headers = {"Modal-Key": self.proxy_key, "Modal-Secret": self.proxy_secret}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise ValueError("Modal transcription returned an invalid response")
        parsed = []
        for item in data["results"]:
            if item.get("error"):
                raise RuntimeError(f"transcription failed for {item.get('url')}: {item['error']}")
            parsed.append((item["index"], _parse_segments(item.get("segments"))))
        return parsed


def _parse_segments(raw: Any) -> tuple[TranscriptSegment, ...]:
    if not isinstance(raw, list):
        raise ValueError("Modal transcription result has no segment list")
    return tuple(
        TranscriptSegment(float(item["start"]), float(item["end"]), item["text"].strip())
        for item in raw
        if isinstance(item.get("text"), str) and item["text"].strip()
    )
