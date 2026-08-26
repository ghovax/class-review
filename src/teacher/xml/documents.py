"""Building the XML documents that carry structured content into a prompt."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from lxml import etree

__all__ = ["build_xml_document"]

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
