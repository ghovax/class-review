"""Build transcript context for lesson chapters."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from teacher.configuration import LessonPolicy, TranscriptPolicy
from teacher.models import (
    Concept,
    PlannedChapter,
    TranscriptSegment,
)
from typing import Final
import re

_SENTENCE_TERMINATORS: Final[str] = ".!?…؟။።॥।۔。！？"


_UNSPACED_TERMINATOR_PATTERN: Final[re.Pattern[str]] = re.compile(r"([。！？])(?=\S)", re.UNICODE)


_ABBREVIATIONS: Final[frozenset[str]] = frozenset(
    {
        "dr",
        "mr",
        "mrs",
        "ms",
        "prof",
        "st",
        "sr",
        "jr",
        "rev",
        "sig",
        "sigg",
        "sigra",
        "sigr",
        "dott",
        "egr",
        "ing",
        "inc",
        "ltd",
        "co",
        "corp",
        "spa",
        "srl",
        "gmbh",
        "e.g",
        "i.e",
        "cf",
        "viz",
        "etc",
        "et",
        "al",
        "fig",
        "eq",
        "ch",
        "vol",
        "no",
        "pp",
        "p",
        "vs",
        "ecc",
        "es",
        "z.b",
        "u.a",
    }
)


_TRAILING_ABBREVIATION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"([A-Za-z]+(?:\.[A-Za-z]+)*)\.$"
)


@dataclass(frozen=True, slots=True)
class TimedSentence:
    """One sentence with the stretch of time it was spoken over."""

    start_seconds: float
    end_seconds: float
    content: str


@dataclass(frozen=True, slots=True)
class TranscriptExcerpt:
    """A run of consecutive sentences shown to a model as one passage."""

    start_seconds: float
    end_seconds: float
    content: str


@dataclass(frozen=True, slots=True)
class ConceptSlice:
    """The transcript excerpts one concept may draw from."""

    concept_index: int
    topic_title: str
    excerpts: tuple[TranscriptExcerpt, ...]


@dataclass(frozen=True, slots=True)
class ChapterContext:
    """The transcript material one chapter may draw from."""

    start_seconds: float
    end_seconds: float
    concept_slices: tuple[ConceptSlice, ...]


def split_into_sentences(
    segment: TranscriptSegment, zero_duration_seconds: float = 1e-6
) -> list[TimedSentence]:
    """Divides one segment into sentences, each given a share of its time."""
    degenerate_width = zero_duration_seconds
    text = segment.content.strip()
    if not text:
        return []

    start_seconds = min(segment.start_seconds, segment.end_seconds)
    end_seconds = max(segment.start_seconds, segment.end_seconds)
    duration_seconds = end_seconds - start_seconds

    sentences = _merge_across_abbreviations(_split_text(text))

    if len(sentences) <= 1:
        widened_end = end_seconds if duration_seconds > 0 else start_seconds + degenerate_width
        return [TimedSentence(start_seconds=start_seconds, end_seconds=widened_end, content=text)]

    if duration_seconds <= 0:
        return [
            TimedSentence(
                start_seconds=start_seconds + position * degenerate_width,
                end_seconds=start_seconds + (position + 1) * degenerate_width,
                content=sentence,
            )
            for position, sentence in enumerate(sentences)
        ]

    weights = [max(1, _count_words(sentence)) for sentence in sentences]
    total_weight = sum(weights)
    timed: list[TimedSentence] = []
    cursor = start_seconds

    for position, sentence in enumerate(sentences):
        share = weights[position] / total_weight if total_weight else 1 / len(sentences)
        next_time = (
            end_seconds if position == len(sentences) - 1 else cursor + duration_seconds * share
        )
        timed.append(TimedSentence(start_seconds=cursor, end_seconds=next_time, content=sentence))
        cursor = next_time
    return timed


def build_chapter_context(
    *,
    chapters: Sequence[PlannedChapter],
    chapter_index: int,
    segments: Sequence[TranscriptSegment],
    lesson_policy: LessonPolicy,
    transcript_policy: TranscriptPolicy,
) -> ChapterContext:
    """Works out what one chapter may draw from, and divides it by concept."""
    if not 0 <= chapter_index < len(chapters):
        return ChapterContext(start_seconds=0.0, end_seconds=0.0, concept_slices=())

    chapter = chapters[chapter_index]
    if not chapter.concepts:
        return ChapterContext(start_seconds=0.0, end_seconds=0.0, concept_slices=())

    start_seconds, end_seconds = _resolve_bounds(chapters, chapter_index, lesson_policy)
    sentences = _select_sentences_in_context(
        segments,
        start_seconds,
        end_seconds,
        transcript_policy,
    )
    concept_slices = _divide_among_concepts(
        concepts=chapter.concepts,
        sentences=sentences,
        context_start=start_seconds,
        context_end=end_seconds,
        lesson_policy=lesson_policy,
    )
    return ChapterContext(
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        concept_slices=concept_slices,
    )


def _resolve_bounds(
    chapters: Sequence[PlannedChapter],
    chapter_index: int,
    lesson_policy: LessonPolicy,
) -> tuple[float, float]:
    """Settles a chapter's bounds against its neighbours."""
    concepts = chapters[chapter_index].concepts
    requested_start = min(concept.transcript_span.start_seconds for concept in concepts)
    requested_end = max(concept.transcript_span.end_seconds for concept in concepts)

    previous_end = _last_end(chapters, chapter_index - 1)
    next_start = _first_start(chapters, chapter_index + 1)

    left_cut = (
        _midpoint(previous_end, requested_start) if previous_end is not None else float("-inf")
    )
    right_cut = _midpoint(requested_end, next_start) if next_start is not None else float("inf")

    margin = lesson_policy.chapter_context_margin_seconds
    start_seconds = max(0.0, requested_start - margin, left_cut)
    end_seconds = max(start_seconds, min(requested_end + margin, right_cut))
    return start_seconds, end_seconds


