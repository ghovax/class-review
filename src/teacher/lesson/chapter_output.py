"""Extracting the small structured envelope around a generated chapter."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from lxml import etree

from teacher.errors import PipelineError
from teacher.models import Citation

__all__ = ["ChapterOutput", "read_chapter_output"]

_CITATION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"[ \t]*`?<Citation>.*?</Citation>`?[ \t]*", re.DOTALL
)
_HEADING_PATTERN: Final[re.Pattern[str]] = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class ChapterOutput:
    """The chapter prose and citations returned by one model call."""

    title: str | None
    content: str
    section_count: int
    citations: tuple[Citation, ...]


def read_chapter_output(
    *, raw_content: str, chapter_index: int, starting_citation_index: int
) -> ChapterOutput:
    """Remove citation envelopes and the optional outer chapter title line.

    The chapter body remains the model's original text.  Teacher deliberately does
    not build or round-trip a Markdown syntax tree; Markdown is an output format,
    not an internal data model.
    """
    del chapter_index
    content = raw_content.strip()
    if not content:
        raise PipelineError.retryable("chapter output is empty")

    citations: list[Citation] = []

    def replace(match: re.Match[str]) -> str:
        citation = _read_citation(
            match.group(0).strip(), starting_citation_index + len(citations) + 1
        )
        if citation is None:
            return match.group(0)
        citations.append(citation)
        return f" [^{citation.number}] "

    content = _CITATION_PATTERN.sub(replace, content)
    headings = list(_HEADING_PATTERN.finditer(content))
    title: str | None = None
    if headings and headings[0].start() == 0 and len(headings[0].group(1)) == 1:
        title = headings[0].group(2).strip() or None
        content = content[headings[0].end() :].lstrip()

    section_count = sum(1 for match in _HEADING_PATTERN.finditer(content) if len(match.group(1)) == 2)
    return ChapterOutput(
        title=title,
        content=content.strip(),
        section_count=section_count,
        citations=tuple(citations),
    )


def _read_citation(element_text: str, number: int) -> Citation | None:
    """Read one XML citation envelope without interpreting the surrounding prose."""
    try:
        element = etree.fromstring(
            element_text.strip().strip("`").encode("utf-8"),
            parser=etree.XMLParser(recover=True, resolve_entities=False),
        )
    except etree.XMLSyntaxError:
        return None
    if element is None:
        return None
    content = _child_text(element, "Content")
    document_index = _child_integer(element, "DocumentIndex")
    page_number = _child_integer(element, "Page")
    if not content or document_index is None or page_number is None:
        return None
    return Citation(
        number=number,
        content=content,
        document_index=document_index,
        page_number=page_number,
    )


def _child_text(element: etree._Element, name: str) -> str:
    child = element.find(name)
    return "" if child is None else "".join(child.itertext()).strip()


def _child_integer(element: etree._Element, name: str) -> int | None:
    try:
        return int(_child_text(element, name))
    except ValueError:
        return None
