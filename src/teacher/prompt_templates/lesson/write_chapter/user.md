# Chapter Batch {{ chapter.index }}

**Critical Language Directive:** Write every word of this chapter in **{{ language }}** (BCP47), without exception. Apply this to the chapter-opening pivot sentence, every heading, every paragraph, every list item label, and every `<Citation>` `<Content>` CDATA block. Treat the directive as sticky regardless of what language the prior chapters in the conversation history used (they are also in **{{ language }}**, by contract). Do not switch languages mid-chapter even when a brief English phrase or a translated quote feels natural—write the phrase in **{{ language }}** instead. Keep verbatim XML structure (tag names, attribute names, the `<Citation>` mechanism itself) unchanged.

The full ruleset for chapter generation lives in the system prompt above—do not expect this user message to restate it. This message carries the per-chapter metadata, the data blocks, a short set of per-chapter reminders for the rules empirically most violated under chat-history pressure, and a pre-output checklist that runs against your draft before you respond.

## Batch Metadata

- **This Chapter:** Chapter **{{ chapter.index }}** of **{{ chapter.total }}**. Read the working title from the `<ChapterTitle>` element inside the `<ChapterContext>` XML data block below. Open the response with that title as the chapter-title heading (e.g. `# <title>`). Strip a structural prefix such as `Chapter N:` or `Module N:` from the title before emitting it; keep only the topical phrase. The title is also subject to the Surface Repair rule below; apply it before emitting the heading. Then write each concept section as a concept heading one level deeper than the chapter title (e.g. `## Concept Name`).
- **Surface Repair (Applies to Every Piece of Reproduced Text):** Treat every string the prompt hands you—the `<ChapterTitle>`, every concept's `<TopicTitle>` / `<LearningObjective>` / `<Rationale>` / `<DoNotRepeat>`, every `TranscriptGroup` `Content`, every `Chapter Document Pages` `Summary` / `Details`, and every `Citation` `<Content>` you author—as input that may carry surface-level defects. Whenever you reproduce, quote, paraphrase, or echo any of it in the chapter output (heading, body prose, list item, or `<Citation>` CDATA), repair the surface before emitting it across these axes:
    - **Math Notation (Repair Both Directions):** Apply the system prompt's math-notation rules to every reproduced span (`<ChapterTitle>`, every `<TopicTitle>`, every heading/CDATA value), repairing both ways: **wrap** genuine math the source left bare or Unicode (subscript, Greek letter, operator expression, charge/index) into LaTeX, and **unwrap** prose wrongly placed in math (`$\mathrm{cAMP}$` becomes `cAMP`, `$\mathrm{lac}$` becomes `lac`, `$GTGTG$` becomes `GTGTG`). A token that reads identically as plain text stays plain in both heading and body; converge any heading/body form mismatch on the single canonical form (a mismatch is a hard symbol-accuracy failure).
    - **Canonicalization:** Rewrite spoken-form symbols, acronyms read letter-by-letter, verbally-described formulas, and colloquial entity names into their textbook form per the Textbook Canonicalization Rule.
    - **Transcription Artefacts:** Fix dropped digits, swapped digit pairs, homophone substitutions, duplicated fragments, and obvious typos per the Normalization Rule.
    - **Slide-Extraction Artefacts:** Fix wrong-cell labels, OCR mojibake, stray hyphenation from line-wrap, and tag-bleed.
    - **Punctuation:** Strip trailing periods, stray quotes, and duplicated punctuation from headings and citation `<Content>`.
    - **Repair Only:** Never change the topical substance—only repair surface form. When a defect is ambiguous (could be a typo or a deliberate term), prefer the most internally-consistent reading the surrounding context supports.
- **Concept Count Contract:** Output exactly **{{ chapter.concept_count }}** concepts, in temporal order, with strict 1:1 mapping to the `ConceptWindow` entries in the data block below. Treat a count mismatch as a hard violation.
- **Chapter Time Range:** **{{ chapter.start_seconds }}** to **{{ chapter.end_seconds }}** seconds. Treat the transcript groups below as covering the lecture material the professor delivered within this span—they are the chapter's primary lecture source. Prior accepted chapters in the conversation history, the Covered Concepts and Prohibition Ledgers, and the chapter document pages remain available as established context the chapter may reference.
- **Conversation Continuity:** Treat prior accepted chapters in the conversation history (**{{ chapter.previous_chapter_count }}** chapters, **{{ chapter.previous_concept_count }}** prior concepts) as the ground truth for what is already established.
- **Output Language:** **{{ language }}** (BCP47), sticky across every sentence and every `<Citation>` `<Content>` CDATA.

