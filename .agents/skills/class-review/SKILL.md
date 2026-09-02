---
name: class-review
description: Help an agent turn a lecture recording or user-provided transcript into a class review, with Modal-first transcription, progressive lesson planning and writing, and Pandoc/Typst export.
metadata:
  short-description: Build a class review from a lecture
---

# Class-review workflow

Use this skill when the user wants a lecture turned into a structured class review, study notes, chapters, or an exported document. Treat chapter grouping, iteration boundaries, and model-call granularity as implementation choices selected by the material and runtime.

## Progressive instructions

Read the instruction files in this order, and only when the preceding phase has produced the material needed by the next phase:

1. First read the [source instructions](instructions/source-transcript.md) and obtain trustworthy source content in the format available. Preserve timestamps when they are supplied; do not require or create a canonical transcript shape. If no reliable lesson duration is available, ask the user for it.
2. Second, once the source content and references exist, read the [outline instructions](instructions/devise-outline.md) and build the lesson outline.
3. Third, once the outline exists, read the [chapter-writing instructions](instructions/write-chapters.md) and write the lesson using the grouping that best preserves its reasoning while eliminating performative filler.
4. Finally, once the lesson is complete, read the [export instructions](instructions/export.md) and render the requested format.

This order protects the reasoning. Loading later instructions too early can poison the analysis by letting formatting, chapter-writing, or export concerns influence source acquisition and outline decisions. Skipping a phase creates the same risk: the agent may elaborate unsupported material, lose the lecture's progression, or optimize the output format before the content is trustworthy.

Do not load later phase instructions early when they are not relevant. Keep internal planning classifications and intermediate model records out of the student-facing lesson unless the user asks to inspect them.
