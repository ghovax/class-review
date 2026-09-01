"""Independent operations for preparing and writing lesson material."""

from __future__ import annotations

import asyncio
import base64
import re
import secrets
from collections.abc import Sequence
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from lxml import etree
from pydantic import BaseModel, Field

from teacher.configuration import ModelsConfiguration, OperationConfiguration
from teacher.lesson.context import build_chapter_context
from teacher.models import (
    Chapter,
    ChapterOutline,
    Citation,
    Concept,
    ConceptDocumentSpan,
    ConceptIntent,
    ExplanationDepth,
    GlossaryEntry,
    LessonMaterials,
    LessonOutline,
    ProgressionAxis,
    Reference,
    ReferenceDocument,
    ReferenceMaterial,
    ReferenceNote,
    ReferencePage,
    ReferenceSection,
    ReferenceSections,
    TimeSpan,
    Transcript,
    TranscriptSegment,
)
from teacher.support import OperationError, call_chat_model
from teacher.xml import OneOrMany, RequiredText, build_xml_document, parse_xml_with_schema


def _configuration(value: ModelsConfiguration | OperationConfiguration) -> OperationConfiguration:
    return (
        value if isinstance(value, OperationConfiguration) else OperationConfiguration(models=value)
    )


class TranscriptRevision:
    """Revises transcript text while keeping its timestamps and languages."""

    def __init__(self, configuration: ModelsConfiguration | OperationConfiguration) -> None:
        self.configuration = _configuration(configuration)

    async def revise(self, transcript: Transcript, *, language: str) -> Transcript:
        terminology = await self._find_terminology(transcript, language)
        pieces = _split_transcript(
            transcript.segments,
            self.configuration.transcript.maximum_request_seconds,
        )
        revised: list[TranscriptSegment] = []
        for piece in pieces:
            revised.extend(await self._revise_piece(piece, terminology, language))
        return _assemble_transcript(revised, transcript.languages)

    async def _find_terminology(
        self, transcript: Transcript, language: str
    ) -> tuple[tuple[str, tuple[str, ...], str], ...]:
        prompts = self.configuration.prompts
        try:
            answer = await call_chat_model(
                self.configuration.models.text,
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
        prompts = self.configuration.prompts
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
            self.configuration.models.text,
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


class ReferenceReader:
    """Reads PDF references into material that other operations can use."""

    def __init__(self, configuration: ModelsConfiguration | OperationConfiguration) -> None:
        self.configuration = _configuration(configuration)

    async def read(self, documents: tuple[ReferenceDocument, ...]) -> ReferenceMaterial:
        references = tuple(
            await asyncio.gather(
                *(self._read_document(document, index) for index, document in enumerate(documents))
            )
        )
        sections = await self._map_sections(references)
        notes = await self._explain_sections(references, sections)
        return ReferenceMaterial(references, sections, notes)

    async def _read_document(self, document: ReferenceDocument, index: int) -> Reference:
        pages = await asyncio.to_thread(_render_pdf, document)
        if not pages:
            raise ValueError(f"reference {document.file_name or index} has no pages")
        model = self.configuration.models.vision or self.configuration.models.text

        async def read_page(page: tuple[int, bytes]) -> ReferencePage:
            number, image = page
            prompts = self.configuration.prompts
            answer = await call_chat_model(
                model,
                [
                    SystemMessage(
                        prompts.render(
                            "documents/extract_document_page/system",
                            {
                                "language_policy": prompts.render("shared_prompts/language_policy"),
                                "mathematics_notation_rules": prompts.render(
                                    "shared_prompts/mathematics_notation_rules"
                                ),
                            },
                        )
                    ),
                    HumanMessage(
                        content=[
                            {
                                "type": "text",
                                "text": prompts.render(
                                    "documents/extract_document_page/user",
                                    {
                                        "document": {
                                            "file_name": document.file_name
                                            or f"document-{index + 1}.pdf",
                                            "index": index,
                                            "page_number": number,
                                        }
                                    },
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64.b64encode(image).decode('ascii')}"
                                },
                            },
                        ]
                    ),
                ],
            )
            summary, details = _read_page_sections(answer.text)
            return ReferencePage(number, summary, details)

        read_pages = await asyncio.gather(*(read_page(page) for page in pages))
        return Reference(
            index, document.file_name or f"document-{index + 1}.pdf", tuple(read_pages)
        )

    async def _map_sections(
        self, references: tuple[Reference, ...]
    ) -> tuple[ReferenceSections, ...]:
        if not references:
            return ()
        prompts = self.configuration.prompts
        page_list = "\n".join(
            f"Document {item.document_index}, page {page.page_number}: {page.summary or ''}"
            for item in references
            for page in item.pages
        )
        answer = await call_chat_model(
            self.configuration.models.text,
            [
                SystemMessage(
                    prompts.render(
                        "documents/map_document_sections/system",
                        {
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
                        "documents/map_document_sections/user", {"page_list_markdown": page_list}
                    )
                ),
            ],
        )
        parsed = parse_xml_with_schema(
            content=answer.text, root_tag="DocumentSections", schema=_SectionsSchema
        )
        by_index = {item.document_index: item for item in references}
        result = []
        for document in parsed.documents:
            reference = by_index.get(document.document_index)
            if reference is None:
                continue
            last_page = max((page.page_number for page in reference.pages), default=1)
            result.append(
                ReferenceSections(
                    reference.document_index,
                    reference.file_name,
                    tuple(
                        ReferenceSection(
                            position,
                            max(1, min(item.start_page, last_page)),
                            max(1, min(max(item.end_page, item.start_page), last_page)),
                            item.title,
                            item.description,
                        )
                        for position, item in enumerate(
                            sorted(document.sections, key=lambda item: item.section_index)
                        )
                    ),
                )
            )
        return tuple(sorted(result, key=lambda item: item.document_index))

    async def _explain_sections(
        self, references: tuple[Reference, ...], sections: tuple[ReferenceSections, ...]
    ) -> tuple[ReferenceNote, ...]:
        by_index = {item.document_index: item for item in references}
        prompts = self.configuration.prompts

        async def explain(item: ReferenceSections, section: ReferenceSection) -> ReferenceNote:
            reference = by_index[item.document_index]
            pages = "\n\n".join(
                f"Page {page.page_number}\n{page.details or ''}"
                for page in reference.pages
                if section.start_page <= page.page_number <= section.end_page
            )
            answer = await call_chat_model(
                self.configuration.models.text,
                [
                    SystemMessage(
                        prompts.render(
                            "documents/explain_document_sections/system",
                            {
                                "language_policy": prompts.render("shared_prompts/language_policy"),
                                "mathematics_notation_rules": prompts.render(
                                    "shared_prompts/mathematics_notation_rules"
                                ),
                            },
                        )
                    ),
                    HumanMessage(
                        prompts.render(
                            "documents/explain_document_sections/user",
                            {
                                "section": {
                                    "document_index": item.document_index,
                                    "document_file_name": item.file_name,
                                    "section_index": section.section_index,
                                    "section_title": section.title,
                                    "section_description": section.description,
                                    "start_page": section.start_page,
                                    "end_page": section.end_page,
                                    "pages_markdown": pages,
                                }
                            },
                        )
                    ),
                ],
            )
            return ReferenceNote(item.document_index, section.section_index, answer.text.strip())

        return tuple(
            await asyncio.gather(
                *(explain(item, section) for item in sections for section in item.sections)
            )
        )


class OutlineWriter:
    """Writes a proposed lesson outline from assembled materials."""

    def __init__(self, configuration: ModelsConfiguration | OperationConfiguration) -> None:
        self.configuration = _configuration(configuration)

    async def draft(self, materials: LessonMaterials) -> LessonOutline:
        prompts = self.configuration.prompts
        start = min(item.start_seconds for item in materials.transcript.segments)
        end = max(item.end_seconds for item in materials.transcript.segments)
        answer = await call_chat_model(
            self.configuration.models.text,
            [
                SystemMessage(
                    prompts.render(
                        "lesson/plan_lesson_outline/system",
                        {
                            "language": materials.language,
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
                        "lesson/plan_lesson_outline/user",
                        {
                            "language": materials.language,
                            "metadata": {
                                "document_count": len(materials.references.documents),
                                "lesson_start_seconds": round(start, 1),
                                "lesson_end_seconds": round(end, 1),
                                "lesson_duration_seconds": round(end - start, 1),
                            },
                            "transcript_segments_xml": _render_transcript(materials.transcript),
                            "document_section_map_xml": _render_reference_sections(
                                materials.references
                            ),
                            "section_explanations_xml": _render_reference_notes(
                                materials.references
                            ),
                        },
                    )
                ),
            ],
        )
        parsed = parse_xml_with_schema(
            content=answer.text, root_tag="LessonOutline", schema=_OutlineSchema
        )
        return _make_outline(parsed, start, end)


class ChapterWriter:
    """Writes one chapter from a chapter outline and the lesson materials."""

    def __init__(self, configuration: ModelsConfiguration | OperationConfiguration) -> None:
        self.configuration = _configuration(configuration)

    async def write(self, outline: ChapterOutline, materials: LessonMaterials) -> Chapter:
        prompts = self.configuration.prompts
        context = build_chapter_context(
            chapter=outline,
            segments=materials.transcript.segments,
            lesson_configuration=self.configuration.lesson,
            transcript_configuration=self.configuration.transcript,
        )
        variables = {
            "language": materials.language,
            "mathematics_notation_rules": prompts.render(
                "shared_prompts/mathematics_notation_rules"
            ),
            "chapter": {
                "index": 0,
                "total": 1,
                "start_seconds": round(context.start_seconds, 1),
                "end_seconds": round(context.end_seconds, 1),
                "concept_count": len(outline.concepts),
                "previous_chapter_count": 0,
                "previous_concept_count": 0,
                "chapter_context_xml": _chapter_xml(outline),
                "covered_concepts_xml": build_xml_document("CoveredConcepts", {}),
                "do_not_repeat_ledger_xml": build_xml_document("ProhibitionLedger", {}),
                "document_pages_markdown": _chapter_references(outline, materials.references),
            },
            "transcript": {
                "excerpt_count": sum(len(item.excerpts) for item in context.concept_slices),
                "excerpts_xml": _context_xml(context),
            },
        }
        answer = await call_chat_model(
            self.configuration.models.text,
            [
                SystemMessage(
                    prompts.render(
                        "lesson/write_lesson_chapter/system",
                        {
                            "language": materials.language,
                            "language_policy": prompts.render("shared_prompts/language_policy"),
                            "xml_policy": prompts.render("shared_prompts/xml_policy"),
                            "mathematics_notation_rules": prompts.render(
                                "shared_prompts/mathematics_notation_rules"
                            ),
                        },
                    )
                ),
                HumanMessage(prompts.render("lesson/write_lesson_chapter/user", variables)),
            ],
        )
        title, content, citations = _read_chapter(answer.text)
        return Chapter(title or outline.title, content, outline.concepts, tuple(citations))


class GlossaryWriter:
    """Writes glossary entries from completed chapters."""

    def __init__(self, configuration: ModelsConfiguration | OperationConfiguration) -> None:
        self.configuration = _configuration(configuration)

    async def write(
        self, outline: LessonOutline, chapters: tuple[Chapter, ...], *, language: str
    ) -> tuple[GlossaryEntry, ...]:
        if not chapters:
            return ()
        prompts = self.configuration.prompts
        content = "\n\n".join(f"# {chapter.title}\n{chapter.content}" for chapter in chapters)
        answer = await call_chat_model(
            self.configuration.models.text,
            [
                SystemMessage(
                    prompts.render(
                        "lesson/build_lesson_glossary/system",
                        {
                            "language": language,
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
                        "lesson/build_lesson_glossary/user",
                        {
                            "language": language,
                            "lesson_title": outline.title,
                            "lesson_markdown": content,
                        },
                    )
                ),
            ],
        )
        parsed = parse_xml_with_schema(
            content=answer.text, root_tag="Glossary", schema=_GlossarySchema
        )
        entries: list[GlossaryEntry] = []
        seen: set[str] = set()
        for term in parsed.terms:
            key = term.short_form.casefold()
            if key in seen:
                continue
            seen.add(key)
            entries.append(
                GlossaryEntry(
                    _new_key(self.configuration.lesson.glossary_key_length),
                    term.short_form,
                    term.description,
                    term.long_form or None,
                )
            )
        return tuple(entries)


def _split_transcript(
    segments: Sequence[TranscriptSegment], maximum: float
) -> list[list[TranscriptSegment]]:
    pieces: list[list[TranscriptSegment]] = []
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


def _render_transcript(transcript: Transcript) -> str:
    return build_xml_document(
        "TranscriptSegments",
        {
            "Segment": [
                {"Beginning": item.start_seconds, "End": item.end_seconds, "Sentence": item.content}
                for item in transcript.segments
            ]
        },
    )


def _render_reference_sections(material: ReferenceMaterial) -> str:
    return build_xml_document(
        "DocumentSections",
        {
            "Document": [
                {
                    "DocumentIndex": item.document_index,
                    "FileName": item.file_name,
                    "Section": [
                        {
                            "SectionIndex": section.section_index,
                            "StartPage": section.start_page,
                            "EndPage": section.end_page,
                            "SectionTitle": section.title,
                            "Description": section.description,
                        }
                        for section in item.sections
                    ],
                }
                for item in material.sections
            ]
        },
    )


def _render_reference_notes(material: ReferenceMaterial) -> str:
    return build_xml_document(
        "SectionExplanations",
        {
            "Section": [
                {
                    "DocumentIndex": item.document_index,
                    "SectionIndex": item.section_index,
                    "Explanation": item.content,
                }
                for item in material.notes
            ]
        },
    )


def _make_outline(parsed: _OutlineSchema, start: float, end: float) -> LessonOutline:
    chapters: list[ChapterOutline] = []
    global_index = 0
    for chapter in parsed.chapters:
        concepts = []
        for index, item in enumerate(chapter.concepts):
            first, second = sorted((item.duration.start_seconds, item.duration.end_seconds))
            span = TimeSpan(min(max(first, start), end), min(max(second, start), end))
            concepts.append(
                Concept(
                    index,
                    global_index,
                    item.topic_title,
                    item.learning_objective,
                    item.must_advance_by,
                    item.intent,
                    item.explanation_depth,
                    item.rationale,
                    span,
                    item.establishes,
                    tuple(
                        ConceptDocumentSpan(span.document_index, tuple(span.section_indices))
                        for span in item.document_spans
                    ),
                )
            )
            global_index += 1
        chapters.append(ChapterOutline(chapter.title, tuple(concepts)))
    return LessonOutline(parsed.title, parsed.description, tuple(chapters))


def _chapter_xml(outline: ChapterOutline) -> str:
    return build_xml_document(
        "ChapterContext",
        {
            "Title": outline.title,
            "Concept": [
                {
                    "ConceptIndex": item.concept_index,
                    "GlobalIndex": item.global_index,
                    "TopicTitle": item.topic_title,
                    "LearningObjective": item.learning_objective,
                    "MustAdvanceBy": item.must_advance_by.value,
                    "Intent": item.intent.value,
                    "ExplanationDepth": item.explanation_depth.value,
                    "Rationale": item.rationale,
                    "Start": item.transcript_span.start_seconds,
                    "End": item.transcript_span.end_seconds,
                }
                for item in outline.concepts
            ],
        },
    )


def _context_xml(context: Any) -> str:
    return build_xml_document(
        "ConceptContexts",
        {
            "ConceptContext": [
                {
                    "ConceptIndex": item.concept_index,
                    "TopicTitle": item.topic_title,
                    "Excerpt": [
                        {
                            "Beginning": excerpt.start_seconds,
                            "End": excerpt.end_seconds,
                            "Content": excerpt.content,
                        }
                        for excerpt in item.excerpts
                    ],
                }
                for item in context.concept_slices
            ]
        },
    )


def _chapter_references(outline: ChapterOutline, material: ReferenceMaterial) -> str:
    wanted = {
        (span.document_index, section)
        for concept in outline.concepts
        for span in concept.document_spans
        for section in span.section_indices
    }
    output = []
    for document in material.documents:
        for section_set in material.sections:
            if section_set.document_index != document.document_index:
                continue
            for section in section_set.sections:
                if (document.document_index, section.section_index) not in wanted:
                    continue
                output.append(f"## {section.title}\n{section.description}")
                output.extend(
                    page.details or ""
                    for page in document.pages
                    if section.start_page <= page.page_number <= section.end_page
                )
    return "\n\n".join(output)


def _read_chapter(content: str) -> tuple[str | None, str, list[Citation]]:
    citations: list[Citation] = []

    def replace(match: re.Match[str]) -> str:
        try:
            element = etree.fromstring(
                match.group(0).encode("utf-8"), parser=etree.XMLParser(recover=True)
            )

            def text(name: str) -> str:
                child = element.find(name)
                return "" if child is None else "".join(child.itertext()).strip()

            citation = Citation(
                len(citations) + 1, text("Content"), int(text("DocumentIndex")), int(text("Page"))
            )
        except (ValueError, TypeError, etree.XMLSyntaxError):
            return match.group(0)
        citations.append(citation)
        return f" [^{citation.number}] "

    body = re.sub(
        r"<Citation>.*?</Citation>", replace, content.strip(), flags=re.DOTALL | re.IGNORECASE
    )
    match = re.match(r"^#{1}\s+(.+?)\s*$", body, re.MULTILINE)
    title = match.group(1).strip() if match else None
    if match:
        body = body[match.end() :].strip()
    return title, body, citations


def _new_key(length: int) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "gls-" + "".join(secrets.choice(alphabet) for _ in range(length))


def _render_pdf(document: ReferenceDocument) -> list[tuple[int, bytes]]:
    import pymupdf

    with pymupdf.open(stream=document.content, filetype="pdf") as pdf:
        return [
            (
                number,
                pdf.load_page(number - 1)
                .get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
                .tobytes("png"),
            )
            for number in range(1, len(pdf) + 1)
        ]


def _read_page_sections(content: str) -> tuple[str, str]:
    body = content.strip()
    headings = list(re.finditer(r"^(#{1,6})[ \t]+.+?[ \t]*$", body, re.MULTILINE))
    if len(headings) < 2:
        raise OperationError.retryable("reference page needs summary and details headings")
    depth = min(len(item.group(1)) for item in headings)
    positions = [item for item in headings if len(item.group(1)) == depth]
    if len(positions) != 2:
        raise OperationError.retryable("reference page needs exactly two sections")
    summary, details = (
        body[positions[0].end() : positions[1].start()].strip(),
        body[positions[1].end() :].strip(),
    )
    if not summary or not details:
        raise OperationError.retryable("reference page has empty material")
    return summary, details


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


class _Duration(BaseModel):
    start_seconds: float = Field(alias="Beginning", ge=0)
    end_seconds: float = Field(alias="End", ge=0)


class _DocumentSpan(BaseModel):
    document_index: int = Field(alias="DocumentIndex", ge=0)
    section_indices: OneOrMany[int] = Field(alias="SectionIndex", default_factory=list)


class _Concept(BaseModel):
    topic_title: RequiredText = Field(alias="TopicTitle")
    learning_objective: RequiredText = Field(alias="LearningObjective")
    must_advance_by: ProgressionAxis = Field(alias="MustAdvanceBy")
    intent: ConceptIntent = Field(alias="Intent")
    explanation_depth: ExplanationDepth = Field(alias="ExplanationDepth")
    rationale: RequiredText = Field(alias="Rationale")
    duration: _Duration = Field(alias="Duration")
    establishes: RequiredText = Field(alias="DoNotRepeat")
    document_spans: OneOrMany[_DocumentSpan] = Field(alias="DocumentSpan", default_factory=list)


class _OutlineChapter(BaseModel):
    title: RequiredText = Field(alias="Title")
    concepts: OneOrMany[_Concept] = Field(alias="Concept")


class _OutlineSchema(BaseModel):
    title: RequiredText = Field(alias="Title")
    description: RequiredText = Field(alias="Description")
    chapters: OneOrMany[_OutlineChapter] = Field(alias="Chapter")


class _GlossaryTerm(BaseModel):
    short_form: RequiredText = Field(alias="Short")
    description: RequiredText = Field(alias="Description")
    long_form: str | None = Field(alias="Long", default=None)


class _GlossarySchema(BaseModel):
    terms: OneOrMany[_GlossaryTerm] = Field(alias="Term", default_factory=list)


class _Section(BaseModel):
    section_index: int = Field(alias="SectionIndex", ge=0)
    start_page: int = Field(alias="StartPage", ge=1)
    end_page: int = Field(alias="EndPage", ge=1)
    title: RequiredText = Field(alias="SectionTitle")
    description: RequiredText = Field(alias="Description")


class _DocumentSections(BaseModel):
    document_index: int = Field(alias="DocumentIndex", ge=0)
    sections: OneOrMany[_Section] = Field(alias="Section", default_factory=list)


class _SectionsSchema(BaseModel):
    documents: OneOrMany[_DocumentSections] = Field(alias="Document", default_factory=list)
