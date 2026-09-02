# Write the lesson

Read the outline, the source excerpts owned by the current writing unit, the relevant references, and the accumulated visible lesson context. Write a coherent review class in the requested language. The learner should hear the lecturer explaining the subject directly, not read a description of the source material, the lesson, or the generation process.

Keep the learner-facing artifact as ordinary Markdown with YAML frontmatter and ordinary citations. Do not emit XML, transport envelopes, internal records, or generation-process commentary in the lesson. Preserve the raw transcript, outline, references, model-call records, and prior lesson versions separately from the visible prose.

## Source fidelity

Use the supplied lecture source as the primary source for:

- the lecture's scope and intended substance;
- order;
- reasoning goals and progression; and
- explanatory depth.

Use relevant knowledge and references to clarify, verify, supply a necessary missing bridge, or correct an incoherent or factually incorrect explanation. They do not authorize unrelated new scope. A source's authority does not require reproducing an error; preserve the lecturer's teaching objective and reasoning path while correcting the defective step and recording substantive repairs in the intermediate artifacts. When retaining a claim, preserve:

- exact values and units;
- signs;
- identifiers;
- distinctions; and
- named entities.

Before writing, resolve source/reference conflicts so the body claim and its citation agree on the same value.

Do not rewrite or normalize the source into a canonical representation. When a likely transcription artefact affects the learner-facing meaning, resolve it only when the surrounding argument makes the intended reading clear:

- obvious transcription defects;
- duplicated fragments;
- malformed numerals; and
- surface terminology.

Do not assign one component's properties to another, broaden a sub-case into a universal law, or turn a deliberate unknown into a fact.

## Preserve and repair the reasoning

The written chapter must be a faithful, teachable reconstruction of the lecturer's reasoning, not a lossy summary. Preserve the full traceable path that takes the learner from the motivating question or premise through the relevant definitions, distinctions, observations, evidence, intermediate inferences, mechanisms, calculations, examples, qualifications, objections, limitations, and conclusion. If the lecturer spends substantial time guiding the learner through a chain, preserve that chain and its exam-relevant insights.

Remove hesitations, repetitions, digressions, and accidental stream-of-consciousness phrasing when doing so improves clarity, but never remove a logical dependency merely because it can be guessed from the conclusion. Do not jump from an initial setup to a final result. Before compressing a passage, identify the steps a learner would need in order to follow, reproduce, test, or apply the reasoning, and retain those steps in a clear order.

Repair the explanation whenever the source leaves a necessary gap or contains an incoherent, ambiguous, or incorrect step:

- supply missing connective reasoning with reliable knowledge and relevant references when needed to make the argument intelligible;
- correct factual or logical errors rather than reproducing them, while preserving the intended question, scope, and pedagogical progression;
- explain the repaired step as part of the lesson so that no necessary gap remains in the learner-facing argument; and
- preserve unresolved uncertainty only when the available evidence cannot establish a correction, rather than silently inventing one.

Keep the repair proportionate. Add what is necessary to make the lecturer's supported reasoning complete, not a generic textbook treatment or an unrelated expansion. Record substantive corrections, inserted bridges, and unresolved conflicts in the intermediate claim/source mapping even when the learner-facing prose reads as one coherent explanation.

## Lecturer voice and connective exposition

Write as a professor teaching the material directly, not as a narrator reporting on a lecture. First-person voice is a perspective, not a word-level pattern: do not make every sentence begin with “I” or turn the lesson into a sequence of promises about what the lecturer will provide.

Use pronouns according to their real function:

- use “I” for a considered choice, observation, qualification, or conclusion that belongs to the lecturer;
- use “we” when guiding the learner through a shared inference or derivation;
- use “you” for a direct invitation, instruction, or test; and
- state technical facts directly when they do not need an explicit speaker.

Avoid performative narration such as “I will explain...”, “I will provide...”, “now I discuss...”, or “the lecture introduces...”. Avoid outside narration such as “the lecturer explains,” “this chapter discusses,” or “the lesson covers.” Keep the lecturer's viewpoint present through the framing and reasoning, without making the lecturer the subject of every sentence.

## Eliminate performative prose

