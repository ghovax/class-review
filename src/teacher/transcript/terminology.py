"""Extract and render transcript terminology."""

from __future__ import annotations

from collections.abc import Sequence
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field
from teacher.configuration import GraphRuntime
from teacher.models import (
    Terminology,
    TerminologyHeard,
    TerminologyTerm,
    TranscriptSegment,
)
from teacher.markdown import compose_markdown
from teacher.prompts import Prompts
from teacher.state import LessonState
from teacher.support import get_logger, call_chat_model
from teacher.xml import OneOrMany, RequiredText, build_xml_document, parse_xml_with_schema
from typing import Final

logger = get_logger(__name__)


EMPTY_TERMINOLOGY: Final[Terminology] = Terminology(terms=())


_TERMINOLOGY_SYSTEM_TEMPLATE = "transcript/extract_transcript_terminology/system"


_TERMINOLOGY_USER_TEMPLATE = "transcript/extract_transcript_terminology/user"


def render_transcript_input(segments: Sequence[TranscriptSegment], prompts: Prompts) -> str:
    """Render transcript lines through the terminology node's local template."""
    rendered_segments = [
        prompts.render(
            "transcript/extract_transcript_terminology/segment",
            {
                "timestamp": f"{segment.start_seconds:.2f}",
                "content": segment.content,
            },
        )
        for segment in segments
    ]
    return compose_markdown(rendered_segments)


async def extract_transcript_terminology(
    state: LessonState, runtime: Runtime[GraphRuntime]
) -> dict[str, object]:
    """Reads the whole machine transcript and settles its terminology."""
    prompts = runtime.context.prompts
    segments = list(state["transcript"].segments)
    transcript_text = render_transcript_input(segments, prompts)

    answer = await call_chat_model(
        runtime.context.models.text,
        [
            SystemMessage(
                prompts.render(
                    _TERMINOLOGY_SYSTEM_TEMPLATE,
                    {
                        "language": ", ".join(state["transcript"].languages),
                        "language_policy": prompts.render("shared_prompts/language_policy"),
                        "xml_policy": prompts.render("shared_prompts/xml_policy"),
                    },
                )
            ),
            HumanMessage(
                prompts.render(
                    _TERMINOLOGY_USER_TEMPLATE,
                    {
                        "language": ", ".join(state["transcript"].languages),
                        "transcript": transcript_text,
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
        terminology_term_count=len(terminology.terms),
    )

    return {"terminology": terminology, "usage_by_model": answer.usage_by_model}


class _HeardTerminologySchema(BaseModel):
    variants: OneOrMany[RequiredText] = Field(alias="Variant")


class _TerminologyTermSchema(BaseModel):
    canonical: RequiredText = Field(alias="Canonical")
    heard: _HeardTerminologySchema = Field(alias="Heard")
    kind: RequiredText = Field(alias="Kind")


class _TerminologySchema(BaseModel):
    terms: OneOrMany[_TerminologyTermSchema] = Field(alias="Term")


def _read_terminology(answer_text: str) -> Terminology:
    """Parses the model's terminology XML into the typed graph value."""
    try:
        parsed = parse_xml_with_schema(
            content=answer_text,
            root_tag="Terminology",
            schema=_TerminologySchema,
        )
        return Terminology(
            terms=tuple(
                TerminologyTerm(
                    canonical=term.canonical,
                    heard=TerminologyHeard(variants=tuple(term.heard.variants)),
                    kind=term.kind,
                )
                for term in parsed.terms
            )
        )
    except Exception:  # noqa: BLE001 - any unusable answer degrades identically
        logger.warning(
            "terminology answer was unusable, correcting without it",
            answer_character_count=len(answer_text),
        )
        return EMPTY_TERMINOLOGY


def render_terminology_xml(terminology: Terminology) -> str:
    """Render typed terminology only at the prompt boundary."""
    return build_xml_document(
        "Terminology",
        {
            "Term": [
                {
                    "Canonical": term.canonical,
                    "Heard": {"Variant": list(term.heard.variants)},
                    "Kind": term.kind,
                }
                for term in terminology.terms
            ]
        },
    )
