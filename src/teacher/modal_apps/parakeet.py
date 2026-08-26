"""Modal deployment for NVIDIA Parakeet transcription."""

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
    .uv_pip_install("nemo_toolkit[asr]", "numpy")
    .entrypoint([])
)
cpu_image = modal.Image.debian_slim().pip_install("fastapi[standard]")
app = modal.App("teacher-parakeet")
model_cache = modal.Volume.from_name("teacher-parakeet-cache", create_if_missing=True)


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
    """Keeps the Parakeet model ready on a GPU container."""

    @modal.enter(snap=True)
    def load_weights(self) -> None:
        """Load, configure, and warm the model for snapshots."""

        import nemo.collections.asr as nemo_asr  # pyright: ignore[reportMissingImports]
        import numpy as np

        self.model = nemo_asr.models.ASRModel.from_pretrained("nvidia/parakeet-tdt-0.6b-v3").cuda()
        self.model.change_attention_model(
            self_attention_model="rel_pos_local_attn", att_context_size=[256, 256]
        )
        self.model.transcribe([np.zeros(16000, dtype=np.float32)], batch_size=1, timestamps=True)

    @modal.method()
    def transcribe_url(self, url: str, index: int) -> dict:
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
    """Transcribe a batch in parallel across GPU containers."""

    try:
        items = validate_items(data)
    except MediaValidationError as error:
        return {"error": str(error)}, error.status_code
    model = ParakeetModel()
    results = list(
        model.transcribe_url.map([item["url"] for item in items], [item["index"] for item in items])
    )
    return {"results": results}


@app.local_entrypoint()
def main(url: str) -> None:
    """Run a comma-separated URL batch from the Modal CLI."""

    urls = [item.strip() for item in url.split(",") if item.strip()]
    model = ParakeetModel()
    print(list(model.transcribe_url.map(urls, list(range(len(urls))))))
