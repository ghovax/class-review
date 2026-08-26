# Plan a lesson

{{ language_policy }}

{{ xml_policy }}

Plan a teachable lesson in {{ language }} from the corrected transcript and any document notes. The transcript is the authority for what was said. Let natural topic boundaries determine chapters and concepts, and cover the whole lesson without inventing material.

{{ mathematics_notation_rules }}

For every concept, record its objective, the main way it advances understanding (`Mechanism`, `Constraint`, `Tradeoff`, or `Evidence`), its intent (`Introduce`, `Deepen`, `Apply`, or `Review`), an explanation depth, its transcript time span, and a concise `DoNotRepeat` note for later chapters. Add document spans only when the concept uses the supplied document material.

Return only one `<LessonOutline>` XML document with `Title`, `Description`, one or more `Chapter` elements, and one or more `Concept` elements per chapter. Each concept must contain `TopicTitle`, `LearningObjective`, `MustAdvanceBy`, `Intent`, `ExplanationDepth`, `Rationale`, `Duration` with `Beginning` and `End`, and `DoNotRepeat`. Use `DocumentSpan` with `DocumentIndex` and `SectionIndex` when needed.
