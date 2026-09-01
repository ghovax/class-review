# Write the lesson

Read the outline, the transcript excerpts owned by the current writing unit, the relevant references, and the accumulated visible lesson context. Write a coherent review class in the requested language. The learner should hear the lecturer explaining the subject directly, not read a description of the source material, the lesson, or the generation process.

## Source fidelity

The transcript controls substance, order, reasoning, and depth. References may clarify or verify a point already supported by the lecture, but they do not authorize new scope. Preserve exact values, units, signs, identifiers, distinctions, and named entities whenever they are retained. Resolve transcript/reference conflicts before writing, and make the body claim and its citation agree on the same resolved value.

Normalize obvious transcription defects, duplicated fragments, malformed numerals, and surface terminology only when the intended reading is supported by the surrounding argument. Do not assign one component's properties to another, broaden a sub-case into a universal law, or turn a deliberate unknown into a fact.

## Lecturer voice and connective exposition

Write every learner-facing paragraph, including the abstract, from the lecturer's perspective. Use first-person singular for the lecturer's choices, explanations, observations, and conclusions: “I begin with...”, “I use this example to show...”, and “I cannot infer...” are appropriate. Use first-person plural when the lecturer and learner reason through an implication together: “We can now see why...”. Address the learner directly with “you” when giving an instruction or inviting an observation. Avoid outside narration such as “the lecture introduces,” “the lecturer explains,” “this chapter discusses,” or “the lesson covers”; those phrases turn the material into a report instead of instruction. Maintain the lecturer's first-person perspective throughout every paragraph rather than reverting to impersonal textbook summary.

Build the lesson as a chain of connected explanations. For each major idea, make the prose show: the problem or question that calls for it, the observation or definition that answers part of it, the mechanism or reasoning that makes the answer intelligible, the consequence or limitation that follows, and the next question or step this creates. Use explicit connective language when needed—“because,” “therefore,” “this matters when,” “that distinction lets us,” and “the next difficulty is”—but make the connections substantive rather than decorative. When an example appears, explain what it demonstrates and how it changes the argument. When a table or list is necessary, introduce the organizing principle and interpret the result in surrounding prose; never leave the reader to reconstruct the relationships from isolated entries.

Run a dictionary-and-reporting check before finalizing. Remove paragraphs that merely define one term, name one fact, or summarize what the lecture did without explaining why it matters. Replace them with connected exposition that relates the term to the active question, its operation, its consequence, or another established concept. Keep headings topical and concise, but make the prose beneath them do the explanatory work.

## Follow treatment intent and depth

Treat treatment intent, explanation depth, and advancement mode as descriptive guidance, not switches. A writing unit may contain a mixture of intents and varying depth; let the source determine how much of each is present and give the main contribution the space and reasoning it needs.

| Treatment intent | Writing behavior |
| --- | --- |
| Introduce | Establish the learner's baseline: define necessary terms, explain the core idea, and supply the reasoning required for the first understanding |
| Deepen | Assume the named baseline and add a substantial layer such as mechanism, constraint, distinction, edge case, consequence, or richer reasoning |
| Apply | Use the established principle without re-deriving it and work through a genuinely new case, decision, comparison, or outcome |
| Review | Use a short, stable reference to reconnect established material; do not rebuild the explanation or pretend it is new |

For explanatory depth, high preserves a dense mechanism, causal argument, meaningful nuance, or edge-case analysis; medium explains the core idea and its main implication with useful detail; low stays concise because the source only sketches or mentions the point. These are points on a continuum, not hard bins: one concept can contain a high-depth mechanism, medium-depth explanation, and low-depth aside. Depth is qualitative, not proportional to airtime. For advancement, mechanism explains how the result is produced, constraint explains where or why the idea is limited, trade-off explains a competing choice, and evidence supplies the observation or source support that tests the idea. These advancement perspectives can also coexist in one passage.

If the transcript revisits an established point, compare it against the prior prose and ledger before writing. Keep the recap proportionate to the new contribution, then develop whatever is genuinely new. A passage can be mostly review while adding a small deepening or application, or mostly introduction while using a familiar idea as an example. Describe and write that mixture honestly instead of forcing a single category.

