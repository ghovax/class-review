# Export the lesson

Read the finished lesson as structured content before serializing it. Prefer a Markdown AST and the serializer supplied by the chosen library; do not hand-build YAML or Markdown by concatenating strings when an AST/serializer is available.

## Canonical Markdown

Keep the body limited to the lesson and place its metadata in YAML frontmatter. Use block-style sequences:

```yaml
---
title: Calculus fundamentals
description: >-
  I connect derivatives to local change, use them to reason about optimization, and identify the assumptions that limit their use.
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

The `description` is the learner-facing abstract. It must:

- be one compact paragraph;
- normally contain 40–80 words and rarely more than 100;
- use first-person lecturer voice;
- synthesize the subject, scope, central question, approach, main mechanism or implication, and meaningful limitation;
- connect related ideas instead of listing chapters; and
- remain grounded in the transcript and relevant references.

Do not write “the lecture introduces...” or “this lesson covers...”. Do not duplicate the lesson body in the abstract.

Preserve the lesson timestamp in the machine-readable `date` field and use that same field for the visible title-block timestamp. Before invoking the template, localize and format the value as a readable calendar date plus hour/minute. Omit seconds, timezone offsets, raw ISO punctuation, and transcript timecodes. Do not create a second display-date metadata field. Use locale-aware date and time libraries rather than handwritten month names.

Keep source citations ordinary and local to the claims they support:

- use ordinary Markdown footnotes or the citation syntax selected by Pandoc;
- preserve source identity, page, and claim alignment;
- do not embed transport markup in the body; and
- do not display transcript segment timecodes or timestamped citation links.

## Template contract and metadata

Treat the supplied export template as the publication contract. Before invoking Pandoc:

- read the actual template in full;
- use its variable names and layout conventions;
- inspect both its Pandoc conditionals and its `conf` call;
- populate every supported field for which the source or requested format provides a value; and
- use the template's declared defaults for format controls when the source does not specify them.

Populate the core metadata as follows:

- `title`: the lesson title;
- `description`: the concise first-person abstract;
- `date`: the machine-readable lesson timestamp, also formatted for the template's visible timestamp using the same field;
- `lang`: the requested BCP 47 language;
- `recording_urls`: public recording links for machine-readable provenance;
- `region`, `papersize`, `mainfont`, `fontsize`, `mathfont`, `codefont`, `linestretch`, `margin`, `columns`, `page-numbering`, `linkcolor`, `citecolor`, `filecolor`, `keywords`, `thanks`, and `abstract-title`: only when supported and relevant; and
- `author`: only when the user explicitly supplies an author identity; otherwise omit it.

Do not create or pass `subtitle`.

Populate the predefined source tables with mappings, not prose:

- `audio-files`: one `{name, duration}` entry per recording;
- `reference-files`: one `{name, pages}` entry per supplied reference file;
- `recordings-label`, `duration-label`, `reference-documents-label`, and `pages-label`: localized overrides only when needed; and
- omit a table's metadata when there is no corresponding source rather than fabricating a row.

The template renders these entries through its predefined `Recordings | Duration` and `Reference documents | Pages` tables. Do not rename them to `sources`, `source_title`, or `reference_documents`; do not concatenate labels; and do not create Markdown tables in the lesson body.

Keep transcript-service identity, retrieval details, raw responses, outlines, references, model-call records, and other intermediate artifacts outside the learner-facing body unless the selected template explicitly supports them.

The body must begin directly with lesson content. Do not duplicate the title, abstract, contents, recording/reference tables, or other template-owned metadata in the body. Do not rely on a custom filter or wrapper to conceal duplicates. Fill the template's existing title, timestamp, abstract, contents, source-table, heading, table, citation, footnote, and page-numbering mechanisms rather than replacing them with a parallel renderer-specific system.

## Pandoc and Typst

Check the available renderers before choosing the output path:

```bash
command -v pandoc
command -v typst
```

For PDF, use Pandoc with the provided `pandoc-typst.template` when Typst is available. For HTML, DOCX, or another Pandoc-supported format, use the native writer and its normal styling facilities. If a requested renderer is unavailable, report the missing dependency and use another available format only with the user's agreement.

Before compiling a PDF, verify the fonts used by the template:

- `Libertinus Math` must be discoverable through `typst fonts`;
- the template must use it for mathematical equations; and
- if it is missing, install or expose the font before compiling rather than accepting a fallback warning.

The Typst template should provide:

- a centered `Abstract` heading above the description;
- a calm title block with the readable lesson timestamp;
- coherent unnumbered heading hierarchy;
- section numbering disabled at the template level;
- lightly blue-tinted table headers with rules above and below the header only;
- no body grid borders;
- left/top table alignment and comfortable spacing;
- a compact glossary term column with definitions taking the remaining width; and
- monospaced filenames in source tables.

Always include a table of contents in the PDF when the lesson has headings. Use the chapter and concept hierarchy, keep entry styling consistent with the body, and make the contents readable rather than dense. Use the template's own outline mechanism and do not add a second contents convention.

Apply one professional style system throughout the export: title and timestamp, abstract, contents, headings, paragraphs, lists, tables, equations, citations, footnotes, page numbering, and spacing should look like parts of one publication. Preserve links and footnotes in every format.

Save reviewable exports to the user's requested location. When no location is specified, use a clearly named file in the user's Downloads folder and keep temporary Pandoc and Typst inputs under the system temporary directory. Never leave generated tests or temporary renderer files in the repository.

## Final checks

Before handing the artifact over, inspect the rendered PDF, HTML, or DOCX when the format supports visual checking. Confirm that:

- the transcript is absent from the body;
- the lesson and abstract use first-person lecturer voice rather than third-person reporting;
- the prose preserves explanatory connections rather than isolated dictionary entries;
- only one `date` field exists in the lesson metadata;
- the visible timestamp is readable and contains no raw ISO punctuation, seconds, or timezone offset;
- recording and reference metadata appear in the template-owned predefined tables rather than as accidental end sections;
- headings and contents entries contain no numeric prefixes;
- section numbering is disabled at the template level;
- no transcript timecode or timestamped citation appears;
- the abstract is concise and its heading has clear vertical separation from surrounding text;
- glossary definitions receive most of the table width;
- filenames are monospaced;
- citations survive conversion; and
- no generation-process boilerplate appears.
