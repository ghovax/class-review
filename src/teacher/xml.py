"""Consolidated Teacher implementation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import StrEnum
from lxml import etree
from pydantic import BaseModel, BeforeValidator, ValidationError
from teacher.support import PipelineError, get_logger
from typing import Any, Final, Annotated
import re

"""XML recovery, schema validation, and document construction."""

"""Recovering usable XML from a model's answer."""


logger = get_logger(__name__)

# A closing marker a model sometimes writes as though it were an element.
_MALFORMED_CHARACTER_DATA_CLOSE: Final[re.Pattern[str]] = re.compile(r"</CDATA>", re.IGNORECASE)

# A closing tag immediately repeated with only tag-free content between, which
# models emit when they lose track of what they have already closed.
_DUPLICATE_CLOSING_TAG: Final[re.Pattern[str]] = re.compile(r"(</([A-Za-z_][\w:.\-]*)>)[^<]*</\2>")

# An ampersand that does not open a character reference.
_BARE_AMPERSAND: Final[re.Pattern[str]] = re.compile(
    r"&(?!#\d+;|#x[0-9A-Fa-f]+;|[A-Za-z][A-Za-z0-9]*;)"
)

# A less-than sign that does not open a tag, a closing tag, a comment, or a
# character-data section.
_STRAY_LESS_THAN: Final[re.Pattern[str]] = re.compile(r"<(?![/!?]|[A-Za-z_])")


def extract_element_text(
    content: str, root_tag: str, metadata: dict[str, Any] | None = None
) -> str:
    """Isolates one element from an answer that may surround it with prose."""
    opening = re.compile(rf"<{re.escape(root_tag)}\b[^>]*>")
    opening_match = opening.search(content)
    if opening_match is None:
        raise PipelineError.retryable(
            f"model answer contains no <{root_tag}> element",
            {**(metadata or {}), "error_code": "xml_parse", "root_tag": root_tag},
        )

    closing = re.compile(rf"</{re.escape(root_tag)}>")
    closing_match = closing.search(content, opening_match.end())
    if closing_match is not None:
        return content[opening_match.start() : closing_match.end()].strip()

    # An answer cut off before its closing tag is exactly the case the recovering
    # parser handles, and it is likeliest on the longest answers, where a retry costs
    # the most.
    logger.info(
        "model answer was cut off before its closing tag, recovering what is there",
        root_tag=root_tag,
        character_count=len(content) - opening_match.start(),
    )
    return content[opening_match.start() :].strip()


def parse_recovering(
    content: str, root_tag: str, metadata: dict[str, Any] | None = None
) -> etree._Element:
    """Parses an answer into an element, repairing what the parser cannot."""
    error_context = {
        **(metadata or {}),
        "error_code": "xml_parse",
        "root_tag": root_tag,
    }
    element_text = extract_element_text(content, root_tag, metadata)
    repaired = _repair(element_text)

    parser = etree.XMLParser(recover=True, resolve_entities=False, strip_cdata=False)
    # Annotated as optional deliberately: the stubs promise an element, but a
    # recovering parse of an answer carrying no element really does yield None.
    root: etree._Element | None
    try:
        root = etree.fromstring(repaired.encode("utf-8"), parser=parser)
    except etree.XMLSyntaxError as error:
        raise PipelineError.retryable(
            "model answer could not be parsed as XML even with recovery",
            error_context,
            error,
        ) from error

    if root is None:
        raise PipelineError.retryable("XML recovery produced no root element", error_context)
    if root.tag != root_tag:
        raise PipelineError.retryable(
            f"recovered root element is <{root.tag}>, expected <{root_tag}>",
            {**error_context, "recovered_root_tag": str(root.tag)},
        )

    if repaired != element_text:
        logger.debug(
            "model answer required XML repair before parsing",
            root_tag=root_tag,
            original_character_count=len(element_text),
            repaired_character_count=len(repaired),
        )
    return root


def read_element_tree(element: etree._Element) -> Any:  # noqa: ANN401
    """Converts an element into nested mappings, lists, and strings."""
    children = list(element)
    if not children:
        return (element.text or "").strip()

    converted: dict[str, Any] = {}
    for child in children:
        # A comment or processing instruction carries a callable tag rather than a
        # name, and contributes nothing to the content being read.
        if callable(child.tag):
            continue
        value = read_element_tree(child)
        existing = converted.get(child.tag)
        if existing is None and child.tag not in converted:
            converted[child.tag] = value
        elif isinstance(existing, list):
            existing.append(value)
        else:
            converted[child.tag] = [existing, value]
    return converted


def _repair(element_text: str) -> str:
    """Applies the three repairs the parser's own recovery does not cover."""
    repaired = _MALFORMED_CHARACTER_DATA_CLOSE.sub("]]>", element_text)
    repaired = _DUPLICATE_CLOSING_TAG.sub(r"\1", repaired)
    return _escape_stray_markup_characters(repaired)


def _escape_stray_markup_characters(element_text: str) -> str:
    """Escapes ampersands and less-than signs that are not part of markup."""
    segments = re.split(r"(<!\[CDATA\[.*?\]\]>)", element_text, flags=re.DOTALL)
    for index, segment in enumerate(segments):
        if segment.startswith("<![CDATA["):
            continue
        escaped = _BARE_AMPERSAND.sub("&amp;", segment)
        segments[index] = _STRAY_LESS_THAN.sub("&lt;", escaped)
    return "".join(segments)


"""Validating recovered XML against a schema, and the coercions it needs."""


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


"""Building the XML documents that carry structured content into a prompt."""


# Two spaces, matching the indentation the prompts are written with.
_INDENTATION = "  "


def build_xml_document(
    root_tag: str,
    payload: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    raw_text_tags: Sequence[str] = (),
) -> str:
    """Renders a payload as an indented XML document."""
    raw_tags = frozenset(raw_text_tags)

    if isinstance(payload, Mapping):
        root = etree.Element(root_tag)
        _fill_element(root, payload, raw_tags)
        etree.indent(root, space=_INDENTATION)
        return etree.tostring(root, encoding="unicode") + "\n"

    rendered_siblings = []
    for item in payload:
        sibling = etree.Element(root_tag)
        _fill_element(sibling, item, raw_tags)
        etree.indent(sibling, space=_INDENTATION)
        rendered_siblings.append(etree.tostring(sibling, encoding="unicode"))
    return "\n".join(rendered_siblings) + "\n"


def _fill_element(
    element: etree._Element, payload: Mapping[str, Any], raw_tags: frozenset[str]
) -> None:
    """Adds one child element per entry in a mapping."""
    for tag, value in payload.items():
        if isinstance(value, Sequence) and not isinstance(value, str | bytes):
            for item in value:
                _append_value(element, tag, item, raw_tags)
        else:
            _append_value(element, tag, value, raw_tags)


def _append_value(parent: etree._Element, tag: str, value: Any, raw_tags: frozenset[str]) -> None:
    """Appends one child element carrying one value."""
    child = etree.SubElement(parent, tag)
    if value is None:
        return
    if isinstance(value, Mapping):
        _fill_element(child, value, raw_tags)
        return
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for item in value:
            _append_value(child, tag, item, raw_tags)
        return

    text = _render_scalar(value)
    if tag in raw_tags or isinstance(value, bool | int | float):
        child.text = text
    else:
        child.text = etree.CDATA(text)


def _render_scalar(value: Any) -> str:
    """Renders one scalar as the text an element will carry."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
