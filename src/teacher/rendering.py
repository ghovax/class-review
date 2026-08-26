"""Rendering the material a prompt is shown."""

from __future__ import annotations

from collections.abc import Sequence

from teacher.models import Document, DocumentSection, TranscriptSegment

__all__ = [
    "render_page_entries",
    "render_page_summaries",
    "render_transcript_text",
]

def render_transcript_text(segments: Sequence[TranscriptSegment]) -> str:
    """Renders segments as one timestamped line each."""
    return "\n".join(f"[{segment.start_seconds:.2f}] {segment.content}" for segment in segments)


def render_page_summaries(documents: Sequence[Document]) -> str:
    """Renders every document's pages by summary alone."""
    blocks: list[str] = []
    for document in sorted(documents, key=lambda item: item.document_index):
        blocks.append(f"## Document {document.document_index}: {document.file_name}")
        blocks.extend(
            f"### Page {page.page_number}\n\n{page.summary.strip()}".strip()
            for page in document.pages
        )
    return "\n\n".join(block for block in blocks if block)


def render_page_entries(
    document: Document | None,
    section: DocumentSection,
) -> str:
    """Renders the pages one section covers, in full."""
    if document is None:
        return ""

    return "\n\n".join(
        f"### Page {page.page_number}\n\n{page.summary.strip()}\n\n{page.details.strip()}".strip()
        for page in document.pages
        if section.start_page <= page.page_number <= section.end_page
    )
