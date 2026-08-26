"""Consolidated Teacher implementation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime
from lxml import etree
from pydantic import BaseModel, Field
from teacher.configuration import GraphRuntime, LessonPolicy, TranscriptPolicy
from teacher.models import (
    Concept,
    PlannedChapter,
    TranscriptSegment,
    Citation,
    PipelineStage,
    PlanCreated,
    StageChanged,
    ConceptDocumentSpan,
    ConceptIntent,
    ExplanationDepth,
    LessonPlan,
    ProgressionAxis,
    TimeSpan,
    ChapterCompleted,
    ChapterStarted,
    Document,
    SectionMap,
    GlossaryDistilled,
    GlossaryEntry,
    LessonAssembled,
    Chapter,
    Lesson,
)
from teacher.markdown import compose_markdown
from teacher.prompts import Prompts
from teacher.state import ChapterAnswer, ChapterDraft, LessonState
from teacher.documents import render_section_pages
from teacher.support import PipelineError, get_logger, call_chat_model, compute_glossary_links
from teacher.xml import (
    OneOrMany,
    RequiredText,
    build_xml_document,
    case_insensitive_with_fallback,
    parse_xml_with_schema,
)
from typing import Final, Annotated
import re
import secrets

"""Lesson graph nodes: planning, chapter writing, glossary, and final assembly."""

"""Deciding which stretch of transcript each chapter and concept may draw from."""


# Sentence-ending punctuation across the scripts a lecture may be written in.
_SENTENCE_TERMINATORS: Final[str] = ".!?…؟။።॥।۔。！？"

# Terminators that are normally written with no space after them.
_UNSPACED_TERMINATOR_PATTERN: Final[re.Pattern[str]] = re.compile(r"([。！？])(?=\S)", re.UNICODE)

# Tokens that routinely end in a full stop without ending a sentence.
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


"""Extracting the small structured envelope around a generated chapter."""


_CITATION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"[ \t]*`?<Citation>.*?</Citation>`?[ \t]*", re.DOTALL
)
_HEADING_PATTERN: Final[re.Pattern[str]] = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class ChapterOutput:
    """The chapter prose and citations returned by one model call."""

    title: str | None
    content: str
    section_count: int
    citations: tuple[Citation, ...]


def read_chapter_output(
    *, raw_content: str, chapter_index: int, starting_citation_index: int
) -> ChapterOutput:
    """Remove citation envelopes and the optional outer chapter title line.

    The chapter body remains the model's original text.  Teacher deliberately does
    not build or round-trip a Markdown syntax tree; Markdown is an output format,
    not an internal data model.
    """
    del chapter_index
    content = raw_content.strip()
    if not content:
        raise PipelineError.retryable("chapter output is empty")

    citations: list[Citation] = []

    def replace(match: re.Match[str]) -> str:
        citation = _read_citation(
            match.group(0).strip(), starting_citation_index + len(citations) + 1
        )
        if citation is None:
            return match.group(0)
        citations.append(citation)
        return f" [^{citation.number}] "

    content = _CITATION_PATTERN.sub(replace, content)
    headings = list(_HEADING_PATTERN.finditer(content))
    title: str | None = None
    if headings and headings[0].start() == 0 and len(headings[0].group(1)) == 1:
        title = headings[0].group(2).strip() or None
        content = content[headings[0].end() :].lstrip()

    section_count = sum(
        1 for match in _HEADING_PATTERN.finditer(content) if len(match.group(1)) == 2
    )
    return ChapterOutput(
        title=title,
        content=content.strip(),
        section_count=section_count,
        citations=tuple(citations),
    )


def _read_citation(element_text: str, number: int) -> Citation | None:
    """Read one XML citation envelope without interpreting the surrounding prose."""
    try:
        element = etree.fromstring(
            element_text.strip().strip("`").encode("utf-8"),
            parser=etree.XMLParser(recover=True, resolve_entities=False),
        )
    except etree.XMLSyntaxError:
        return None
    if element is None:
        return None
    content = _child_text(element, "Content")
    document_index = _child_integer(element, "DocumentIndex")
    page_number = _child_integer(element, "Page")
    if not content or document_index is None or page_number is None:
        return None
    return Citation(
        number=number,
        content=content,
        document_index=document_index,
        page_number=page_number,
    )


def _child_text(element: etree._Element, name: str) -> str:
    child = element.find(name)
    return "" if child is None else "".join(str(text) for text in child.itertext()).strip()


def _child_integer(element: etree._Element, name: str) -> int | None:
    try:
        return int(_child_text(element, name))
    except ValueError:
        return None


"""Drafting the plan every chapter is then written against."""


logger = get_logger(__name__)

_PLAN_SYSTEM_TEMPLATE = "lesson/plan_lesson_outline/system"
_PLAN_USER_TEMPLATE = "lesson/plan_lesson_outline/user"
_PLAN_ROOT_TAG = "LessonOutline"


class _DocumentSpanSchema(BaseModel):
    """The document sections one concept draws on."""

    document_index: int = Field(alias="DocumentIndex", ge=0)
    section_indices: OneOrMany[int] = Field(alias="SectionIndex", default_factory=list)


class _DurationSchema(BaseModel):
    """The transcript context selected for one concept."""

    start_seconds: float = Field(alias="Beginning", ge=0)
    end_seconds: float = Field(alias="End", ge=0)


class _ConceptSchema(BaseModel):
    """One concept the plan declared."""

    topic_title: RequiredText = Field(alias="TopicTitle")
    learning_objective: RequiredText = Field(alias="LearningObjective")
    must_advance_by: Annotated[
        ProgressionAxis,
        case_insensitive_with_fallback(ProgressionAxis, ProgressionAxis.MECHANISM),
    ] = Field(alias="MustAdvanceBy")
    intent: Annotated[
        ConceptIntent,
        case_insensitive_with_fallback(ConceptIntent, ConceptIntent.INTRODUCE),
    ] = Field(alias="Intent")
    explanation_depth: Annotated[
        ExplanationDepth,
        case_insensitive_with_fallback(ExplanationDepth, ExplanationDepth.MEDIUM),
    ] = Field(alias="ExplanationDepth")
    rationale: RequiredText = Field(alias="Rationale")
    duration: _DurationSchema = Field(alias="Duration")
    establishes: RequiredText = Field(alias="DoNotRepeat")
    document_spans: OneOrMany[_DocumentSpanSchema] = Field(
        alias="DocumentSpan", default_factory=list
    )


class _ChapterSchema(BaseModel):
    """One chapter the plan declared."""

    title: RequiredText = Field(alias="Title")
    concepts: OneOrMany[_ConceptSchema] = Field(alias="Concept")


class _OutlineSchema(BaseModel):
    """The element a plan call is expected to answer with."""

    title: RequiredText = Field(alias="Title")
    description: RequiredText = Field(alias="Description")
    chapters: OneOrMany[_ChapterSchema] = Field(alias="Chapter")


async def plan_lesson_outline(
    state: LessonState, runtime: Runtime[GraphRuntime]
) -> dict[str, object]:
    """Drafts the plan the chapters will be written against."""
    segments = state.get("clean_transcript", [])
    if not segments:
        raise PipelineError.terminal(
            "there is no transcript to plan a lesson from", {"segment_count": 0}
        )

    stream_writer = get_stream_writer()
    stream_writer(StageChanged(stage=PipelineStage.PLANNING_LESSON))

    prompts = runtime.context.inputs.prompts
    start_seconds = min(segment.start_seconds for segment in segments)
    end_seconds = max(segment.end_seconds for segment in segments)
    duration_seconds = max(0.0, end_seconds - start_seconds)
    documents = state.get("documents", [])

    logger.info(
        "plan drafting started",
        segment_count=len(segments),
        document_count=len(documents),
        duration_seconds=duration_seconds,
    )

    system_prompt = prompts.render(
        _PLAN_SYSTEM_TEMPLATE,
        {
            "language": state["output_language"],
            "language_policy": prompts.render("shared_prompts/language_policy"),
            "xml_policy": prompts.render("shared_prompts/xml_policy"),
            "mathematics_notation_rules": prompts.render(
                "shared_prompts/mathematics_notation_rules"
            ),
        },
    )
    user_prompt = prompts.render(
        _PLAN_USER_TEMPLATE,
        {
            "language": state["output_language"],
            "metadata": {
                "document_count": len(documents),
                "lesson_start_seconds": round(start_seconds, 1),
                "lesson_end_seconds": round(end_seconds, 1),
                "lesson_duration_seconds": round(duration_seconds, 1),
            },
            "transcript_segments_xml": _render_transcript(state, runtime.context.transcript),
            "document_section_map_xml": _render_section_map(state),
            "section_explanations_xml": _render_notes(state),
        },
    )
    _check_request_size(
        character_count=len(system_prompt) + len(user_prompt),
        segment_count=len(segments),
        duration_seconds=duration_seconds,
        policy=runtime.context.lesson,
    )

    answer = await call_chat_model(
        runtime.context.models.text,
        [SystemMessage(system_prompt), HumanMessage(user_prompt)],
        metadata={"segment_count": len(segments)},
    )

    plan = _read_plan(
        answer.text,
        transcript_start_seconds=start_seconds,
        transcript_end_seconds=end_seconds,
        policy=runtime.context.lesson,
    )
    logger.info(
        "plan drafted",
        lecture_title=plan.title,
        chapter_count=len(plan.chapters),
        concept_count=sum(len(chapter.concepts) for chapter in plan.chapters),
    )
    stream_writer(PlanCreated(plan=plan))

    return {"plan": plan, "usage_by_model": answer.usage_by_model}


def _render_transcript(state: LessonState, policy: TranscriptPolicy) -> str:
    """Renders the transcript with its sentences, for the plan to plan over."""
    clean_transcript = state.get("clean_transcript")
    if clean_transcript is None:
        raise PipelineError.terminal("the corrected transcript is missing")
    return build_xml_document(
        "TranscriptSegments",
        {
            "Segment": [
                {
                    "Beginning": round(segment.start_seconds, policy.timestamp_decimals),
                    "End": round(segment.end_seconds, policy.timestamp_decimals),
                    "Sentence": [
                        {
                            "Beginning": round(
                                sentence.start_seconds,
                                policy.timestamp_decimals,
                            ),
                            "End": round(
                                sentence.end_seconds,
                                policy.timestamp_decimals,
                            ),
                            "Text": sentence.content,
                        }
                        for sentence in split_into_sentences(segment)
                    ],
                }
                for segment in clean_transcript
            ]
        },
    )


def _render_section_map(state: LessonState) -> str:
    """Renders how the documents divide into sections."""
    section_map = state.get("section_map")
    if section_map is None or not section_map.documents:
        return build_xml_document("DocumentSections", {})
    return build_xml_document(
        "DocumentSections",
        {
            "Document": [
                {
                    "DocumentIndex": entry.document_index,
                    "FileName": entry.file_name,
                    "Section": [
                        {
                            "SectionIndex": section.section_index,
                            "StartPage": section.start_page,
                            "EndPage": section.end_page,
                            "SectionTitle": section.title,
                            "Description": section.description,
                        }
                        for section in entry.sections
                    ],
                }
                for entry in section_map.documents
            ]
        },
    )


def _render_notes(state: LessonState) -> str:
    """Renders the section explanations."""
    notes = state.get("section_notes", [])
    if not notes:
        return build_xml_document("SectionExplanations", {})
    return build_xml_document(
        "SectionExplanations",
        {
            "Section": [
                {
                    "DocumentIndex": note.document_index,
                    "SectionIndex": note.section_index,
                    "Explanation": note.content,
                }
                for note in notes
            ]
        },
    )


def _read_plan(
    answer_text: str,
    *,
    transcript_start_seconds: float,
    transcript_end_seconds: float,
    policy: LessonPolicy,
) -> LessonPlan:
    """Read the answer into a plan, held to the transcript that exists."""
    parsed = parse_xml_with_schema(
        content=answer_text, root_tag=_PLAN_ROOT_TAG, schema=_OutlineSchema
    )
    if not parsed.chapters:
        raise PipelineError.retryable("the plan declares no chapters")
    _check_asserted_values(parsed, policy)

    global_index = 0
    chapters_list: list[PlannedChapter] = []
    for chapter in parsed.chapters:
        concepts: list[Concept] = []
        for concept_index, concept in enumerate(chapter.concepts):
            concepts.append(
                Concept(
                    concept_index=concept_index,
                    global_index=global_index,
                    topic_title=concept.topic_title,
                    learning_objective=concept.learning_objective,
                    must_advance_by=concept.must_advance_by,
                    intent=concept.intent,
                    explanation_depth=concept.explanation_depth,
                    rationale=concept.rationale,
                    transcript_span=_clamp_span(
                        concept.duration.start_seconds,
                        concept.duration.end_seconds,
                        transcript_start_seconds,
                        transcript_end_seconds,
                    ),
                    establishes=concept.establishes,
                    document_spans=tuple(
                        ConceptDocumentSpan(
                            document_index=span.document_index,
                            section_indices=tuple(span.section_indices),
                        )
                        for span in concept.document_spans
                    ),
                )
            )
            global_index += 1
        chapters_list.append(PlannedChapter(title=chapter.title, concepts=tuple(concepts)))
    chapters = tuple(chapters_list)

    if not any(chapter.concepts for chapter in chapters):
        raise PipelineError.retryable("the plan declares no concepts")

    return LessonPlan(title=parsed.title, description=parsed.description, chapters=chapters)


def _clamp_span(first: float, second: float, lower: float, upper: float) -> TimeSpan:
    """Brings one concept's span inside the recording that exists."""
    start = min(first, second)
    end = max(first, second)
    clamped_start = min(max(start, lower), upper)
    clamped_end = min(max(end, clamped_start), upper)
    if (start, end) != (clamped_start, clamped_end):
        logger.warning(
            "plan named a stretch outside the recording, bringing it inside",
            named_start_seconds=start,
            named_end_seconds=end,
            clamped_start_seconds=clamped_start,
            clamped_end_seconds=clamped_end,
        )
    return TimeSpan(start_seconds=clamped_start, end_seconds=clamped_end)


