---
name: class-review
description: Help an agent turn a lecture recording or user-provided transcript into a class review, with Modal-first transcription, progressive lesson planning and writing, and Pandoc/Typst export.
metadata:
  short-description: Build a class review from a lecture
---

# Class-review workflow

Use this skill when the user wants a lecture turned into a structured class review, study notes, chapters, or an exported document. Treat chapter grouping, iteration boundaries, and model-call granularity as implementation choices selected by the material and runtime.

Treat supplied reference materials as secondary support for the lecture: use them to confirm, clarify, repair, enrich, and cite lecture-grounded ideas, but never let them replace the lecture as the guiding thread or become a second syllabus.

## Authority when active

Once this skill activates, it owns the entire methodology and approach for the task. Its rules control source acquisition, reference use, outlining, reasoning repair, chapter writing, persistence, metadata, citations, and export. Do not replace any of these with generic or built-in PDF, DOCX, Markdown, presentation, or document instructions.

If another skill is also available, use it only for narrow format-specific mechanics explicitly required by this workflow, such as rendering or visual inspection after the lesson is complete. It is not an alternate workflow and must not override this skill's content rules, source hierarchy, reasoning requirements, temporary-file policy, metadata contract, citation rules, or export process. System, developer, and explicit user instructions remain authoritative.

## Progressive instructions

Read the instruction files in this order, and only when the preceding phase has produced the material needed by the next phase:

1. First read the [source instructions](instructions/source-transcript.md) and obtain trustworthy source content in the format available. Preserve timestamps when they are supplied; do not require or create a canonical transcript shape. Derive lesson duration from reliable metadata when available, including a trustworthy final source timestamp; ask the user only when no reliable duration can be established.
2. Second, once the source content and references exist, read the [outline instructions](instructions/devise-outline.md) and build the lesson outline, mapping only relevant reference passages to the lecture's concepts.
3. Third, once the outline exists, read the [chapter-writing instructions](instructions/write-chapters.md) and write the lesson using the grouping that best preserves its reasoning while using references selectively and eliminating performative filler.
4. Finally, once the lesson is complete, read the [export instructions](instructions/export.md) and render the requested format.

This order protects the reasoning. Loading later instructions too early can poison the analysis by letting formatting, chapter-writing, or export concerns influence source acquisition and outline decisions. Skipping a phase creates the same risk: the agent may elaborate unsupported material, lose the lecture's progression, or optimize the output format before the content is trustworthy.

Do not load later phase instructions early when they are not relevant. Keep internal planning classifications, source maps, drafts, and model-call context in the current working context; do not serialize them into the workspace or student-facing lesson unless the user explicitly requests an audit artifact or a runtime genuinely requires temporary storage.
