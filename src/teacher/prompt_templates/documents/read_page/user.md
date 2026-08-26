# Document Page Context Request

## Page Metadata

- **Document Index:** **{{ document.index }}** (0-based).
- **File Name:** **{{ document.file_name }}**.
- **Page Number:** **{{ document.page_number }}**.

---

## Per-Page Critical Reminders

The system prompt above carries the full ruleset. This section pings the rules most likely to slip on a per-page basis.

- **Source Fidelity:** Extract and explain only what is visibly supported by the rendered page image. Do not embellish from prior knowledge about the topic the page covers.
- **Language Preservation:** Keep the source language and the page's technical terminology stable. Do not translate or paraphrase technical terms.
- **Uncertainty:** When content is ambiguous or unreadable, name the ambiguity in place rather than guessing.
- **Two-Section Shape:** Output exactly two top-level headings, both at the same depth, in the order Summary then Details. Do not add any additional heading at the same depth, and do not use heading syntax inside section bodies.
- **Summary Is One or Two Prose Sentences:** Use prose only—no lists, no headings.
- **Details Is an Explanatory Walkthrough:** Explain the page's substance as if a student asked you to explain the image. Cover every instructionally relevant signal—definitions, formulas, values, named entities, relationships, conditions, examples, and caveats. Render visible source section titles as **bold labels** inside the Details body, never as Markdown headings.
- **Notation Hygiene:** Before responding, confirm every rule from the math-notation section was respected. The recurring violations to scan for:
  - No Unicode glyphs for math, chemistry, or Greek letters—every super/subscript, Greek letter, operator, relation symbol, degree symbol, or arrow must be its LaTeX command inside math delimiters.
  - No prose token wrapped in a math span—acronyms, identifiers, named entities, and multi-letter labels stay as plain prose.
  - Math delimiters reserved for genuinely mathematical content—never domain terminology.
  - Currency as ISO 4217 code everywhere—no currency glyph in the output.

---

## Required Output Shape

```markdown
# Summary

[One or two sentences, prose only, capturing what this page is about and its instructional role.]

# Details

[An explanatory walkthrough of the page's substance, written as if explaining the page to a student. Use bold labels for visible source section titles, classical-labeled lists for genuinely enumerable items, prose for continuous reasoning.]
```