def _check_request_size(
    *,
    character_count: int,
    segment_count: int,
    duration_seconds: float,
    policy: LessonPolicy,
) -> None:
    """Refuses a request no provider will accept, naming why it grew."""
    logger.info(
        "plan request assembled",
        request_character_count=character_count,
        segment_count=segment_count,
        duration_seconds=round(duration_seconds, 1),
    )
    if character_count <= policy.maximum_plan_request_characters:
        return
    raise PipelineError.terminal(
        "the transcript is too long to draft a plan from in one request",
        {
            "request_character_count": character_count,
            "maximum_request_characters": policy.maximum_plan_request_characters,
            "segment_count": segment_count,
            "duration_seconds": round(duration_seconds, 1),
            "duration_hours": round(duration_seconds / 3600, 2),
        },
    )


def _check_asserted_values(parsed: _OutlineSchema, policy: LessonPolicy) -> None:
    """Holds every number the answer states to a plausible range."""
    for chapter in parsed.chapters:
        for concept in chapter.concepts:
            for label, value, ceiling in (
                (
                    "start_seconds",
                    concept.duration.start_seconds,
                    policy.maximum_model_seconds,
                ),
                (
                    "end_seconds",
                    concept.duration.end_seconds,
                    policy.maximum_model_seconds,
                ),
            ):
                if value > ceiling:
                    raise PipelineError.retryable(
                        "the plan states a value beyond what could be real",
                        {
                            "field_name": label,
                            "stated_value": value,
                            "maximum_value": ceiling,
                            "chapter_title": chapter.title,
                        },
                    )
            for span in concept.document_spans:
                if span.document_index > policy.maximum_model_index:
                    raise PipelineError.retryable(
                        "the plan states a document beyond what could be real",
                        {
                            "stated_value": span.document_index,
                            "maximum_value": policy.maximum_model_index,
                        },
                    )


