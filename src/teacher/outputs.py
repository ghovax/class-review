"""Render structured lessons as Markdown, HTML, DOCX, and PDF."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
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
from babel.core import UnknownLocaleError
from babel.dates import format_date, format_time, get_datetime_format


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
    lesson_timestamp: datetime | None = None
    recording_urls: tuple[str, ...] = ()
    reference_documents: tuple[ReferenceDocument, ...] = ()
    share_url: str | None = None


class ExportError(RuntimeError):
    """Reports that a requested representation could not be rendered."""


@dataclass(frozen=True, slots=True)
class ExportLabels:
    """The human-readable labels one exported document needs."""

    recordings: str
    duration: str
    reference_documents: str
    pages: str
    glossary: str
    glossary_term: str
    glossary_definition: str
    page_abbreviation: str


_LABELS_BY_LANGUAGE = {
    "en": ExportLabels(
        "Recordings",
        "Duration",
        "Reference documents",
        "Pages",
        "Glossary",
        "Term",
        "Definition",
        "p.",
    ),
    "it": ExportLabels(
        "Registrazioni",
        "Durata",
        "Documenti di riferimento",
        "Pagine",
        "Glossario",
        "Termine",
        "Definizione",
        "p.",
    ),
    "tr": ExportLabels(
        "Kayıtlar", "Süre", "Referans belgeler", "Sayfa", "Sözlük", "Terim", "Tanım", "s."
    ),
    "es": ExportLabels(
        "Grabaciones",
        "Duración",
        "Documentos de referencia",
        "Páginas",
        "Glosario",
        "Término",
        "Definición",
        "p.",
    ),
    "fr": ExportLabels(
        "Enregistrements",
        "Durée",
        "Documents de référence",
        "Pages",
        "Glossaire",
        "Terme",
        "Définition",
        "p.",
    ),
    "de": ExportLabels(
        "Aufnahmen",
        "Dauer",
        "Referenzdokumente",
        "Seiten",
        "Glossar",
        "Begriff",
        "Definition",
        "S.",
    ),
    "pt": ExportLabels(
        "Gravações",
        "Duração",
        "Documentos de referência",
        "Páginas",
        "Glossário",
        "Termo",
        "Definição",
        "p.",
    ),
    "nl": ExportLabels(
        "Opnamen",
        "Duur",
        "Referentiedocumenten",
        "Pagina's",
        "Woordenlijst",
        "Term",
        "Definitie",
        "p.",
    ),
    "pl": ExportLabels(
        "Nagrania",
        "Czas trwania",
        "Dokumenty źródłowe",
        "Strony",
        "Słowniczek",
        "Termin",
        "Definicja",
        "s.",
    ),
    "ru": ExportLabels(
        "Записи",
        "Длительность",
        "Справочные документы",
        "Страницы",
        "Глоссарий",
        "Термин",
        "Определение",
        "с.",
    ),
    "uk": ExportLabels(
        "Записи",
        "Тривалість",
        "Довідкові документи",
        "Сторінки",
        "Глосарій",
        "Термін",
        "Визначення",
        "с.",
    ),
    "ja": ExportLabels("録音", "長さ", "参考資料", "ページ", "用語集", "用語", "定義", "p."),
    "ko": ExportLabels("녹음", "재생 시간", "참고 문서", "페이지", "용어집", "용어", "정의", "쪽"),
    "zh": ExportLabels("录音", "时长", "参考文档", "页码", "术语表", "术语", "定义", "页"),
    "ar": ExportLabels(
        "التسجيلات", "المدة", "المستندات المرجعية", "الصفحات", "المسرد", "المصطلح", "التعريف", "ص."
    ),
    "hi": ExportLabels("रिकॉर्डिंग", "अवधि", "संदर्भ दस्तावेज़", "पृष्ठ", "शब्दावली", "शब्द", "परिभाषा", "पृ."),
    "he": ExportLabels(
        "הקלטות", "משך", "מסמכי עזר", "עמודים", "מילון מונחים", "מונח", "הגדרה", "עמ׳"
    ),
    "el": ExportLabels(
        "Ηχογραφήσεις",
        "Διάρκεια",
        "Έγγραφα αναφοράς",
        "Σελίδες",
        "Γλωσσάρι",
        "Όρος",
        "Ορισμός",
        "σελ.",
    ),
    "sv": ExportLabels(
        "Inspelningar",
        "Varaktighet",
        "Referensdokument",
        "Sidor",
        "Ordlista",
        "Term",
        "Definition",
        "s.",
    ),
    "da": ExportLabels(
        "Optagelser",
        "Varighed",
        "Referencedokumenter",
        "Sider",
        "Ordliste",
        "Term",
        "Definition",
        "s.",
    ),
    "no": ExportLabels(
        "Opptak", "Varighet", "Referansedokumenter", "Sider", "Ordliste", "Term", "Definisjon", "s."
    ),
    "fi": ExportLabels(
        "Tallenteet", "Kesto", "Viiteasiakirjat", "Sivut", "Sanasto", "Termi", "Määritelmä", "s."
    ),
    "cs": ExportLabels(
        "Nahrávky",
        "Délka",
        "Referenční dokumenty",
        "Strany",
        "Glosář",
        "Termín",
        "Definice",
        "str.",
    ),
    "ro": ExportLabels(
        "Înregistrări",
        "Durată",
        "Documente de referință",
        "Pagini",
        "Glosar",
        "Termen",
        "Definiție",
        "p.",
    ),
    "hu": ExportLabels(
        "Felvételek",
        "Időtartam",
        "Hivatkozási dokumentumok",
        "Oldalak",
        "Szójegyzék",
        "Kifejezés",
        "Definíció",
        "o.",
    ),
    "vi": ExportLabels(
        "Bản ghi",
        "Thời lượng",
        "Tài liệu tham khảo",
        "Trang",
        "Bảng thuật ngữ",
        "Thuật ngữ",
        "Định nghĩa",
        "tr.",
    ),
    "id": ExportLabels(
        "Rekaman",
        "Durasi",
        "Dokumen referensi",
        "Halaman",
        "Glosarium",
        "Istilah",
        "Definisi",
        "h.",
    ),
    "bg": ExportLabels(
        "Записи",
        "Продължителност",
        "Референтни документи",
        "Страници",
        "Речник",
        "Термин",
        "Определение",
        "стр.",
    ),
    "ca": ExportLabels(
        "Gravacions",
        "Durada",
        "Documents de referència",
        "Pàgines",
        "Glossari",
        "Terme",
        "Definició",
        "p.",
    ),
}


def primary_language(language: str | None) -> str:
    """Extracts the normalized leading subtag of a BCP 47 language tag."""
    subtag = (language or "en").replace("_", "-").split("-", 1)[0].strip().lower()
    return subtag or "en"


def export_labels(language: str | None) -> ExportLabels:
    """Resolves export labels, falling back to English."""
    return _LABELS_BY_LANGUAGE.get(primary_language(language), _LABELS_BY_LANGUAGE["en"])


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
    return render_table(headers, rows, code_columns=(0,))


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


def _frontmatter_data(lesson: Lesson, metadata: ExportMetadata) -> dict[str, object]:
    """Build typed metadata for the Markdown frontmatter AST."""
    page_counts = _citation_page_counts(lesson)
    references = [
        {
            "file_name": reference_document_name(document, index),
            "pages": page_counts.get(index),
        }
        for index, document in enumerate(metadata.reference_documents)
    ]
    return {
        "title": lesson.title.strip() or "Untitled",
        "description": lesson.description.strip(),
        "language": metadata.language.strip() or "en",
        "author": metadata.author.strip() if metadata.author else None,
        "date": metadata.lesson_timestamp.isoformat() if metadata.lesson_timestamp else None,
        "recording_urls": list(metadata.recording_urls),
        "duration_seconds": _lecture_duration_seconds(lesson),
        "reference_documents": references,
        "share_url": metadata.share_url,
    }


_TEMPLATES = Prompts(package="teacher.output_templates")


def render_export_template(name: str, variables: Mapping[str, object]) -> str:
    """Render one packaged export shape with strict placeholder checking."""

    try:
        return _TEMPLATES.render(name, variables)
    except OperationError as error:
        raise ExportError(f"export template {name!r} could not be rendered") from error


def _render_markdown(lesson: Lesson, metadata: ExportMetadata) -> str:
    """Render a complete lesson with metadata kept in YAML frontmatter."""
    return _render_lesson_markdown(lesson, metadata)


def _render_lesson_markdown(
    lesson: Lesson, metadata: ExportMetadata, *, include_source_tables: bool = False
) -> str:
    """Render lesson blocks and attach typed metadata through the Markdown AST."""
    blocks = [
        *(build_source_tables(lesson, metadata) if include_source_tables else ()),
        *_chapter_blocks(lesson),
        *_glossary_blocks(lesson, metadata),
    ]
    definitions = build_citation_definitions(lesson, metadata)
    if definitions:
        blocks.extend(f"[^{number}]: {body}" for number, body in definitions.items())
    return compose_markdown(blocks, frontmatter_data=_frontmatter_data(lesson, metadata))


def _render_pandoc_markdown(lesson: Lesson, metadata: ExportMetadata) -> bytes:
    """Add visual source tables only to non-Markdown presentations."""
    return _render_lesson_markdown(lesson, metadata, include_source_tables=True).encode("utf-8")


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
    """Render the glossary as one dictionary-style table through packaged templates."""
    if not lecture.glossary:
        return []
    labels = export_labels(metadata.language)
    rows: list[tuple[str, str]] = []
    for entry in lecture.glossary:
        display_name = (
            f"{entry.short_form} ({entry.long_form})" if entry.long_form else entry.short_form
        )
        rows.append((display_name, entry.description))
    return [
        render_export_template("glossary", {"title": labels.glossary}).strip(),
        render_table(
            (labels.glossary_term, labels.glossary_definition),
            rows,
            align=(None, None),
        ),
    ]


def _shift_headings(markdown: str, levels: int) -> str:
    """Moves every heading in a chapter by a fixed number of levels."""
    return shift_headings(markdown, levels)


_PANDOC_TIMEOUT_SECONDS: Final[int] = 40
_PANDOC_INPUT_FORMAT: Final[str] = "markdown+smart+footnotes+raw_html+header_attributes"
_ANCHOR_BEFORE_HEADING: Final[re.Pattern[bytes]] = re.compile(
    rb'^<a id="([^"]+)"></a>\s*(#{1,6} .+)$', re.MULTILINE
)
_INTERNAL_LINK: Final[re.Pattern[bytes]] = re.compile(rb"\[([^\]]+)\]\(#[^)]+\)")


def _pandoc_metadata(metadata: ExportMetadata) -> dict[str, str]:
    """Build the scalar metadata consumed by the packaged PDF template."""
    values = {"lang": primary_language(metadata.language)}
    if metadata.author and metadata.author.strip():
        values["author"] = metadata.author.strip()
    if metadata.lesson_timestamp:
        locale = (metadata.language or "en").replace("-", "_")
        try:
            date_text = format_date(
                metadata.lesson_timestamp.date(),
                format="long",
                locale=locale,
            )
            time_text = format_time(
                metadata.lesson_timestamp,
                format="short",
                locale=locale,
            )
            datetime_pattern = str(get_datetime_format("short", locale=locale))
            values["lesson-date"] = datetime_pattern.replace("{1}", date_text).replace(
                "{0}", time_text
            )
        except (UnknownLocaleError, ValueError):
            date_text = format_date(metadata.lesson_timestamp.date(), format="long", locale="en")
            time_text = format_time(metadata.lesson_timestamp, format="short", locale="en")
            datetime_pattern = str(get_datetime_format("short", locale="en"))
            values["lesson-date"] = datetime_pattern.replace("{1}", date_text).replace(
                "{0}", time_text
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
        markdown = _render_pandoc_markdown(lesson, resolved_metadata)
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
            pandoc_input = _ANCHOR_BEFORE_HEADING.sub(rb"\2 {#\1}", markdown)
            if output_format is ExportFormat.PDF:
                # Typst does not receive the raw HTML anchors inside table
                # cells, so glossary links would otherwise point at labels
                # that do not exist and make the PDF compilation fail.
                pandoc_input = _INTERNAL_LINK.sub(rb"\1", pandoc_input)
            completed = subprocess.run(
                command,
                input=pandoc_input,
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
        if output_format is ExportFormat.HTML:
            rendered = _inject_html_table_styles(rendered)
        return rendered


def _inject_html_table_styles(rendered: bytes) -> bytes:
    """Embed the packaged table stylesheet so HTML exports remain portable."""
    style_resource = resources.files("teacher.output_templates").joinpath("pandoc-html.css")
    try:
        stylesheet = style_resource.read_text(encoding="utf-8").encode("utf-8")
    except OSError as error:
        raise ExportError("HTML export stylesheet could not be read") from error
    marker = b"</head>"
    if marker not in rendered:
        return rendered
    return rendered.replace(marker, b"<style>" + stylesheet + b"</style>" + marker, 1)
