"""Read and render individual document pages."""

from __future__ import annotations

from collections.abc import Sequence
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.runtime import Runtime
from langgraph.types import Command, Send
from pydantic import BaseModel
from teacher.configuration import GraphRuntime
from teacher.markdown import compose_markdown
from models_provider import ModelUsage
from teacher.prompts import Prompts
from teacher.models import (
    Document,
    DocumentSource,
    DocumentSection,
)
from teacher.state import DocumentPageReading
from teacher.support import PipelineError, classify_retryable, get_logger, call_chat_model
from typing import Any
import re

from teacher.documents.decode import _decode_document


def render_document_summaries(documents: Sequence[Document], prompts: Prompts) -> str:
    """Render document summaries for section mapping through local templates."""
    document_blocks: list[str] = []
    for document in sorted(documents, key=lambda item: item.document_index):
        page_blocks = tuple(
            prompts.render(
                "documents/map_document_sections/page",
                {
                    "page": {
                        "number": page.page_number,
                        "summary": (page.summary or "Page content unavailable.").strip(),
                    }
                },
            )
            for page in document.pages
        )
        document_blocks.append(
            prompts.render(
                "documents/map_document_sections/document",
                {
                    "document": {
                        "index": document.document_index,
                        "file_name": document.file_name,
                        "pages": compose_markdown(page_blocks),
                    }
                },
            )
        )
    return compose_markdown(document_blocks)


def render_section_pages(
    document: Document | None,
    section: DocumentSection,
    prompts: Prompts,
) -> str:
    """Render the pages covered by one section through its local template."""
    if document is None:
        return ""
    return compose_markdown(
        prompts.render(
            "documents/explain_document_sections/page",
            {
                "page": {
                    "number": page.page_number,
                    "summary": (page.summary or "Page content unavailable.").strip(),
                    "details": (page.details or "No details were extracted.").strip(),
                }
            },
        )
        for page in document.pages
        if section.start_page <= page.page_number <= section.end_page
    )


class DocumentReadRequest(BaseModel):
    """One indexed document source."""

    document_index: int
    source: DocumentSource
    model_config = {"arbitrary_types_allowed": True}


class DocumentPageReadRequest(BaseModel):
    """One rendered document page."""

    document_index: int
    file_name: str
    page_number: int
    image_data_url: str


async def load_document_pages(
    state: DocumentReadRequest, runtime: Runtime[GraphRuntime]
) -> Command[str]:
    """Load one document and send each rendered page for extraction."""

    item = state
    imported = await _decode_document(item.source, document_index=item.document_index)
    if not imported.pages:
        return Command(update={}, goto=["assemble_documents_from_pages"])
    shell = Document(
        document_index=imported.document_index,
        file_name=imported.file_name,
        pages=(),
    )
    return Command(
        update={"documents": [shell]},
        goto=[
            Send(
                "extract_document_page",
                DocumentPageReadRequest(
                    document_index=imported.document_index,
                    file_name=imported.file_name,
                    page_number=page.page_number,
                    image_data_url=page.image_data_url,
                ),
            )
            for page in imported.pages
        ],
    )


logger = get_logger(__name__)


_PAGE_SYSTEM_TEMPLATE = "documents/extract_document_page/system"


_PAGE_USER_TEMPLATE = "documents/extract_document_page/user"


