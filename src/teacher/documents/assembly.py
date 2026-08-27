"""Assemble document page readings into documents."""

from __future__ import annotations

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime
from langgraph.types import Overwrite
from teacher.configuration import GraphRuntime
from teacher.models import (
    Document,
    DocumentRead,
    DocumentPage,
)
from teacher.state import DocumentPageReading, LessonState
from teacher.support import PipelineError, get_logger

logger = get_logger(__name__)


async def assemble_documents_from_pages(
    state: LessonState, runtime: Runtime[GraphRuntime]
) -> dict[str, object]:
    """Merge page readings into their documents, in page order."""
    del runtime
    documents = state.get("documents", [])
    page_readings = state.get("page_readings", [])

    chosen = _select_page_readings(page_readings)
    known_indices = {document.document_index for document in documents}
    orphaned = sorted({document_index for document_index, _ in chosen} - known_indices)
    if orphaned:
        raise PipelineError.terminal(
            "a page was read for a document that was never rendered",
            {"orphaned_document_indices": orphaned},
        )

    assembled: list[Document] = []
    stream_writer = get_stream_writer()

    for document in sorted(documents, key=lambda item: item.document_index):
        pages_for_document = sorted(
            (
                reading
                for (document_index, _), reading in chosen.items()
                if document_index == document.document_index
            ),
            key=lambda reading: reading.page_number,
        )
        unreadable_count = sum(
            1
            for reading in pages_for_document
            if reading.summary is None or reading.details is None
        )
        assembled.append(
            Document(
                document_index=document.document_index,
                file_name=document.file_name,
                pages=tuple(
                    DocumentPage(
                        page_number=reading.page_number,
                        summary=reading.summary,
                        details=reading.details,
                    )
                    for reading in pages_for_document
                ),
            )
        )
        logger.info(
            "document assembled",
            document_index=document.document_index,
            file_name=document.file_name,
            page_count=len(pages_for_document),
            unreadable_page_count=unreadable_count,
        )
        stream_writer(
            DocumentRead(
                document_index=document.document_index,
                file_name=document.file_name,
                page_count=len(pages_for_document),
                unreadable_page_count=unreadable_count,
            )
        )

    return {"documents": Overwrite(value=assembled)}


def _select_page_readings(
    page_readings: list[DocumentPageReading],
) -> dict[tuple[int, int], DocumentPageReading]:
    """Pick one reading per page, preferring a complete one over an empty one."""
    chosen: dict[tuple[int, int], DocumentPageReading] = {}
    for reading in page_readings:
        key = (reading.document_index, reading.page_number)
        present = chosen.get(key)
        present_is_empty = present is not None and (
            present.summary is None or present.details is None
        )
        reading_is_complete = reading.summary is not None and reading.details is not None
        if present is None or (present_is_empty and reading_is_complete):
            chosen[key] = reading
    return chosen