def _divide_among_concepts(
    *,
    concepts: Sequence[Concept],
    sentences: Sequence[TimedSentence],
    context_start: float,
    context_end: float,
    lesson_policy: LessonPolicy,
) -> tuple[ConceptSlice, ...]:
    """Divides a chapter's transcript context among its concepts."""
    ordered = sorted(
        enumerate(concepts),
        key=lambda entry: (entry[1].transcript_span.start_seconds, entry[0]),
    )

    slices: list[tuple[int, ConceptSlice]] = []
    for position, (original_position, concept) in enumerate(ordered):
        is_first = position == 0
        is_last = position == len(ordered) - 1
        slice_start = (
            context_start
            if is_first
            else _midpoint(
                ordered[position - 1][1].transcript_span.end_seconds,
                concept.transcript_span.start_seconds,
            )
        )
        slice_end = (
            context_end
            if is_last
            else _midpoint(
                concept.transcript_span.end_seconds,
                ordered[position + 1][1].transcript_span.start_seconds,
            )
        )
        covered = [
            sentence for sentence in sentences if slice_start <= _midpoint_of(sentence) < slice_end
        ]
        slices.append(
            (
                original_position,
                ConceptSlice(
                    concept_index=concept.concept_index,
                    topic_title=concept.topic_title,
                    excerpts=_build_transcript_excerpts(covered, lesson_policy),
                ),
            )
        )

    return tuple(entry[1] for entry in sorted(slices, key=lambda entry: entry[0]))


