"""Markdown parsing and serialization backed by Wenmode."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from functools import partial
import re

import yaml
from wenmode import MarkdownRenderer, Wenmode
from wenmode.nodes import Heading, InlineCode, Node, Parent, Root, Table, TableCell, TableRow, Text
from wenmode.plugins import frontmatter
from wenmode.presets import github


_FRONTMATTER_DUMP = partial(
    yaml.safe_dump,
    sort_keys=False,
    allow_unicode=True,
    default_flow_style=False,
    width=1000,
)
_MARKDOWN = Wenmode(
    rules=github,
    renderer=MarkdownRenderer(),
    plugins=[frontmatter.configure(load=yaml.safe_load, dump=_FRONTMATTER_DUMP)],
)
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


def compose_markdown(
    parts: Iterable[str], *, frontmatter_data: Mapping[str, object] | None = None
) -> str:
    """Parse Markdown blocks into one AST, optionally attaching YAML frontmatter."""
    document, footnotes = _parse(parts)
    if frontmatter_data is not None:
        frontmatter_document = Root(data={"frontmatter": dict(frontmatter_data)})
        frontmatter_document.children.extend(document.children)
        document = frontmatter_document
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


def render_table(
    headers: tuple[str, str],
    rows: Iterable[tuple[str, str]],
    *,
    code_columns: tuple[int, ...] = (),
    align: tuple[str | None, str | None] = (None, "right"),
) -> str:
    """Build and serialize a Markdown table with Wenmode AST nodes."""

    def cell(value: str, column_index: int, *, code: bool = False) -> TableCell:
        content = (
            InlineCode(value=value) if code and column_index in code_columns else Text(value=value)
        )
        return TableCell(children=[content])

    table_rows: list[Node] = [
        TableRow(
            children=[
                cell(headers[0], 0),
                cell(headers[1], 1),
            ]
        ),
        *(
            TableRow(
                children=[
                    cell(left, 0, code=True),
                    cell(right, 1, code=True),
                ]
            )
            for left, right in rows
        ),
    ]
    table = Table(align=list(align), children=table_rows)
    return _MARKDOWN.render_node(Root(children=[table])).strip()
