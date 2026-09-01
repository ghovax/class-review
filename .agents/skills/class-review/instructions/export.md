# Export the lesson

Read the finished lesson as structured content before serializing it. Prefer a Markdown AST and the serializer supplied by the chosen library; do not hand-build YAML or Markdown by concatenating strings when an AST/serializer is available.

## Canonical Markdown

Keep the body limited to the lesson and place its metadata in YAML frontmatter. Use block-style sequences:

```yaml
---
title: Calculus fundamentals
description: >-
  This review class examines how derivatives describe local change, how their
  mechanism supports optimization, and which assumptions limit their use.
  It connects the lecture's definitions, examples, evidence, and practical
  implications in one coherent account.
lang: en
date: 2026-09-01T17:50:00+02:00
recording_urls:
  - https://example.test/lecture.m4a
audio-files:
  - name: lecture.m4a
    duration: "47:06"
reference-files:
  - name: calculus-notes.pdf
    pages: 7
---
```

The description in the frontmatter is the paper-style abstract. Keep it very concise: one compact paragraph, normally 40–80 words and rarely more than 100. It must use the lecturer's first-person voice and still synthesize the lesson's subject, scope, central question or problem, approach or framework, principal mechanism or implication, and meaningful limitation. Write “I introduce...” or “we examine...” rather than “the lecture introduces...” or “this lesson covers...”. Compress related ideas instead of turning the abstract into a miniature contents page or a second copy of the lesson. Keep every statement grounded in the source.

Preserve the lesson timestamp in machine-readable `date` and derive the template's separate localized `lesson-date` display value by default. Use locale-aware date and time libraries rather than handwritten month names. Keep transcript segment timecodes and timestamped citation links internal unless the user explicitly requests them. Keep export labels together in a language-keyed dictionary or the selected locale resource so translations remain consistent across the document. Never render the raw machine-readable timestamp directly as visible text.

Use ordinary Markdown footnotes or the citation syntax selected by Pandoc. Put citations next to the claims they support and preserve source identity, page, and claim alignment. Do not embed transport markup in the body. Do not display timestamps or timestamped links in the exported lesson; use ordinary source citations without time parameters, and keep timestamp precision in the intermediate transcript and outline only unless the user explicitly requests timecodes.

## Template contract and metadata

Treat the supplied export template as the publication contract. Read the actual template before invoking Pandoc, use its variable names and layout conventions, and populate every supported field for which the source or requested format provides a value. Do not leave supported fields unattended by habit, substitute a private metadata convention, or introduce a second title/abstract wrapper that the template must hide.

Keep the lesson's machine-readable metadata in YAML frontmatter using the names that the actual template accepts. In the supplied Typst template, inspect both the Pandoc conditionals and the `conf` call before passing a variable: do not assume that a standard Pandoc key is rendered merely because it is present in frontmatter. At minimum, populate `title`, `author` (default `Lecture review`), the concise `description`, the machine-readable `date`, `lang`, and `recording_urls`; do not create or pass `subtitle`, because the template does not support it. For the predefined source tables, populate `audio-files` as a block-style list of `{name, duration}` entries and `reference-files` as a block-style list of `{name, pages}` entries. Populate `region`, `papersize`, `mainfont`, `fontsize`, `mathfont`, `codefont`, `linestretch`, `margin`, `columns`, `page-numbering`, `linkcolor`, `citecolor`, `filecolor`, `keywords`, `thanks`, `abstract-title`, and any other template-specific fields when they are actually supported and relevant. Use the template's declared defaults for format controls when the source does not specify them. Keep transcript-service and retrieval details in the intermediate source record unless the selected template explicitly supports them; the template-owned source tables must render supported metadata, with no manual end-of-document source block and no invented header or ad hoc convention.

In the supplied template, `audio-files` and `reference-files` are data structures, not body text. Their predefined tables are emitted before the contents using the exact historical schema: recording `name` plus `duration`, and reference-file `name` plus `pages`. Pass the entries as YAML mappings; do not concatenate labels, rename them to `sources`, `source_title`, or `reference_documents`, or create Markdown tables in the lesson body. If no recording or reference file exists, omit that table's metadata rather than fabricating a row. Keep public recording URLs in `recording_urls` for machine-readable provenance, but do not add a separate visible URL table unless the selected template explicitly provides one.

The body must begin directly with the lesson content. The title, abstract, contents, recording/reference tables, and other publication metadata belong to frontmatter and the template-supported title/contents/source-table blocks. Do not duplicate them in the body and do not rely on a custom filter or wrapper to conceal duplicates. Derive and pass a localized `lesson-date` display value from `date` by default, while preserving the machine-readable timestamp in frontmatter; keep transcript segment timecodes out of the visible lesson unless explicitly requested. Omit `author` unless the user explicitly supplies an identity. Fill the template's existing title, abstract, contents, source, heading, table, citation, footnote, and page-numbering mechanisms rather than replacing them with a parallel renderer-specific system. If the template exposes a supported file or reference field, fill it with the original filename and page data; do not silently drop that metadata or invent a new naming scheme.

## Pandoc and Typst

Check the available renderers before choosing the output path:

```bash
command -v pandoc
command -v typst
```

For PDF, use Pandoc with the provided `pandoc-typst.template` when Typst is available. For HTML, DOCX, or another Pandoc-supported format, use the native writer and its normal styling facilities. If a requested renderer is unavailable, report the missing dependency and use another available format only with the user's agreement.

The Typst template should provide a centered `Abstract` heading above the description, a calm title block with the rendered lesson timestamp, coherent unnumbered heading hierarchy, and section numbering disabled at the template level. Tables use a lightly blue-tinted header with rules above and below the header only, no body grid borders, left/top alignment, and comfortable spacing. The glossary is a dictionary-style table with a compact term column and the definition column taking the remaining width. Filenames in source tables use a monospaced font.

Always include a table of contents in the PDF when the lesson has headings. Use the chapter and concept hierarchy, keep the entry styling consistent with the body, and make the contents readable rather than dense. Do not rely on an optional renderer flag to decide whether the contents exists. Ensure the contents and body are produced by the template's own outline mechanism, without adding a second custom contents convention.

Apply the same professional style system throughout the export: title and abstract, table of contents, headings, paragraphs, lists, tables, equations, citations, footnotes, page numbering, and spacing should look like parts of one publication. Do not mix ad hoc styles between chapters or allow the renderer's defaults to override the chosen template selectively.

Keep equivalent visual intent for HTML without relying on a repository CSS asset: blue-tinted headers, header rules only, no body borders, compact glossary terms, and monospaced filenames. Preserve links and footnotes in every format.

Save reviewable exports to the user's requested location. When no location is specified, use a clearly named file in the user's Downloads folder and keep temporary Pandoc and Typst inputs under the system temporary directory. Never leave generated tests or temporary renderer files in the repository.

Before handing the artifact over, inspect the rendered PDF, HTML, or DOCX when the format supports visual checking. Confirm that the transcript is absent from the body, the lesson and abstract use first-person lecturer voice rather than third-person reporting, the prose preserves explanatory connections rather than isolated dictionary entries, metadata remains frontmatter and is actually reflected wherever the template supports it, the localized lesson timestamp is rendered without raw ISO punctuation, recording and reference metadata appear in the template-owned predefined tables rather than as accidental end sections, headings and contents entries contain no numeric prefixes, section numbering is disabled at the template level, no transcript timecode or timestamped citation appears, the abstract is concise and its heading has clear vertical separation from surrounding text, glossary definitions receive most of the table width, filenames are monospaced, citations survive conversion without visible timestamps, and no generation-process boilerplate appears.