"""Writing one chapter, with every chapter written before it in view."""


logger = get_logger(__name__)

_CHAPTER_SYSTEM_TEMPLATE = "lesson/write_lesson_chapter/system"
_CHAPTER_USER_TEMPLATE = "lesson/write_lesson_chapter/user"


async def write_lesson_chapter(
    state: LessonState, runtime: Runtime[GraphRuntime]
) -> dict[str, object]:
    """Writes the next chapter that has not been written yet."""
    plan = state.get("plan")
    if plan is None:
        raise PipelineError.terminal("there is no plan to write chapters from")

    drafts = state.get("chapter_drafts", [])
    chapter_index = len(drafts)
    if chapter_index >= len(plan.chapters):
        raise PipelineError.terminal(
            "the chapter index has run past the plan",
            {"chapter_index": chapter_index, "chapter_count": len(plan.chapters)},
        )

    chapter = plan.chapters[chapter_index]
    stream_writer = get_stream_writer()
    if chapter_index == 0:
        stream_writer(StageChanged(stage=PipelineStage.WRITING_CHAPTERS))
    stream_writer(
        ChapterStarted(
            chapter_index=chapter_index,
            title=chapter.title,
            total_chapters=len(plan.chapters),
        )
    )

    context = build_chapter_context(
        chapters=plan.chapters,
        chapter_index=chapter_index,
        segments=state.get("clean_transcript", []),
        lesson_policy=runtime.context.lesson,
        transcript_policy=runtime.context.transcript,
    )
    if not any(slice_.excerpts for slice_ in context.concept_slices):
        logger.warning(
            "the chapter context holds no transcript",
            chapter_index=chapter_index,
            chapter_title=chapter.title,
            context_start_seconds=context.start_seconds,
            context_end_seconds=context.end_seconds,
        )

    logger.info(
        "chapter writing started",
        chapter_index=chapter_index,
        chapter_title=chapter.title,
        total_chapters=len(plan.chapters),
        concept_count=len(chapter.concepts),
        prior_chapter_count=len(drafts),
        context_start_seconds=context.start_seconds,
        context_end_seconds=context.end_seconds,
    )

    prompts = runtime.context.inputs.prompts
    request = prompts.render(
        _CHAPTER_USER_TEMPLATE,
        {
            "language": state["output_language"],
            "mathematics_notation_rules": prompts.render(
                "shared_prompts/mathematics_notation_rules"
            ),
            "chapter": _build_chapter_variables(
                plan=plan,
                chapter_index=chapter_index,
                context=context,
                documents=state.get("documents", []),
                section_map=state.get("section_map"),
                prompts=prompts,
            ),
            "transcript": {
                "excerpt_count": sum(len(slice_.excerpts) for slice_ in context.concept_slices),
                "excerpts_xml": _render_excerpts(context),
            },
        },
    )

    answer = await call_chat_model(
        runtime.context.models.text,
        [
            SystemMessage(
                prompts.render(
                    _CHAPTER_SYSTEM_TEMPLATE,
                    {
                        "language": state["output_language"],
                        "language_policy": prompts.render("shared_prompts/language_policy"),
                        "xml_policy": prompts.render("shared_prompts/xml_policy"),
                        "mathematics_notation_rules": prompts.render(
                            "shared_prompts/mathematics_notation_rules"
                        ),
                    },
                )
            ),
            *_thread_prior_answers(state.get("chapter_answers", [])),
            HumanMessage(request),
        ],
        metadata={"chapter_index": chapter_index},
    )

    parsed = read_chapter_output(
        raw_content=answer.text,
        chapter_index=chapter_index,
        starting_citation_index=_count_prior_citations(drafts),
    )

    logger.info(
        "chapter writing completed",
        chapter_index=chapter_index,
        chapter_title=parsed.title or chapter.title,
        section_count=parsed.section_count,
        citation_count=len(parsed.citations),
        content_character_count=len(parsed.content),
    )
    stream_writer(
        ChapterCompleted(
            chapter_index=chapter_index,
            title=parsed.title or chapter.title,
            citation_count=len(parsed.citations),
            total_chapters=len(plan.chapters),
        )
    )

    return {
        "chapter_drafts": [
            ChapterDraft(
                chapter_index=chapter_index,
                title=parsed.title,
                content=parsed.content,
                citations=parsed.citations,
            )
        ],
        "chapter_answers": [ChapterAnswer(chapter_index=chapter_index, content=answer.text)],
        "usage_by_model": answer.usage_by_model,
    }


