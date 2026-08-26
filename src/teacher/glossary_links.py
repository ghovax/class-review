"""Find and render glossary links with plain text operations."""

from __future__ import annotations

import re
from collections.abc import Sequence

from teacher.models import GlossaryEntry, GlossaryLink

__all__ = ["apply_glossary_links", "compute_glossary_links"]


def compute_glossary_links(
    chapter_contents: Sequence[str], glossary_entries: Sequence[GlossaryEntry]
) -> list[tuple[GlossaryLink, ...]]:
    """Link the first plain-text occurrence of each glossary term."""
    remaining = {entry.key for entry in glossary_entries if entry.short_form.strip()}
    links_per_chapter: list[tuple[GlossaryLink, ...]] = []
    for content in chapter_contents:
        chapter_links: list[GlossaryLink] = []
        for entry in glossary_entries:
            if entry.key not in remaining:
                continue
            phrase = entry.short_form.strip()
            match = re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", content, re.IGNORECASE)
            if match is None:
                continue
            chapter_links.append(
                GlossaryLink(key=entry.key, start=match.start(), end=match.end())
            )
            remaining.remove(entry.key)
        links_per_chapter.append(tuple(sorted(chapter_links, key=lambda link: link.start)))
    return links_per_chapter


def apply_glossary_links(content: str, links: Sequence[GlossaryLink]) -> str:
    """Wrap stored character ranges in ordinary Markdown links."""
    result = content
    for link in sorted(links, key=lambda item: item.start, reverse=True):
        if not 0 <= link.start < link.end <= len(result):
            continue
        text = result[link.start : link.end]
        result = f"{result[:link.start]}[{text}](#glossary-{link.key}){result[link.end:]}"
    return result
