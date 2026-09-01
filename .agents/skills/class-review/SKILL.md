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

1. First read the [source instructions](instructions/source-transcript.md) and obtain a trustworthy timestamped source.
2. Second, once the transcript and references exist, read the [outline instructions](instructions/devise-outline.md) and build the lesson outline.
3. Third, once the outline exists, read the [chapter-writing instructions](instructions/write-chapters.md) and write the lesson using the grouping that best preserves its reasoning.
4. Finally, once the lesson is complete, read the [export instructions](instructions/export.md) and render the requested format.

This order protects the reasoning. Loading later instructions too early can poison the analysis by letting formatting, chapter-writing, or export concerns influence source acquisition and outline decisions. Skipping a phase creates the same risk: the agent may elaborate unsupported material, lose the lecture's progression, or optimize the output format before the content is trustworthy.

Do not load later phase instructions early when they are not relevant. Keep internal planning classifications and intermediate model records out of the student-facing lesson unless the user asks to inspect them.

## Boundaries

- Prefer Modal for transcription. Use local execution only when the machine can run the selected model reliably or the user explicitly requests it.
- If no usable recording or timestamped transcript exists, ask the user to provide the transcript instead of inventing one.
- Preserve the original source, normalized transcript, outline, references, model-call records, and rendered artifacts as separate intermediate data.
- Write the lesson in ordinary Markdown with YAML frontmatter and ordinary citations. Do not emit XML or transport envelopes in any user-facing artifact.
- Preserve recording provenance in `recording_urls` and, for Pandoc/Typst exports, pass the template's predefined `audio-files` metadata as a block-style list of `{name, duration}` entries. Preserve reference-file provenance for that export as `reference-files`, a block-style list of `{name, pages}` entries. These fields render the template's existing `Recordings | Duration` and `Reference documents | Pages` tables; do not replace them with `sources`, inline labels, custom source conventions, or manual body sections.
- Keep transcript-service identity in the intermediate source record unless the selected template has an explicit supported field for it. Do not invent a visible `Sources:` line just to expose provenance that the template does not support.
- Keep timestamped transcript data and source-to-claim mappings in the intermediate artifacts. Do not expose timecodes, timestamp labels, or timestamped citation links in the learner-facing lesson or exported PDF unless the user explicitly requests them.
- Preserve the lesson timestamp as machine-readable `date` metadata and provide the template's localized `lesson-date` display value by default. This visible lesson timestamp is distinct from transcript timecodes, which remain internal unless explicitly requested. Do not add a generated author label; only use `author` when the user explicitly supplies an identity.
- Keep the learner-facing frontmatter abstract to one compact paragraph, normally 40–80 words and rarely over 100; do not duplicate the lesson body in the abstract.
- Do not create or populate a `subtitle` field or a generated author label. If the user explicitly supplies an author identity, pass it unchanged; otherwise omit `author` entirely.
- Never prefix chapter or concept headings with ordinal numbers. Keep heading text purely topical; the template must disable section numbering and the contents must use the same unnumbered titles.
- Write the learner-facing lesson and abstract in first-person lecturer voice: use “I” for the lecturer's explanations and judgments, and “we” when walking through shared reasoning. Do not describe the lecture, lecturer, or lesson from outside in third person.
- Make the exposition connective and argumentative. Link each observation to the mechanism it reveals, the consequence it creates, and the next question or step it motivates; do not produce a dictionary-like recollection of disconnected definitions, examples, or facts.
- Preserve provider-returned response metadata, tool calls, usage, cache counters, and reasoning fields when the runtime exposes them. Keep private reasoning opaque and separate from the lesson.
- Use locale-aware libraries for dates, times, and language labels rather than maintaining manual calendar tables.
- Do not add automatic-generation boilerplate or commentary about the generation process to the lesson.
