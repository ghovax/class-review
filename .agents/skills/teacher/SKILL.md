---
name: teacher
description: Generate, resume, and export a durable lesson with the teacher Python library. Use for long-running lesson generation from audio, timestamped transcripts, and optional PDFs.
---

# Lesson generation

Before starting, ask for:

- transcript files or audio URLs;
- one audio language per recording;
- desired lesson language;
- optional PDF sources;
- final output location and format;
- an optional persistent SQLite checkpoint location for durable resume;
- model identifiers, reasoning effort, and the credential source.

The checkpoint is optional for an in-memory run. An unsaved `LessonResult` disappears
with the process.

Construct `Transcript` from the caller's timestamped data. Provide supplementary
documents as `DocumentSource(content=file_bytes, file_name=...)`; the bytes may come
from local storage, a web client, or object storage. Teacher decodes supplied PDF bytes
internally. Audio transcription and file retrieval remain application responsibilities.

Create ready-to-use models through the independent `models-provider` package, then
assign them with `ModelSelection`. Use one text model and add a vision model only when
page interpretation needs a different model. Credentials and provider-specific transport
stay inside Models Provider.

Build a small Python script around `LessonGraph`:

```python
from models_provider import Models
from teacher import LessonGraph, ModelSelection

models = Models()
graph = LessonGraph(
    models=ModelSelection(text=models.chat("openai/gpt-4.1-mini")),
)
```

Call `LessonGraph.generate` with the transcript, output language, and optional
`DocumentSource` values. The graph creates a run identifier when one is not supplied.

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

Save the typed `LessonResult` before exit. Use `render_export_markdown` or
`export_to_bytes(..., format="markdown")` for Markdown and
`export_to_bytes(..., format="pdf")` or `PdfExporter` for PDF. Other formats can consume
the typed `Lesson` value directly.

Do not ask for or pass a length. The graph derives chapter and concept structure from
the material; content-aware length control remains a future improvement.
