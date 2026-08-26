"""The barrier that folds every page's documents back into its document."""

from __future__ import annotations

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime
from langgraph.types import Overwrite

from teacher.configuration import GraphRuntime
from teacher.errors import PipelineError
from teacher.events import DocumentRead
from teacher.logging_support import get_logger
from teacher.models import Document, DocumentPage
from teacher.state import StagedPage, LessonState

__all__ = ["finish_documents"]

logger = get_logger(__name__)


async def finish_documents(state: LessonState, runtime: Runtime[GraphRuntime]) -> dict[str, object]:
    """Merges the staged pages into their documents, in page order."""
    del runtime
    documents = state.get("documents", [])
    staged_pages = state.get("staged_pages", [])

    chosen = _choose_best_documents(staged_pages)
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
                staged
                for (document_index, _), staged in chosen.items()
                if document_index == document.document_index
            ),
            key=lambda staged: staged.page_number,
        )
        unreadable_count = sum(1 for staged in pages_for_document if not staged.was_extracted)
        assembled.append(
            Document(
                document_index=document.document_index,
                file_name=document.file_name,
                source_url=document.source_url,
                pages=tuple(
                    DocumentPage(
                        page_number=staged.page_number,
                        summary=staged.summary,
                        details=staged.details,
                    )
                    for staged in pages_for_document
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


def _choose_best_documents(
    staged_pages: list[StagedPage],
) -> dict[tuple[int, int], StagedPage]:
    """Picks one documents per page, preferring a real one over a placeholder."""
    chosen: dict[tuple[int, int], StagedPage] = {}
    for staged in staged_pages:
        key = (staged.document_index, staged.page_number)
        present = chosen.get(key)
        if present is None or (not present.was_extracted and staged.was_extracted):
            chosen[key] = staged
    return chosen
