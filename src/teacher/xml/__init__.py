"""Recovering XML from model answers and validating it against a schema."""

from __future__ import annotations

from teacher.xml.documents import build_xml_document
from teacher.xml.recovery import (
    extract_element_text,
    parse_recovering,
    read_element_tree,
)
from teacher.xml.schema_definitions import (
    OneOrMany,
    RequiredText,
    case_insensitive_with_fallback,
    parse_xml_with_schema,
)

__all__ = [
    "OneOrMany",
    "RequiredText",
    "build_xml_document",
    "case_insensitive_with_fallback",
    "extract_element_text",
    "parse_recovering",
    "parse_xml_with_schema",
    "read_element_tree",
]