## Expected Output Skeleton

The **heading hierarchy** is the contract; the **format inside each concept is content-driven**. The bracketed strings are placeholders — never reproduce the brackets or their text. The list, table, and sub-topics shown below are **illustrative of what a concept body may contain**, not a fixed layout: each belongs in *whichever* concept's content calls for it, not the position drawn here.

```markdown
# Chapter Title

[Opening paragraph — write continuous prose that opens directly on substance per the Opening Paragraph rule (no roadmap, no progress-bridge). For a later chapter, pivot from the prior chapter's result stated as a bare-fact terminal noun phrase.]

## A Concept Topic

[Selected body. Connected, causal explanation is prose. When the selected content is a set of parallel, enumerable items — named sub-types, properties, steps, sites — surface them as a classical-label list rather than burying them in a sentence:]

* **[A named item]:** [Its selected explanation on the same line — equivalent to prose treatment of the same point]
* **[Another named item]:** [Its selected explanation; nest a sub-list under an item that itself enumerates a parallel set]

## Another Concept Topic

[Selected body. When the selected content is a genuine matrix — two or more entities compared across two or more shared attributes — render it as a Markdown table, never as prose and never as parallel label-lists:]

| [Entity] | [An attribute] | [Another attribute] | [Further attribute columns as the matrix needs] |
| --- | --- | --- | --- |
| [First entity] | [Its value] | [Its value] | [Its value] |
| [Second entity] | [Its value] | [Its value] | [Its value] |
| [Further entity rows, one per compared entity] | [its value] | [Its value] | [Its value] |

[Prose then continues, building on the table without restating it. When a concept divides into named sub-topics, split it with `### Sub-Topic Title` headings.]

## Final Concept Topic

[Selected body, ending on its last substantive sentence — no closing summary or meta-commentary.]
```

- **This Is a Heading Contract, Not a Layout Template:** Keep exactly one chapter-title heading (`#`) and one concept heading (`##`) per `ConceptWindow` in temporal order, each anchored to its own topic. **Position implies nothing** — do not copy the example's placement; a list, a table, a sub-division, or none may appear in any concept, exactly as the material dictates. **Let format follow content:** connected, causal reasoning stays prose; a set of parallel, enumerable items (named sub-types, properties, steps, sites) is surfaced as a classical-label list rather than buried in a sentence; a genuine entity-by-attribute matrix (two or more entities across two or more shared attributes) is rendered as a Markdown table, never as prose or parallel label-lists. None of these shapes is a quota to fill — they emerge from what the chapter is teaching. The one failure to actively guard against is the opposite: flattening genuinely enumerable or tabular material into undifferentiated prose, which discards structure the reader needs.

## Per-Chapter Critical Reminders (Most-Violated Rules)

These rules are empirically most violated under long chat-history pressure. The system prompt defines them in full—treat this section as the per-chapter ping so the obligation does not fade.

