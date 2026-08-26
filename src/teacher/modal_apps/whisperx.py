"""Modal deployment for WhisperX transcription."""

from __future__ import annotations

import urllib.error

import modal

from teacher.modal_apps.common import (
    MediaValidationError,
    decode_to_pcm,
    download,
    probe_audio,
    validate_items,
)

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
    .uv_pip_install("whisperx", "numpy")
    .entrypoint([])
)
cpu_image = modal.Image.debian_slim().pip_install("fastapi[standard]")
app = modal.App("teacher-whisperx")
model_cache = modal.Volume.from_name("teacher-whisperx-cache", create_if_missing=True)


def merge_adjacent_segments(segments: list[dict]) -> list[dict]:
    """Merge adjacent Whisper segments until a sentence terminator."""

    if not segments:
        return []
    closers = "\"'”’»›)]}）】〕］｝〉》」』"
    terminators = ".!?…。！？｡۔؟॥။"
    merged: list[dict] = []
    current = dict(segments[0])
    current["text"] = (current.get("text") or "").strip()
    for raw in segments[1:]:
        following = dict(raw)
        following["text"] = (following.get("text") or "").strip()
        trailing = current["text"].rstrip()
        while trailing and trailing[-1] in closers:
            trailing = trailing[:-1].rstrip()
        if trailing and trailing[-1] in terminators:
            merged.append(_capitalize(current))
            current = following
            continue
        text = following["text"]
        for index, character in enumerate(text):
            if character.isalpha():
                text = text[:index] + character.lower() + text[index + 1 :]
                break
        separator = (
            ""
            if not current["text"]
            or not text
            or current["text"].endswith(" ")
            or text[0] in ",.;:!?%)]}”’»›"
            else " "
        )
        current["text"] += separator + text
        current["end"] = following.get("end", current.get("end"))
    merged.append(_capitalize(current))
    return merged


def _capitalize(segment: dict) -> dict:
    """Capitalize the first alphabetic character of one segment."""

    text = segment.get("text") or ""
    for index, character in enumerate(text):
        if character.isalpha():
            segment["text"] = text[:index] + character.upper() + text[index + 1 :]
            break
    return segment


@app.cls(
    gpu="L40S",
    image=gpu_image,
    min_containers=0,
    scaledown_window=2,
    enable_memory_snapshot=True,
    experimental_options={"enable_gpu_snapshot": True},
    volumes={"/cache": model_cache},
)
class WhisperXModel:
    """Keeps the WhisperX model ready on a GPU container."""

    @modal.enter(snap=True)
    def load_weights(self) -> None:
        """Load and warm the fixed WhisperX model."""

        import numpy as np
        import whisperx  # pyright: ignore[reportMissingImports]

        self.model = whisperx.load_model(
            whisper_arch="large-v3-turbo",
            device="cuda",
            compute_type="float16",
            download_root="/cache",
            asr_options={
                "temperatures": [0.0],
                "initial_prompt": None,
                "beam_size": 1,
                "condition_on_previous_text": False,
                "compression_ratio_threshold": 1.8,
                "log_prob_threshold": -0.5,
                "no_speech_threshold": 0.5,
                "hallucination_silence_threshold": 2.0,
                "suppress_blank": True,
                "repetition_penalty": 1.15,
                "no_repeat_ngram_size": 4,
            },
            vad_options={"vad_onset": 0.5, "vad_offset": 0.363},
        )
        self.model.transcribe(np.zeros(16000, dtype=np.float32), batch_size=1)

    @modal.method()
    def transcribe_url(self, url: str, index: int, language: str | None = None) -> dict:
        """Download, decode, and transcribe one URL inside the GPU container."""

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
        result = self.model.transcribe(
            audio=waveform, batch_size=64, language=language, task="transcribe"
        )
        return {
            **base,
            "segments": merge_adjacent_segments(result.get("segments", [])),
            "detected_language": result.get("language", language or ""),
        }


@app.function(image=cpu_image, timeout=3600)
@modal.fastapi_endpoint(method="POST", requires_proxy_auth=True)
def transcribe(data: dict):
    """Transcribe one same-language input set across GPU containers."""

    try:
        items = validate_items(data)
    except MediaValidationError as error:
        return {"error": str(error)}, error.status_code
    language = (data.get("language") or "").strip().replace("_", "-").lower() or None
    model = WhisperXModel()
    results = list(
        model.transcribe_url.map(
            [item["url"] for item in items],
            [item["index"] for item in items],
            [language] * len(items),
        )
    )
    return {"results": results}


@app.local_entrypoint()
def main(url: str, language: str = "") -> None:
    """Run a comma-separated set of URLs from the Modal CLI."""

    urls = [item.strip() for item in url.split(",") if item.strip()]
    selected = language.strip().replace("_", "-").lower() or None
    model = WhisperXModel()
    print(list(model.transcribe_url.map(urls, list(range(len(urls))), [selected] * len(urls))))
