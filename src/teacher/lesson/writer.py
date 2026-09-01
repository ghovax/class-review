"""Coordinate writing for a complete lesson outline."""

from __future__ import annotations

import asyncio
from enum import StrEnum

from teacher.interfaces import ChapterWritingOperation, ChatModel
from teacher.lesson.chapter import ChapterWriter
from teacher.models import Chapter, LessonMaterials, LessonOutline
from teacher.prompts import Prompts


class LessonWritingStrategy(StrEnum):
    """Execution strategy chosen by the caller for outline chapter writing."""

    SEQUENTIAL = "sequential"
    CONCURRENT = "concurrent"


class LessonWriter:
    """Write every chapter in an outline with caller-selected coordination."""

    def __init__(
        self,
        text_model: ChatModel,
        *,
        prompts: Prompts | None = None,
        chapter_writer: ChapterWritingOperation | None = None,
    ) -> None:
        self.chapter_writer = chapter_writer or ChapterWriter(text_model, prompts=prompts)

    async def write(
        self,
        outline: LessonOutline,
        materials: LessonMaterials,
        *,
        strategy: LessonWritingStrategy | str = LessonWritingStrategy.CONCURRENT,
    ) -> tuple[Chapter, ...]:
        """Write all outline chapters sequentially or concurrently as requested."""
        try:
            selected_strategy = LessonWritingStrategy(strategy)
        except ValueError as error:
            supported = ", ".join(item.value for item in LessonWritingStrategy)
            raise ValueError(
                f"unsupported lesson writing strategy; expected: {supported}"
            ) from error

        total_chapters = len(outline.chapters)
        if selected_strategy is LessonWritingStrategy.CONCURRENT:
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

        chapters: list[Chapter] = []
        previous_concept_count = 0
        for index, chapter_outline in enumerate(outline.chapters, start=1):
            chapters.append(
                await self.chapter_writer.write(
                    chapter_outline,
                    materials,
                    chapter_index=index,
                    total_chapters=total_chapters,
                    previous_chapter_count=index - 1,
                    previous_concept_count=previous_concept_count,
                )
            )
            previous_concept_count += len(chapter_outline.concepts)
        return tuple(chapters)