## Flexible writing units

Choose the writing unit from the material and the available context window. It may be the whole lesson, a group of chapters, one chapter, or a smaller coherent unit. Atomic chapter writing is an implementation detail, not a required public strategy. When writing iteratively, carry forward the completed visible prose, terminology decisions, established claims, unresolved uncertainties, and citation mapping.

For each unit:

1. Identify the unit's owned concepts and use their objectives, intent, depth, and rationale as binding editorial guidance.
2. Compare every new passage with all earlier visible prose and the do-not-repeat ledger. Treat earlier prose as the ground truth when it is richer than the ledger.
3. Develop only the net-new contribution. When a later passage relies on an established term, mechanism, value, or example, refer to it by name and advance from it instead of redefining it.
4. Preserve the source's causal, procedural, and evidentiary reasoning. Do not compress a chain until its conclusion becomes an unsupported fact.
5. Write in direct first-person lecturer-to-learner voice. Use “I” and “we” naturally to make the speaking perspective explicit. Do not mention the transcript, recording, pages, slides, prompt, metadata, outline, or lesson position.
6. Use concise, topical, unnumbered headings. Do not write ordinal prefixes such as `1.` or `2.1` into heading text; section ordering is handled by the document structure and table of contents.
7. Open directly on substance. Avoid contents previews, progress announcements, backward pointers, forward references, and transition sentences whose only job is to announce where the reader is.
8. End each concept on its last substantive sentence. Do not append a recap, a setup for the next concept, an offer to elaborate, or generation commentary.

Timestamped source segments are an internal evidence and planning aid. Do not place transcript timecodes, timestamp labels, or timestamped links in the learner-facing lesson. Use ordinary source citations or a conventional bibliography entry without a time parameter; retain precise segment timestamps only in the normalized source, outline, and internal claim mapping. The document-level lesson timestamp may be rendered by the export template from `date`/`lesson-date`.

## Choose the presentation form

No presentation form has priority by default. Choose the form, or combination of forms, that makes the source's structure clearest while preserving every substantive detail. A single concept may move from explanatory prose to a list of cases, then to a comparison table, and back to prose that interprets the comparison. The choice should follow the information, not a preference for prose, lists, or tables.

One content unit should have one didactic function, but the complete lesson may interweave several forms. Use argumentative prose for a connected mechanism, explanation, implication, or causal chain when sentences are the clearest way to preserve it. Use a labeled list for genuinely parallel types, properties, requirements, cases, or procedural steps. Use a table for a multidimensional comparison: two or more entities described by two or more shared attributes. Use equations or other formal notation when the subject requires them. Use subsections when a concept contains distinct sub-mechanisms or phases.

Do not repeat the same information in prose, a list, and a table merely to create visual variety. Conversely, do not flatten a rich mechanism into prose when a list or table would make its parts clearer, and do not force a comparison into a paragraph when a table would make the relationships visible. Lists and tables are not permission to omit nuance, qualifications, causal links, or evidence: preserve the full depth of the source in whichever form you choose.

## Publication-style presentation

Write like a polished paper, textbook chapter, or professional study handout. Do not use ASCII art, boxed diagrams, decorative separators, Mermaid or other diagram syntax, emoji, chat-style labels, fake quotations, pseudo-UI, or response scaffolding such as `Answer:` and `Here is a summary:`. Do not turn the lesson into a transcript of the agent's work or into a stream of status updates.

Use one coherent publication system across the entire lesson: the same heading hierarchy, typography, list treatment, table treatment, citation style, spacing logic, and level of formality. Do not improvise a different visual or rhetorical style for each chapter. Let content determine structure while the shared style system keeps the document visibly unified.

Do not represent ordinary causal, procedural, or chronological sequences as ASCII arrow chains such as `A -> B -> C`, or as LaTeX arrow series such as `$A \to B \to C$`. Prefer a numbered or labeled list when the steps are separate, or connected prose when the relationship is continuous; lists are clearer for learners and make each step auditable. Keep arrow notation only when it is genuinely part of the subject matter—for example, a chemical reaction or transformation, a mathematical mapping, or another formal relation that the source actually teaches. Even then, use it sparingly and do not decorate ordinary exposition with it.