1. **Citation Coverage:** Every concept window carrying a `DocumentSpan` owes at least one inline `<Citation>`; count the spans below and match that count, distributed across the owning concepts.
2. **Citation Page Specificity:** Point each `<Citation>` at the page whose `Summary` / `Details` holds the attached sentence's *specific* claim, not a topical neighbor; if no in-scope page supports it, move the citation to a sentence that is supported.
3. **Transcript vs. Document Conflict:** Carry every retained value and identifier verbatim. When a body sentence and its citation `<Content>` give different values for the *same* entity, resolve to one (prefer internal consistency, then artefact tells, then specificity) and write that value in both—never let them disagree. Full procedure in the system prompt.
4. **Before-Concept Inventory:** Before each concept after the first, mentally list the `DoNotRepeat` ledgers plus what you have already written, cross-check the current `TranscriptGroup`, develop only the non-overlap, and reference the rest by its established name.
5. **Language Stickiness:** Every sentence, heading, and citation `<Content>` in **{{ language }}**, pivots included—no drift to English the chat history tempts.
6. **No Bridge Paragraphs:** A concept's last paragraph is its own substance, never setup for the next; if removing it still leaves the concept complete, it belonged to the next concept.
7. **No Re-Introduced Examples:** Introduce a named example once; every later mention is a one-clause back-reference by name—rebuilding it with new attributes as a fresh "application" is the same violation.
8. **Moderate Sentence Length:** Prefer two or three shorter sentences to one clause-heavy sentence; a sentence enumerating three or more parallel entities is a candidate for a list or a per-entity split.
9. **List Item Depth + Nested Sub-Lists:** A list preserves the selected substance just as prose would, and an item that itself enumerates a parallel set gets a nested sub-list. Do not let formatting silently make the editorial treatment shorter or longer.
10. **Tables For Matrix Content (run the grid test):** Before shaping any set of two or more related items, ask: do they share two or more attributes each item has a value for? If yes it is a matrix — render it as a Markdown table, never as parallel label-lists and **never as parallel prose sentences/paragraphs that each cover the same dimensions** for a different entity. The most-missed cases are comparisons of three-plus items across shared dimensions (receptor types by ion permeability and block, environmental conditions by outcome, variants by parameters, states by association constants); a single-dimension enumeration stays a list.
11. **Chapter Boundary Behavior:** No lesson-level conclusion or closing summary at any chapter's end; open with the substance-first opening paragraph—for a later chapter, pivoting from the prior chapter's result stated as a bare-fact terminal noun phrase.
12. **No Meta-Sequencing or Forward-References (Function Test):** Write one continuous narrative; never narrate its own structure. Test each clause by function, not words: does it tell the reader about a part of the lesson — already read or still to come — instead of teaching? If so it is a defect, in any language (banned shapes in the system prompt's **Forbidden Phrasings** table — test the function, don't pattern-match). Tempting because prior chapters and the full outline are in view, but naming the reading position is always the defect. Worst offender is the **chapter opening**: no contents-preview roadmap or progress bridge — open on substance, pivoting from the prior chapter's result as a bare-fact terminal noun phrase.
13. **Never Break The Fourth Wall:** The student sees only the finished lesson — the source slides, transcript, pages, figures, and tables don't exist for them. Never point at the source (fourth-wall row of the system prompt's **Forbidden Phrasings** table); state each fact directly in the professor's voice, with the only reference to a source page being inside a `<Citation>` tag.

---

## Current Chapter Focus (Authoritative For This Turn)

```xml
{{ chapter.chapter_context_xml }}
```

---

## Chapter Document Pages (Mapped Page Details for This Chapter Only)

{{ chapter.document_pages_markdown }}

---

## Covered Concepts Ledger (Do-Not-Repeat Baseline)

- **Prior Chapters Included in Accumulation:** **{{ chapter.previous_chapter_count }}**.
- **Prior Concepts Already Covered:** **{{ chapter.previous_concept_count }}**.

```xml
{{ chapter.covered_concepts_xml }}
```

## Prohibition Ledger (DoNotRepeat Directives From All Prior Concepts, Extracted for Direct Reference)

Cross-check the current concept's transcript against every entry below before writing. Each is a hard prohibition on **redevelopment** (never redefine its terms, re-derive its values/formulas, rebuild its mechanism, or recapitulate its conclusions) — but not on reference: a `Deepen` advancing it, an `Apply` using it as a worked-case baseline, and a `Review` connecting it via a one-clause callback are all intended. When the transcript revisits a listed item, compress it to a one-clause back-reference by name and develop the net-new contribution from there.

```xml
{{ chapter.do_not_repeat_ledger_xml }}
```

---

## Transcript Metadata

- **Total Group Count:** The transcript below carries **{{ transcript.group_count }}** grouped ranges across all concept windows.

**Active Sifting Protocol:** Cross-reference each `TranscriptGroup` against the Prohibition Ledger above: develop material not yet in the Ledger at the professor's depth and the concept's `Intent` framing; compress anything already in it to a one-clause back-reference by name.

**Scope and Depth Calibration (Practical Reminder):** For every concept, use the stated `High`, `Medium`, or `Low` treatment. Preserve the causal links the source requires, but do not expand beyond its coverage. `ExplanationDepth` determines relative development inside that source-driven scope.

