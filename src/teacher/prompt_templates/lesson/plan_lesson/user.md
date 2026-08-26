# Lesson Outline Request

**Language Directive (Read First):** Write every CDATA value in this outline in **{{ metadata.language }}** (BCP47), including the lesson title and description, every chapter title, every concept topic title, every learning objective, every rationale, and every do-not-repeat ledger. Never translate XML tag names, attribute names, and enum tokens—keep them verbatim.

The full ruleset, schema, and golden XML shape live in the system prompt above. This user message carries the per-lesson metadata, the run-specific quotas, the data blocks the outline depends on, and a short critical-reminders block for the rules empirically most violated.

## Run Metadata

- **Output Language:** **{{ metadata.language }}** (BCP47). Apply this only to CDATA text. Do not translate XML tag names, schema structure, or enum tokens such as `Introduce` or `High`.
- **Lesson Timing:** Starts at **{{ metadata.lesson_start_seconds }}s**, ends at **{{ metadata.lesson_end_seconds }}s**, total duration **{{ metadata.lesson_duration_seconds }}s**. Read per-segment and per-sentence timestamps from `TranscriptSegments` below—anchor concept-window boundaries to actual `<Segment>` `<Beginning>` and `<End>` values.
- **Documents Provided:** **{{ metadata.document_count }}**.

## Run-Specific Quotas

- **Chapter Count:** Let semantic topic boundaries and teaching continuity determine the chapter count.
- **Concept Count:** Let actual transcript density and pedagogical structure determine the concept count.

---

## Section Explanations (Auxiliary Grounding for `DocumentSpan` Only)

Each `<Section>` carries one cohesive, multi-paragraph Markdown explanation that aggregates every page in the section into a continuous narrative. Use these explanations to decide which concept windows touch document-grounded material; the per-page summary / details blocks are intentionally not surfaced here to keep the prompt context bounded.

```xml
{{ section_explanations_xml }}
```

---

## Document Section Map (Authoritative Source for Every `DocumentSpan` and `SectionIndex`)

```xml
{{ document_section_map_xml }}
```

---

## Transcript

Each `<Segment>` carries authoritative `<Beginning>` and `<End>` timestamps; `<Sentence>` entries carry proportionally-interpolated timestamps for within-segment topic positioning. Use `<Segment>` boundaries to anchor concept windows.

```xml
{{ transcript_segments_xml }}
```

---

## Critical Reminders (Most Likely To Be Missed)

These rules are empirically most violated under run pressure. The system prompt defines them fully—treat this section as the per-run ping.

1. **Segment Boundary Alignment:** Align every concept `Beginning` with a `<Segment>` `<Beginning>` (within 15s) and every concept `End` with a `<Segment>` `<End>` (within 15s). Never split a `<Segment>` across two concept windows—splitting guarantees duplicated content in the chapters that elaborate this outline.
2. **Include `<DocumentSpan>` Whenever the Concept Touches Document-Grounded Material:** Use `<SectionIndex>` ordinals from the `DocumentSectionMap` below, never page numbers, never timestamps. Keep all `<SectionIndex>` tags under one `<DocumentSpan>` in the same `<DocumentIndex>`.
3. **Write `<DoNotRepeat>` on Every Concept Including the First:** Write it as direct instructions to the chapters that will elaborate this outline, naming the specific terms, values, examples, mechanism chains, and causal conclusions this concept establishes for the first time. An empty or shallow `DoNotRepeat` ledger directly causes intra-chapter and cross-chapter repetition in the resulting lesson.
4. **Concept Boundary Coherence:** Never let two concept windows, adjacent or distant, have `LearningObjective` values that ask for the same mechanism, derivation, or quantitative result. Make the later window's objective presuppose what the prior window established and target only net-new advancement. Cross-check against the `DoNotRepeat` field of every prior concept before writing each new objective.
5. **CDATA Discipline:** Wrap every free-form textual field in `<![CDATA[…]]>`. Write the enum fields `Intent`, `ExplanationDepth`, and `MustAdvanceBy` as plain tokens with no CDATA. Write numeric metadata fields (`DocumentIndex`, `SectionIndex`, `Beginning`, `End`) as plain numbers with no CDATA.
6. **Output Purity:** Begin the response with `<LessonOutline>` and end it with `</LessonOutline>`. Do not use Markdown commentary, a preamble, or code fences. Do not echo raw metadata in the output.
7. **Notation Hygiene in CDATA:** Apply the system prompt's math-notation rules inside every CDATA field. Scan for: no bare Unicode glyph (super/subscript, Greek letter, operator, relation, degree, arrow) — each is its LaTeX command inside `$…$`; no prose token wrapped in math (acronyms, identifiers, named entities, multi-letter labels stay plain); inline math only; currency as ISO 4217 code, never a glyph. **Greek letters are always math, even as symbol labels:** a Greek letter used as a coefficient, angle, parameter, rate, significance level, or subtype label in any field takes its LaTeX command — `$\alpha$`, `$\beta$`, `$\alpha_1$`, never bare `α`, `β`, `α₁` (the "structural document" framing never relaxes this; an objective naming `α` and `β` writes `$\alpha$` and `$\beta$`).
8. **Single-Script Discipline (Critical):** Restrict every CDATA character to the script **{{ language }}** requires. The failure mode to catch is **mid-token substitution** — one or two characters inside an inflected word silently replaced by another script (a Han/CJK ideograph like "特"/"异", stray Cyrillic in a Latin outline). Treat any non-target-script character as a hard failure. (Greek letters are the separate notation case: a Greek symbol is math, `$\alpha$`, never a bare prose glyph.)

---

This is the final pass I committed to at the start of this turn. Before I emit, I read the outline once more against every reminder above — notation clean inside every CDATA field (no bare Unicode glyph, no HTML markup, every identifier notated consistently), pure {{ language }} (BCP47) with no foreign-script character, the XML exact, coverage faithful to the source, and every `LearningObjective` net-new against all prior concepts — and I repair anything that slipped. I do not hand over an outline that breaks a commitment I already made to myself.