## Human-readable expression

Write every form as a careful human instructor would present it to an intelligent learner. Cover the full supported substance and preserve its precision, but give the reader one manageable logical move at a time. In prose, prefer short or medium-length sentences, concrete verbs, and clear paragraph boundaries. Split a sentence when it contains several nested clauses, qualifications, or independent conclusions; use a list when the material contains separate parallel steps or cases. Let paragraphs vary naturally: a short paragraph may state a hinge or result, while a longer paragraph may be necessary to carry a connected chain of reasoning. Do not target a uniform paragraph length, sentence count, or visual rhythm; split or combine paragraphs when the didactic function changes, not when a fixed size is reached.

Use technical language when the lesson requires it, but do not use jargon to sound authoritative. Define a necessary term at its first important use, then use it consistently. Replace avoidable specialist wording with ordinary language, without replacing a precise technical distinction with a vague simplification. Keep the complete reasoning intact while making the path through it easy to follow.

The goal is complete, precise understanding with minimal cognitive friction—not maximal compression, ornamental complexity, or an artificially simplified summary.

## Language and notation

Write all learner-facing prose, headings, labels, and citation text in the requested BCP 47 language. Keep terminology stable across the lesson and use canonical textbook forms for technical terms, identifiers, units, formulas, and symbols. A spoken acronym becomes its standard written acronym; a verbally described formula becomes canonical notation; a colloquial entity name becomes its formal name without changing the underlying fact.

Use inline LaTeX for genuine mathematics, including equations, relations, indices, exponents, units, Greek symbols, charges, and mathematical operators. Keep ordinary words, names, acronyms, gene/protein identifiers, and multi-letter labels as plain prose. Do not use unnecessary Unicode math or symbol characters in learner-facing content. Write operators and symbols with LaTeX instead: use \times rather than a typographic x or multiplication sign, \to rather than an arrow glyph, \ge rather than a greater-than-or-equal glyph, and \alpha rather than a bare Greek character. Apply the same rule to chemical charges, subscripts, superscripts, and reaction notation. Write causal relationships as sentences, not symbol chains; retain arrow notation only when it is genuinely required by the chemistry or mathematics being taught.

## Evidence and citations

Cite a claim where the chosen output format supports citations, placing the citation immediately after the sentence it supports. Cite the page or source that supports that specific claim, not a topical neighbor. When the lecture supplies the claim but no reference supports it, do not attach an unrelated citation. Keep citation text in the requested language and make it agree with the body on every relevant value and identifier.

For a lecture-only source, a conventional source link or bibliography entry is sufficient. Do not turn the lecture's internal time map into visible timecode citations. Timestamp precision belongs in the preserved source and outline, not in the student-facing prose or PDF.

Keep recording provenance in `recording_urls` and export-table metadata in `audio-files` as structured `{name, duration}` entries; keep reference-file export metadata in `reference-files` as `{name, pages}` entries. The selected template renders those fields through its predefined `Recordings | Duration` and `Reference documents | Pages` tables. Keep transcript-service and retrieval details in intermediate artifacts unless the template explicitly supports them. Do not spell metadata out as prose, add a manually authored `Sources` or `Source` section, or append a second bibliography-like block to the lesson body.

## Intermediate call data

For every model call, retain the exact request messages, response object, visible output, response metadata, tool calls, token usage, cache counters, and provider-exposed reasoning fields when the runtime exposes them. Use the complete assistant response as context for later writing units when the model interface supports it. Keep private reasoning opaque and separate from the student-facing lesson; never invent, paraphrase, or publish hidden chain-of-thought.

If a call is retried, retain the successful result and the failure metadata. Never silently replace an earlier unit's source, terminology, citation, or established claim without recording the change. Preserve the raw transcript and intermediate artifacts even when a normalized lesson is produced.

Before exporting, verify complete coverage, coherent progression, first-person lecturer voice, connective explanations, no third-person lesson report, no dictionary-like definition sequence, no transcript dump, no unsupported claims, no duplicated or drifting terminology, no accidental numbering, no raw internal classifications, no transport markup, and no automatic-generation boilerplate. Continue to the [export instructions](export.md).
