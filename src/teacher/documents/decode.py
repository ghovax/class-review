"""Decode supplied document bytes into rendered pages."""

from __future__ import annotations

from teacher.models import (
    DocumentSource,
    DocumentPages,
    RenderedPage,
)
from teacher.support import PipelineError
import asyncio
import base64


async def _decode_document(source: DocumentSource, *, document_index: int) -> DocumentPages:
    """Render PDF bytes into page images for the graph's document nodes."""
    try:
        return await asyncio.to_thread(_render_pdf, source, document_index)
    except Exception as error:  # noqa: BLE001
        raise PipelineError.terminal(
            f"could not decode document {source.file_name or document_index}", cause=error
        ) from error


def _render_pdf(source: DocumentSource, document_index: int) -> DocumentPages:
    import pymupdf

    file_name = source.file_name or f"document-{document_index + 1}.pdf"
    with pymupdf.open(stream=source.content, filetype="pdf") as pdf_document:
        pages = []
        for page_number in range(1, len(pdf_document) + 1):
            pdf_page = pdf_document.load_page(page_number - 1)
            pixmap = pdf_page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
            encoded = base64.b64encode(pixmap.tobytes("png")).decode("ascii")
            pages.append(
                RenderedPage(
                    page_number=page_number,
                    image_data_url=f"data:image/png;base64,{encoded}",
                )
            )
    return DocumentPages(document_index=document_index, file_name=file_name, pages=tuple(pages))
