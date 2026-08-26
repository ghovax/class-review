"""File-oriented output API."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Protocol, runtime_checkable

from teacher.models import Lesson
from teacher.outputs.markdown import render_export_markdown
from teacher.outputs.models import ExportError, ExportFormat, ExportMetadata
from teacher.outputs.pdf import render_pdf

__all__ = [
    "Exporter",
    "MarkdownExporter",
    "PdfExporter",
    "export_to_bytes",
    "save_data",
]


@runtime_checkable
class Exporter(Protocol):
    """Writes a completed lesson to a caller-selected location."""

    def save(
        self,
        lesson: Lesson,
        destination: str | Path,
        *,
        metadata: ExportMetadata | None = None,
    ) -> Path: ...


class MarkdownExporter:
    """Writes the bundled Markdown representation."""

    def save(
        self,
        lesson: Lesson,
        destination: str | Path,
        *,
        metadata: ExportMetadata | None = None,
    ) -> Path:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(export_to_bytes(lesson, format=ExportFormat.MARKDOWN, metadata=metadata))
        return path


class PdfExporter:
    """Writes the bundled Pandoc and Typst PDF representation."""

    def save(
        self,
        lesson: Lesson,
        destination: str | Path,
        *,
        metadata: ExportMetadata | None = None,
    ) -> Path:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(export_to_bytes(lesson, format=ExportFormat.PDF, metadata=metadata))
        return path


def export_to_bytes(
    lesson: Lesson,
    *,
    format: ExportFormat | str,  # noqa: A002
    metadata: ExportMetadata | None = None,
) -> bytes:
    """Render a lesson as Markdown or PDF bytes."""

    try:
        selected = ExportFormat(format)
    except ValueError as error:
        supported = ", ".join(item.value for item in ExportFormat)
        raise ExportError(
            f"unsupported export format {format!r}; expected one of: {supported}"
        ) from error
    resolved_metadata = metadata or ExportMetadata()
    markdown = render_export_markdown(lesson, resolved_metadata).encode("utf-8")
    return (
        markdown if selected is ExportFormat.MARKDOWN else render_pdf(markdown, resolved_metadata)
    )


def save_data(lesson: Lesson, destination: str | Path) -> Path:
    """Save the complete lesson data as UTF-8 JSON."""

    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dataclasses.asdict(lesson), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
