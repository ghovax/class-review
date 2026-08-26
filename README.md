# teacher

`teacher` turns a timestamped lecture transcript and optional PDFs into a
structured lesson through one resumable graph: transcript cleanup, source
reading, lesson planning, chapter writing, glossary creation, and export.

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
    working_directory: Path,
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

`LessonGraph.resume(run_id: str)` accepts the stable run identifier and
continues from `checkpoint_path`.

The graph output is:

```python
LessonResult(
    lesson: Lesson,
    usage_by_model: dict[str, LanguageModelUsage],
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

## Generate a lesson

```python
import asyncio
from pathlib import Path

from models_provider import LangMeshProvider, ModelConfiguration
from teacher import GraphConfiguration, LessonGraph, MarkdownExporter
from teacher.importers import JsonTranscriptImporter
from teacher.models import Recording


async def main() -> None:
    output = Path("output/lesson.md")
    configuration = GraphConfiguration(
        language_model=ModelConfiguration(
            provider="anthropic",
            model="claude-sonnet-4-5",
            reasoning_effort="high",
        ),
        checkpoint_path=Path("output/lesson.checkpoints.sqlite"),
        working_directory=Path.cwd(),
        model_provider=LangMeshProvider(providers={"anthropic": "sk-ant-..."}),
    )
    transcript = await JsonTranscriptImporter().load(
        [Recording(url="transcript.json", index=0)], audio_languages=["it"]
    )
    async with LessonGraph(configuration) as graph:
        result = await graph.generate(
            transcript=transcript,
            output_language="en",
            run_id="cell-biology-2026-08-26",
        )
    MarkdownExporter().save(result.lesson, output)


asyncio.run(main())
```

There is deliberately no length option. Structure and depth are derived from
the material. Optional PDF input requires `page_language_model`; Modal
transcription backends are available under `teacher.modal_apps`.
