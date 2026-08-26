"""Calling a chat model and reporting what the call consumed."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

from teacher.errors import PipelineError
from teacher.models import LanguageModelUsage

__all__ = ["ModelAnswer", "call_chat_model"]


@dataclass(frozen=True, slots=True)
class ModelAnswer:
    """One model answer with the usage the call consumed."""

    text: str
    usage_by_model: dict[str, LanguageModelUsage]


async def call_chat_model(
    chat_model: BaseChatModel,
    messages: Sequence[BaseMessage],
    *,
    metadata: dict[str, Any] | None = None,
) -> ModelAnswer:
    """Calls a chat model and reports its answer with the usage it consumed."""
    with get_usage_metadata_callback() as usage_callback:
        response = await chat_model.ainvoke(list(messages))

    # `text` is a property returning a string subclass.
    trimmed = response.text.strip()
    if not trimmed:
        raise PipelineError.retryable("the model returned an empty answer", dict(metadata or {}))

    return ModelAnswer(text=trimmed, usage_by_model=_read_usage(usage_callback.usage_metadata))


def _read_usage(usage_metadata: Any) -> dict[str, LanguageModelUsage]:  # noqa: ANN401
    """Converts collected usage metadata into the channel's shape."""
    converted: dict[str, LanguageModelUsage] = {}
    for model_name, counts in (usage_metadata or {}).items():
        input_details = counts.get("input_token_details") or {}
        converted[str(model_name)] = LanguageModelUsage(
            prompt_tokens=int(counts.get("input_tokens", 0)),
            completion_tokens=int(counts.get("output_tokens", 0)),
            total_tokens=int(counts.get("total_tokens", 0)),
            cached_tokens=int(input_details.get("cache_read", 0)),
            cache_write_tokens=int(input_details.get("cache_creation", 0)),
        )
    return converted
