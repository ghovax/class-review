"""Consolidated Teacher implementation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from importlib import resources
from pathlib import PurePosixPath, Path
from teacher.models import ReferenceDocument, Lesson, Citation
from teacher.markdown import compose_markdown, render_table, shift_headings
from teacher.prompts import Prompts
from teacher.support import OperationError, apply_glossary_links
from tempfile import TemporaryDirectory
from typing import Final
from urllib.parse import unquote, urlsplit
from uuid import uuid4
import json
import re
import subprocess

import segno

"""Lesson export to Markdown, PDF, and JSON."""

"""Values shared across the public export API and its renderers."""


class ExportFormat(StrEnum):
    """A representation the exporter can emit."""

    MARKDOWN = "markdown"
    HTML = "html"
    DOCX = "docx"
    PDF = "pdf"


@dataclass(frozen=True, slots=True)
class ExportMetadata:
    """Optional context that accompanies a lecture into an exported document."""

    language: str = "en"
    author: str | None = None
    lesson_date: date | None = None
    recording_urls: tuple[str, ...] = ()
    reference_documents: tuple[ReferenceDocument, ...] = ()
    share_url: str | None = None
    include_generated_notice: bool = True
    generated_notice: str | None = None


class ExportError(RuntimeError):
    """Reports that a requested representation could not be rendered."""


"""Localized labels and dates used by exported documents."""


@dataclass(frozen=True, slots=True)
class ExportLabels:
    """The human-readable labels one exported document needs."""

    recordings: str
    duration: str
    reference_documents: str
    pages: str
    glossary: str
    generated_notice: str
    page_abbreviation: str


_LABELS_BY_LANGUAGE = {
    "en": ExportLabels(
        recordings="Recordings",
        duration="Duration",
        reference_documents="Reference documents",
        pages="Pages",
        glossary="Glossary",
        generated_notice=("These notes were generated automatically - double-check them."),
        page_abbreviation="p.",
    ),
    "it": ExportLabels(
        recordings="Registrazioni",
        duration="Durata",
        reference_documents="Documenti di riferimento",
        pages="Pagine",
        glossary="Glossario",
        generated_notice=("Questi appunti sono stati generati automaticamente - ricontrollali."),
        page_abbreviation="p.",
    ),
    "tr": ExportLabels(
        recordings="Kayıtlar",
        duration="Süre",
        reference_documents="Referans belgeler",
        pages="Sayfa",
        glossary="Sözlük",
        generated_notice="Bu notlar otomatik olarak oluşturuldu - bir kontrol et.",
        page_abbreviation="s.",
    ),
}

_MONTHS_BY_LANGUAGE = {
    "en": (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ),
    "it": (
        "gennaio",
        "febbraio",
        "marzo",
        "aprile",
        "maggio",
        "giugno",
        "luglio",
        "agosto",
        "settembre",
        "ottobre",
        "novembre",
        "dicembre",
    ),
    "tr": (
        "Ocak",
        "Şubat",
        "Mart",
        "Nisan",
        "Mayıs",
        "Haziran",
        "Temmuz",
        "Ağustos",
        "Eylül",
        "Ekim",
        "Kasım",
        "Aralık",
    ),
}


def primary_language(language: str | None) -> str:
    """Extracts the normalized leading subtag of a BCP 47 language tag."""
    subtag = (language or "en").replace("_", "-").split("-", 1)[0].strip().lower()
    return subtag or "en"


def export_labels(language: str | None) -> ExportLabels:
    """Resolves export labels, falling back to English."""
    return _LABELS_BY_LANGUAGE.get(primary_language(language), _LABELS_BY_LANGUAGE["en"])


def format_lesson_date(lesson_date: date, language: str | None) -> str:
    """Formats a calendar date for the supported export language."""
    selected_language = primary_language(language)
    months = _MONTHS_BY_LANGUAGE.get(selected_language, _MONTHS_BY_LANGUAGE["en"])
    month = months[lesson_date.month - 1]
    if selected_language == "en":
        return f"{month} {lesson_date.day}, {lesson_date.year}"
    return f"{lesson_date.day} {month} {lesson_date.year}"


"""Building the source-listing tables used by lesson outputs."""


def build_source_tables(lecture: Lesson, metadata: ExportMetadata) -> list[str]:
    """Builds recording and reference-document tables as text blocks."""
    labels = export_labels(metadata.language)
    blocks: list[str] = []
    recordings = tuple(metadata.recording_urls)
    if recordings:
        total_duration = _lecture_duration_seconds(lecture)
        recording_rows = [
            (
                _recording_name(recording, recording_index),
                _format_duration(total_duration)
                if recording_index == len(recordings) - 1 and total_duration > 0
                else "",
            )
            for recording_index, recording in enumerate(recordings)
        ]
        blocks.append(_table((labels.recordings, labels.duration), recording_rows))

    documents = tuple(metadata.reference_documents)
    if documents:
        page_counts = _citation_page_counts(lecture)
        document_rows = [
            (
                reference_document_name(document, document_index),
                f"{page_counts[document_index]} {labels.page_abbreviation}"
                if document_index in page_counts
                else "",
            )
            for document_index, document in enumerate(documents)
        ]
        blocks.append(_table((labels.reference_documents, labels.pages), document_rows))
    return blocks


def reference_document_name(document: ReferenceDocument, document_index: int) -> str:
    """Resolves a stable display name for one reference document."""
    return document.file_name or f"Document {document_index + 1}"


def _recording_name(recording: str, recording_index: int) -> str:
    """Resolves a stable display name for one source recording."""
    return _url_file_name(recording) or f"Recording {recording_index + 1}"


def _url_file_name(url: str) -> str:
    """Reads a decoded file name from a URL path when one exists."""
    return PurePosixPath(unquote(urlsplit(url).path)).name


def _citation_page_counts(lecture: Lesson) -> dict[int, int]:
    """Finds the highest cited page for every reference document."""
    page_counts: dict[int, int] = {}
    for chapter in lecture.chapters:
        for citation in chapter.citations:
            page_counts[citation.document_index] = max(
                page_counts.get(citation.document_index, 0), citation.page_number
            )
    return page_counts


def _lecture_duration_seconds(lecture: Lesson) -> int:
    """Finds the final transcript offset covered by the lecture."""
    return round(
        max(
            (
                concept.transcript_span.end_seconds
                for chapter in lecture.chapters
                for concept in chapter.concepts
            ),
            default=0.0,
        )
    )


def _format_duration(total_seconds: int) -> str:
    """Formats a source duration compactly without locale-sensitive words."""
    hours, remaining_seconds = divmod(total_seconds, 3600)
    minutes = remaining_seconds // 60
    parts = [f"{hours} h"] if hours else []
    if minutes or not parts:
        parts.append(f"{minutes} min")
    return " ".join(parts)


def _table(headers: tuple[str, str], rows: list[tuple[str, str]]) -> str:
    """Render a two-column source table through the Markdown library."""
    return render_table(headers, rows)


"""Building structured citation footnote bodies for lecture outputs."""


def build_citation_definitions(lecture: Lesson, metadata: ExportMetadata) -> dict[str, str]:
    """Builds plain footnote bodies keyed by their public marker."""
    citations = sorted(
        (citation for chapter in lecture.chapters for citation in chapter.citations),
        key=lambda citation: citation.number,
    )
    return {
        str(citation.number): _citation_definition(citation, metadata.reference_documents)
        for citation in citations
    }


def _citation_definition(
    citation: Citation, reference_documents: tuple[ReferenceDocument, ...]
) -> str:
    """Builds one citation definition from typed data."""
    if 0 <= citation.document_index < len(reference_documents):
        document_name = reference_document_name(
            reference_documents[citation.document_index], citation.document_index
        )
    else:
        document_name = f"Document {citation.document_index + 1}"
    return f"{citation.content.strip()} (`{document_name}`, p. {citation.page_number})"


"""Building the canonical Markdown export from plain lesson data."""


_TEMPLATES = Prompts(package="teacher.output_templates")


def render_export_template(name: str, variables: Mapping[str, object]) -> str:
    """Render one packaged export shape with strict placeholder checking."""

    try:
        return _TEMPLATES.render(name, variables)
    except OperationError as error:
        raise ExportError(f"export template {name!r} could not be rendered") from error


def _render_markdown(lesson: Lesson, metadata: ExportMetadata) -> str:
    """Render a complete lesson from packaged blocks."""
    blocks = [
        render_export_template(
            "lesson",
            {
                "title": lesson.title.strip() or "Untitled",
                "description": lesson.description.strip(),
            },
        ).strip(),
        *build_source_tables(lesson, metadata),
    ]
    blocks.extend(_chapter_blocks(lesson))
    blocks.extend(_glossary_blocks(lesson, metadata))
    definitions = build_citation_definitions(lesson, metadata)
    if definitions:
        blocks.extend(f"[^{number}]: {body}" for number, body in definitions.items())
    return compose_markdown(blocks)


def _chapter_blocks(lecture: Lesson) -> list[str]:
    """Renders every chapter through the packaged text shape."""
    blocks: list[str] = []
    for chapter_index, chapter in enumerate(lecture.chapters):
        linked_content = apply_glossary_links(chapter.content, chapter.glossary_links)
        blocks.append(
            render_export_template(
                "chapter",
                {
                    "title": chapter.title.strip() or f"Chapter {chapter_index + 1}",
                    "content": _shift_headings(linked_content, 1),
                },
            ).strip()
        )
    return blocks


def _glossary_blocks(lecture: Lesson, metadata: ExportMetadata) -> list[str]:
    """Renders the glossary heading and entries through packaged text shapes."""
    if not lecture.glossary:
        return []
    labels = export_labels(metadata.language)
    blocks = [render_export_template("glossary", {"title": labels.glossary}).strip()]
    for entry in lecture.glossary:
        display_name = (
            f"{entry.short_form} ({entry.long_form})" if entry.long_form else entry.short_form
        )
        blocks.append(
            render_export_template(
                "glossary_entry",
                {
                    "key": entry.key,
                    "title": display_name,
                    "description": entry.description,
                },
            ).strip()
        )
    return blocks


def _shift_headings(markdown: str, levels: int) -> str:
    """Moves every heading in a chapter by a fixed number of levels."""
    return shift_headings(markdown, levels)


"""Converting canonical lecture Markdown into PDF bytes with Pandoc and Typst."""


_PANDOC_TIMEOUT_SECONDS: Final[int] = 40
_PANDOC_INPUT_FORMAT: Final[str] = "markdown+smart+footnotes+raw_html+header_attributes"
_ANCHOR_BEFORE_HEADING: Final[re.Pattern[bytes]] = re.compile(
    rb'^<a id="([^"]+)"></a>\s*(#{1,6} .+)$', re.MULTILINE
)


def _pandoc_metadata(metadata: ExportMetadata) -> dict[str, str]:
    """Build the scalar metadata consumed by the packaged PDF template."""
    labels = export_labels(metadata.language)
    values = {"lang": primary_language(metadata.language)}
    if metadata.author and metadata.author.strip():
        values["author"] = metadata.author.strip()
    if metadata.lesson_date:
        values["date"] = format_lesson_date(metadata.lesson_date, metadata.language)
    if metadata.include_generated_notice:
        values["generated-notice"] = (
            metadata.generated_notice.strip()
            if metadata.generated_notice and metadata.generated_notice.strip()
            else labels.generated_notice
        )
    return values


class MarkdownExporter:
    """Render a lesson as canonical Markdown bytes."""

    def render(
        self,
        lesson: Lesson,
        *,
        metadata: ExportMetadata | None = None,
    ) -> bytes:
        return _render_markdown(lesson, metadata or ExportMetadata()).encode("utf-8")


class PandocExporter:
    """Render canonical Markdown in a selected Pandoc output format."""

    def __init__(self, output_format: ExportFormat | str) -> None:
        try:
            selected = ExportFormat(output_format)
        except ValueError as error:
            supported = ", ".join(
                item.value for item in ExportFormat if item is not ExportFormat.MARKDOWN
            )
            raise ExportError(
                f"unsupported Pandoc format {output_format!r}; expected one of: {supported}"
            ) from error
        if selected is ExportFormat.MARKDOWN:
            raise ExportError("PandocExporter does not render Markdown; use MarkdownExporter")
        self.output_format = selected

    def render(
        self,
        lesson: Lesson,
        *,
        metadata: ExportMetadata | None = None,
    ) -> bytes:
        resolved_metadata = metadata or ExportMetadata()
        markdown = MarkdownExporter().render(lesson, metadata=resolved_metadata)
        return _render_pandoc(markdown, resolved_metadata, self.output_format)


def _render_pandoc(
    markdown: bytes,
    metadata: ExportMetadata,
    output_format: ExportFormat,
) -> bytes:
    """Convert Markdown using a private temporary directory."""
    template_resource = resources.files("teacher.output_templates").joinpath(
        "pandoc-typst.template"
    )
    with resources.as_file(template_resource) as template_path:
        return _run_pandoc(markdown, metadata, template_path, output_format)


def _run_pandoc(
    markdown: bytes,
    metadata: ExportMetadata,
    template_path: Path,
    output_format: ExportFormat,
) -> bytes:
    """Run Pandoc with unique temporary names and return its result."""
    with TemporaryDirectory(prefix="teacher-pandoc-") as temporary_directory:
        working_directory = Path(temporary_directory)
        output_path = working_directory / f"teacher-export-{uuid4().hex}.{output_format.value}"
        metadata_path = working_directory / f"teacher-metadata-{uuid4().hex}.json"
        pandoc_metadata = _pandoc_metadata(metadata)

        if metadata.share_url and output_format is ExportFormat.PDF:
            qr_code_path = working_directory / f"teacher-qr-{uuid4().hex}.svg"
            segno.make_qr(metadata.share_url, error="m").save(
                str(qr_code_path), scale=4, border=1, dark="#000000", light="#ffffff"
            )
            pandoc_metadata["qr-image-path"] = qr_code_path.name

        metadata_path.write_text(json.dumps(pandoc_metadata, ensure_ascii=False), encoding="utf-8")
        command = [
            "pandoc",
            "--sandbox",
            "--from",
            _PANDOC_INPUT_FORMAT,
            "--standalone",
            "--to",
            output_format.value,
            "--output",
            str(output_path),
            f"--metadata-file={metadata_path}",
        ]
        if output_format is ExportFormat.PDF:
            command.extend(
                [
                    "--shift-heading-level-by=-1",
                    "--toc",
                    "--toc-depth=2",
                    "--pdf-engine=typst",
                    f"--template={template_path}",
                ]
            )

        try:
            completed = subprocess.run(
                command,
                input=_ANCHOR_BEFORE_HEADING.sub(rb"\2 {#\1}", markdown),
                cwd=working_directory,
                capture_output=True,
                check=False,
                timeout=_PANDOC_TIMEOUT_SECONDS,
            )
        except FileNotFoundError as error:
            raise ExportError("Pandoc export requires pandoc on PATH") from error
        except OSError as error:
            raise ExportError("Pandoc export could not start") from error
        except subprocess.TimeoutExpired as error:
            raise ExportError(
                f"Pandoc export exceeded {_PANDOC_TIMEOUT_SECONDS} seconds"
            ) from error

        if completed.returncode != 0:
            details = completed.stderr.decode("utf-8", errors="replace").strip()
            raise ExportError(f"Pandoc export failed: {details or 'pandoc exited unsuccessfully'}")
        try:
            rendered = output_path.read_bytes()
        except OSError as error:
            raise ExportError("Pandoc export completed without an output file") from error
        if not rendered:
            raise ExportError("Pandoc export produced an empty file")
        if output_format is ExportFormat.PDF and not rendered.startswith(b"%PDF-"):
            raise ExportError("Pandoc export produced bytes that are not a PDF")
        return rendered
