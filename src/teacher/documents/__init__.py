"""Consolidated Teacher implementation."""

from __future__ import annotations

from collections.abc import Sequence
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime
from langgraph.types import Command, Send, Overwrite
from pydantic import BaseModel, Field
from teacher.configuration import GraphRuntime
from teacher.markdown import compose_markdown
from models_provider import ModelUsage
from teacher.prompts import Prompts
from teacher.models import (
    Document,
    DocumentSource,
    DocumentSection,
    DocumentSections,
    SectionMap,
    SectionNotes,
    DocumentRead,
    DocumentPage,
)
from teacher.state import DocumentPageReading, LessonState
from teacher.support import PipelineError, classify_retryable, get_logger, call_chat_model
from teacher.xml import OneOrMany, RequiredText, parse_xml_with_schema
from typing import Any
import asyncio
import re

"""Document graph nodes: page reading, section mapping, notes, and assembly."""

"""Loading source documents and routing their pages."""


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
    if runtime.context.page_model is None:
        raise PipelineError.terminal("page_model is required when documents are supplied")
    if runtime.context.document_reader is None:
        raise PipelineError.terminal("document_reader is required when documents are supplied")
    imported = await runtime.context.document_reader.read(
        item.source, document_index=item.document_index
    )
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


"""Reading one rendered page."""


logger = get_logger(__name__)

_PAGE_SYSTEM_TEMPLATE = "documents/extract_document_page/system"
_PAGE_USER_TEMPLATE = "documents/extract_document_page/user"


async def extract_document_page(
    state: DocumentPageReadRequest, runtime: Runtime[GraphRuntime]
) -> dict[str, object]:
    """Reads one page, leaving its content empty when all attempts fail."""
    page = state
    page_model = runtime.context.page_model
    if page_model is None:
        raise PipelineError.terminal("page_model is required when documents are supplied")
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
    maximum_attempts = max(1, runtime.context.page_attempts)

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


"""Organizing every document's pages into the sections they actually form."""


logger = get_logger(__name__)

_SECTIONS_SYSTEM_TEMPLATE = "documents/map_document_sections/system"
_SECTIONS_USER_TEMPLATE = "documents/map_document_sections/user"
_SECTIONS_ROOT_TAG = "DocumentSections"


class _SectionSchema(BaseModel):
    """One section the model identified."""

    section_index: int = Field(alias="SectionIndex", ge=0)
    start_page: int = Field(alias="StartPage", ge=1)
    end_page: int = Field(alias="EndPage", ge=1)
    title: RequiredText = Field(alias="SectionTitle")
    description: RequiredText = Field(alias="Description")


class _DocumentSchema(BaseModel):
    """One document's sections."""

    document_index: int = Field(alias="DocumentIndex", ge=0)
    sections: OneOrMany[_SectionSchema] = Field(alias="Section")


class _SectionMapSchema(BaseModel):
    """The element a segmentation call is expected to answer with."""

    documents: OneOrMany[_DocumentSchema] = Field(alias="Document")


async def map_document_sections(
    state: LessonState, runtime: Runtime[GraphRuntime]
) -> dict[str, object]:
    """Divides every document into sections."""
    prompts = runtime.context.prompts
    documents = state.get("documents", [])
    if not documents:
        logger.info("no documents to segment")
        return {"section_map": SectionMap(documents=())}

    answer = await call_chat_model(
        runtime.context.text_model,
        [
            SystemMessage(
                prompts.render(
                    _SECTIONS_SYSTEM_TEMPLATE,
                    {
                        "language_policy": prompts.render("shared_prompts/language_policy"),
                        "mathematics_notation_rules": prompts.render(
                            "shared_prompts/mathematics_notation_rules"
                        ),
                    },
                )
            ),
            HumanMessage(
                prompts.render(
                    _SECTIONS_USER_TEMPLATE,
                    {"page_list_markdown": render_document_summaries(documents, prompts)},
                )
            ),
        ],
        metadata={"document_count": len(documents)},
    )

    section_map = _read_section_map(answer.text, documents)
    logger.info(
        "documents segmented",
        document_count=len(documents),
        section_count=sum(len(entry.sections) for entry in section_map.documents),
    )
    return {"section_map": section_map, "usage_by_model": answer.usage_by_model}


