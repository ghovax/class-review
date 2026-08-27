"""Build the lesson glossary from completed chapters."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field
from teacher.configuration import GraphRuntime
from teacher.models import (
    GlossaryDistilled,
    GlossaryEntry,
)
from teacher.markdown import compose_markdown
from teacher.state import LessonState
from teacher.support import get_logger, call_chat_model
from teacher.xml import (
    OneOrMany,
    RequiredText,
    parse_xml_with_schema,
)
from typing import Final
import secrets

logger = get_logger(__name__)

_GLOSSARY_SYSTEM_TEMPLATE = "lesson/build_lesson_glossary/system"
_GLOSSARY_USER_TEMPLATE = "lesson/build_lesson_glossary/user"
_GLOSSARY_ROOT_TAG = "Glossary"
_KEY_ALPHABET: Final[str] = "abcdefghijklmnopqrstuvwxyz0123456789"
_KEY_PREFIX = "gls-"


class _TermSchema(BaseModel):
    """One term the model distilled."""

    short_form: RequiredText = Field(alias="Short")
    description: RequiredText = Field(alias="Description")
    long_form: str | None = Field(alias="Long", default=None)


class _GlossarySchema(BaseModel):
    """The element a glossary call is expected to answer with."""

    terms: OneOrMany[_TermSchema] = Field(alias="Term", default_factory=list)


async def build_lesson_glossary(
    state: LessonState, runtime: Runtime[GraphRuntime]
) -> dict[str, object]:
    """Distils the lecture's key terms from its completed chapters."""
    plan = state.get("plan")
    drafts = state.get("chapter_drafts", [])
    if plan is None or not drafts:
        logger.info("no chapters to distil a glossary from")
        return {"glossary": []}

    prompts = runtime.context.prompts
    answer = await call_chat_model(
        runtime.context.models.text,
        [
            SystemMessage(
                prompts.render(
                    _GLOSSARY_SYSTEM_TEMPLATE,
                    {
                        "language": state["output_language"],
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
                    _GLOSSARY_USER_TEMPLATE,
                    {
                        "language": state["output_language"],
                        "lesson_title": plan.title,
                        "lesson_markdown": compose_markdown(
                            prompts.render(
                                "lesson/build_lesson_glossary/chapter",
                                {
                                    "title": (
                                        draft.title
                                        or (
                                            plan.chapters[draft.chapter_index].title
                                            if draft.chapter_index < len(plan.chapters)
                                            else ""
                                        )
                                    ).strip(),
                                    "content": draft.content.strip(),
                                },
                            )
                            for draft in sorted(drafts, key=lambda item: item.chapter_index)
                        ),
                    },
                )
            ),
        ],
        metadata={"chapter_count": len(drafts)},
    )

    glossary = _read_glossary(answer.text, runtime.context.lesson.glossary_key_length)
    logger.info("glossary distilled", term_count=len(glossary))

    stream_writer = get_stream_writer()
    stream_writer(GlossaryDistilled(term_count=len(glossary)))

    return {"glossary": glossary, "usage_by_model": answer.usage_by_model}


def _read_glossary(answer_text: str, key_length: int) -> list[GlossaryEntry]:
    """Reads the answer into glossary entries, minting a key for each."""
    parsed = parse_xml_with_schema(
        content=answer_text, root_tag=_GLOSSARY_ROOT_TAG, schema=_GlossarySchema
    )

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
