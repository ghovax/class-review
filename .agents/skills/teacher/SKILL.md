---
name: teacher
description: Generate, resume, and export a durable lesson with the teacher Python library. Use for long-running lesson generation from audio, timestamped transcripts, and optional PDFs.
---

# Lesson generation

Before starting, ask for:

- a saved timestamped transcript, or an audio source when a separate transcription
  operation is requested;
- one audio language per recording when transcribing separately;
- desired lesson language;
- optional PDF sources or document bytes;
- final output location and format;
- an optional persistent SQLite checkpoint location for durable resume;
- model identifiers, reasoning effort, and the credential source.

## Transcription lifecycle

Teacher does not transcribe audio. Run transcription separately, preserve the original
timestamped result on durable storage, and construct `Transcript` from that saved data
when invoking Teacher. Never retranscribe the same recording for a later lesson run
unless the user explicitly requests a new transcription.

Use a simple application-owned transcript file, for example:

```json
{
  "languages": ["en"],
  "segments": [
    {
      "start_seconds": 0.0,
      "end_seconds": 4.2,
      "content": "Today we introduce spaced repetition."
    }
  ]
}
```

The checkpoint is optional for an in-memory run. An unsaved `LessonResult` disappears
with the process.

Construct `Transcript` from the saved timestamped data. Provide a local supplementary
document with `DocumentSource.from_path("/tmp/lecture-notes.pdf")`. For Google Drive, a
web client, or object storage, pass the retrieved file bytes and display name to
`DocumentSource`; Teacher decodes supplied PDF bytes internally. Audio transcription and
file retrieval remain application responsibilities.

Create ready-to-use models through the independent `models-provider` package, then
assign them with `ModelSelection`. Use one text model and add a vision model only when
page interpretation needs a different model. Credentials and provider-specific transport
stay inside Models Provider.

The host must load `.env` files or other secret sources itself before calling
`Models.from_environment()`. `Models()` does not inspect process environment variables,
and neither library parses `.env` files. An explicitly supplied credential store takes
precedence when both sources contain credentials.

Build a small Python script around `LessonGraph`:

```python
from models_provider import Models
from teacher import LessonGraph, ModelSelection

models = Models.from_environment()
graph = LessonGraph(
    models=ModelSelection(text=models.chat("openai/gpt-4.1-mini")),
)
```

Call `LessonGraph.generate` with the transcript, output language, and optional
`DocumentSource` values. The graph creates a run identifier when one is not supplied.

A complete short-lived invocation can look like this:

```python
import asyncio
import json
from pathlib import Path

from models_provider import Models
from teacher import (
    DocumentSource,
    ExportFormat,
    LessonGraph,
    ModelSelection,
    Transcript,
    TranscriptSegment,
    export_to_bytes,
)


def read_transcript(path: Path) -> Transcript:
    data = json.loads(path.read_text(encoding="utf-8"))
    return Transcript(
        segments=tuple(TranscriptSegment(**segment) for segment in data["segments"]),
        languages=tuple(data["languages"]),
    )


async def main() -> None:
    graph = LessonGraph(
        models=ModelSelection(text=Models.from_environment().chat("openai/gpt-4.1-mini")),
        checkpoint_path=Path("/tmp/lecture.lesson.sqlite"),
    )
    async with graph:
        result = await graph.generate(
            transcript=read_transcript(Path("/tmp/lecture.transcript.json")),
            documents=(DocumentSource.from_path("/tmp/lecture-notes.pdf"),),
            output_language="en",
            run_id="lecture-2026-08-27",
        )
    Path("/tmp/lecture.lesson.md").write_bytes(
        export_to_bytes(result.lesson, format=ExportFormat.MARKDOWN)
    )


asyncio.run(main())
```

For a Google Drive source, replace `DocumentSource.from_path(...)` with a
`DocumentSource` built from the bytes returned by the Drive client. The Drive client and
its authentication remain outside Teacher.

Always launch the script detached:

```bash
nohup uv run python run_lesson.py >lesson.log 2>&1 </dev/null &
echo $! >lesson.pid
```

Return the PID, log path, checkpoint path, and expected output path immediately. Monitor
with `tail lesson.log` and `ps -p "$(cat lesson.pid)"`; never hold an agent command open
for the full run.

After an interruption, reconstruct the same graph with the same persistent checkpoint
location and call `LessonGraph.resume(run_id)`. Use a new identifier only when the user
wants a fresh result.

Persist or export the typed `LessonResult` before exit. Use `render_export_markdown` or
`export_to_bytes(..., format="markdown")` for Markdown and
`export_to_bytes(..., format="pdf")` or `PdfExporter` for PDF. Other formats can consume
the typed `Lesson` value directly.

Do not ask for or pass a length. The graph derives chapter and concept structure from
the material; content-aware length control remains a future improvement.
