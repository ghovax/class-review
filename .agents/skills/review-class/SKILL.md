---
name: review-class
description: Help an agent turn a lecture recording or user-provided transcript into a review-class lesson, with Modal-first transcription, progressive lesson planning and writing, and Pandoc/Typst export.
metadata:
  short-description: Build a review-class lesson from a lecture
---

# Review-class workflow

Use this skill when the user wants a lecture turned into a structured review class, study notes, chapters, or an exported document. Treat chapter grouping, iteration boundaries, and model-call granularity as implementation choices selected by the material and runtime.

## Progressive instructions

Read the instruction files in this order, and only when the preceding phase has produced the material needed by the next phase:

1. First read [source-transcript.md](instructions/source-transcript.md) and obtain a trustworthy timestamped source.
2. Second, once the transcript and references exist, read [devise-outline.md](instructions/devise-outline.md) and build the lesson outline.
3. Third, once the outline exists, read [write-chapters.md](instructions/write-chapters.md) and write the lesson using the grouping that best preserves its reasoning.
4. Finally, once the lesson is complete, read [export.md](instructions/export.md) and render the requested format.

Do not load later phase instructions early when they are not relevant. Keep internal planning classifications and intermediate model records out of the student-facing lesson unless the user asks to inspect them.

## Boundaries

- Prefer Modal for transcription. Use local execution only when the machine can run the selected model reliably or the user explicitly requests it.
- If no usable recording or timestamped transcript exists, ask the user to provide the transcript instead of inventing one.
- Preserve the original source, normalized transcript, outline, references, model-call records, and rendered artifacts as separate intermediate data.
- Write the lesson in ordinary Markdown with YAML frontmatter and ordinary citations. Do not emit XML or transport envelopes in any user-facing artifact.
- Preserve provider-returned response metadata, tool calls, usage, cache counters, and reasoning fields when the runtime exposes them. Keep private reasoning opaque and separate from the lesson.
- Use locale-aware libraries for dates, times, and language labels rather than maintaining manual calendar tables.
- Do not add automatic-generation boilerplate or commentary about the generation process to the lesson.