## Transcript

The transcript is partitioned by concept. Each `ConceptTranscript` block carries a `ConceptIndex`, a `TopicTitle`, and one or more `TranscriptGroup` entries holding the transcript content the chapter must develop for that concept. Every transcript sentence appears in exactly one `ConceptTranscript` block. Use each block as primary source for its corresponding concept—do not move substance across blocks.

```xml
{{ transcript.groups_xml }}
```

---

## Pre-Output Checklist – Verify Before Responding

Run the following checks against the draft chapter, in order, before emitting the response. Any failure means rewrite, not append a disclaimer.

### Structural

- [ ] **Output Purity:** Pure Markdown, no wrappers; exactly one chapter-title heading (`#`) plus **{{ chapter.concept_count }}** concept headings (`##`) in `ConceptWindow` order (strict 1:1); no second chapter title.
- [ ] **Chapter Title:** Heading matches the `<ChapterTitle>` CDATA, edited only to strip a `Chapter N:`-style prefix and apply Surface Repair—never invented.
- [ ] **Concept Openings:** Each concept goes straight into body content—no preamble, no sub-topic heading before its first sentence.
- [ ] **Chapter Ending:** Ends on the last concept's last substantive sentence—no closing summary, meta-commentary, or offer to continue.

### Citations

- [ ] **Coverage:** Every `DocumentSpan`-bearing concept has at least one `<Citation>` (count and verify).
- [ ] **Page Specificity:** Each citation's page actually holds the attached sentence's specific claim, not a topical neighbor.
- [ ] **Content Faithfulness:** Each `<Content>` restates the cited page's specific claim, in **{{ language }}**, matching the body value (the resolved value on a conflict).
- [ ] **Format:** Each `<Citation>` is one unbroken inline block after terminal punctuation, one page per tag, `DocumentIndex` in the concept's span, notation-clean inside CDATA.

### Repetition and Pedagogical Sequencing

- [ ] **Non-Repetition:** No concept restates, redefines, or re-derives any fact, value, mechanism step, or conclusion already established here or in the ledgers (rephrasing counts; reference-by-name does not).
- [ ] **Before-Concept Inventory:** For each concept after the first, the three-step inventory ran before the first sentence.
- [ ] **No Meta-Sequencing or Forward-References:** Apply the function test—no clause points at where content sits (backward, forward, or announce-later); test the function, not the example strings.
- [ ] **Openings Open On Substance:** No chapter opens with a contents-preview roadmap or a progress bridge; the deletion test passes ("in this chapter" / "we will now" / "after examining" all removable).

### Language and Source Fidelity

- [ ] **Language & Single-Script:** Everything in **{{ language }}**, pivots and CDATA included; no foreign-script character (mid-token substitution is the failure mode). Greek is the notation case, not this one.
- [ ] **Fourth Wall:** No reference to source slides, pages, figures, tables, or the deck anywhere—facts stated directly; source pages only inside `<Citation>`.
- [ ] **No Overgeneralization:** No sentence claims more than the source supports.
- [ ] **Argumentative Discourse:** Every paragraph reads as one connected line of reasoning, never strung-together facts — each sentence carries the prior's conclusion forward through cause, consequence, contrast, or refinement.
- [ ] **Reasoning Integrity:** Confirm every retained conclusion carries the causal support established by the source without becoming a disconnected fact.
- [ ] **Scope and Depth Calibration Matched:** Each concept follows the stated `High`, `Medium`, or `Low` treatment. Confirm the relative ordering remains visible and no more expansive treatment leaked into the chapter.
- [ ] **Document Proportionality:** No topic developed past the professor's transcript depth; documents clarify, not expand.

### Format Balance

