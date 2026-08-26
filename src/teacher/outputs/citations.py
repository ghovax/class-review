"""Building structured citation footnote bodies for lecture outputs."""

from __future__ import annotations

from teacher.models import Citation, DocumentSource, Lesson
from teacher.outputs.models import ExportMetadata
from teacher.outputs.source_listings import source_document_name

__all__ = ["build_citation_definitions"]


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
    citation: Citation, reference_documents: tuple[DocumentSource, ...]
) -> str:
    """Builds one citation definition from typed data."""
    if 0 <= citation.document_index < len(reference_documents):
        document_name = source_document_name(
            reference_documents[citation.document_index], citation.document_index
        )
    else:
        document_name = f"Document {citation.document_index + 1}"
    return f"{citation.content.strip()} (`{document_name}`, p. {citation.page_number})"
