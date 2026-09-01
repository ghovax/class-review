"""Revise timestamped transcripts with the packaged prompts."""

from __future__ import annotations

from collections.abc import Sequence

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from teacher.interfaces import ChatModel
from teacher.models import Transcript, TranscriptSegment
from teacher.prompts import Prompts, get_prompts
from teacher.support import OperationError, call_chat_model
from teacher.xml import OneOrMany, RequiredText, build_xml_document, parse_xml_with_schema


_MAX_TRANSCRIPT_REQUEST_SECONDS = 1800.0


class TranscriptRevision:
    """Revises transcript text while keeping its timestamps and languages."""

    def __init__(
        self,
        text_model: ChatModel,
        *,
        prompts: Prompts | None = None,
    ) -> None:
        self.text_model = text_model
        self.prompts = get_prompts(prompts)

    async def revise(self, transcript: Transcript, *, language: str) -> Transcript:
        """Revise transcript prose in bounded chunks while preserving timestamps."""
        terminology = await self._find_terminology(transcript, language)
        pieces = _split_transcript(transcript.segments)
        revised: list[TranscriptSegment] = []
        for piece in pieces:
            revised.extend(await self._revise_piece(piece, terminology, language))
        return _assemble_transcript(revised, transcript.languages)

    async def _find_terminology(
        self, transcript: Transcript, language: str
    ) -> tuple[tuple[str, tuple[str, ...], str], ...]:
        prompts = self.prompts
        try:
            answer = await call_chat_model(
                self.text_model,
                [
                    SystemMessage(
                        prompts.render(
                            "transcript/extract_transcript_terminology/system",
                            {
                                "language": language,
                                "language_policy": prompts.render("shared_prompts/language_policy"),
                                "xml_policy": prompts.render("shared_prompts/xml_policy"),
                            },
                        )
                    ),
                    HumanMessage(
                        prompts.render(
                            "transcript/extract_transcript_terminology/user",
                            {
                                "language": language,
                                "transcript": "\n".join(
                                    f"[{item.start_seconds:.2f}] {item.content}"
                                    for item in transcript.segments
                                ),
                            },
                        )
                    ),
                ],
            )
            parsed = parse_xml_with_schema(
                content=answer.text, root_tag="Terminology", schema=_TerminologySchema
            )
        except (OperationError, ValueError):
            return ()
        return tuple(
            (term.canonical, tuple(term.heard.variants), term.kind) for term in parsed.terms
        )

    async def _revise_piece(
        self,
        segments: Sequence[TranscriptSegment],
        terminology: tuple[tuple[str, tuple[str, ...], str], ...],
        language: str,
    ) -> list[TranscriptSegment]:
        prompts = self.prompts
        source = build_xml_document(
            "Transcript",
            {
                "Segment": [
                    {"Timestamp": item.start_seconds, "Content": item.content} for item in segments
                ]
            },
        )
        terms = build_xml_document(
            "Terminology",
            {
                "Term": [
                    {"Canonical": canonical, "Heard": {"Variant": list(variants)}, "Kind": kind}
                    for canonical, variants, kind in terminology
                ]
            },
        )
        answer = await call_chat_model(
            self.text_model,
            [
                SystemMessage(
                    prompts.render(
                        "transcript/correct_transcript/system",
                        {
                            "language": language,
                            "language_policy": prompts.render("shared_prompts/language_policy"),
                            "xml_policy": prompts.render("shared_prompts/xml_policy"),
                        },
                    )
                ),
                HumanMessage(
                    prompts.render(
                        "transcript/correct_transcript/user",
                        {
                            "language": language,
                            "start_seconds": segments[0].start_seconds,
                            "end_seconds": segments[-1].end_seconds,
                            "terminology_xml": terms,
                            "transcript_xml": source,
                        },
                    )
                ),
            ],
        )
        parsed = parse_xml_with_schema(
            content=answer.text,
            root_tag="CorrectedTranscript",
            schema=_CorrectedTranscriptSchema,
        )
        timestamps = sorted(
            (
                min(max(unit.timestamp, segments[0].start_seconds), segments[-1].end_seconds),
                unit.content,
            )
            for unit in parsed.segments
        )
        return [
            TranscriptSegment(
                timestamp,
                timestamps[index + 1][0]
                if index + 1 < len(timestamps)
                else segments[-1].end_seconds,
                content,
            )
            for index, (timestamp, content) in enumerate(timestamps)
        ]


def _split_transcript(segments: Sequence[TranscriptSegment]) -> list[list[TranscriptSegment]]:
    pieces: list[list[TranscriptSegment]] = []
    maximum = _MAX_TRANSCRIPT_REQUEST_SECONDS
    maximum = 1800.0
    for segment in segments:
        if not pieces or segment.end_seconds - pieces[-1][0].start_seconds > maximum:
            pieces.append([segment])
        else:
            pieces[-1].append(segment)
    return pieces


def _assemble_transcript(
    segments: Sequence[TranscriptSegment], languages: Sequence[str]
) -> Transcript:
    unique = {(item.start_seconds, item.end_seconds, item.content): item for item in segments}
    ordered = sorted(unique.values(), key=lambda item: (item.start_seconds, item.end_seconds))
    return Transcript(
        tuple(
            TranscriptSegment(
                item.start_seconds,
                max(
                    item.start_seconds,
                    ordered[index + 1].start_seconds
                    if index + 1 < len(ordered)
                    else item.end_seconds,
                ),
                item.content,
            )
            for index, item in enumerate(ordered)
        ),
        tuple(languages),
    )


class _Heard(BaseModel):
    variants: OneOrMany[RequiredText] = Field(alias="Variant")


class _Term(BaseModel):
    canonical: RequiredText = Field(alias="Canonical")
    heard: _Heard = Field(alias="Heard")
    kind: RequiredText = Field(alias="Kind")


class _TerminologySchema(BaseModel):
    terms: OneOrMany[_Term] = Field(alias="Term", default_factory=list)


class _CorrectedUnit(BaseModel):
    timestamp: float = Field(alias="Timestamp", ge=0)
    content: RequiredText = Field(alias="Content")


class _CorrectedTranscriptSchema(BaseModel):
    segments: OneOrMany[_CorrectedUnit] = Field(alias="Segment")