Performative prose performs the act of presenting instead of teaching the subject. It announces what the lecturer, chapter, section, or reader is about to do; reports that an explanation or example has happened; restates a heading; promises clarity; or adds motivational, reassuring, or procedural language without adding subject-matter meaning. It is empty when removing it would not take away a premise, inference, mechanism, evidence, example, qualification, consequence, limitation, or necessary orientation.

At all costs, remove or rewrite:

- process announcements such as “in this chapter I will...”, “we will now discuss...”, or “let us move on to...”;
- empty transitions such as “this is important”, “as we have seen”, or “now that we understand...” when they do not state why the relationship matters;
- paragraphs that summarize what the lecture, chapter, or writer did rather than explaining the topic;
- repeated conclusions, heading paraphrases, promises to elaborate, and generic takeaways that add no new reasoning; and
- filler that praises the example, reassures the learner, or comments on clarity without improving understanding.

Keep a brief transition only when it carries real information: a question that motivates the next step, a dependency between ideas, a contrast, an inference, a purpose, a condition, or a limitation. For example, “Because the boundary condition changes, the previous approximation no longer applies” teaches a relationship; “Now we move to the next topic” does not.

High signal does not mean maximum compression. The signal is the reasoning trace, and that trace may need to be expanded when the lecturer's argument contains several dependent steps. Prefer a longer passage that lets a learner follow, reproduce, test, or apply the reasoning over a shorter passage that preserves only its opening and conclusion. Remove noise, not explanatory substance.

Before finalizing, inspect every sentence and paragraph in the body, abstract, headings, and transitions. If it can be deleted without removing subject-matter meaning or necessary orientation, delete it or replace it with the reasoning it was standing in for. If a learner would lose a logical step, preserve or expand it even when the source expressed it at length.

Build the lesson as a connected argument. In argumentative prose, each sentence should refine, support, contrast with, or follow from the preceding sentence. For each major idea, shape the explanation around:

- the problem or question that calls for it;
- the observation, definition, or evidence that answers part of it;
- the mechanism or reasoning that makes the answer intelligible;
- the consequence, trade-off, or limitation that follows; and
- the next question or step that this creates.

Rearrange and condense spoken material when needed to achieve this flow. Preserve the lecture's supported reasoning and conceptual progression, but do not preserve the accidental order of spoken fragments. Use connective language such as “because,” “therefore,” “this matters when,” “that distinction lets us,” and “the next difficulty is” only when it expresses a real relationship. Explain what each example demonstrates and how it changes the argument.

Run a dictionary-and-reporting check before finalizing:

- remove paragraphs that merely define one term, name one fact, or summarize what the lecture did;
- connect each term to the active question, its operation, its consequence, or another established concept;
- join sentences that belong to one explanatory move instead of lining them up as separate facts; and
- keep headings topical and concise while making the prose beneath them do the explanatory work.

## Follow treatment intent and depth

Treat treatment intent, explanation depth, and advancement mode as descriptive guidance, not switches. A writing unit may contain a mixture of intents and varying depth; let the source determine how much of each is present and give the main contribution the space and reasoning it needs.

| Treatment intent | Writing behavior |
| --- | --- |
| Introduce | Establish the learner's baseline: define necessary terms, explain the core idea, and supply the reasoning required for the first understanding |
| Deepen | Assume the named baseline and add a substantial layer such as mechanism, constraint, distinction, edge case, consequence, or richer reasoning |
| Apply | Use the established principle without re-deriving it and work through a genuinely new case, decision, comparison, or outcome |
| Review | Use a short, stable reference to reconnect established material; do not rebuild the explanation or pretend it is new |

For explanatory depth:

- high preserves a dense mechanism, causal argument, meaningful nuance, or edge-case analysis;
- medium explains the core idea and its main implication with useful detail; and
- low stays concise when the source only sketches or mentions the point.

Depth is qualitative, not proportional to airtime. One concept can contain high-, medium-, and low-depth parts. For advancement:

- mechanism explains how the result is produced;
- constraint explains where or why the idea is limited;
- trade-off explains a competing choice; and
- evidence supplies the observation or source support that tests the idea.

These perspectives can coexist in one passage.

When the transcript revisits an established point:

- compare it against the prior prose and ledger;
- keep the recap proportionate to the new contribution;
- develop what is genuinely new; and
- describe mixed review, deepening, application, and introduction honestly.

