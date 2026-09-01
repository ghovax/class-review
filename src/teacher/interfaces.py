"""Interfaces accepted by Teacher operations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from langchain_core.messages import BaseMessage
from teacher.models import Chapter, ChapterOutline, LessonMaterials


class ChatModel(Protocol):
    """Minimal asynchronous chat-model interface required by Teacher."""

    async def ainvoke(self, messages: Sequence[BaseMessage]) -> Any: ...


class ChapterWritingOperation(Protocol):
    """Operation interface accepted by the full-outline lesson writer."""

    async def write(
        self,
        outline: ChapterOutline,
        materials: LessonMaterials,
        *,
        chapter_index: int,
        total_chapters: int,
        previous_chapter_count: int,
        previous_concept_count: int,
    ) -> Chapter: ...
