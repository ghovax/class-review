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
- model provider, model, reasoning effort, and explicit credentials/configuration source.

Do not proceed without the output and checkpoint destinations. A run usually takes 15–20 minutes, and an unsaved `LessonResult` disappears with its process.

Use `JsonTranscriptImporter` for timestamped JSON, construct `Transcript` for in-memory data, or implement `TranscriptImporter`. For audio, use `ModalTranscriptImporter`; it routes supported languages to Parakeet and the rest to WhisperX. Pass endpoint URLs and Modal proxy credentials directly. Deploy the bundled apps with `modal deploy -m teacher.modal_apps.parakeet` and `modal deploy -m teacher.modal_apps.whisperx`.

Configure models through `models-provider`. Use `ModelConfiguration` with a provider and model, and use `LangMeshProvider` when LangMesh's provider catalogue, API keys, custom endpoints, or ChatGPT/Cursor subscription authentication are needed. Pass LangMesh `Configuration` or `CredentialStore` values to `LangMeshProvider`; another `ModelProvider` implementation may be supplied for a different backend. Never ask for or use environment variables.

Build a small Python script around `GraphConfiguration` and `LessonGraph`. Supply `page_language_model` only with PDFs. Call `LessonGraph.generate` with the transcript, output language, stable run ID, and optional `DocumentSource` values.

Always launch the script detached:

```bash
nohup uv run python run_lesson.py >lesson.log 2>&1 </dev/null &
echo $! >lesson.pid
```

Return the PID, log path, checkpoint path, run ID, and expected output path immediately. Monitor with `tail lesson.log` and `ps -p "$(cat lesson.pid)"`; never hold an agent command open for the full run.

After an interruption, reconstruct the same `GraphConfiguration` and call `LessonGraph.resume(run_id)` with the same checkpoint and run ID. Use a new ID only when the user wants a fresh result.

Save the result before exit. Use `MarkdownExporter` for Markdown, `PdfExporter` for PDF, or `save_data` for complete JSON. A custom destination may implement `Exporter`; DOCX and other formats can consume the saved structure.

Do not ask for or pass a length. The graph derives chapter and concept structure from the material; content-aware length control remains a future improvement.
