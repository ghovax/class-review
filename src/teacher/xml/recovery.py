"""Recovering usable XML from a model's answer."""

from __future__ import annotations

import re
from typing import Any, Final

from lxml import etree

from teacher.errors import PipelineError
from teacher.logging_support import get_logger

__all__ = ["extract_element_text", "parse_recovering", "read_element_tree"]

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
