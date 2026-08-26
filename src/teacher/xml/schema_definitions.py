"""Validating recovered XML against a schema, and the coercions it needs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ValidationError

from teacher.errors import PipelineError
from teacher.logging_support import get_logger
from teacher.xml.recovery import parse_recovering, read_element_tree

__all__ = [
    "OneOrMany",
    "RequiredText",
    "case_insensitive_with_fallback",
    "parse_xml_with_schema",
]

logger = get_logger(__name__)


def _coerce_to_sequence(value: Any) -> Any:  # noqa: ANN401
    """Wraps a single value in a list, leaving a list untouched."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


type OneOrMany[ItemType] = Annotated[list[ItemType], BeforeValidator(_coerce_to_sequence)]
"""A field accepting one value or many, always documents back as a list.

Applied as ``OneOrMany[ChapterSchema]``. A tag that appears once and the same
tag repeated among its siblings are indistinguishable in the answer, so every
field that may repeat has to accept both shapes.
"""


def _require_non_empty_text(value: Any) -> Any:  # noqa: ANN401
    """Trims text and rejects it when nothing is left."""
    if not isinstance(value, str):
        raise ValueError("expected text content, found a nested element")
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("expected non-empty text content")
    return trimmed


# Text that must be present and must not be blank.
RequiredText = Annotated[str, BeforeValidator(_require_non_empty_text)]


def case_insensitive_with_fallback[EnumType: StrEnum](
    enum_type: type[EnumType], fallback: EnumType
) -> BeforeValidator:
    """Builds a validator that tolerates casing drift and near-miss synonyms."""
    canonical_by_lowercase = {member.value.lower(): member for member in enum_type}

    def coerce(value: Any) -> Any:  # noqa: ANN401
        """Normalises one value into the closed set."""
        if not isinstance(value, str):
            return fallback
        matched = canonical_by_lowercase.get(value.strip().lower())
        if matched is None:
            logger.debug(
                "value outside the accepted set replaced with the fallback",
                enum_type=enum_type.__name__,
                received_value=value.strip()[:64],
                fallback_value=fallback.value,
            )
            return fallback
        return matched

    return BeforeValidator(coerce)


def parse_xml_with_schema[SchemaType: BaseModel](
    *,
    content: str,
    root_tag: str,
    schema: type[SchemaType],
    metadata: Mapping[str, Any] | None = None,
) -> SchemaType:
    """Recovers XML from a model's answer and validates it against a schema."""
    error_context: dict[str, Any] = {
        **(metadata or {}),
        "error_code": "xml_parse",
        "root_tag": root_tag,
    }
    root = parse_recovering(content, root_tag, error_context)
    tree = read_element_tree(root)

    try:
        return schema.model_validate(tree)
    except ValidationError as error:
        failures = _describe_validation_failures(error)
        first_failure = failures[0] if failures else None
        message = (
            f"recovered <{root_tag}> does not match the expected schema"
            if first_failure is None
            else (
                f"recovered <{root_tag}> does not match the expected schema at "
                f"{first_failure['field_path'] or '(root)'}: "
                f"{first_failure['message']}"
            )
        )
        raise PipelineError.retryable(
            message, {**error_context, "schema_failures": failures}, error
        ) from error


def _describe_validation_failures(error: ValidationError) -> list[dict[str, str]]:
    """Flattens validation failures into a payload suitable for logging."""
    return [
        {
            "field_path": _format_field_path(failure.get("loc", ())),
            "failure_type": str(failure.get("type", "")),
            "message": str(failure.get("msg", "")),
        }
        for failure in error.errors()
    ]


def _format_field_path(location: Sequence[Any]) -> str:
    """Renders a field location as a readable path."""
    rendered = ""
    for segment in location:
        if isinstance(segment, int):
            rendered += f"[{segment}]"
        else:
            rendered += f".{segment}" if rendered else str(segment)
    return rendered