- [ ] **Enumerable Content Not Flattened:** Any set of parallel, enumerable items in the material is surfaced as a classical-label list, not buried in a sentence; connected reasoning stays prose. The check is that genuine structure was not flattened into prose—not that a list quota was met.
- [ ] **Tables For Matrices (grid test):** Scan every list AND every run of parallel prose sentences/paragraphs — if the items share two or more attributes with per-item values, it is a matrix and must be a Markdown table (two or more attribute columns), not parallel label-lists and not parallel prose. Re-check the densest comparison in the chapter specifically; that is the one most often left flattened.
- [ ] **No Disguised Heading-Lists:** No run of consecutive `**Topic:**` stand-alone paragraphs—those are a list; reserve bold for inline emphasis.
- [ ] **List Item Depth:** Each list item carries its selected prose-equivalent substance—formatting neither shortens nor expands the editorial treatment.
- [ ] **Nested Sub-Lists:** An item enumerating a parallel set uses a nested sub-list (no deeper than two levels), not an inline comma phrase.
- [ ] **One Format, One Time:** No paragraph immediately echoed by a list on the same content.
- [ ] **Register Consistency:** Prose-to-list ratio and opening style match prior chapters unless content-driven; do not propagate all-prose drift.

### Notation (Chapter-Specific Checks)

The general notation rules live in the system prompt and are re-scanned in the Final Notation Pass below; these three are the chapter-specific traps the general rules do not cover:

- [ ] **Headings Carry The Same Notation Discipline As Body:** Scan every `#` / `##` / `###` line for a bare Unicode glyph or a bare backslash-command. `## Heading \alpha_2` is a hard failure—Markdown stringify escapes it and the reader sees raw `\alpha\_2`; write `## Heading $\alpha_2$`. Apply Surface Repair even when the source `<ChapterTitle>` / `<TopicTitle>` CDATA already carries the defect.
- [ ] **Citation `<Content>` CDATA Follows Body Notation Exactly:** Read each `<Content>` in isolation—no bare glyph, no backslash-command outside `$…$`, and no over-wrapping of an acronym in `$\mathrm{}$` that the body correctly leaves plain. CDATA is not a more "formal" register.
- [ ] **Citation Tag Well-Formedness:** Every `<Citation>` has its closing `</Citation>` on the same line; a missing or line-broken close ships the tag as raw XML instead of a footnote reference.

---

## Final Notation Pass (Highest-Impact Defect Class)

Symbol accuracy is the single most common reason a finished chapter fails review, so the last thing before emitting is a notation scan. The full ruleset, restated here so it is directly in front of you for this final pass:

{{ mathematics_notation_rules }}

Walk the draft once more for the recurring defects below, applying the *principle* to every analogous token, not only to these illustrative examples:

- **Prose Wrongly In Math:** a word, acronym, gene/operon, or code in `$…$` / `\mathrm{}` (`$\mathrm{cAMP}$`, `$\mathrm{lac}$`, `$GTGTG$`, `$\mathrm{GABA}$`, `$\mathrm{NMDA}$`). Strip-and-read: if it reads identically as plain text, it stays plain prose — including a bare acronym whose *subscripted* form is genuinely math (`$\mathrm{GABA}_A$` is math; bare `GABA` is prose, even one sentence apart).
- **Math Wrongly Left Bare:** an assignment, relation, power, or formula with no `$…$` (`T=3`, `pH<7`, `R^2=0.95`).
- **Bare Unicode Glyph Anywhere:** a raw Greek letter, super/subscript, operator, degree, or arrow in body, heading, table cell, or `<Citation>` CDATA; each becomes its LaTeX command inside `$…$`.
- **Arrow Chain:** three-or-more entities chained by any arrow (Unicode or LaTeX) is a list, never `$\rightarrow$` spans; the only carve-out is a single canonical domain expression (`$f: A \to B$`, `$\lim_{x \to 0}$`, a balanced reaction).
- **Consistency:** one notational form per entity, the body matching every adjacent citation `<Content>`; every backslash-command inside `$…$`; citation and footnote markers left bare.

---

This is the final pass I committed to at the start of this turn. Before I emit, I read the draft once more against every rule above — notation first (no standalone `$\mathrm{Word}$` prose-wrap, no bare Unicode glyph or bare arrow anywhere including table cells and headings, every identifier notated consistently), then pure {{ language }} (BCP47) throughout, then one continuous narrative with no signposting (in {{ language }} too — the local equivalent of "as we saw / as we examined", including a recap relative clause at a chapter opening), no forward-references, chapter-opening roadmap, or progress bridge, no reference to the source slides, pages, figures, or tables, every citation well-formed and grounded, source scope respected, and each content-driven structure used only where appropriate — and I repair anything that slipped. I do not hand over a chapter that breaks a commitment I already made to myself.
