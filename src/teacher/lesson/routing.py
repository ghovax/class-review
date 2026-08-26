"""Deciding when the chapter loop has finished."""

from __future__ import annotations

from typing import Literal

from teacher.logging_support import get_logger
from teacher.state import LessonState

__all__ = ["route_after_chapter"]

logger = get_logger(__name__)


def route_after_chapter(
    state: LessonState,
) -> Literal["write_chapter", "build_glossary"]:
    """Sends the run back for another chapter, or onward once none are left."""
    plan = state.get("plan")
    written = len(state.get("chapter_drafts", []))
    if plan is not None and written < len(plan.chapters):
        return "write_chapter"

    logger.info("every chapter written", chapter_count=written)
    return "build_glossary"
