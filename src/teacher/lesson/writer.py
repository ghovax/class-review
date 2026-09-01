"""Coordinate ordered writing for a complete lesson outline."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from models_provider import ModelUsage

from teacher.interfaces import ChatModel
from teacher.lesson.chapter import ChapterWriter, ChapterWriting
from teacher.lesson.context import build_chapter_context
from teacher.models import Chapter, LessonMaterials, LessonOutline
from teacher.prompts import Prompts
from teacher.support import ModelAnswer


@dataclass(frozen=True, slots=True)
class LessonWritingResult:
    """Completed chapters and the model calls retained while writing them."""

    chapters: tuple[Chapter, ...]
    chapter_writings: tuple[ChapterWriting, ...]
    usage_by_model: dict[str, ModelUsage]

    def __iter__(self) -> Iterator[Chapter]:
        """Allow existing callers to iterate over the completed chapters."""
        return iter(self.chapters)

    def __len__(self) -> int:
        """Report the number of completed chapters."""
        return len(self.chapters)

    def __getitem__(self, index: int | slice) -> Chapter | tuple[Chapter, ...]:
        """Allow existing callers to index or slice the completed chapters."""
        return self.chapters[index]


class LessonWriter:
    """Write a complete lesson in outline order with continuity between chapters."""

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
    ) -> LessonWritingResult:
        """Write chapters sequentially while retaining every successful model call."""
        total_chapters = len(outline.chapters)
        writings: list[ChapterWriting] = []
        previous_concepts = []
        previous_answers: list[ModelAnswer] = []

        for position, chapter_outline in enumerate(outline.chapters):
            context = build_chapter_context(
                chapter=chapter_outline,
                previous_chapter=outline.chapters[position - 1] if position else None,
                next_chapter=(
                    outline.chapters[position + 1] if position + 1 < total_chapters else None
                ),
                segments=materials.transcript.segments,
            )
            writing = await self.chapter_writer._write(
                chapter_outline,
                materials,
                chapter_index=position + 1,
                total_chapters=total_chapters,
                previous_chapter_count=position,
                previous_concept_count=len(previous_concepts),
                previous_concepts=tuple(previous_concepts),
                previous_answers=tuple(previous_answers),
                context=context,
            )
            writings.append(writing)
            previous_concepts.extend(chapter_outline.concepts)
            previous_answers.append(writing.model_answer)

        return LessonWritingResult(
            chapters=tuple(writing.chapter for writing in writings),
            chapter_writings=tuple(writings),
            usage_by_model=_merge_usage(writing.model_answer for writing in writings),
        )


def _merge_usage(answers: Iterator[ModelAnswer]) -> dict[str, ModelUsage]:
    """Aggregate usage without losing reasoning-token and cache counters."""
    totals: dict[str, ModelUsage] = {}
    for answer in answers:
        for model_name, usage in answer.usage_by_model.items():
            totals[model_name] = totals.get(model_name, ModelUsage()).combined_with(usage)
    return totals
