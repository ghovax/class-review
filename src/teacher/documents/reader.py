"""Read reference documents into typed lesson material."""

from __future__ import annotations

import asyncio
import base64
import re

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from teacher.interfaces import ChatModel
from teacher.models import (
    Reference,
    ReferenceDocument,
    ReferenceMaterial,
    ReferenceNote,
    ReferencePage,
    ReferenceSection,
    ReferenceSections,
)
from teacher.prompts import Prompts, get_prompts
from teacher.support import OperationError, call_chat_model
from teacher.xml import OneOrMany, RequiredText, parse_xml_with_schema


class ReferenceReader:
    """Reads PDF references into material that other operations can use."""

    def __init__(
        self,
        text_model: ChatModel,
        vision_model: ChatModel | None = None,
        *,
        prompts: Prompts | None = None,
    ) -> None:
        self.text_model = text_model
        self.vision_model = vision_model
        self.prompts = get_prompts(prompts)

    async def read(self, documents: tuple[ReferenceDocument, ...]) -> ReferenceMaterial:
        """Read every supplied PDF and map its pages into explained sections."""
        references = tuple(
            await asyncio.gather(
                *(self._read_document(document, index) for index, document in enumerate(documents))
            )
        )
        sections = await self._map_sections(references)
        notes = await self._explain_sections(references, sections)
        return ReferenceMaterial(references, sections, notes)

    async def _read_document(self, document: ReferenceDocument, index: int) -> Reference:
        pages = await asyncio.to_thread(_render_pdf, document)
        if not pages:
            raise ValueError(f"reference {document.file_name or index} has no pages")
        model = self.vision_model or self.text_model

        async def read_page(page: tuple[int, bytes]) -> ReferencePage:
            number, image = page
            prompts = self.prompts
            answer = await call_chat_model(
                model,
                [
                    SystemMessage(
                        prompts.render(
                            "documents/extract_document_page/system",
                            {
                                "language_policy": prompts.render("shared_prompts/language_policy"),
                                "mathematics_notation_rules": prompts.render(
                                    "shared_prompts/mathematics_notation_rules"
                                ),
                            },
                        )
                    ),
                    HumanMessage(
                        content=[
                            {
                                "type": "text",
                                "text": prompts.render(
                                    "documents/extract_document_page/user",
                                    {
                                        "document": {
                                            "file_name": document.file_name
                                            or f"document-{index + 1}.pdf",
                                            "index": index,
                                            "page_number": number,
                                        }
                                    },
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64.b64encode(image).decode('ascii')}"
                                },
                            },
                        ]
                    ),
                ],
            )
            summary, details = _read_page_sections(answer.text)
            return ReferencePage(number, summary, details)

        read_pages = await asyncio.gather(*(read_page(page) for page in pages))
        return Reference(
            index, document.file_name or f"document-{index + 1}.pdf", tuple(read_pages)
        )

    async def _map_sections(
        self, references: tuple[Reference, ...]
    ) -> tuple[ReferenceSections, ...]:
        if not references:
            return ()
        prompts = self.prompts
        page_list = "\n".join(
            f"Document {item.document_index}, page {page.page_number}: {page.summary or ''}"
            for item in references
            for page in item.pages
        )
        answer = await call_chat_model(
            self.text_model,
            [
                SystemMessage(
                    prompts.render(
                        "documents/map_document_sections/system",
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
                        "documents/map_document_sections/user", {"page_list_markdown": page_list}
                    )
                ),
            ],
        )
        parsed = parse_xml_with_schema(
            content=answer.text, root_tag="DocumentSections", schema=_SectionsSchema
        )
        by_index = {item.document_index: item for item in references}
        result = []
        for document in parsed.documents:
            reference = by_index.get(document.document_index)
            if reference is None:
                continue
            last_page = max((page.page_number for page in reference.pages), default=1)
            result.append(
                ReferenceSections(
                    reference.document_index,
                    reference.file_name,
                    tuple(
                        ReferenceSection(
                            position,
                            max(1, min(item.start_page, last_page)),
                            max(1, min(max(item.end_page, item.start_page), last_page)),
                            item.title,
                            item.description,
                        )
                        for position, item in enumerate(
                            sorted(document.sections, key=lambda item: item.section_index)
                        )
                    ),
                )
            )
        return tuple(sorted(result, key=lambda item: item.document_index))

    async def _explain_sections(
        self, references: tuple[Reference, ...], sections: tuple[ReferenceSections, ...]
    ) -> tuple[ReferenceNote, ...]:
        by_index = {item.document_index: item for item in references}
        prompts = self.prompts

        async def explain(item: ReferenceSections, section: ReferenceSection) -> ReferenceNote:
            reference = by_index[item.document_index]
            pages = "\n\n".join(
                f"Page {page.page_number}\n{page.details or ''}"
                for page in reference.pages
                if section.start_page <= page.page_number <= section.end_page
            )
            answer = await call_chat_model(
                self.text_model,
                [
                    SystemMessage(
                        prompts.render(
                            "documents/explain_document_sections/system",
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
                            "documents/explain_document_sections/user",
                            {
                                "section": {
                                    "document_index": item.document_index,
                                    "document_file_name": item.file_name,
                                    "section_index": section.section_index,
                                    "section_title": section.title,
                                    "section_description": section.description,
                                    "start_page": section.start_page,
                                    "end_page": section.end_page,
                                    "pages_markdown": pages,
                                }
                            },
                        )
                    ),
                ],
            )
            return ReferenceNote(item.document_index, section.section_index, answer.text.strip())

        return tuple(
            await asyncio.gather(
                *(explain(item, section) for item in sections for section in item.sections)
            )
        )


def _render_pdf(document: ReferenceDocument) -> list[tuple[int, bytes]]:
    import pymupdf

    with pymupdf.open(stream=document.content, filetype="pdf") as pdf:
        return [
            (
                number,
                pdf.load_page(number - 1)
                .get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
                .tobytes("png"),
            )
            for number in range(1, len(pdf) + 1)
        ]


def _read_page_sections(content: str) -> tuple[str, str]:
    body = content.strip()
    headings = list(re.finditer(r"^(#{1,6})[ \t]+.+?[ \t]*$", body, re.MULTILINE))
    if len(headings) < 2:
        raise OperationError.retryable("reference page needs summary and details headings")
    depth = min(len(item.group(1)) for item in headings)
    positions = [item for item in headings if len(item.group(1)) == depth]
    if len(positions) != 2:
        raise OperationError.retryable("reference page needs exactly two sections")
    summary, details = (
        body[positions[0].end() : positions[1].start()].strip(),
        body[positions[1].end() :].strip(),
    )
    if not summary or not details:
        raise OperationError.retryable("reference page has empty material")
    return summary, details


class _Section(BaseModel):
    section_index: int = Field(alias="SectionIndex", ge=0)
    start_page: int = Field(alias="StartPage", ge=1)
    end_page: int = Field(alias="EndPage", ge=1)
    title: RequiredText = Field(alias="SectionTitle")
    description: RequiredText = Field(alias="Description")


class _DocumentSections(BaseModel):
    document_index: int = Field(alias="DocumentIndex", ge=0)
    sections: OneOrMany[_Section] = Field(alias="Section", default_factory=list)


class _SectionsSchema(BaseModel):
    documents: OneOrMany[_DocumentSections] = Field(alias="Document", default_factory=list)
