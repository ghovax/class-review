"""Consolidated Teacher implementation."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from teacher.models import Recording, Transcript, TranscriptSegment, ImportedDocument, DocumentSource, RenderedPage
from teacher.support import PipelineError
from typing import Any, Final, cast
from urllib.parse import unquote, urlparse
import asyncio
import base64
import io
import json
import re

import httpx

"""Transcript and PDF input adapters."""

"""Transcript input from local JSON files."""


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

"""Transcript input through the bundled Modal endpoints."""


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

"""Default PDF input from local paths or URLs."""


_PDF_SIGNATURE = b"%PDF-"
_CONFIRMATION_LINK = re.compile(
    r"""(?:href|action)=["'](?P<target>[^"']*confirm=[^"']*)["']""", re.I
)


def _read_local_pdf(location: str) -> tuple[bytes, str, str] | None:
    """Read a local PDF without blocking the event loop."""
    path = Path(location).expanduser()
    if not path.is_file():
        return None
    return path.read_bytes(), str(path.resolve()), path.name


class WebPdfImporter:
    """Downloads or reads a PDF and renders every page as a JPEG data URL."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 60.0,
        render_scale: float = 1.5,
        image_quality: int = 85,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.render_scale = render_scale
        self.image_quality = image_quality
        self.client = client

    async def load(self, source: DocumentSource, *, document_index: int) -> ImportedDocument:
        content, resolved_url, downloaded_name = await self._read(source.url)
        if not content.startswith(_PDF_SIGNATURE):
            raise PipelineError.terminal("the source is not a PDF", {"source": source.url})
        file_name = self._file_name(source, downloaded_name)
        return ImportedDocument(
            document_index=document_index,
            source_url=resolved_url,
            file_name=file_name,
            pages=tuple(self._render(content)),
        )

    async def _read(self, location: str) -> tuple[bytes, str, str | None]:
        local = await asyncio.to_thread(_read_local_pdf, location)
        if local is not None:
            return local

        if self.client is not None:
            response = await self._request(self.client, location)
            response = await self._follow_confirmation(self.client, response)
            return self._response(response)

        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
            response = await self._request(client, location)
            response = await self._follow_confirmation(client, response)
            return self._response(response)
    async def _request(self, client: httpx.AsyncClient, location: str) -> httpx.Response:
        try:
            response = await client.get(location, follow_redirects=True)
        except httpx.HTTPError as error:
            raise PipelineError.retryable(
                "the document could not be downloaded", {"source": location}, error
            ) from error
        if response.status_code >= 400:
            retryable = response.status_code == 429 or response.status_code >= 500
            raise PipelineError(
                "the document source returned an error",
                {
                    "source": location,
                    "status_code": response.status_code,
                    "retryable": retryable,
                },
            )
        return response

    async def _follow_confirmation(
        self, client: httpx.AsyncClient, response: httpx.Response
    ) -> httpx.Response:
        if "text/html" not in (response.headers.get("content-type") or ""):
            return response
        match = _CONFIRMATION_LINK.search(response.text)
        if match is None:
            return response
        target = str(response.url.join(match.group("target").replace("&amp;", "&")))
        return await self._request(client, target)

    def _response(self, response: httpx.Response) -> tuple[bytes, str, str | None]:
        disposition = response.headers.get("content-disposition")
        name = None
        if disposition:
            message = EmailMessage()
            message["Content-Disposition"] = disposition
            name = message.get_filename()
        return response.content, str(response.url), name.strip() if name else None

    def _render(self, content: bytes) -> list[RenderedPage]:
        try:
            import pypdfium2
        except ImportError as error:
            raise PipelineError.terminal(
                "PDF input requires pypdfium2", {"required_package": "pypdfium2"}
            ) from error
        try:
            document = pypdfium2.PdfDocument(content)
        except Exception as error:
            raise PipelineError.terminal("the PDF could not be opened", cause=error) from error
        try:
            return [
                RenderedPage(
                    page_number=index + 1,
                    image_data_url=self._encode(
                        cast(Any, document[index]).render(scale=self.render_scale).to_pil()
                    ),
                )
                for index in range(len(document))
            ]
        finally:
            document.close()

    def _encode(self, image: object) -> str:
        buffer = io.BytesIO()
        image.convert("RGB").save(  # type: ignore[attr-defined]
            buffer, format="JPEG", quality=self.image_quality
        )
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"

    @staticmethod
    def _file_name(source: DocumentSource, downloaded_name: str | None) -> str:
        for candidate in (downloaded_name, source.file_name):
            if candidate and candidate.strip():
                return candidate.strip()
        path_name = Path(unquote(urlparse(source.url).path)).name.strip()
        if path_name:
            return path_name
        raise PipelineError.terminal("the document has no usable name", {"source": source.url})
