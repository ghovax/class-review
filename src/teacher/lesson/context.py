"""Build bounded, sentence-aware transcript context for lesson chapters."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import re
from typing import Final

from teacher.models import ChapterOutline, TranscriptSegment


# These are algorithmic safeguards, not caller-selected writing strategies.
_CHAPTER_CONTEXT_MARGIN_SECONDS: Final[float] = 45.0
_CHAPTER_GROUP_SECONDS: Final[float] = 600.0
_ZERO_DURATION_SECONDS: Final[float] = 1e-6
_SENTENCE_TERMINATORS: Final[str] = ".!?…؟။።॥।۔。！？"
_UNSPACED_TERMINATOR_PATTERN: Final[re.Pattern[str]] = re.compile(r"([。！？])(?=\S)")
_TRAILING_ABBREVIATION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"([A-Za-z]+(?:\.[A-Za-z]+)*)\.$"
)
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


@dataclass(frozen=True, slots=True)
class TimedSentence:
    """One sentence with the stretch of time it was spoken over."""

    start_seconds: float
    end_seconds: float
    content: str


@dataclass(frozen=True, slots=True)
class TranscriptExcerpt:
    """A consecutive run of transcript sentences shown as one context block."""

    start_seconds: float
    end_seconds: float
    content: str


@dataclass(frozen=True, slots=True)
class ConceptSlice:
    """The transcript one concept may draw from."""

    concept_index: int
    topic_title: str
    excerpts: tuple[TranscriptExcerpt, ...]


@dataclass(frozen=True, slots=True)
class ChapterContext:
    """The bounded transcript context sent with one chapter request."""

    start_seconds: float
    end_seconds: float
    concept_slices: tuple[ConceptSlice, ...]


def split_into_sentences(
    segment: TranscriptSegment, zero_duration_seconds: float = _ZERO_DURATION_SECONDS
) -> list[TimedSentence]:
    """Split one segment into sentences and distribute its timestamps proportionally."""
    text = segment.content.strip()
    if not text:
        return []

    start_seconds = min(segment.start_seconds, segment.end_seconds)
    end_seconds = max(segment.start_seconds, segment.end_seconds)
    duration_seconds = end_seconds - start_seconds
    sentences = _merge_across_abbreviations(_split_text(text))

    if len(sentences) <= 1:
        widened_end = end_seconds if duration_seconds > 0 else start_seconds + zero_duration_seconds
        return [TimedSentence(start_seconds, widened_end, text)]

    if duration_seconds <= 0:
        return [
            TimedSentence(
                start_seconds + position * zero_duration_seconds,
                start_seconds + (position + 1) * zero_duration_seconds,
                sentence,
            )
            for position, sentence in enumerate(sentences)
        ]

    weights = [max(1, len(sentence.split())) for sentence in sentences]
    total_weight = sum(weights)
    cursor = start_seconds
    timed: list[TimedSentence] = []
    for position, sentence in enumerate(sentences):
        next_time = (
            end_seconds
            if position == len(sentences) - 1
            else cursor + duration_seconds * weights[position] / total_weight
        )
        timed.append(TimedSentence(cursor, next_time, sentence))
        cursor = next_time
    return timed


def build_chapter_context(
    *,
    chapter: ChapterOutline,
    segments: Sequence[TranscriptSegment],
    previous_chapter: ChapterOutline | None = None,
    next_chapter: ChapterOutline | None = None,
) -> ChapterContext:
    """Collect and assign transcript context without crossing chapter boundaries."""
    if not chapter.concepts:
        return ChapterContext(0.0, 0.0, ())

    requested_start = min(item.transcript_span.start_seconds for item in chapter.concepts)
    requested_end = max(item.transcript_span.end_seconds for item in chapter.concepts)
    previous_end = _chapter_end(previous_chapter)
    next_start = _chapter_start(next_chapter)
    left_cut = (
        _midpoint(previous_end, requested_start) if previous_end is not None else float("-inf")
    )
    right_cut = _midpoint(requested_end, next_start) if next_start is not None else float("inf")
    start_seconds = max(0.0, requested_start - _CHAPTER_CONTEXT_MARGIN_SECONDS, left_cut)
    end_seconds = max(
        start_seconds,
        min(requested_end + _CHAPTER_CONTEXT_MARGIN_SECONDS, right_cut),
    )

    sentences = _clip_to_window(segments, start_seconds, end_seconds)
    ordered_concepts = sorted(
        enumerate(chapter.concepts),
        key=lambda item: (item[1].transcript_span.start_seconds, item[0]),
    )
    slices: list[tuple[int, ConceptSlice]] = []
    for position, (original_position, concept) in enumerate(ordered_concepts):
        slice_start = (
            start_seconds
            if position == 0
            else _midpoint(
                ordered_concepts[position - 1][1].transcript_span.end_seconds,
                concept.transcript_span.start_seconds,
            )
        )
        slice_end = (
            end_seconds
            if position == len(ordered_concepts) - 1
            else _midpoint(
                concept.transcript_span.end_seconds,
                ordered_concepts[position + 1][1].transcript_span.start_seconds,
            )
        )
        covered = [
            sentence for sentence in sentences if slice_start <= _midpoint_of(sentence) < slice_end
        ]
        slices.append(
            (
                original_position,
                ConceptSlice(
                    concept.concept_index,
                    concept.topic_title,
                    _group_sentences(covered),
                ),
            )
        )

    return ChapterContext(
        start_seconds,
        end_seconds,
        tuple(item[1] for item in sorted(slices, key=lambda item: item[0])),
    )


def _clip_to_window(
    segments: Sequence[TranscriptSegment], window_start: float, window_end: float
) -> list[TimedSentence]:
    """Split overlapping transcript segments and keep sentences by midpoint."""
    overlapping = [
        segment
        for segment in segments
        if segment.end_seconds > window_start and segment.start_seconds < window_end
    ]
    sentences = [
        sentence
        for segment in sorted(
            overlapping,
            key=lambda item: (item.start_seconds, item.end_seconds, item.content),
        )
        for sentence in split_into_sentences(segment)
    ]
    return sorted(
        (
            sentence
            for sentence in sentences
            if window_start <= _midpoint_of(sentence) < window_end
            and sentence.end_seconds > sentence.start_seconds
            and sentence.content.strip()
        ),
        key=lambda item: (item.start_seconds, item.end_seconds, item.content),
    )


def _group_sentences(sentences: Sequence[TimedSentence]) -> tuple[TranscriptExcerpt, ...]:
    """Group nearby sentences into bounded excerpts while preserving their order."""
    groups: list[TranscriptExcerpt] = []
    for sentence in sentences:
        if not groups:
            groups.append(
                TranscriptExcerpt(sentence.start_seconds, sentence.end_seconds, sentence.content)
            )
            continue
        current = groups[-1]
        if sentence.end_seconds - current.start_seconds <= _CHAPTER_GROUP_SECONDS:
            groups[-1] = TranscriptExcerpt(
                current.start_seconds,
                sentence.end_seconds,
                re.sub(r"[ \t]{2,}", " ", f"{current.content} {sentence.content}").strip(),
            )
        else:
            groups.append(
                TranscriptExcerpt(sentence.start_seconds, sentence.end_seconds, sentence.content)
            )
    return tuple(groups)


def _split_text(text: str) -> list[str]:
    """Split text at sentence boundaries across supported writing systems."""
    spaced = _UNSPACED_TERMINATOR_PATTERN.sub(r"\1 ", text)
    boundary = re.compile(rf"(?<=[{re.escape(_SENTENCE_TERMINATORS)}])\s+|\n+")
    return [fragment.strip() for fragment in boundary.split(spaced) if fragment.strip()]


def _merge_across_abbreviations(fragments: Sequence[str]) -> list[str]:
    """Join fragments when a sentence split landed inside an abbreviation."""
    merged: list[str] = []
    for fragment in fragments:
        if merged and _ends_with_abbreviation(merged[-1]):
            merged[-1] = f"{merged[-1]} {fragment}"
        else:
            merged.append(fragment)
    return merged


def _ends_with_abbreviation(sentence: str) -> bool:
    match = _TRAILING_ABBREVIATION_PATTERN.search(sentence)
    return match is not None and match.group(1).lower() in _ABBREVIATIONS


def _midpoint(left: float, right: float) -> float:
    return (left + right) / 2


def _midpoint_of(sentence: TimedSentence) -> float:
    return (sentence.start_seconds + sentence.end_seconds) / 2


def _chapter_end(chapter: ChapterOutline | None) -> float | None:
    if chapter is None or not chapter.concepts:
        return None
    return max(concept.transcript_span.end_seconds for concept in chapter.concepts)


def _chapter_start(chapter: ChapterOutline | None) -> float | None:
    if chapter is None or not chapter.concepts:
        return None
    return min(concept.transcript_span.start_seconds for concept in chapter.concepts)
