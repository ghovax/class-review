"""Build glossary entries from completed lesson chapters."""

from __future__ import annotations

import secrets

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from teacher.interfaces import ChatModel
from teacher.markdown import compose_markdown
from teacher.models import Chapter, GlossaryEntry, LessonOutline
from teacher.prompts import Prompts, get_prompts
from teacher.support import call_chat_model
from teacher.xml import OneOrMany, RequiredText, parse_xml_with_schema


_GLOSSARY_KEY_LENGTH = 10


class GlossaryWriter:
    """Writes glossary entries from completed chapters."""

    def __init__(
        self,
        text_model: ChatModel,
        *,
        prompts: Prompts | None = None,
    ) -> None:
        self.text_model = text_model
        self.prompts = get_prompts(prompts)

    async def write(
        self, outline: LessonOutline, chapters: tuple[Chapter, ...], *, language: str
    ) -> tuple[GlossaryEntry, ...]:
        """Extract distinct glossary entries from completed chapter prose."""
        if not chapters:
            return ()
        prompts = self.prompts
        content = compose_markdown(
            [f"# {chapter.title}\n{chapter.content}" for chapter in chapters]
        )
        answer = await call_chat_model(
            self.text_model,
            [
                SystemMessage(
                    prompts.render(
                        "lesson/build_lesson_glossary/system",
                        {
                            "language": language,
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
                        "lesson/build_lesson_glossary/user",
                        {
                            "language": language,
                            "lesson_title": outline.title,
                            "lesson_markdown": content,
                        },
                    )
                ),
            ],
        )
        parsed = parse_xml_with_schema(
            content=answer.text, root_tag="Glossary", schema=_GlossarySchema
        )
        entries: list[GlossaryEntry] = []
        seen: set[str] = set()
        for term in parsed.terms:
            key = term.short_form.casefold()
            if key in seen:
                continue
            seen.add(key)
            entries.append(
                GlossaryEntry(
                    _new_glossary_key(),
                    term.short_form,
                    term.description,
                    term.long_form or None,
                )
            )
        return tuple(entries)


def _new_glossary_key() -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "glossary-" + "".join(secrets.choice(alphabet) for _ in range(_GLOSSARY_KEY_LENGTH))


class _GlossaryTerm(BaseModel):
    short_form: RequiredText = Field(alias="Short")
    description: RequiredText = Field(alias="Description")
    long_form: str | None = Field(alias="Long", default=None)


class _GlossarySchema(BaseModel):
    terms: OneOrMany[_GlossaryTerm] = Field(alias="Term", default_factory=list)