def _select_sentences_in_context(
    segments: Sequence[TranscriptSegment],
    context_start: float,
    context_end: float,
    transcript_policy: TranscriptPolicy,
) -> list[TimedSentence]:
    """Divide the transcript into sentences and keep those in the chapter context."""
    overlapping = [
        segment
        for segment in segments
        if max(segment.start_seconds, segment.end_seconds) > context_start
        and min(segment.start_seconds, segment.end_seconds) < context_end
    ]
    sentences = [
        sentence
        for segment in sorted(
            overlapping,
            key=lambda item: (
                min(item.start_seconds, item.end_seconds),
                max(item.start_seconds, item.end_seconds),
                item.content,
            ),
        )
        for sentence in split_into_sentences(segment, transcript_policy.zero_duration_seconds)
    ]
    kept = [
        sentence
        for sentence in sentences
        if context_start <= _midpoint_of(sentence) < context_end
        and sentence.end_seconds > sentence.start_seconds
        and sentence.content.strip()
    ]
    return sorted(
        kept,
        key=lambda item: (item.start_seconds, item.end_seconds, item.content),
    )


def _build_transcript_excerpts(
    sentences: Sequence[TimedSentence], lesson_policy: LessonPolicy
) -> tuple[TranscriptExcerpt, ...]:
    """Join consecutive sentences into passages within the model context limit."""
    excerpts: list[TranscriptExcerpt] = []
    for sentence in sentences:
        if not excerpts:
            excerpts.append(
                TranscriptExcerpt(
                    start_seconds=sentence.start_seconds,
                    end_seconds=sentence.end_seconds,
                    content=sentence.content,
                )
            )
            continue
        current = excerpts[-1]
        if (
            sentence.end_seconds - current.start_seconds
            <= lesson_policy.maximum_chapter_context_seconds
        ):
            excerpts[-1] = TranscriptExcerpt(
                start_seconds=current.start_seconds,
                end_seconds=sentence.end_seconds,
                content=re.sub(r"[ \t]{2,}", " ", f"{current.content} {sentence.content}").strip(),
            )
        else:
            excerpts.append(
                TranscriptExcerpt(
                    start_seconds=sentence.start_seconds,
                    end_seconds=sentence.end_seconds,
                    content=sentence.content,
                )
            )
    return tuple(excerpts)


def _split_text(text: str) -> list[str]:
    """Divides text at sentence boundaries."""
    spaced = _UNSPACED_TERMINATOR_PATTERN.sub(r"\1 ", text)
    boundary = re.compile(rf"(?<=[{re.escape(_SENTENCE_TERMINATORS)}])\s+|\n+", re.UNICODE)
    return [fragment.strip() for fragment in boundary.split(spaced) if fragment.strip()]


def _merge_across_abbreviations(fragments: Sequence[str]) -> list[str]:
    """Glues a fragment back on when the split landed inside an abbreviation."""
    merged: list[str] = []
    for fragment in fragments:
        if merged and _ends_with_abbreviation(merged[-1]):
            merged[-1] = f"{merged[-1]} {fragment}"
        else:
            merged.append(fragment)
    return merged


def _ends_with_abbreviation(sentence: str) -> bool:
    """Reports whether a fragment ends in a known abbreviation."""
    match = _TRAILING_ABBREVIATION_PATTERN.search(sentence)
    return match is not None and match.group(1).lower() in _ABBREVIATIONS


def _count_words(text: str) -> int:
    """Counts the words in a fragment."""
    return len([word for word in text.strip().split() if word])


def _midpoint(left_end: float, right_start: float) -> float:
    """Return the instant two adjacent transcript contexts meet at."""
    return (left_end + right_start) / 2


def _midpoint_of(sentence: TimedSentence) -> float:
    """Return a sentence's midpoint for context selection."""
    return (sentence.start_seconds + sentence.end_seconds) / 2


def _last_end(chapters: Sequence[PlannedChapter], index: int) -> float | None:
    """Returns where a chapter's material ends, when the chapter exists."""
    if not 0 <= index < len(chapters) or not chapters[index].concepts:
        return None
    return max(concept.transcript_span.end_seconds for concept in chapters[index].concepts)


def _first_start(chapters: Sequence[PlannedChapter], index: int) -> float | None:
    """Returns where a chapter's material begins, when the chapter exists."""
    if not 0 <= index < len(chapters) or not chapters[index].concepts:
        return None
    return min(concept.transcript_span.start_seconds for concept in chapters[index].concepts)
