# Teacher

Teacher turns a timestamped transcript and optional document bytes into a structured lesson through a resumable graph. It cleans the transcript, extracts document material, plans chapters, writes the lesson, builds a glossary, and provides Markdown or PDF bytes.

## Invocation

Transcribe audio separately and save the timestamped result before invoking Teacher. That saved transcript can be reused for every later lesson generation.

```python
from __future__ import annotations

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


def load_transcript(path: Path) -> Transcript:
    """Load the timestamped transcript saved by the transcription application."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return Transcript(
        segments=tuple(
            TranscriptSegment(
                start_seconds=segment["start_seconds"],
                end_seconds=segment["end_seconds"],
                content=segment["content"],
            )
            for segment in data["segments"]
        ),
        languages=tuple(data["languages"]),
    )


async def main() -> None:
    transcript = load_transcript(Path("/tmp/calculus.transcript.json"))
    local_pdf = DocumentSource.from_path("/tmp/calculus-notes.pdf")

    # Documents can come from any source; Teacher receives their bytes.
    documents = (local_pdf,)
    models = Models.from_environment()
    graph = LessonGraph(
        models=ModelSelection(text=models.chat("openai/gpt-4.1-mini")),
        checkpoint_path=Path("/tmp/calculus.lesson.sqlite"),
    )

    async with graph:
        result = await graph.generate(
            transcript=transcript,
            documents=documents,
            output_language="en",
            run_id="calculus-lecture",
        )

    Path("/tmp/calculus.lesson.md").write_bytes(
        export_to_bytes(result.lesson, format=ExportFormat.MARKDOWN)
    )


asyncio.run(main())
```

The application owns source clients and authentication; Teacher receives only the resulting bytes. The SQLite checkpoint and the Markdown output are explicit files, so a later process can resume or reuse the generated result.

Load model environment variables in the host before calling `Models.from_environment()`; neither Teacher nor Models Provider parses `.env` files.

`models` is a ready-to-use model selection. The text model handles transcript and lesson writing. An optional vision model handles rendered document pages; when omitted, the text model is reused.

```python
ModelSelection(
    text=models.chat("openai/gpt-4.1-mini"),
    vision=models.chat("openai/gpt-4.1-mini"),
)
```

Teacher does not load a model catalogue or resolve credentials. Models Provider owns those concerns.

## Input contract

```python
Transcript(
    segments=(
        TranscriptSegment(
            start_seconds=0.0,
            end_seconds=4.2,
            content="Today we introduce spaced repetition.",
        ),
    ),
    languages=("en",),
)

document_path = Path("/tmp/calculus-lecture.pdf")
document = DocumentSource(
    content=document_path.read_bytes(),
    file_name=document_path.name,
)
```

`DocumentSource.from_path(...)` is a convenience that reads bytes once. A web client, Google Drive client, or object-storage client can provide the same bytes directly. Teacher renders PDF bytes internally, so the graph does not care where they came from.

## Output contract

```python
LessonResult(
    lesson=Lesson(...),
    usage_by_model={"openai/gpt-4.1-mini": ModelUsage(...)},
    run_id="generated-run-identity",
)
```

The run identity is generated automatically. Pass an explicit `run_id` only when an application needs a stable checkpoint key, then call `resume(run_id)` after an interruption.

Exports are separate from graph execution:

```python
markdown_bytes = export_to_bytes(lesson, format=ExportFormat.MARKDOWN)
pdf_bytes = export_to_bytes(lesson, format=ExportFormat.PDF)
```

## Package layout

| Area               | Responsibility                              |
| ------------------ | ------------------------------------------- |
| `graph.py`         | Graph routing and node relationships        |
| `transcript/`      | Terminology and transcript correction       |
| `documents/`       | Page extraction, sections, and explanations |
| `lesson/`          | Planning, chapters, glossary, and assembly  |
| `models.py`        | Caller inputs and generated lesson values   |
| `configuration.py` | Model selection and execution policies      |
| `xml.py`           | Compact model XML parsing and recovery      |
| `outputs.py`       | Markdown and PDF export                     |

XML is used only at the model boundary. Teacher parses it immediately into typed values and does not store raw XML in graph state.

## Visual graph

Run `uv run --with "langgraph-cli[inmem]" langgraph dev --no-browser` from the repository root. The command starts a local in-memory server and prints the LangGraph Studio URL.