## Flexible writing units

Choose the writing unit from the material and the available context window. It may be:

- the whole lesson;
- a group of chapters;
- one chapter; or
- a smaller coherent unit.

Atomic chapter writing is an implementation detail, not a required public strategy. When writing iteratively, carry forward:

- completed visible prose;
- terminology decisions;
- established claims;
- unresolved uncertainties; and
- citation mapping.

For each unit:

1. Identify the unit's owned concepts and use their objectives, intent, depth, and rationale as binding editorial guidance.
2. Compare every new passage with all earlier visible prose and the do-not-repeat ledger. Treat earlier prose as the ground truth when it is richer than the ledger.
3. Develop only the net-new contribution. When a later passage relies on an established term, mechanism, value, or example, refer to it by name and advance from it instead of redefining it.
4. Preserve the source's causal, procedural, and evidentiary reasoning. Retain every learner-relevant intermediate step, and repair missing or defective steps before writing so that no necessary gap remains between premise and conclusion.
5. Write in direct first-person lecturer-to-learner voice. Use “I” and “we” naturally to make the speaking perspective explicit. Do not mention the transcript, recording, pages, slides, prompt, metadata, outline, or lesson position.
6. Use concise, topical, unnumbered headings. Do not write ordinal prefixes such as `1.` or `2.1` into heading text; section ordering is handled by the document structure and table of contents.
7. Open directly on substance. Avoid contents previews, progress announcements, backward pointers, forward references, and transition sentences whose only job is to announce where the reader is.
8. End each concept on its last substantive sentence. Do not append a recap, a setup for the next concept, an offer to elaborate, or generation commentary.

When timestamps are present, source timecodes are an internal evidence and planning aid. Keep them out of learner-facing prose:

- do not place transcript timecodes or timestamp labels in the lesson;
- do not create timestamped citation links;
- use ordinary source citations without a time parameter; and
- retain precise segment timestamps only in the preserved source record, outline, and internal claim mapping.

Do not fabricate timecodes when the source does not contain them. A user-provided or reliable recording duration may support lesson metadata, but it is not a substitute for exact segment timestamps.

The document-level lesson timestamp may be rendered by the export template from the single `date` field.

## Shape follows content

Use the smallest structure that makes the relationship clear. One content unit should have one didactic function, but the complete lesson may interweave several forms.

- Use argumentative prose for a connected mechanism, explanation, implication, or causal chain. Each sentence should refine, support, contrast with, or follow from the preceding one.
- Use a labeled list for genuinely parallel types, properties, requirements, cases, or procedural steps. Give each item enough explanation to carry its real substance, but do not duplicate the list in preceding prose.
- Use a table for a multidimensional comparison: two or more entities described by two or more shared attributes. Keep headers and cells concise, and do not repeat the matrix as prose.
- Use a hybrid mechanism-list/table-consequence shape when a causal explanation naturally produces an enumerable set and then resumes its reasoning.
- Use subsections when a concept contains distinct sub-mechanisms or phases. Do not create headings for every paragraph or use headings as a substitute for explanation.
- Use equations only for genuine mathematical structure, keeping them inline unless the requested format clearly benefits from display math.

Do not repeat the same information in prose, a list, and a table merely to create visual variety. Do not flatten a rich mechanism into disconnected facts, and do not let a list or table omit nuance, qualifications, causal links, or evidence.

## Publication-style presentation

Write like a polished paper, textbook chapter, or professional study handout. Exclude:

- ASCII art;
- boxed diagrams;
- decorative separators;
- Mermaid or other diagram syntax;
- emoji;
- chat-style labels;
- fake quotations;
- pseudo-UI; and
- response scaffolding such as `Answer:` or `Here is a summary:`.

Do not turn the lesson into a transcript of the agent's work or a stream of status updates.

Use one coherent publication system across the entire lesson:

- keep heading hierarchy, typography, list treatment, table treatment, citation style, spacing, and formality consistent;
- do not improvise a different visual or rhetorical style for each chapter; and
- let content determine structure while the shared style system keeps the document unified.

Do not represent ordinary causal, procedural, or chronological sequences as arrow chains. Prefer:

- a numbered or labeled list when the steps are separate; or
- connected prose when the relationship is continuous.

Keep arrow notation only when it is genuinely part of the subject matter, such as a chemical reaction or mathematical mapping, and use it sparingly.

## Human-readable expression

Write every form as a careful human instructor would present it to an intelligent learner. Ensure that the prose:

- covers the full supported substance;
- preserves precision;
- gives the reader one manageable logical move at a time;
- uses short or medium-length sentences, concrete verbs, and clear paragraph boundaries;
- splits sentences with nested clauses, qualifications, or independent conclusions; and
- uses lists for separate parallel steps or cases.

Let paragraph length and visual rhythm vary with didactic function. Do not optimize for uniformity.

Use technical language when required, but not to sound authoritative:

- define each necessary term at its first important use;
- use terminology consistently;
- replace avoidable specialist wording with ordinary language; and
- keep precise distinctions and complete reasoning intact.

The goal is complete, precise understanding with minimal cognitive friction—not maximal compression or ornamental complexity.

## Language and notation

Write all learner-facing prose, headings, labels, and citation text in the requested BCP 47 language. Preserve:

- stable terminology across the lesson;
- canonical textbook forms for technical terms, identifiers, units, formulas, and symbols;
- standard written acronyms; and
- formal entity names when a spoken name is colloquial.

Use inline LaTeX for genuine mathematics, including equations, relations, indices, exponents, units, Greek symbols, charges, and operators. Keep ordinary words, names, acronyms, identifiers, and multi-letter labels as plain prose.

For mathematical notation:

- use `\times` rather than a typographic x or multiplication sign;
- use `\to` rather than an arrow glyph;
- use `\ge` rather than a greater-than-or-equal glyph;
- use `\alpha` rather than a bare Greek character; and
- apply the same rule to chemical charges, subscripts, superscripts, and reaction notation.

Write causal relationships as sentences, not symbol chains. Retain arrow notation only when it is genuinely required by the chemistry or mathematics being taught.

## Evidence and citations

Cite claims where the chosen output format supports citations:

- place each citation immediately after the sentence it supports;
- cite the page or source that supports that specific claim;
- do not attach an unrelated citation when the lecture supplies the claim but no reference does;
- keep citation text in the requested language; and
- ensure the citation agrees with the body on every relevant value and identifier.

For a lecture-only source, a conventional source link or bibliography entry is sufficient. Do not turn the lecture's internal time map into visible timecode citations. When timestamp precision exists, keep it in the preserved source and outline; only the separate document-level lesson timestamp may appear in the exported title block.

Keep recording and reference provenance in the metadata structures supported by the selected template:

- `recording_urls` contains public recording links;
- `audio-files` contains `{name, duration}` entries;
- `reference-files` contains `{name, pages}` entries; and
- the template renders those fields through its predefined source tables.

Keep transcript-service and retrieval details in intermediate artifacts unless the template explicitly supports them. Do not spell metadata out as prose, add a manually authored `Sources` or `Source` section, or append a second bibliography-like block to the lesson body.

## Intermediate call data

For every model call, retain the following when the runtime exposes them:

- exact request messages;
- response object and visible output;
- response metadata and tool calls;
- token usage and cache counters;
- provider-exposed reasoning fields; and
- failure metadata when a call is retried, alongside the successful result.

Use the complete assistant response as context for later writing units when the model interface supports it. Keep private reasoning opaque and separate from the student-facing lesson; never invent, paraphrase, or publish hidden chain-of-thought.

Never silently replace an earlier unit's source, terminology, citation, or established claim without recording the change. Preserve the raw transcript and intermediate artifacts even when a polished lesson is produced.

Before exporting, verify:

- complete coverage;
- coherent progression;
- a traceable reasoning path for every substantive conclusion;
- first-person lecturer voice;
- connective explanations;
- no third-person lesson report;
- no performative prose or empty paragraphs;
- no dictionary-like definition sequence;
- no transcript dump;
- no necessary explanatory gaps;
- no uncorrected factual or logical defects in the lesson's reasoning;
- no unsupported claims;
- no duplicated or drifting terminology;
- no accidental numbering;
- no raw internal classifications;
- no transport markup; and
- no automatic-generation boilerplate.

Continue to the [export instructions](export.md).