def _thread_prior_answers(
    answers: Sequence[ChapterAnswer],
) -> list[AIMessage]:
    """Threads every earlier chapter's answer forward, and nothing else."""
    return [
        AIMessage(answer.content) for answer in sorted(answers, key=lambda item: item.chapter_index)
    ]


def _count_prior_citations(drafts: Sequence[ChapterDraft]) -> int:
    """Counts the citations earlier chapters already emitted."""
    return sum(len(draft.citations) for draft in drafts)


def _build_chapter_variables(
    *,
    plan: LessonPlan,
    chapter_index: int,
    context: ChapterContext,
    documents: Sequence[Document],
    section_map: SectionMap | None,
    prompts: Prompts,
) -> dict[str, object]:
    """Assembles what the chapter request says about the chapter."""
    chapter = plan.chapters[chapter_index]
    earlier_chapters = plan.chapters[:chapter_index]
    earlier_concepts = [concept for earlier in earlier_chapters for concept in earlier.concepts]

    return {
        "index": chapter_index,
        "total": len(plan.chapters),
        "start_seconds": round(context.start_seconds, 1),
        "end_seconds": round(context.end_seconds, 1),
        "concept_count": len(chapter.concepts),
        "previous_chapter_count": len(earlier_chapters),
        "previous_concept_count": len(earlier_concepts),
        "chapter_context_xml": _render_chapter_context(chapter),
        "covered_concepts_xml": _render_covered_concepts(earlier_concepts),
        "do_not_repeat_ledger_xml": _render_established_ledger(earlier_concepts),
        "document_pages_markdown": _render_document_material(
            chapter=chapter,
            documents=documents,
            section_map=section_map,
            prompts=prompts,
        ),
    }


