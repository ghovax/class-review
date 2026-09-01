# Teacher

Teacher provides independent operations for turning timestamped transcripts and reference documents into structured lessons. It does not impose a workflow runner: applications choose the order, concurrency, persistence, retries, and any LangGraph integration themselves.

## Usage

The transcription application creates the timestamped transcript. Teacher receives that value; it does not download or transcribe audio.

```python
from models_provider import Models

from teacher import (
    ChapterWriter,
    GlossaryWriter,
    Lesson,
    LessonMaterials,
    ModelsConfiguration,
    OutlineWriter,
    ReferenceDocument,
    ReferenceReader,
    Transcript,
    TranscriptRevision,
    TranscriptSegment,
)

provider_models = Models.from_environment()
models = ModelsConfiguration(
    text=provider_models.chat("openai/gpt-4.1-mini"),
    vision=provider_models.chat("openai/gpt-4.1-mini"),
)

transcript = Transcript(
    segments=(
        TranscriptSegment(
            start_seconds=0.0,
            end_seconds=8.4,
            content="Today we introduce the derivative.",
        ),
        TranscriptSegment(
            start_seconds=8.4,
            end_seconds=22.7,
            content="A derivative measures how quickly a function changes.",
        ),
    ),
    languages=("en",),
)

documents = (ReferenceDocument.from_path("calculus-notes.pdf"),)

transcript = await TranscriptRevision(models).revise(transcript, language="en")
references = await ReferenceReader(models).read(documents)
materials = LessonMaterials(transcript, references, language="en")
outline = await OutlineWriter(models).draft(materials)
chapters = tuple(
    await ChapterWriter(models).write(chapter, materials)
    for chapter in outline.chapters
)
glossary = await GlossaryWriter(models).write(outline, chapters, language="en")
lesson = Lesson.from_parts(outline=outline, chapters=chapters, glossary=glossary)
```

Each operation is independent. A caller can skip transcript revision, provide a hand-written `LessonOutline`, write chapters concurrently, or replace one operation with a compatible class. The data objects contain values; the operation classes perform actions.

## Models

`ModelsConfiguration` is the only model dependency each built-in operation needs. `text` is required. `vision` is optional and falls back to `text` for reference pages. Any `models-provider` chat model, or another compatible model implementing `ainvoke`, can be supplied.

```python
models = ModelsConfiguration(text=text_model, vision=vision_model)
outline_writer = OutlineWriter(models)
```

## Custom operations

The built-in classes are also the extension points. Override only the operation an application wants to change:

```python
from teacher import LessonMaterials, LessonOutline, OutlineWriter


class CustomOutlineWriter(OutlineWriter):
    async def draft(self, materials: LessonMaterials) -> LessonOutline:
        return LessonOutline(
            title="Calculus fundamentals",
            description="An introduction to derivatives.",
            chapters=(),
        )


outline = await CustomOutlineWriter(models).draft(materials)
```

An application can use these operations in ordinary Python, its own LangGraph, or another workflow system. Teacher does not expose a graph, checkpoint manager, or orchestration object.

## Exporting

Export is separate from lesson creation:

```python
from teacher import ExportFormat, export_to_bytes

markdown = export_to_bytes(lesson, format=ExportFormat.MARKDOWN)
pdf = export_to_bytes(lesson, format=ExportFormat.PDF)
```

PDF export requires `pandoc` and `typst` on `PATH`.
