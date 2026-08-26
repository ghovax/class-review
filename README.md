# teacher

`teacher` turns a timestamped lecture transcript and optional PDFs into a
structured lesson through one resumable graph: transcript cleanup, source
reading, lesson planning, chapter writing, glossary creation, and export.

## Code layout

The package follows the graph rather than a generic utilities hierarchy:

```text
graph.py              graph wiring, fan-out, barriers, and chapter loop
transcript/           find terms -> correct batches -> finish transcript
documents/            load PDFs -> read pages -> map sections -> explain sections
lesson/               plan -> write chapters -> glossary -> finish lesson
importers/             transcript and PDF input adapters, including Modal clients
xml/                   one public XML recovery and schema-validation boundary
outputs/               Markdown/PDF/JSON export
```

The prompt files contain model-facing instructions only. Prompt fragments that
were just one-line formatting wrappers are represented directly at the node or
rendering boundary, so the execution path does not jump through a second
prompt-fragment module.

## Explicit API contract

The graph input is:

```python
Transcript(
    segments: tuple[TranscriptSegment, ...],
    languages: tuple[str, ...],
)

TranscriptSegment(
    start_seconds: float,
    end_seconds: float,
    content: str,
)

DocumentSource(url: str, file_name: str | None = None)
```

The execution configuration is:

```python
GraphConfiguration(
    language_model: ModelConfiguration,
    checkpoint_path: Path,
    model_provider: ModelProvider,
    page_language_model: ModelConfiguration | None = None,
    document_importer: DocumentImporter = WebPdfImporter(),
    ...bounded graph settings...
)
```

The graph call is:

```python
async with LessonGraph(configuration) as graph:
    result = await graph.generate(
        transcript: Transcript,
        output_language: str,
        run_id: str,
        sources: Sequence[DocumentSource] = (),
    )
```

`run_id` is the caller-chosen stable key for the SQLite checkpoint. It must be
provided when starting a run and reused unchanged for
`LessonGraph.resume(run_id: str)` after an interruption.

The graph output is:

```python
LessonResult(
    lesson: Lesson,
    usage_by_model: dict[str, LanguageModelUsage],
    run_id: str,
)

Lesson(
    title: str,
    description: str,
    chapters: tuple[Chapter, ...],
    glossary: tuple[GlossaryEntry, ...],
)

Chapter(
    title: str,
    content: str,
    concepts: tuple[Concept, ...],
    citations: tuple[Citation, ...],
    glossary_links: tuple[GlossaryLink, ...],
)
```

`content` is retained as model-authored text. Teacher does not parse it into a
custom Markdown tree. `MarkdownExporter` writes the text plus source tables,
glossary anchors, and citation footnotes; `PdfExporter` converts the same
export; `save_data` writes the complete typed lesson as JSON.

In a real caller, the input values are ordinary immutable Python values:

```python
transcript = Transcript(
    segments=(
        TranscriptSegment(0.0, 4.2, "The first idea is ..."),
        TranscriptSegment(4.2, 9.8, "The second idea is ..."),
    ),
    languages=("en",),
)
sources = (
    DocumentSource(
        url="https://example.org/handout.pdf",
        file_name="handout.pdf",
    ),
)
```

`sources` is caller-owned just like `transcript`: pass zero or more
`DocumentSource` values to `generate`. Each source is fetched and analyzed by
the configured document importer. A caller that already has recordings may
instead use `JsonTranscriptImporter` or `ModalTranscriptImporter` to produce
the same `Transcript` value.

## Generate a lesson

```python
import asyncio
from pathlib import Path

from langmesh.models_provider import LangMeshProvider
from models_provider import ModelConfiguration
from teacher import GraphConfiguration, LessonGraph, MarkdownExporter
from teacher import DocumentSource, Transcript, TranscriptSegment


async def main() -> None:
    output = Path("output/lesson.md")
    configuration = GraphConfiguration(
        language_model=ModelConfiguration(
            provider="anthropic",
            model="claude-sonnet-4-5",
            reasoning_effort="high",
        ),
        checkpoint_path=Path("output/lesson.checkpoints.sqlite"),
        model_provider=LangMeshProvider(providers={"anthropic": "sk-ant-..."}),
    )
    transcript = Transcript(
        segments=(
            TranscriptSegment(0.0, 4.2, "The first idea is ..."),
            TranscriptSegment(4.2, 9.8, "The second idea is ..."),
        ),
        languages=("en",),
    )
    sources = (
        DocumentSource(
            url="https://example.org/handout.pdf",
            file_name="handout.pdf",
        ),
    )
    async with LessonGraph(configuration) as graph:
        result = await graph.generate(
            transcript=transcript,
            output_language="en",
            run_id="cell-biology-2026-08-26",
            sources=sources,
        )
    MarkdownExporter().save(result.lesson, output)


asyncio.run(main())
```

There is deliberately no length option. Structure and depth are derived from
the material. Optional PDF input requires `page_language_model`; Modal
transcription backends are available under `teacher.modal_apps`.
