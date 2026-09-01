---
name: review-class
description: Help an agent turn a lecture recording or user-provided transcript into a review-class lesson, with Modal-first transcription, progressive lesson planning and writing, and Pandoc/Typst export.
metadata:
  short-description: Build a review-class lesson from a lecture
---

# Review-class workflow

Use this skill when the user wants a lecture turned into a structured review class, study notes, chapters, or an exported document. Keep the workflow flexible: the lesson shape, chapter grouping, and degree of automation are implementation choices, not user-facing strategies or enums.

## Progressive instructions

Read the instruction files in this order, and only after the preceding phase has produced the material needed by the next phase:

1. First read [source-transcript.md](instructions/source-transcript.md) before deciding how to obtain the lecture source.
2. Second, once a timestamped transcript and any references exist, read [devise-outline.md](instructions/devise-outline.md) and devise a typed or plainly structured outline.
3. Third, once the outline exists, read [write-chapters.md](instructions/write-chapters.md) and write the lesson with continuity across whatever chapter grouping best serves the material.
4. Finally, once the lesson is complete, read [export.md](instructions/export.md) and render the requested format.

Do not load all phase instructions at once when a later phase is not yet relevant. Do not emit the skill's internal classification table, planning notes, or intermediate reasoning unless the user asks to inspect them.

## Non-negotiable boundaries

- Prefer Modal for transcription. The local machine is a fallback only when it can run the chosen model reliably or the user explicitly requests local execution.
- If neither a usable recording nor a timestamped transcript is available, ask the user to provide the transcript instead of inventing one.
- Keep timestamps and the original transcript available as intermediate source data throughout the workflow.
- Use ordinary Markdown and YAML frontmatter for lesson artifacts. YAML sequences use block-list syntax, never JavaScript-style array notation.
- Do not output XML, XML envelopes, XML schemas, XML citations, or XML-shaped transport data in user-facing lesson artifacts.
- Preserve the complete inputs and outputs of model calls when the runtime exposes them, including response metadata, tool calls, usage, and provider-exposed reasoning fields. Treat hidden chain-of-thought as opaque provider data; do not fabricate or reveal it.
- Use locale-aware standard libraries for dates, times, and language labels. Do not create hand-written month tables or duplicate language fields.
- Never add an automatic-generation disclaimer or equivalent boilerplate.
