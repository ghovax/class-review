# Export the lesson

Read the finished lesson as structured content before serializing it. Prefer a Markdown AST and the serializer supplied by the chosen library; do not hand-build YAML or Markdown by concatenating strings when an AST/serializer is available.

## Canonical Markdown

Keep metadata in YAML frontmatter and keep the body limited to the lesson. Use block-style YAML sequences, not JavaScript notation:

```yaml
---
title: Calculus fundamentals
description: An introduction to derivatives.
language: en
date: 2026-09-01T17:50:00+02:00
recording_urls:
  - https://example.test/lecture.m4a
reference_documents:
  - file_name: calculus-notes.pdf
    pages: 7
---
```

Use only `language`, never a duplicate `lang` field. Preserve the timestamp in machine-readable frontmatter, but display it pleasantly in rendered formats: localized date and hour/minute, without seconds, timezone offsets, or raw ISO punctuation in the visible title block.

Use ordinary Markdown footnotes or the citation syntax selected by Pandoc. Do not embed XML citation envelopes or any other transport markup in the body.

## Pandoc and Typst

Check availability before choosing a renderer:

```bash
command -v pandoc
command -v typst
```

For PDF, use Pandoc with the provided [pandoc-typst.template](../assets/pandoc-typst.template) when Typst is available. For HTML, DOCX, or another Pandoc-supported format, use the native Pandoc writer and the format's stylesheet/template when available. If Pandoc or Typst is unavailable, report the missing dependency and use another available renderer rather than silently emitting a different format.

The PDF template must provide a centered `Abstract` heading above the description, pleasant localized date/time, coherent heading hierarchy, and a calm table style. Tables should have a lightly blue-tinted header, header rules above and below, no body grid borders, left/top alignment, and enough spacing for readability. The glossary is a dictionary-like table: keep the term column compact and give the definition column the remaining width. Filenames in the recordings/reference table use a monospaced font.

Improve HTML to follow the same visual rules: blue-tinted header, rules around the header only, no body borders, compact glossary term column, and monospaced filenames. Preserve links and footnotes in every format.

Save reviewable exports to the user's requested location; when no location is specified, use a clearly named file in `~/Downloads` and keep temporary Pandoc/Typst inputs under the system temporary directory. Never leave generated test files in the repository.

Before handing the artifact over, inspect the rendered PDF/HTML/DOCX when the format supports visual checking. Confirm the source transcript is absent, metadata remains in frontmatter, headings are not unexpectedly numbered, the abstract heading is centered, glossary definitions receive most of the table width, filenames are monospaced, and no automatic-generation disclaimer appears.
