"""Coordinate writing for a complete lesson outline."""

from __future__ import annotations

import asyncio

from teacher.interfaces import ChatModel
from teacher.lesson.chapter import ChapterWriter
from teacher.models import Chapter, LessonMaterials, LessonOutline
from teacher.prompts import Prompts


class LessonWriter:
    """Write a complete lesson while keeping chapter coordination internal."""

    def __init__(
        self,
        text_model: ChatModel,
        *,
        prompts: Prompts | None = None,
    ) -> None:
        self.chapter_writer = ChapterWriter(text_model, prompts=prompts)

    async def write_lesson(
        self,
        outline: LessonOutline,
        materials: LessonMaterials,
    ) -> tuple[Chapter, ...]:
        """Write all outline chapters as one complete lesson operation."""
        total_chapters = len(outline.chapters)
        return tuple(
            await asyncio.gather(
                *(
                    self.chapter_writer.write(
                        chapter_outline,
                        materials,
                        chapter_index=index,
                        total_chapters=total_chapters,
                        previous_chapter_count=index - 1,
                        previous_concept_count=sum(
                            len(previous.concepts) for previous in outline.chapters[: index - 1]
                        ),
                    )
                    for index, chapter_outline in enumerate(outline.chapters, start=1)
                )
            )
        )
