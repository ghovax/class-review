"""Rendering the material a prompt is shown."""

from __future__ import annotations

from collections.abc import Sequence

from teacher.models import Document, DocumentSection, TranscriptSegment
from teacher.prompts import Prompts

__all__ = [
    "render_page_entries",
    "render_page_summaries",
    "render_transcript_text",
]

_TRANSCRIPT_LINE_TEMPLATE = "fragments/transcript_line"
_DOCUMENT_SECTION_TEMPLATE = "fragments/document_section"
_PAGE_SUMMARY_TEMPLATE = "fragments/page_summary"
_PAGE_ENTRY_TEMPLATE = "fragments/page_entry"


def render_transcript_text(segments: Sequence[TranscriptSegment], prompts: Prompts) -> str:
    """Renders segments as one timestamped line each."""
    return "\n".join(
        prompts.render(
            _TRANSCRIPT_LINE_TEMPLATE,
            {
                "start_seconds": f"{segment.start_seconds:.2f}",
                "content": segment.content,
            },
        )
        for segment in segments
    )


def render_page_summaries(documents: Sequence[Document], prompts: Prompts) -> str:
    """Renders every document's pages by summary alone."""
    blocks: list[str] = []
    for document in sorted(documents, key=lambda item: item.document_index):
        blocks.append(
            prompts.render(
                _DOCUMENT_SECTION_TEMPLATE,
                {
                    "document_index": document.document_index,
                    "file_name": document.file_name,
                },
            ).strip()
        )
        blocks.extend(
            prompts.render(
                _PAGE_SUMMARY_TEMPLATE,
                {"page_number": page.page_number, "summary": page.summary},
            ).strip()
            for page in document.pages
        )
    return "\n\n".join(block for block in blocks if block)


def render_page_entries(
    document: Document | None,
    section: DocumentSection,
    prompts: Prompts,
) -> str:
    """Renders the pages one section covers, in full."""
    if document is None:
        return ""

    return "\n\n".join(
        prompts.render(
            _PAGE_ENTRY_TEMPLATE,
            {
                "page_number": page.page_number,
                "summary": page.summary,
                "details": page.details,
            },
        ).strip()
        for page in document.pages
        if section.start_page <= page.page_number <= section.end_page
    )
