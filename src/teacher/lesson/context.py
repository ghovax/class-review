"""Build transcript excerpts for one chapter."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from teacher.configuration import LessonConfiguration, TranscriptConfiguration
from teacher.models import ChapterOutline, TranscriptSegment


@dataclass(frozen=True, slots=True)
class TimedSentence:
    start_seconds: float
    end_seconds: float
    content: str


@dataclass(frozen=True, slots=True)
class TranscriptExcerpt:
    start_seconds: float
    end_seconds: float
    content: str


@dataclass(frozen=True, slots=True)
class ConceptSlice:
    concept_index: int
    topic_title: str
    excerpts: tuple[TranscriptExcerpt, ...]


@dataclass(frozen=True, slots=True)
class ChapterContext:
    start_seconds: float
    end_seconds: float
    concept_slices: tuple[ConceptSlice, ...]


def split_into_sentences(
    segment: TranscriptSegment, zero_duration_seconds: float = 1e-6
) -> list[TimedSentence]:
    text = segment.content.strip()
    if not text:
        return []
    text = re.sub(r"([。！？])(?=\S)", r"\1 ", text)
    fragments = [
        part.strip() for part in re.split(r"(?<=[.!?…؟။።॥।۔。！？])\s+|\n+", text) if part.strip()
    ]
    if len(fragments) == 1:
        return [
            TimedSentence(
                segment.start_seconds,
                max(segment.end_seconds, segment.start_seconds + zero_duration_seconds),
                text,
            )
        ]
    duration = max(0.0, segment.end_seconds - segment.start_seconds)
    weights = [max(1, len(fragment.split())) for fragment in fragments]
    total = sum(weights)
    cursor = segment.start_seconds
    result: list[TimedSentence] = []
    for index, fragment in enumerate(fragments):
        end = (
            segment.end_seconds
            if index == len(fragments) - 1
            else cursor + duration * weights[index] / total
        )
        result.append(TimedSentence(cursor, max(cursor, end), fragment))
        cursor = end
    return result


def build_chapter_context(
    *,
    chapter: ChapterOutline,
    segments: Sequence[TranscriptSegment],
    lesson_configuration: LessonConfiguration,
    transcript_configuration: TranscriptConfiguration,
) -> ChapterContext:
    if not chapter.concepts:
        return ChapterContext(0.0, 0.0, ())
    start = min(item.transcript_span.start_seconds for item in chapter.concepts)
    end = max(item.transcript_span.end_seconds for item in chapter.concepts)
    start = max(0.0, start - lesson_configuration.chapter_context_margin_seconds)
    end += lesson_configuration.chapter_context_margin_seconds
    sentences = [
        sentence
        for segment in segments
        if segment.end_seconds > start and segment.start_seconds < end
        for sentence in split_into_sentences(
            segment, transcript_configuration.zero_duration_seconds
        )
        if start <= (sentence.start_seconds + sentence.end_seconds) / 2 < end
    ]
    slices = []
    for concept in chapter.concepts:
        excerpts = tuple(
            TranscriptExcerpt(sentence.start_seconds, sentence.end_seconds, sentence.content)
            for sentence in sentences
            if concept.transcript_span.start_seconds
            <= (sentence.start_seconds + sentence.end_seconds) / 2
            <= concept.transcript_span.end_seconds
        )
        slices.append(ConceptSlice(concept.concept_index, concept.topic_title, excerpts))
    return ChapterContext(start, end, tuple(slices))
