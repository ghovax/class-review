# Write the lesson

Read the outline, the transcript excerpts owned by the current writing unit, the relevant references, and the accumulated visible lesson context. Write a coherent review class in the requested language. The learner should hear the lecturer explaining the subject directly, not read a description of the source material, the lesson, or the generation process.

Keep the learner-facing artifact as ordinary Markdown with YAML frontmatter and ordinary citations. Do not emit XML, transport envelopes, internal records, or generation-process commentary in the lesson. Preserve the raw transcript, outline, references, model-call records, and prior lesson versions separately from the visible prose.

## Source fidelity

Use the transcript as the authority for:

- substance;
- order;
- reasoning; and
- explanatory depth.

Use references only to clarify or verify a point already supported by the lecture. They do not authorize new scope. When retaining a claim, preserve:

- exact values and units;
- signs;
- identifiers;
- distinctions; and
- named entities.

Before writing, resolve transcript/reference conflicts so the body claim and its citation agree on the same value.

Normalize only when the intended reading is supported by the surrounding argument:

- obvious transcription defects;
- duplicated fragments;
- malformed numerals; and
- surface terminology.

Do not assign one component's properties to another, broaden a sub-case into a universal law, or turn a deliberate unknown into a fact.

## Lecturer voice and connective exposition

Write every learner-facing paragraph, including the abstract, from the lecturer's perspective:

- use first-person singular for choices, explanations, observations, and conclusions;
- use first-person plural when the lecturer and learner reason through an implication together;
- address the learner directly with “you” for instructions or invitations; and
- maintain first-person perspective instead of reverting to impersonal textbook summary.

Use constructions such as “I begin with...”, “I use this example to show...”, “I cannot infer...”, and “We can now see why...”. Avoid outside narration such as “the lecture introduces,” “the lecturer explains,” “this chapter discusses,” or “the lesson covers.”

Build the lesson as a chain of connected explanations. For each major idea, show:

- the problem or question that calls for it;
- the observation or definition that answers part of it;
- the mechanism or reasoning that makes the answer intelligible;
- the consequence or limitation that follows; and
- the next question or step it creates.

Use connective language such as “because,” “therefore,” “this matters when,” “that distinction lets us,” and “the next difficulty is” when it expresses real reasoning. Explain what each example demonstrates and how it changes the argument. When using a table or list, introduce its organizing principle and interpret the result in surrounding prose.

Run a dictionary-and-reporting check before finalizing:

- remove paragraphs that merely define one term, name one fact, or summarize what the lecture did;
- relate each term to the active question, its operation, its consequence, or another established concept; and
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
4. Preserve the source's causal, procedural, and evidentiary reasoning. Do not compress a chain until its conclusion becomes an unsupported fact.
5. Write in direct first-person lecturer-to-learner voice. Use “I” and “we” naturally to make the speaking perspective explicit. Do not mention the transcript, recording, pages, slides, prompt, metadata, outline, or lesson position.
6. Use concise, topical, unnumbered headings. Do not write ordinal prefixes such as `1.` or `2.1` into heading text; section ordering is handled by the document structure and table of contents.
7. Open directly on substance. Avoid contents previews, progress announcements, backward pointers, forward references, and transition sentences whose only job is to announce where the reader is.
8. End each concept on its last substantive sentence. Do not append a recap, a setup for the next concept, an offer to elaborate, or generation commentary.

Timestamped source segments are an internal evidence and planning aid. Keep them out of learner-facing prose:

- do not place transcript timecodes or timestamp labels in the lesson;
- do not create timestamped citation links;
- use ordinary source citations without a time parameter; and
- retain precise segment timestamps only in the normalized source, outline, and internal claim mapping.

The document-level lesson timestamp may be rendered by the export template from the single `date` field.

## Choose the presentation form

No presentation form has priority by default. Choose the form that makes the source's structure clearest while preserving every substantive detail. A single concept may move from explanatory prose to a list of cases, then to a comparison table, and back to prose that interprets the comparison.

Choose the form according to the information:

- use argumentative prose for a connected mechanism, explanation, implication, or causal chain;
- use a labeled list for genuinely parallel types, properties, requirements, cases, or procedural steps;
- use a table for a multidimensional comparison between entities with shared attributes;
- use equations or other formal notation when the subject requires them; and
- use subsections when a concept contains distinct sub-mechanisms or phases.

One content unit should have one didactic function, but the complete lesson may interweave several forms. Do not repeat the same information in prose, a list, and a table merely to create visual variety. Do not flatten a rich mechanism into prose when another form would make its parts clearer, and do not let lists or tables omit nuance, qualifications, causal links, or evidence.

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

For a lecture-only source, a conventional source link or bibliography entry is sufficient. Do not turn the lecture's internal time map into visible timecode citations. Timestamp precision belongs in the preserved source and outline; only the separate document-level lesson timestamp may appear in the exported title block.

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

Never silently replace an earlier unit's source, terminology, citation, or established claim without recording the change. Preserve the raw transcript and intermediate artifacts even when a normalized lesson is produced.

Before exporting, verify:

- complete coverage;
- coherent progression;
- first-person lecturer voice;
- connective explanations;
- no third-person lesson report;
- no dictionary-like definition sequence;
- no transcript dump;
- no unsupported claims;
- no duplicated or drifting terminology;
- no accidental numbering;
- no raw internal classifications;
- no transport markup; and
- no automatic-generation boilerplate.

Continue to the [export instructions](export.md).
