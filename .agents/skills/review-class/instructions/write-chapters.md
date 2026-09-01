# Write the lesson

Read the outline, the transcript excerpts owned by the current writing unit, the relevant references, and the accumulated visible lesson context. Write a coherent review class in the requested language. The learner should see a direct academic explanation, not a description of the source material or the generation process.

## Source fidelity

The transcript controls substance, order, reasoning, and depth. References may clarify or verify a point already supported by the lecture, but they do not authorize new scope. Preserve exact values, units, signs, identifiers, distinctions, and named entities whenever they are retained. Resolve transcript/reference conflicts before writing, and make the body claim and its citation agree on the same resolved value.

Normalize obvious transcription defects, duplicated fragments, malformed numerals, and surface terminology only when the intended reading is supported by the surrounding argument. Do not assign one component's properties to another, broaden a sub-case into a universal law, or turn a deliberate unknown into a fact.

## Execute the outline labels

Treat treatment intent, explanation depth, and advancement mode as operational guidance, not decorative labels:

| Label | Writing behavior |
| --- | --- |
| Introduce | Establish the learner's baseline: define necessary terms, explain the core idea, and supply the reasoning required for the first understanding |
| Deepen | Assume the named baseline and add a substantial layer such as mechanism, constraint, distinction, edge case, consequence, or richer reasoning |
| Apply | Use the established principle without re-deriving it and work through a genuinely new case, decision, comparison, or outcome |
| Review | Use a short, stable reference to reconnect established material; do not rebuild the explanation or pretend it is new |

For depth, high preserves a dense mechanism, causal argument, meaningful nuance, or edge-case analysis; medium explains the core idea and its main implication with useful detail; low stays concise because the source only sketches or mentions the point. Depth is qualitative, not proportional to airtime. For advancement, mechanism explains how the result is produced, constraint explains where or why the idea is limited, trade-off explains a competing choice, and evidence supplies the observation or source support that tests the idea.

If the transcript revisits an established point, compare it against the prior prose and ledger before writing. Keep the recap to the minimum needed for the new intent, and write only the net-new advancement at the selected depth. Do not label a restatement deepen, a repeated toy example apply, or an extensive treatment high when the source provides no corresponding reasoning.

## Flexible writing units

Choose the writing unit from the material and the available context window. It may be the whole lesson, a group of chapters, one chapter, or a smaller coherent unit. Atomic chapter writing is an implementation detail, not a required public strategy. When writing iteratively, carry forward the completed visible prose, terminology decisions, established claims, unresolved uncertainties, and citation mapping.

For each unit:

1. Identify the unit's owned concepts and use their objectives, intent, depth, and rationale as binding editorial guidance.
2. Compare every new passage with all earlier visible prose and the do-not-repeat ledger. Treat earlier prose as the ground truth when it is richer than the ledger.
3. Develop only the net-new contribution. When a later passage relies on an established term, mechanism, value, or example, refer to it by name and advance from it instead of redefining it.
4. Preserve the source's causal, procedural, and evidentiary reasoning. Do not compress a chain until its conclusion becomes an unsupported fact.
5. Write in direct professor-to-learner voice. Do not mention the transcript, recording, pages, slides, prompt, metadata, outline, or lesson position.
6. Open directly on substance. Avoid contents previews, progress announcements, backward pointers, forward references, and transition sentences whose only job is to announce where the reader is.
7. End each concept on its last substantive sentence. Do not append a recap, a setup for the next concept, an offer to elaborate, or generation commentary.

## Shape follows content

Use the smallest structure that makes the relationship clear. One content unit should have one didactic function.

- Use argumentative prose for a connected mechanism, explanation, implication, or causal chain. Each sentence should refine, support, contrast, or follow from the preceding one.
- Use a labeled list for genuinely parallel types, properties, requirements, cases, or procedural steps. Give each item enough explanation to carry its real substance; do not duplicate the list in preceding prose.
- Use a table for a multidimensional comparison: two or more entities described by two or more shared attributes. Keep headers and cells concise and do not repeat the matrix as prose.
- Use a hybrid mechanism–list/table–consequence shape when a causal explanation naturally produces an enumerable set and then resumes its reasoning.
- Use subsections when a concept contains distinct sub-mechanisms or phases. Do not create headings for every paragraph or use headings as a substitute for an explanation.
- Use equations only for genuine mathematical structure. Keep them inline unless the requested format clearly benefits from display math.

## Language and notation

Write all learner-facing prose, headings, labels, and citation text in the requested BCP 47 language. Keep terminology stable across the lesson and use canonical textbook forms for technical terms, identifiers, units, formulas, and symbols. A spoken acronym becomes its standard written acronym; a verbally described formula becomes canonical notation; a colloquial entity name becomes its formal name without changing the underlying fact.

Use inline LaTeX for genuine mathematics, including equations, relations, indices, exponents, units, Greek symbols, charges, and mathematical operators. Keep ordinary words, names, acronyms, gene/protein identifiers, and multi-letter labels as plain prose. Do not paste raw mathematical glyphs such as arrows, Greek letters, superscripts, or relation signs. Write causal relationships as sentences, not symbol chains.

## Evidence and citations

Cite a claim where the chosen output format supports citations, placing the citation immediately after the sentence it supports. Cite the page or source that supports that specific claim, not a topical neighbor. When the lecture supplies the claim but no reference supports it, do not attach an unrelated citation. Keep citation text in the requested language and make it agree with the body on every relevant value and identifier.

## Intermediate call data

For every model call, retain the exact request messages, response object, visible output, response metadata, tool calls, token usage, cache counters, and provider-exposed reasoning fields when the runtime exposes them. Use the complete assistant response as context for later writing units when the model interface supports it. Keep private reasoning opaque and separate from the student-facing lesson; never invent, paraphrase, or publish hidden chain-of-thought.

If a call is retried, retain the successful result and the failure metadata. Never silently replace an earlier unit's source, terminology, citation, or established claim without recording the change. Preserve the raw transcript and intermediate artifacts even when a normalized lesson is produced.

Before exporting, verify complete coverage, coherent progression, no transcript dump, no unsupported claims, no duplicated or drifting terminology, no accidental numbering, no raw internal classifications, no transport markup, and no automatic-generation boilerplate. Continue to [export.md](export.md).
