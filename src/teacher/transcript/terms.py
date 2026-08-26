"""Establishing the canonical terminology before correction fans out."""

from __future__ import annotations

from typing import Final

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.runtime import Runtime

from teacher.configuration import GraphRuntime
from teacher.logging_support import get_logger
from teacher.model_calls import call_chat_model
from teacher.rendering import render_transcript_text
from teacher.state import LessonState
from teacher.xml import extract_element_text

__all__ = ["EMPTY_TERMINOLOGY", "find_terms"]

logger = get_logger(__name__)

# What every batch is given when no terminology could be established.
EMPTY_TERMINOLOGY: Final[str] = "<Glossary></Glossary>"

_SYSTEM_TEMPLATE = "transcript/find_terms/system"
_USER_TEMPLATE = "transcript/find_terms/user"
_ROOT_TAG = "Glossary"


async def find_terms(state: LessonState, runtime: Runtime[GraphRuntime]) -> dict[str, object]:
    """Reads the whole machine transcript and settles its terminology."""
    prompts = runtime.context.prompts
    segments = list(state["transcript"].segments)
    transcript_text = render_transcript_text(segments)

    answer = await call_chat_model(
        runtime.context.text_model,
        [
            SystemMessage(
                prompts.render(
                    _SYSTEM_TEMPLATE,
                    {
                        "audio_language": ", ".join(state["transcript"].languages),
                        "language_policy": prompts.render("language_policy"),
                    },
                )
            ),
            HumanMessage(
                prompts.render(
                    _USER_TEMPLATE,
                    {
                        "audio_language": ", ".join(state["transcript"].languages),
                        "transcript_full": transcript_text,
                    },
                )
            ),
        ],
        metadata={"segment_count": len(segments)},
    )

    terminology = _read_terminology(answer.text)
    logger.info(
        "terminology extracted",
        segment_count=len(segments),
        terminology_character_count=len(terminology),
        was_established=terminology != EMPTY_TERMINOLOGY,
    )

    return {"terminology": terminology, "usage_by_model": answer.usage_by_model}


def _read_terminology(answer_text: str) -> str:
    """Isolates the terminology element, falling back to the empty set."""
    try:
        return extract_element_text(answer_text, _ROOT_TAG)
    except Exception:  # noqa: BLE001 - any unusable answer degrades identically
        logger.warning(
            "terminology answer was unusable, correcting without it",
            answer_character_count=len(answer_text),
        )
        return EMPTY_TERMINOLOGY
