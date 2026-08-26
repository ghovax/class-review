"""Markdown parsing and serialization backed by Wenmode."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
import re

from wenmode import MarkdownRenderer, Wenmode
from wenmode.nodes import Heading, Node, Parent, Root, Table, TableCell, TableRow, Text
from wenmode.presets import github


_MARKDOWN = Wenmode(rules=github, renderer=MarkdownRenderer())
_FOOTNOTE_MARKER = re.compile(r"\[\^([^\]]+)\]")


def _parse(parts: Iterable[str]) -> tuple[Root, dict[str, str]]:
    document = Root()
    footnotes: dict[str, str] = {}
    for part in parts:
        content = part.strip()
        if not content:
            continue

        def protect(match: re.Match[str]) -> str:
            token = f"x__fn{len(footnotes)}__"
            footnotes[token.replace("_", r"\_")] = match.group(0)
            return token

        document.children.extend(_MARKDOWN.parse(_FOOTNOTE_MARKER.sub(protect, content)).children)
    return document, footnotes


def _serialize(document: Root, footnotes: dict[str, str]) -> str:
    rendered = _MARKDOWN.render_node(document).strip()
    for token, marker in footnotes.items():
        rendered = rendered.replace(token, marker)
    return rendered


def compose_markdown(parts: Iterable[str]) -> str:
    """Parse Markdown blocks into one AST, then serialize that AST."""
    document, footnotes = _parse(parts)
    return _serialize(document, footnotes)


def shift_headings(markdown: str, levels: int) -> str:
    """Change heading depth in Markdown through the external AST library."""
    document, footnotes = _parse([markdown])
    for node in _headings(document.children):
        node.depth = min(6, max(1, node.depth + levels))
    return _serialize(document, footnotes)


def _headings(nodes: Iterable[Node]) -> Iterator[Heading]:
    for node in nodes:
        if isinstance(node, Heading):
            yield node
        if isinstance(node, Parent):
            yield from _headings(node.children)


def render_table(headers: tuple[str, str], rows: Iterable[tuple[str, str]]) -> str:
    """Build and serialize a Markdown table with Wenmode AST nodes."""
    table_rows: list[Node] = [
        TableRow(
            children=[
                TableCell(children=[Text(value=headers[0])]),
                TableCell(children=[Text(value=headers[1])]),
            ]
        ),
        *(
            TableRow(
                children=[
                    TableCell(children=[Text(value=left)]),
                    TableCell(children=[Text(value=right)]),
                ]
            )
            for left, right in rows
        ),
    ]
    table = Table(align=[None, "right"], children=table_rows)
    return _MARKDOWN.render_node(Root(children=[table])).strip()
