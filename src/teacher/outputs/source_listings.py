"""Building the source-listing tables used by lesson outputs."""

from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from teacher.models import DocumentSource, Lesson, Recording
from teacher.outputs.localization import export_labels
from teacher.outputs.models import ExportMetadata

__all__ = ["build_source_tables", "source_document_name"]


def build_source_tables(lecture: Lesson, metadata: ExportMetadata) -> list[str]:
    """Builds recording and reference-document tables as text blocks."""
    labels = export_labels(metadata.language)
    blocks: list[str] = []
    recordings = tuple(metadata.recordings)
    if recordings:
        total_duration = _lecture_duration_seconds(lecture)
        recording_rows = [
            (
                _recording_name(recording, recording_index),
                _format_duration(total_duration)
                if recording_index == len(recordings) - 1 and total_duration > 0 else "",
            )
            for recording_index, recording in enumerate(recordings)
        ]
        blocks.append(_table((labels.recordings, labels.duration), recording_rows))

    documents = tuple(metadata.reference_documents)
    if documents:
        page_counts = _citation_page_counts(lecture)
        document_rows = [
            (source_document_name(document, document_index),
             f"{page_counts[document_index]} {labels.page_abbreviation}"
             if document_index in page_counts else "")
            for document_index, document in enumerate(documents)
        ]
        blocks.append(_table((labels.reference_documents, labels.pages), document_rows))
    return blocks


def source_document_name(document: DocumentSource, document_index: int) -> str:
    """Resolves a stable display name for one reference document."""
    return document.file_name or _url_file_name(document.url) or f"Document {document_index + 1}"


def _recording_name(recording: Recording, recording_index: int) -> str:
    """Resolves a stable display name for one source recording."""
    return (
        recording.file_name or _url_file_name(recording.url) or f"Recording {recording_index + 1}"
    )


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
    """Render a two-column source table without an intermediate document tree."""
    lines = [f"| {headers[0]} | {headers[1]} |", "| --- | ---: |"]
    lines.extend(f"| {left.replace('|', '\\|')} | {right} |" for left, right in rows)
    return "\n".join(lines)
