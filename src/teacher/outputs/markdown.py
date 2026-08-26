"""Building the canonical Markdown export from plain lesson data."""

from __future__ import annotations

import re
from collections.abc import Mapping

from teacher.errors import PipelineError
from teacher.glossary_links import apply_glossary_links
from teacher.models import Lesson
from teacher.outputs.citations import build_citation_definitions
from teacher.outputs.localization import export_labels
from teacher.outputs.models import ExportError, ExportMetadata
from teacher.outputs.source_listings import build_source_tables
from teacher.prompts import Prompts

__all__ = ["render_export_markdown"]

_TEMPLATES = Prompts(package="teacher.output_templates")


def render_export_template(name: str, variables: Mapping[str, object]) -> str:
    """Render one packaged export shape with strict placeholder checking."""

    try:
        return _TEMPLATES.render(name, variables)
    except PipelineError as error:
        raise ExportError(f"export template {name!r} could not be rendered") from error


def render_export_markdown(lesson: Lesson, metadata: ExportMetadata) -> str:
    """Renders a complete lesson by joining packaged text blocks."""
    blocks = [render_export_template("lesson", {
        "title": lesson.title.strip() or "Untitled",
        "description": lesson.description.strip(),
    }).strip(), *build_source_tables(lesson, metadata)]
    blocks.extend(_chapter_blocks(lesson))
    blocks.extend(_glossary_blocks(lesson, metadata))
    definitions = build_citation_definitions(lesson, metadata)
    if definitions:
        blocks.append("\n\n".join(f"[^{number}]: {body}" for number, body in definitions.items()))
    return "\n\n".join(block for block in blocks if block).strip() + "\n"


def _chapter_blocks(lecture: Lesson) -> list[str]:
    """Renders every chapter through the packaged text shape."""
    blocks: list[str] = []
    for chapter_index, chapter in enumerate(lecture.chapters):
        linked_content = apply_glossary_links(chapter.content, chapter.glossary_links)
        blocks.append(render_export_template("chapter", {
            "title": chapter.title.strip() or f"Chapter {chapter_index + 1}",
            "content": _shift_headings(linked_content, 1),
        }).strip())
    return blocks


def _glossary_blocks(lecture: Lesson, metadata: ExportMetadata) -> list[str]:
    """Renders the glossary heading and entries through packaged text shapes."""
    if not lecture.glossary:
        return []
    labels = export_labels(metadata.language)
    blocks = [render_export_template("glossary", {"title": labels.glossary}).strip()]
    for entry in lecture.glossary:
        display_name = (
            f"{entry.short_form} ({entry.long_form})" if entry.long_form else entry.short_form
        )
        blocks.append(render_export_template("glossary_entry", {
            "key": entry.key,
            "title": display_name,
            "description": entry.description,
        }).strip())
    return blocks


def _shift_headings(markdown: str, levels: int) -> str:
    """Moves every heading in a chapter by a fixed number of levels."""
    def shift(match: re.Match[str]) -> str:
        level = min(6, max(1, len(match.group(1)) + levels))
        return f"{'#' * level} {match.group(2)}"

    return re.sub(r"^(#{1,6})[ \t]+(.+?)[ \t]*$", shift, markdown, flags=re.MULTILINE).strip()
