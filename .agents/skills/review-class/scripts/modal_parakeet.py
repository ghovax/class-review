"""Modal deployment for NVIDIA Parakeet lecture transcription."""

from __future__ import annotations

import json
import subprocess
import tempfile
import urllib.error
import urllib.request

import modal


class MediaValidationError(ValueError):
    """A media validation failure with an HTTP status for the endpoint."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def download(url: str) -> bytes:
    """Download remote media bytes with a bounded request."""
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def probe_audio(file_bytes: bytes) -> dict[str, float | str | None]:
    """Validate media and return its duration and detected format."""
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
    """Decode media to mono 16 kHz signed PCM for the ASR model."""
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
    """Validate and order endpoint inputs by their stable integer index."""
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


gpu_image = (
    modal.Image.from_registry("nvidia/cuda:12.8.0-cudnn-devel-ubuntu22.04", add_python="3.12")
    .env(
        {
            "HF_XET_HIGH_PERFORMANCE": "1",
            "HF_HOME": "/cache",
            "TORCH_HOME": "/root/.cache/torch",
        }
    )
    .apt_install("ffmpeg")
    .uv_pip_install("nemo_toolkit[asr]", "numpy")
    .entrypoint([])
)
cpu_image = modal.Image.debian_slim().pip_install("fastapi[standard]")
app = modal.App("review-class-parakeet")
model_cache = modal.Volume.from_name("review-class-parakeet-cache", create_if_missing=True)


@app.cls(
    gpu="L40S",
    image=gpu_image,
    min_containers=0,
    scaledown_window=2,
    enable_memory_snapshot=True,
    experimental_options={"enable_gpu_snapshot": True},
    volumes={"/cache": model_cache},
)
class ParakeetModel:
    """Keep the Parakeet model warm on a GPU container."""

    @modal.enter(snap=True)
    def load_weights(self) -> None:
        """Load and warm the fixed model before accepting requests."""
        import nemo.collections.asr as nemo_asr  # pyright: ignore[reportMissingImports]
        import numpy as np

        self.model = nemo_asr.models.ASRModel.from_pretrained(
            "nvidia/parakeet-tdt-0.6b-v3"
        ).cuda()
        self.model.change_attention_model(
            self_attention_model="rel_pos_local_attn", att_context_size=[256, 256]
        )
        self.model.transcribe([np.zeros(16000, dtype=np.float32)], batch_size=1, timestamps=True)

    @modal.method()
    def transcribe_url(self, url: str, index: int) -> dict:
        """Download, validate, decode, and transcribe one recording."""
        import numpy as np

        base = {"url": url, "index": index}
        try:
            file_bytes = download(url)
            probe_audio(file_bytes)
            pcm_bytes = decode_to_pcm(file_bytes)
        except urllib.error.URLError as error:
            return {
                **base,
                "error": f"Failed to download file: {error.reason}",
                "status_code": 502,
            }
        except MediaValidationError as error:
            return {**base, "error": str(error), "status_code": error.status_code}

        waveform = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        hypothesis = self.model.transcribe([waveform], batch_size=1, timestamps=True)[0]
        return {
            **base,
            "segments": [
                {"start": item["start"], "end": item["end"], "text": item["segment"]}
                for item in hypothesis.timestamp.get("segment", [])
            ],
        }


@app.function(image=cpu_image, timeout=3600)
@modal.fastapi_endpoint(method="POST", requires_proxy_auth=True)
def transcribe(data: dict):
    """Transcribe indexed recordings in parallel across GPU containers."""
    try:
        items = validate_items(data)
    except MediaValidationError as error:
        return {"error": str(error)}, error.status_code
    model = ParakeetModel()
    return {
        "results": list(
            model.transcribe_url.map(
                [item["url"] for item in items], [item["index"] for item in items]
            )
        )
    }


@app.local_entrypoint()
def main(url: str) -> None:
    """Run comma-separated URLs through the Modal deployment."""
    urls = [item.strip() for item in url.split(",") if item.strip()]
    model = ParakeetModel()
    print(list(model.transcribe_url.map(urls, list(range(len(urls))))))
