"""The two channel reducers the branch state schemas need beyond the built-ins."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from teacher.models import LanguageModelUsage

__all__ = ["merge_usage_by_model", "upsert_by"]


def upsert_by[ItemType](
    index_field: str,
) -> Callable[[Sequence[ItemType], Sequence[ItemType]], list[ItemType]]:
    """Builds a reducer that merges by an identity field and sorts the result."""

    def reduce(existing: Sequence[ItemType], incoming: Sequence[ItemType]) -> list[ItemType]:
        """Merges two writes to the channel."""
        merged = {getattr(item, index_field): item for item in existing}
        for item in incoming:
            merged[getattr(item, index_field)] = item
        return sorted(merged.values(), key=lambda item: getattr(item, index_field))

    return reduce


def merge_usage_by_model(
    existing: Mapping[str, LanguageModelUsage],
    incoming: Mapping[str, LanguageModelUsage],
) -> dict[str, LanguageModelUsage]:
    """Adds usage per model, so parallel branches both contribute their counts."""
    merged = dict(existing)
    for model_name, usage in incoming.items():
        present = merged.get(model_name)
        merged[model_name] = usage if present is None else present.combined_with(usage)
    return merged
