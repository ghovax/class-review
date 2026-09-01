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
    LessonWriter,
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

`ChapterWriter` is the low-level choice when a caller wants one chapter as an
independent unit. `LessonWriter` accepts the complete outline as one lesson
and owns its internal coordination:

```python
writing = await LessonWriter(text_model).write_lesson(
    outline,
    materials,
)
chapters = writing.chapters
lesson = Lesson.from_parts(outline=outline, chapters=chapters)
```

`LessonWriter` writes chapters in outline order and carries each completed model
response into the next chapter. `writing.chapter_writings` retains the exact
request messages, provider response objects, parsed chapter, and per-call usage
for inspection or persistence. Callers may skip transcript revision, provide a
hand-written outline, subclass `LessonWriter` for a different lesson-level
implementation, or use `ChapterWriter` directly when they want one independent
chapter. `ChapterWriter.write_with_trace(...)` provides the same retained call
data when writing one chapter directly.

## Public interfaces

- `TranscriptRevision(text_model).revise(...)` revises transcript text.
- `ReferenceReader(text_model, vision_model).read(...)` reads reference documents.
- `OutlineWriter(text_model).draft(...)` writes a proposed lesson outline.
- `ChapterWriter(text_model).write(...)` writes one proposed chapter.
- `GlossaryWriter(text_model).write(...)` writes glossary entries from chapters.
- `Lesson.from_parts(...)` creates the final lesson deterministically.

Each interface accepts the model arguments it needs directly. `ReferenceReader` accepts an optional `vision_model` and uses its `text_model` when one is not supplied. Models from `models-provider`, or another provider exposing `ainvoke`, are compatible.

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

Markdown is the canonical lesson representation. Its YAML frontmatter keeps the lesson
metadata and source context machine-readable; the body contains only the lesson material.
Pandoc converts it to other formats.

```python
from teacher import ExportFormat, MarkdownExporter, PandocExporter

markdown = MarkdownExporter().render(lesson)
pdf = PandocExporter(ExportFormat.PDF).render(lesson)
html = PandocExporter(ExportFormat.HTML).render(lesson)
```

Pass `ExportMetadata(lesson_timestamp=...)` when the lesson should carry an
ISO-8601 timestamp. Markdown keeps that value, along with the other export
context, in YAML frontmatter.

`PandocExporter` runs in a private temporary directory. Its output, metadata, and optional QR image each receive unique names, and the directory is removed after rendering. PDF uses the bundled Typst template; HTML and DOCX use Pandoc's native writers.

PDF export requires `pandoc` and `typst` on `PATH`. HTML and DOCX require only `pandoc`.
