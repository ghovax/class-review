# Export the lesson

Read the finished lesson as structured content before serializing it. Prefer a Markdown AST and the serializer supplied by the chosen library; do not hand-build YAML or Markdown by concatenating strings when an AST/serializer is available.

## Canonical Markdown

Keep the body limited to the lesson and place its metadata in YAML frontmatter. Use block-style sequences:

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

Preserve the timestamp in machine-readable frontmatter, but display it pleasantly in rendered formats: localized date and hour/minute, without seconds, timezone offsets, or raw ISO punctuation in the visible title block. Use locale-aware date and time libraries rather than handwritten month names. Keep export labels together in a language-keyed dictionary or the selected locale resource so translations remain consistent across the document.

Use ordinary Markdown footnotes or the citation syntax selected by Pandoc. Put citations next to the claims they support and preserve source identity, page, and claim alignment. Do not embed transport markup in the body.

## Pandoc and Typst

Check the available renderers before choosing the output path:

```bash
command -v pandoc
command -v typst
```

For PDF, use Pandoc with the provided `pandoc-typst.template` when Typst is available. For HTML, DOCX, or another Pandoc-supported format, use the native writer and its normal styling facilities. If a requested renderer is unavailable, report the missing dependency and use another available format only with the user's agreement.

The Typst template should provide a centered `Abstract` heading above the description, a calm title block, localized date/time, coherent heading hierarchy, and no unexpected automatic section numbering. Tables use a lightly blue-tinted header with rules above and below the header only, no body grid borders, left/top alignment, and comfortable spacing. The glossary is a dictionary-style table with a compact term column and the definition column taking the remaining width. Filenames in source tables use a monospaced font.

Keep equivalent visual intent for HTML without relying on a repository CSS asset: blue-tinted headers, header rules only, no body borders, compact glossary terms, and monospaced filenames. Preserve links and footnotes in every format.

Save reviewable exports to the user's requested location. When no location is specified, use a clearly named file in the user's Downloads folder and keep temporary Pandoc and Typst inputs under the system temporary directory. Never leave generated tests or temporary renderer files in the repository.

Before handing the artifact over, inspect the rendered PDF, HTML, or DOCX when the format supports visual checking. Confirm that the transcript is absent from the body, metadata remains frontmatter, headings are not unexpectedly numbered, the abstract heading is centered, glossary definitions receive most of the table width, filenames are monospaced, citations survive conversion, and no generation-process boilerplate appears.