def _render_chapter_context(chapter: PlannedChapter) -> str:
    """Renders what this chapter is asked to teach."""
    return build_xml_document(
        "ChapterContext",
        {
            "Title": chapter.title,
            "Concept": [
                {
                    "ConceptIndex": concept.concept_index,
                    "GlobalIndex": concept.global_index,
                    "TopicTitle": concept.topic_title,
                    "LearningObjective": concept.learning_objective,
                    "MustAdvanceBy": str(concept.must_advance_by),
                    "Intent": str(concept.intent),
                    "ExplanationDepth": str(concept.explanation_depth),
                    "Rationale": concept.rationale,
                    "Start": round(concept.transcript_span.start_seconds, 1),
                    "End": round(concept.transcript_span.end_seconds, 1),
                    "DocumentSpan": [
                        {
                            "DocumentIndex": span.document_index,
                            "SectionIndex": list(span.section_indices),
                        }
                        for span in concept.document_spans
                    ],
                }
                for concept in chapter.concepts
            ],
        },
    )


def _render_covered_concepts(earlier_concepts: Sequence[Concept]) -> str:
    """Renders what earlier chapters already taught."""
    return build_xml_document(
        "CoveredConcepts",
        {
            "Concept": [
                {
                    "ConceptIndex": concept.concept_index,
                    "GlobalIndex": concept.global_index,
                    "TopicTitle": concept.topic_title,
                    "LearningObjective": concept.learning_objective,
                    "MustAdvanceBy": str(concept.must_advance_by),
                    "Start": round(concept.transcript_span.start_seconds, 1),
                    "End": round(concept.transcript_span.end_seconds, 1),
                }
                for concept in earlier_concepts
            ]
        },
    )


