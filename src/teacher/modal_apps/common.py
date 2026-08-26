"""Media handling shared by the Modal transcription applications."""

from __future__ import annotations

import json
import subprocess
import tempfile
import urllib.request


class MediaValidationError(ValueError):
    """Carries the HTTP status appropriate for a media failure."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def download(url: str) -> bytes:
    """Download remote media bytes."""

    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def probe_audio(file_bytes: bytes) -> dict[str, float | str | None]:
    """Validate media and return its duration and format."""

    with tempfile.NamedTemporaryFile(suffix=".audio") as temporary:
        temporary.write(file_bytes)
        temporary.flush()
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                temporary.name,
            ],
            capture_output=True,
            check=False,
        )
    if result.returncode != 0:
        raise MediaValidationError(f"Not a valid media file: {result.stderr.decode()}")
    info = json.loads(result.stdout)
    streams = info.get("streams", [])
    if not any(stream.get("codec_type") == "audio" for stream in streams):
        raise MediaValidationError("No audio stream found in file")
    duration = float(info.get("format", {}).get("duration") or 0)
    if duration <= 0:
        duration = next(
            (
                float(item["duration"])
                for item in streams
                if item.get("codec_type") == "audio" and item.get("duration")
            ),
            0.0,
        )
    if duration <= 0:
        raise MediaValidationError("Could not determine audio duration")
    if duration > 10_800:
        raise MediaValidationError("Audio exceeds the three-hour limit")
    return {"duration": duration, "format": info.get("format", {}).get("format_name")}


def decode_to_pcm(file_bytes: bytes) -> bytes:
    """Decode media to mono 16 kHz signed PCM."""

    with tempfile.NamedTemporaryFile(suffix=".audio") as temporary:
        temporary.write(file_bytes)
        temporary.flush()
        result = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-threads",
                "0",
                "-i",
                temporary.name,
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-f",
                "s16le",
                "pipe:1",
            ],
            capture_output=True,
            check=False,
        )
    if result.returncode != 0:
        raise MediaValidationError(f"ffmpeg failed: {result.stderr.decode()}", status_code=422)
    return result.stdout


def validate_items(data: dict) -> list[dict[str, str | int]]:
    """Validate and order the endpoint item payload."""

    items = data.get("items")
    if not isinstance(items, list) or not items:
        raise MediaValidationError("Missing or empty 'items' field")
    validated = []
    for item in items:
        if not isinstance(item, dict):
            raise MediaValidationError("Each item must be an object")
        url, index = item.get("url"), item.get("index")
        if not isinstance(url, str) or not url.strip() or not isinstance(index, int):
            raise MediaValidationError("Each item needs a URL and integer index")
        validated.append({"url": url.strip(), "index": index})
    return sorted(validated, key=lambda item: int(item["index"]))
