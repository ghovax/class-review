# Teacher

Teacher turns a timestamped transcript and optional document bytes into a structured
lesson through a resumable graph. It cleans the transcript, extracts document material,
plans chapters, writes the lesson, builds a glossary, and provides Markdown or PDF
bytes.

## Public flow

```python
from models_provider import Models
from teacher import DocumentSource, LessonGraph, ModelSelection

models = Models()

graph = LessonGraph(
    models=ModelSelection(text=models.chat("openai/gpt-4.1-mini")),
)

source = DocumentSource.from_path("/tmp/calculus-lecture.pdf")

async with graph:
    result = await graph.generate(
        transcript=transcript,
        documents=(source,),
        output_language="en",
    )
```

`models` is a ready-to-use model selection. The text model handles transcript and lesson
writing. An optional vision model handles rendered document pages; when omitted, the
text model is reused.

```python
ModelSelection(
    text=models.chat("openai/gpt-4.1-mini"),
    vision=models.chat("openai/gpt-4.1-mini"),
)
```

Teacher does not load a model catalogue or resolve credentials. Models Provider owns
those concerns.

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

DocumentSource(
    content=pdf_bytes,
    file_name="calculus-lecture.pdf",
)
```

`DocumentSource.from_path(...)` is a convenience that reads bytes once. A web client or
object-storage client can provide the same bytes directly. Teacher renders PDF bytes
internally, so the graph does not care where they came from.

## Output contract

```python
LessonResult(
    lesson=Lesson(...),
    usage_by_model={"openai/gpt-4.1-mini": ModelUsage(...)},
    run_id="generated-run-identity",
)
```

The run identity is generated automatically. Pass an explicit `run_id` only when an
application needs a stable checkpoint key, then call `resume(run_id)` after an
interruption.

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

XML is used only at the model boundary. Teacher parses it immediately into typed values
and does not store raw XML in graph state.
