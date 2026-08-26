"""Values shared across the public export API and its renderers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from teacher.models import DocumentSource, Recording

__all__ = ["ExportError", "ExportFormat", "ExportMetadata"]


class ExportFormat(StrEnum):
    """A representation the exporter can emit."""

    MARKDOWN = "markdown"
    PDF = "pdf"


@dataclass(frozen=True, slots=True)
class ExportMetadata:
    """Optional context that accompanies a lecture into an exported document."""

    language: str = "en"
    author: str | None = None
    lesson_date: date | None = None
    recordings: tuple[Recording, ...] = ()
    reference_documents: tuple[DocumentSource, ...] = ()
    share_url: str | None = None
    include_generated_notice: bool = True
    generated_notice: str | None = None


class ExportError(RuntimeError):
    """Reports that a requested representation could not be rendered."""