def _render_established_ledger(earlier_concepts: Sequence[Concept]) -> str:
    """Renders everything earlier chapters already established."""
    return build_xml_document(
        "ProhibitionLedger",
        {
            "Established": [
                {
                    "GlobalIndex": concept.global_index,
                    "TopicTitle": concept.topic_title,
                    "Statement": concept.establishes,
                }
                for concept in earlier_concepts
            ]
        },
    )


def _render_document_material(
    *,
    chapter: PlannedChapter,
    documents: Sequence[Document],
    section_map: SectionMap | None,
    prompts: Prompts,
) -> str:
    """Renders the document pages this chapter's concepts point at."""
    if not documents or section_map is None:
        return ""

    documents_by_index = {document.document_index: document for document in documents}
    sections_by_document = {
        entry.document_index: {section.section_index: section for section in entry.sections}
        for entry in section_map.documents
    }

    rendered: list[str] = []
    for concept in chapter.concepts:
        for span in concept.document_spans:
            document = documents_by_index.get(span.document_index)
            sections = sections_by_document.get(span.document_index, {})
            if document is None:
                continue
            for section_index in span.section_indices:
                section = sections.get(section_index)
                if section is None:
                    continue
                entry = render_section_pages(document, section, prompts)
                if entry and entry not in rendered:
                    rendered.append(entry)

    return compose_markdown(rendered)


