"""Explain the sections identified in document material."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.runtime import Runtime
from teacher.configuration import GraphRuntime
from models_provider import ModelUsage
from teacher.models import (
    Document,
    DocumentSection,
    SectionNotes,
)
from teacher.state import LessonState
from teacher.support import get_logger, call_chat_model
import asyncio

from teacher.documents.read_page import render_section_pages

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
        runtime.context.models.text,
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