async def extract_document_page(
    state: DocumentPageReadRequest, runtime: Runtime[GraphRuntime]
) -> dict[str, object]:
    """Reads one page, leaving its content empty when all attempts fail."""
    page = state
    page_model = runtime.context.models.vision or runtime.context.models.text
    prompts = runtime.context.prompts
    system_prompt = prompts.render(
        _PAGE_SYSTEM_TEMPLATE,
        {
            "language_policy": prompts.render("shared_prompts/language_policy"),
            "mathematics_notation_rules": prompts.render(
                "shared_prompts/mathematics_notation_rules"
            ),
        },
    )
    user_prompt = prompts.render(
        _PAGE_USER_TEMPLATE,
        {
            "document": {
                "file_name": page.file_name,
                "index": page.document_index,
                "page_number": page.page_number,
            }
        },
    )

    accumulated_usage: dict[str, ModelUsage] = {}
    maximum_attempts = max(1, runtime.context.retries.page_attempts)

    for attempt_number in range(1, maximum_attempts + 1):
        try:
            answer = await call_chat_model(
                page_model,
                [
                    SystemMessage(system_prompt),
                    HumanMessage(
                        content=[
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": page.image_data_url},
                            },
                        ]
                    ),
                ],
                metadata={
                    "document_index": page.document_index,
                    "page_number": page.page_number,
                    "attempt_number": attempt_number,
                },
            )
            accumulated_usage = _combine(accumulated_usage, answer.usage_by_model)
            summary, details = _read_sections(answer.text)
        except PipelineError as error:
            accumulated_usage = _combine(accumulated_usage, getattr(error, "usage_by_model", {}))
            if not classify_retryable(error) or attempt_number == maximum_attempts:
                logger.warning(
                    "page could not be read, recording an empty page reading",
                    document_index=page.document_index,
                    page_number=page.page_number,
                    attempt_number=attempt_number,
                    error_message=str(error),
                    error_metadata=error.metadata,
                )
                return _page_reading_update(page, accumulated_usage)
            logger.info(
                "page reading attempt failed, trying again",
                document_index=page.document_index,
                page_number=page.page_number,
                attempt_number=attempt_number,
                error_message=str(error),
            )
            continue

        logger.info(
            "page read",
            document_index=page.document_index,
            page_number=page.page_number,
            attempt_number=attempt_number,
            summary_character_count=len(summary),
            details_character_count=len(details),
        )
        return {
            "page_readings": [
                DocumentPageReading(
                    document_index=page.document_index,
                    page_number=page.page_number,
                    summary=summary,
                    details=details,
                )
            ],
            "usage_by_model": accumulated_usage,
        }

    return _page_reading_update(page, accumulated_usage)


def _page_reading_update(
    page: DocumentPageReadRequest,
    usage: dict[str, ModelUsage],
) -> dict[str, object]:
    """Build the empty reading recorded when a page could not be read."""
    return {
        "page_readings": [
            DocumentPageReading(
                document_index=page.document_index,
                page_number=page.page_number,
                summary=None,
                details=None,
            )
        ],
        "usage_by_model": usage,
    }


def _combine(accumulated: dict[str, ModelUsage], incoming: Any) -> dict[str, ModelUsage]:
    """Adds one attempt's usage to what earlier attempts consumed."""
    combined = dict(accumulated)
    for model_name, usage in (incoming or {}).items():
        present = combined.get(model_name)
        combined[model_name] = usage if present is None else present.combined_with(usage)
    return combined


def _read_sections(answer_text: str) -> tuple[str, str]:
    """Splits the answer into its summary and its details."""
    content = answer_text.strip()
    if not content:
        raise PipelineError.retryable("the page reading is empty")

    headings = list(re.finditer(r"^(#{1,6})[ \t]+.+?[ \t]*$", content, re.MULTILINE))
    if len(headings) < 2:
        raise PipelineError.retryable(
            "the page reading carries fewer than two headings",
            {"heading_count": len(headings)},
        )

    depths = [len(match.group(1)) for match in headings]
    shallowest_depth = min(depths)
    section_positions = [
        match for match, depth in zip(headings, depths, strict=True) if depth == shallowest_depth
    ]
    if len(section_positions) != 2:
        raise PipelineError.retryable(
            "the page reading does not carry exactly two sections",
            {
                "section_count": len(section_positions),
                "shallowest_depth": shallowest_depth,
            },
        )

    summary_start, details_start = section_positions
    summary = content[summary_start.end() : details_start.start()].strip()
    details = content[details_start.end() :].strip()

    if not summary:
        raise PipelineError.retryable("the page reading has an empty summary")
    if not details:
        raise PipelineError.retryable("the page reading has empty details")
    return summary, details