def _render_excerpts(context: ChapterContext) -> str:
    """Render the transcript this chapter may draw from, arranged by concept."""
    return build_xml_document(
        "ConceptContexts",
        {
            "ConceptContext": [
                {
                    "ConceptIndex": concept_slice.concept_index,
                    "TopicTitle": concept_slice.topic_title,
                    "Excerpt": [
                        {
                            "Beginning": round(excerpt.start_seconds, 1),
                            "End": round(excerpt.end_seconds, 1),
                            "Content": excerpt.content,
                        }
                        for excerpt in concept_slice.excerpts
                    ],
                }
                for concept_slice in context.concept_slices
            ]
        },
    )


"""Distilling the lecture's key terms once every chapter is written."""


logger = get_logger(__name__)

_GLOSSARY_SYSTEM_TEMPLATE = "lesson/build_lesson_glossary/system"
_GLOSSARY_USER_TEMPLATE = "lesson/build_lesson_glossary/user"
_GLOSSARY_ROOT_TAG = "Glossary"

# Keys are built from this alphabet alone, so a key is always safe to write into a
# link destination and to match against in body text.
_KEY_ALPHABET: Final[str] = "abcdefghijklmnopqrstuvwxyz0123456789"
_KEY_PREFIX: Final[str] = "gls-"


class _TermSchema(BaseModel):
    """One term the model distilled."""

    short_form: RequiredText = Field(alias="Short")
    description: RequiredText = Field(alias="Description")
    long_form: str | None = Field(alias="Long", default=None)


class _GlossarySchema(BaseModel):
    """The element a glossary call is expected to answer with."""

    terms: OneOrMany[_TermSchema] = Field(alias="Term", default_factory=list)


async def build_lesson_glossary(
    state: LessonState, runtime: Runtime[GraphRuntime]
) -> dict[str, object]:
    """Distils the lecture's key terms from its completed chapters."""
    plan = state.get("plan")
    drafts = state.get("chapter_drafts", [])
    if plan is None or not drafts:
        logger.info("no chapters to distil a glossary from")
        return {"glossary": []}

    prompts = runtime.context.inputs.prompts
    answer = await call_chat_model(
        runtime.context.models.text,
        [
            SystemMessage(
                prompts.render(
                    _GLOSSARY_SYSTEM_TEMPLATE,
                    {
                        "language": state["output_language"],
                        "language_policy": prompts.render("shared_prompts/language_policy"),
                        "xml_policy": prompts.render("shared_prompts/xml_policy"),
                        "mathematics_notation_rules": prompts.render(
                            "shared_prompts/mathematics_notation_rules"
                        ),
                    },
                )
            ),
            HumanMessage(
                prompts.render(
                    _GLOSSARY_USER_TEMPLATE,
                    {
                        "language": state["output_language"],
                        "lesson_title": plan.title,
                        "lesson_markdown": compose_markdown(
                            prompts.render(
                                "lesson/build_lesson_glossary/chapter",
                                {
                                    "title": (
                                        draft.title
                                        or (
                                            plan.chapters[draft.chapter_index].title
                                            if draft.chapter_index < len(plan.chapters)
                                            else ""
                                        )
                                    ).strip(),
                                    "content": draft.content.strip(),
                                },
                            )
                            for draft in sorted(drafts, key=lambda item: item.chapter_index)
                        ),
                    },
                )
            ),
        ],
        metadata={"chapter_count": len(drafts)},
    )

    glossary = _read_glossary(answer.text, runtime.context.lesson.glossary_key_length)
    logger.info("glossary distilled", term_count=len(glossary))

    stream_writer = get_stream_writer()
    stream_writer(GlossaryDistilled(term_count=len(glossary)))

    return {"glossary": glossary, "usage_by_model": answer.usage_by_model}


