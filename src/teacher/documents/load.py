"""Loading source documents and dispatching their pages."""

from __future__ import annotations

from langgraph.runtime import Runtime
from langgraph.types import Command, Send
from pydantic import BaseModel

from teacher.configuration import GraphRuntime
from teacher.errors import PipelineError
from teacher.models import Document, DocumentSource


class DocumentToLoad(BaseModel):
    """One indexed document source."""

    document_index: int
    source: DocumentSource
    model_config = {"arbitrary_types_allowed": True}


class PageToRead(BaseModel):
    """One rendered document page."""

    document_index: int
    file_name: str
    page_number: int
    image_data_url: str


async def load_document(state: DocumentToLoad, runtime: Runtime[GraphRuntime]) -> Command[str]:
    """Load one document and send each rendered page for extraction."""

    item = state
    if runtime.context.page_model is None:
        raise PipelineError.terminal("page_model is required when documents are supplied")
    imported = await runtime.context.document_importer.load(
        item.source, document_index=item.document_index
    )
    if not imported.pages:
        return Command(update={}, goto=["finish_documents"])
    shell = Document(
        document_index=imported.document_index,
        file_name=imported.file_name,
        source_url=imported.source_url,
        pages=(),
    )
    return Command(
        update={"documents": [shell]},
        goto=[
            Send(
                "read_page",
                PageToRead(
                    document_index=imported.document_index,
                    file_name=imported.file_name,
                    page_number=page.page_number,
                    image_data_url=page.image_data_url,
                ),
            )
            for page in imported.pages
        ],
    )
