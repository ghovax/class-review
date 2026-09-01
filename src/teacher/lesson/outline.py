"""Draft lesson outlines from transcript and reference material."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from teacher.interfaces import ChatModel
from teacher.models import (
    ChapterOutline,
    Concept,
    ConceptDocumentSpan,
    LessonMaterials,
    LessonOutline,
    ProgressionAxis,
    ConceptIntent,
    ExplanationDepth,
    ReferenceMaterial,
    TimeSpan,
    Transcript,
)
from teacher.prompts import Prompts, get_prompts
from teacher.support import call_chat_model
from teacher.xml import OneOrMany, RequiredText, build_xml_document, parse_xml_with_schema


class OutlineWriter:
    """Writes a proposed lesson outline from assembled materials."""

    def __init__(
        self,
        text_model: ChatModel,
        *,
        prompts: Prompts | None = None,
    ) -> None:
        self.text_model = text_model
        self.prompts = get_prompts(prompts)

    async def draft(self, materials: LessonMaterials) -> LessonOutline:
        """Draft a lesson outline from the corrected transcript and references."""
        prompts = self.prompts
        start = min(item.start_seconds for item in materials.transcript.segments)
        end = max(item.end_seconds for item in materials.transcript.segments)
        answer = await call_chat_model(
            self.text_model,
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
