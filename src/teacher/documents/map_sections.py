"""Map document pages into coherent sections."""

from __future__ import annotations

from collections.abc import Sequence
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field
from teacher.configuration import GraphRuntime
from teacher.models import (
    Document,
    DocumentSection,
    DocumentSections,
    SectionMap,
)
from teacher.state import LessonState
from teacher.support import PipelineError, get_logger, call_chat_model
from teacher.xml import OneOrMany, RequiredText, parse_xml_with_schema

from teacher.documents.read_page import render_document_summaries

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
        runtime.context.models.text,
        [
            SystemMessage(
                prompts.render(
                    _SECTIONS_SYSTEM_TEMPLATE,
                    {
                        "language_policy": prompts.render("shared_prompts/language_policy"),
                        "xml_policy": prompts.render("shared_prompts/xml_policy"),
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
