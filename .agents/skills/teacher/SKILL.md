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
- durable SQLite checkpoint location and stable run ID;
- model provider, model, reasoning effort, and explicit credentials/configuration
  source.

Do not proceed without the output and checkpoint destinations. A run usually takes 15–20
minutes, and an unsaved `LessonResult` disappears with its process.

Construct `Transcript` from the caller's timestamped data. Provide supplementary
documents as `DocumentSource(content=file_bytes, file_name=...)`; the bytes may come
from local storage, a web client, or object storage. Supply a `DocumentReader` only when
documents are present. Audio transcription, file retrieval, and persistence remain
application responsibilities.

Configure models through the independent `models-provider` package. Use
`ModelConfiguration` with a provider and model, then pass any `ModelProvider`
implementation to `GraphModels`. Credentials and provider-specific transport belong to
that implementation; Teacher does not read environment variables or select a provider.

Build a small Python script around `GraphConfiguration` and `LessonGraph`. Supply
`page_language_model` only with PDFs. Call `LessonGraph.generate` with the transcript,
output language, stable run ID, and optional `DocumentSource` values.

Always launch the script detached:

```bash
nohup uv run python run_lesson.py >lesson.log 2>&1 </dev/null &
echo $! >lesson.pid
```

Return the PID, log path, checkpoint path, run ID, and expected output path immediately.
Monitor with `tail lesson.log` and `ps -p "$(cat lesson.pid)"`; never hold an agent
command open for the full run.

After an interruption, reconstruct the same `GraphConfiguration` and call
`LessonGraph.resume(run_id)` with the same checkpoint and run ID. Use a new ID only when
the user wants a fresh result.

Save the typed `LessonResult` before exit. Use `render_export_markdown` or
`export_to_bytes(..., format="markdown")` for Markdown and
`export_to_bytes(..., format="pdf")` or `PdfExporter` for PDF. Other formats can consume
the typed `Lesson` value directly.

Do not ask for or pass a length. The graph derives chapter and concept structure from
the material; content-aware length control remains a future improvement.
