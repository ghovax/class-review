# Teacher

Teacher provides independent operations for turning a timestamped transcript and reference documents into a structured lesson. It does not impose a workflow runner; an application owns ordering, concurrency, persistence, retries, and any LangGraph integration.

## Usage

The transcription application creates the timestamped transcript. Teacher receives that value and does not download or transcribe audio.

```python
from models_provider import Models

from teacher import (
    ChapterWriter,
    GlossaryWriter,
    Lesson,
    LessonMaterials,
    OutlineWriter,
    ReferenceDocument,
    ReferenceReader,
    Transcript,
    TranscriptRevision,
    TranscriptSegment,
)

provider_models = Models.from_environment()
text_model = provider_models.chat("openai/gpt-4.1-mini")
vision_model = provider_models.chat("openai/gpt-4.1-mini")

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

transcript = await TranscriptRevision(text_model).revise(transcript, language="en")
references = await ReferenceReader(text_model, vision_model).read(documents)
materials = LessonMaterials(transcript, references, language="en")
outline = await OutlineWriter(text_model).draft(materials)
chapters = tuple(
    await ChapterWriter(text_model).write(chapter, materials)
    for chapter in outline.chapters
)
glossary = await GlossaryWriter(text_model).write(outline, chapters, language="en")
lesson = Lesson.from_parts(outline=outline, chapters=chapters, glossary=glossary)
```

Each operation is independent. Callers may skip transcript revision, provide a hand-written outline, write chapters concurrently, or replace an operation with a compatible class.

## Operations

- `TranscriptRevision(text_model).revise(...)` revises transcript text.
- `ReferenceReader(text_model, vision_model).read(...)` reads reference documents.
- `OutlineWriter(text_model).draft(...)` writes a proposed lesson outline.
- `ChapterWriter(text_model).write(...)` writes one proposed chapter.
- `GlossaryWriter(text_model).write(...)` writes glossary entries from chapters.
- `Lesson.from_parts(...)` creates the final lesson deterministically.

Each operation accepts the model arguments it needs directly. `ReferenceReader` accepts an optional `vision_model` and uses its `text_model` when one is not supplied. Models from `models-provider`, or another provider exposing `ainvoke`, are compatible.

## Custom operations

The built-in classes are also extension points. Override only the operation that needs different behavior:

```python
from teacher import ChapterOutline, LessonOutline, LessonMaterials, OutlineWriter


class CustomOutlineWriter(OutlineWriter):
    async def draft(self, materials: LessonMaterials) -> LessonOutline:
        return LessonOutline(
            title="Calculus fundamentals",
            description="An introduction to derivatives.",
            chapters=(ChapterOutline(title="Derivatives", concepts=()),),
        )


outline = await CustomOutlineWriter(text_model).draft(materials)
```

The application can use these operations in ordinary Python, its own LangGraph, or another workflow system. Teacher does not expose a graph or checkpoint manager.

## Exporting

Export belongs to the lesson:

```python
from teacher import ExportFormat

markdown = lesson.export(ExportFormat.MARKDOWN)
pdf = lesson.export(ExportFormat.PDF)
```

PDF export requires `pandoc` and `typst` on `PATH`.
