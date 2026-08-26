# Teacher

Teacher turns a timestamped lecture transcript and optional document bytes into a structured lesson through one resumable graph. The graph cleans the transcript, reads supplied document pages, plans chapters, writes the lesson, builds a glossary, and exposes Markdown and PDF output.

## Code layout

| Area | Responsibility | Main file |
| --- | --- | --- |
| Graph | Wiring, fan-out, barriers, and the chapter loop | `graph.py` |
| Transcript | Terminology, correction batches, and assembly | `transcript.py` |
| Documents | Page reading, section mapping, and explanations | `documents.py` |
| Lesson | Planning, chapter writing, glossary, and assembly | `lesson.py` |
| Inputs | Typed caller values and document reader protocol | `models.py` |
| Configuration | Model selection, reader injection, and graph limits | `configuration.py` |
| XML | One recovery and schema-validation boundary | `xml.py` |
| Outputs | Markdown and the optional Pandoc and Typst PDF path | `outputs.py` |

Prompt files contain only model-facing instructions. The graph owns the flow, and the caller owns transcript and document sourcing.

## Input contract

```python
Transcript(
    segments=tuple[TranscriptSegment, ...],
    languages=tuple[str, ...],
)

TranscriptSegment(
    start_seconds=float,
    end_seconds=float,
    content=str,
)

DocumentSource(content=bytes, file_name=str | None = None)

Terminology(
    terms=tuple[TerminologyTerm, ...],
)

TerminologyTerm(
    canonical=str,
    heard=TerminologyHeard(variants=tuple[str, ...]),
    kind=str,
)
```

Teacher validates non-empty document bytes and text, non-negative timestamps, and ordered segment timestamps when these values are constructed. `sources` is caller-owned and may be empty. When sources are present, `GraphConfiguration.document_reader` must provide one implementation of the `DocumentReader` protocol:

```python
class DocumentReader(Protocol):
    async def read(
        self,
        source: DocumentSource,
        *,
        document_index: int,
    ) -> DocumentPages: ...
```

The reader may receive bytes loaded from local files, a web client, object storage, or any other application-specific source. Teacher does not care where the bytes came from and does not choose a downloader. Teacher parses model XML into typed values immediately; XML is used only at the model boundary.

## Graph call

```python
async with LessonGraph(configuration) as graph:
    result = await graph.generate(
        transcript=transcript,
        output_language="en",
        run_id="cell-biology-2026-08-26",
        sources=sources,
    )
```

`run_id` is the caller-chosen stable key for the SQLite checkpoint. Reuse it with `LessonGraph.resume(run_id)` after an interruption.

## Configuration

```python
configuration = GraphConfiguration(
    language_model=ModelConfiguration(
        provider="anthropic",
        model="claude-sonnet-4-5",
        reasoning_effort="high",
    ),
    checkpoint_path=Path("output/lesson.checkpoints.sqlite"),
    model_provider=provider,
    page_language_model=page_provider_configuration,
    document_reader=reader,
)
```

`model_provider` is any implementation of the independent Models Provider interface. Teacher does not import or select a concrete provider. `page_language_model` is required when `sources` is non-empty.

## Output contract

```python
LessonResult(
    lesson=Lesson(
        title=str,
        description=str,
        chapters=tuple[Chapter, ...],
        glossary=tuple[GlossaryEntry, ...],
    ),
    usage_by_model=dict[str, ModelUsage],
    run_id=str,
)

Chapter(
    title=str,
    content=str,
    concepts=tuple[Concept, ...],
    citations=tuple[Citation, ...],
    glossary_links=tuple[GlossaryLink, ...],
)
```

`Chapter.content` remains model-authored text. Teacher does not parse it into a custom Markdown tree. Use `render_export_markdown` for the canonical Markdown representation and `PdfExporter` when a PDF is wanted:

```python
markdown = render_export_markdown(result.lesson, metadata=metadata)
Path("output/lesson.md").write_bytes(markdown.encode("utf-8"))
PdfExporter().save(result.lesson, "output/lesson.pdf", metadata=metadata)
```

The PDF path delegates to Pandoc and Typst. The surrounding application can persist JSON or any other representation directly from the typed `Lesson` value.

## Example input

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
        content=Path("handout.pdf").read_bytes(),
        file_name="handout.pdf",
    ),
)
```

There is no length option. Structure and depth come from the material and the plan. Input sourcing, persistence, and non-PDF exports remain application concerns. `ModelUsage` is defined by the independent Models Provider library.
