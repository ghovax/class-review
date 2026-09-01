from teacher import (
    Chapter,
    ChapterOutline,
    Concept,
    ConceptIntent,
    ExplanationDepth,
    GlossaryEntry,
    Lesson,
    LessonOutline,
    ProgressionAxis,
    TimeSpan,
)


def test_lesson_is_built_from_outline_and_chapters() -> None:
    concept = Concept(
        concept_index=0,
        global_index=0,
        topic_title="Limits",
        learning_objective="Understand limits",
        must_advance_by=ProgressionAxis.MECHANISM,
        intent=ConceptIntent.INTRODUCE,
        explanation_depth=ExplanationDepth.MEDIUM,
        rationale="A foundation",
        transcript_span=TimeSpan(0, 1),
        establishes="The limit is approached",
    )
    outline = LessonOutline("Calculus", "Basics", (ChapterOutline("Limits", (concept,)),))
    chapter = Chapter("Limits", "A limit is a value approached by a function.", (concept,))

    lesson = Lesson.from_parts(
        outline=outline,
        chapters=(chapter,),
        glossary=(GlossaryEntry("limit-key", "limit", "A value approached by a function."),),
    )

    assert lesson.title == "Calculus"
    assert lesson.chapters[0].glossary_links[0].key == "limit-key"
