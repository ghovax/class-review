"""Interfaces for transcript and document input."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from teacher.models import DocumentSource, Recording, RenderedPage, Transcript


@dataclass(frozen=True, slots=True)
class ImportedDocument:
    """A resolved document and its rendered pages."""

    document_index: int
    source_url: str
    file_name: str
    pages: tuple[RenderedPage, ...]


@runtime_checkable
class TranscriptImporter(Protocol):
    """Loads timestamped speech from recordings."""

    async def load(
        self,
        recordings: Sequence[Recording],
        *,
        audio_languages: str | Sequence[str],
    ) -> Transcript: ...


@runtime_checkable
class DocumentImporter(Protocol):
    """Loads and renders one source document."""

    async def load(self, source: DocumentSource, *, document_index: int) -> ImportedDocument: ...