def _read_glossary(answer_text: str, key_length: int) -> list[GlossaryEntry]:
    """Reads the answer into glossary entries, minting a key for each."""
    parsed = parse_xml_with_schema(
        content=answer_text, root_tag=_GLOSSARY_ROOT_TAG, schema=_GlossarySchema
    )

    entries: list[GlossaryEntry] = []
    seen_short_forms: set[str] = set()
    for term in parsed.terms:
        short_form = term.short_form.strip()
        comparable = short_form.casefold()
        if not short_form or comparable in seen_short_forms:
            continue
        seen_short_forms.add(comparable)
        long_form = (term.long_form or "").strip()
        entries.append(
            GlossaryEntry(
                key=_mint_key(key_length),
                short_form=short_form,
                description=term.description,
                long_form=long_form or None,
            )
        )
    return entries


def _mint_key(key_length: int) -> str:
    """Mints a key that is safe as a link destination and as a match target."""
    suffix = "".join(secrets.choice(_KEY_ALPHABET) for _ in range(key_length))
    return f"{_KEY_PREFIX}{suffix}"


"""Assembling the lesson, and deciding where its terms are linked."""


logger = get_logger(__name__)


async def assemble_completed_lesson(
    state: LessonState, runtime: Runtime[GraphRuntime]
) -> dict[str, object]:
    """Assembles the lesson from everything written."""
    del runtime
    plan = state.get("plan")
    if plan is None:
        raise PipelineError.terminal("there is no plan to assemble a lesson from")

    stream_writer = get_stream_writer()
    stream_writer(StageChanged(stage=PipelineStage.ASSEMBLING_LESSON))

    drafts_by_index = {draft.chapter_index: draft for draft in state.get("chapter_drafts", [])}
    missing = sorted(index for index in range(len(plan.chapters)) if index not in drafts_by_index)
    if missing:
        raise PipelineError.terminal(
            "the plan calls for chapters that were never written",
            {
                "missing_chapter_indices": missing,
                "chapter_count": len(plan.chapters),
            },
        )

    glossary = tuple(state.get("glossary", []))
    contents = [drafts_by_index[index].content for index in range(len(plan.chapters))]
    links_per_chapter = compute_glossary_links(contents, glossary)

    chapters = tuple(
        Chapter(
            title=(drafts_by_index[index].title or plan_chapter.title).strip(),
            content=drafts_by_index[index].content,
            concepts=plan_chapter.concepts,
            citations=tuple(
                Citation(
                    number=citation.number,
                    content=citation.content,
                    document_index=citation.document_index,
                    page_number=citation.page_number,
                )
                for citation in drafts_by_index[index].citations
            ),
            glossary_links=links_per_chapter[index],
        )
        for index, plan_chapter in enumerate(plan.chapters)
    )

    lesson = Lesson(
        title=plan.title,
        description=plan.description,
        chapters=chapters,
        glossary=glossary,
    )

    logger.info(
        "lesson assembled",
        lesson_title=lesson.title,
        chapter_count=len(lesson.chapters),
        citation_count=sum(len(chapter.citations) for chapter in lesson.chapters),
        glossary_term_count=len(lesson.glossary),
        linked_occurrence_count=sum(len(chapter.glossary_links) for chapter in lesson.chapters),
    )
    stream_writer(LessonAssembled(title=lesson.title, chapters=lesson.chapters))

    return {"lesson": lesson}
