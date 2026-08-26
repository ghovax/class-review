"""Distilling the lecture's key terms once every chapter is written."""

from __future__ import annotations

import secrets
from collections.abc import Sequence
from typing import Final

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from teacher.configuration import GraphRuntime
from teacher.events import GlossaryDistilled
from teacher.logging_support import get_logger
from teacher.model_calls import call_chat_model
from teacher.models import GlossaryEntry, LessonPlan
from teacher.prompt_fragments import render_language_policy
from teacher.prompts import Prompts
from teacher.state import ChapterDraft, LessonState
from teacher.xml.schema_definitions import (
    OneOrMany,
    RequiredText,
    parse_xml_with_schema,
)

__all__ = ["build_glossary", "render_lesson_markdown"]

logger = get_logger(__name__)

_SYSTEM_TEMPLATE = "lesson/build_glossary/system"
_USER_TEMPLATE = "lesson/build_glossary/user"
_NOTATION_TEMPLATE = "mathematics_notation_rules"
_ROOT_TAG = "Glossary"
_CHAPTER_SECTION_TEMPLATE = "fragments/chapter_section"

# Keys are built from this alphabet alone, so a key is always safe to write into a
# link destination and to match against in body text.
_KEY_ALPHABET: Final[str] = "abcdefghijklmnopqrstuvwxyz0123456789"
_KEY_PREFIX: Final[str] = "gls-"


class _TermSchema(BaseModel):
    """One term the model distilled."""

    short_form: RequiredText = Field(alias="Short")
    description: RequiredText = Field(alias="Description")
    long_form: str | None = Field(alias="Long", default=None)


class _GlossarySchema(BaseModel):
    """The element a glossary call is expected to answer with."""

    terms: OneOrMany[_TermSchema] = Field(alias="Term", default_factory=list)


async def build_glossary(state: LessonState, runtime: Runtime[GraphRuntime]) -> dict[str, object]:
    """Distils the lecture's key terms from its finished chapters."""
    plan = state.get("plan")
    drafts = state.get("chapter_drafts", [])
    if plan is None or not drafts:
        logger.info("no chapters to distil a glossary from")
        return {"glossary": []}

    prompts = runtime.context.prompts
    answer = await call_chat_model(
        runtime.context.text_model,
        [
            SystemMessage(
                prompts.render(
                    _SYSTEM_TEMPLATE,
                    {
                        "language": state["output_language"],
                        "language_policy": render_language_policy(prompts),
                        "mathematics_notation_rules": prompts.render(_NOTATION_TEMPLATE),
                    },
                )
            ),
            HumanMessage(
                prompts.render(
                    _USER_TEMPLATE,
                    {
                        "language": state["output_language"],
                        "lesson_title": plan.title,
                        "lesson_markdown": render_lesson_markdown(plan, drafts, prompts),
                    },
                )
            ),
        ],
        metadata={"chapter_count": len(drafts)},
    )

    glossary = _read_glossary(answer.text, runtime.context.glossary_key_length)
    logger.info("glossary distilled", term_count=len(glossary))

    stream_writer = get_stream_writer()
    stream_writer(GlossaryDistilled(term_count=len(glossary)))

    return {"glossary": glossary, "usage_by_model": answer.usage_by_model}


def render_lesson_markdown(
    plan: LessonPlan,
    drafts: Sequence[ChapterDraft],
    prompts: Prompts,
) -> str:
    """Stitches the written chapters into one document."""
    return "\n\n".join(
        prompts.render(
            _CHAPTER_SECTION_TEMPLATE,
            {
                "chapter_title": draft.title
                or (
                    plan.chapters[draft.chapter_index].title
                    if draft.chapter_index < len(plan.chapters)
                    else ""
                ),
                "chapter_content": draft.content,
            },
        ).strip()
        for draft in sorted(drafts, key=lambda item: item.chapter_index)
    )


def _read_glossary(answer_text: str, key_length: int) -> list[GlossaryEntry]:
    """Reads the answer into glossary entries, minting a key for each."""
    parsed = parse_xml_with_schema(content=answer_text, root_tag=_ROOT_TAG, schema=_GlossarySchema)

    entries: list[GlossaryEntry] = []
    seen_short_forms: set[str] = set()
    for term in parsed.terms:
        short_form = term.short_form.strip()
        comparable = short_form.casefold()
        if not short_form or comparable in seen_short_forms:
            continue
        seen_short_forms.add(comparable)
        long_form = (term.long_form or "").strip()
        entries.append(
            GlossaryEntry(
                key=_mint_key(key_length),
                short_form=short_form,
                description=term.description,
                long_form=long_form or None,
            )
        )
    return entries


def _mint_key(key_length: int) -> str:
    """Mints a key that is safe as a link destination and as a match target."""
    suffix = "".join(secrets.choice(_KEY_ALPHABET) for _ in range(key_length))
    return f"{_KEY_PREFIX}{suffix}"