def _read_section_map(answer_text: str, documents: Sequence[Document]) -> SectionMap:
    """Reads the answer into a section map, checking it against the documents."""
    parsed = parse_xml_with_schema(
        content=answer_text,
        root_tag=_SECTIONS_ROOT_TAG,
        schema=_SectionMapSchema,
        metadata={"document_count": len(documents)},
    )

    documents_by_index = {document.document_index: document for document in documents}
    entries: list[DocumentSections] = []

    for parsed_document in parsed.documents:
        document = documents_by_index.get(parsed_document.document_index)
        if document is None:
            raise PipelineError.retryable(
                "the segmentation names a document that was never read",
                {
                    "named_document_index": parsed_document.document_index,
                    "known_document_indices": sorted(documents_by_index),
                },
            )

        last_page = max((page.page_number for page in document.pages), default=0)
        sections: list[DocumentSection] = []
        for position, parsed_section in enumerate(
            sorted(parsed_document.sections, key=lambda item: item.section_index)
        ):
            start_page = min(max(parsed_section.start_page, 1), max(last_page, 1))
            end_page = min(max(parsed_section.end_page, start_page), max(last_page, 1))
            if last_page == 0:
                continue
            sections.append(
                DocumentSection(
                    section_index=position,
                    start_page=start_page,
                    end_page=end_page,
                    title=parsed_section.title,
                    description=parsed_section.description,
                )
            )

        entries.append(
            DocumentSections(
                document_index=document.document_index,
                file_name=document.file_name,
                sections=tuple(sections),
            )
        )

    return SectionMap(
        documents=tuple(
            sorted(entries, key=lambda document_sections: document_sections.document_index)
        )
    )


"""Turning each section's pages into one continuous explanation."""


logger = get_logger(__name__)

_NOTES_SYSTEM_TEMPLATE = "documents/explain_document_sections/system"
_NOTES_USER_TEMPLATE = "documents/explain_document_sections/user"


async def explain_document_sections(
    state: LessonState, runtime: Runtime[GraphRuntime]
) -> dict[str, object]:
    """Narrates every section of every document."""
    section_map = state.get("section_map")
    documents = state.get("documents", [])
    if section_map is None or not section_map.documents:
        logger.info("no sections to explain")
        return {"section_notes": []}

    prompts = runtime.context.prompts
    system_prompt = prompts.render(
        _NOTES_SYSTEM_TEMPLATE,
        {
            "language_policy": prompts.render("shared_prompts/language_policy"),
            "mathematics_notation_rules": prompts.render(
                "shared_prompts/mathematics_notation_rules"
            ),
        },
    )
    documents_by_index = {document.document_index: document for document in documents}

    requests = [
        (entry.document_index, entry.file_name, section)
        for entry in section_map.documents
        for section in entry.sections
    ]
    if not requests:
        logger.info("the section map is empty")
        return {"section_notes": []}

    logger.info("section explanation started", section_count=len(requests))

    async with asyncio.TaskGroup() as task_scope:
        tasks = [
            task_scope.create_task(
                _explain_one(
                    document=documents_by_index.get(document_index),
                    document_index=document_index,
                    file_name=file_name,
                    section=section,
                    system_prompt=system_prompt,
                    runtime=runtime,
                )
            )
            for document_index, file_name, section in requests
        ]

    notes: list[SectionNotes] = []
    accumulated_usage: dict[str, ModelUsage] = {}
    for task in tasks:
        explanation, usage = task.result()
        notes.append(explanation)
        for model_name, entry in usage.items():
            present = accumulated_usage.get(model_name)
            accumulated_usage[model_name] = (
                entry if present is None else present.combined_with(entry)
            )

    notes.sort(key=lambda item: (item.document_index, item.section_index))
    logger.info(
        "section explanation completed",
        section_count=len(notes),
        total_character_count=sum(len(item.content) for item in notes),
    )
    return {
        "section_notes": notes,
        "usage_by_model": accumulated_usage,
    }


async def _explain_one(
    *,
    document: Document | None,
    document_index: int,
    file_name: str,
    section: DocumentSection,
    system_prompt: str,
    runtime: Runtime[GraphRuntime],
) -> tuple[SectionNotes, dict[str, ModelUsage]]:
    """Narrates one section."""
    pages_markdown = render_section_pages(document, section, runtime.context.prompts)
    answer = await call_chat_model(
        runtime.context.text_model,
        [
            SystemMessage(system_prompt),
            HumanMessage(
                runtime.context.prompts.render(
                    _NOTES_USER_TEMPLATE,
                    {
                        "section": {
                            "document_index": document_index,
                            "document_file_name": file_name,
                            "section_index": section.section_index,
                            "section_title": section.title,
                            "section_description": section.description,
                            "start_page": section.start_page,
                            "end_page": section.end_page,
                            "pages_markdown": pages_markdown,
                        }
                    },
                )
            ),
        ],
        metadata={
            "document_index": document_index,
            "section_index": section.section_index,
        },
    )

    return (
        SectionNotes(
            document_index=document_index,
            section_index=section.section_index,
            content=answer.text.strip(),
        ),
        answer.usage_by_model,
    )


"""Assembling every page reading back into its document."""


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
