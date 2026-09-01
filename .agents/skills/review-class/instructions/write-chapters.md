# Write the lesson

Read the outline, owned transcript excerpts, references, and the applicable macro-classification notes. Write a coherent review class in the requested language. The lesson should teach the material directly; it should not mention prompts, agents, internal classifications, transcripts, or behind-the-scenes processing.

## Flexible writing units

Choose the writing unit from the material and the available context window. You may write one complete lesson, a group of chapters, or individual chapters. Atomic chapter writing is an implementation choice, not a required public strategy. When writing in multiple iterations, carry forward the completed visible prose, established claims, terminology decisions, unresolved uncertainties, and citation mapping.

For each unit:

1. Read only the source excerpts and references owned by that unit, plus the accumulated visible lesson context that must remain consistent.
2. Develop the new contribution at the depth indicated by the outline; compress already-established material to a brief reference by name.
3. Preserve causal and procedural reasoning instead of reducing the source to disconnected conclusions.
4. Use prose for connected reasoning, lists for genuinely parallel items, tables for real comparisons, and equations only where mathematical structure is necessary.
5. Keep headings topical and let the content determine whether subsections are useful. Do not add automatic numbering merely because a renderer can add it.
6. Cite claims with the ordinary citation syntax supported by the selected Markdown/Pandoc workflow. Put each citation next to the claim it supports and keep the cited source, page, and claim aligned.

Do not paste the entire source transcript into the lesson. The lesson contains the teaching derived from it, not a transcript dump. Do not add a bibliography unless the requested output needs one. Do not add the automatic-notes disclaimer or an equivalent sentence.

## Intermediate call data

When using a model, retain the exact request messages, response object, visible output, response metadata, tool calls, token usage, cache counters, and provider-exposed reasoning fields in the run's intermediate record. Use the complete assistant response as context for later units when the model interface supports it. If a provider exposes hidden reasoning, keep it opaque and separate from the student-facing lesson; never invent, paraphrase, or publish private chain-of-thought.

If a unit fails and is retried, retain the successful result and the failure metadata. A later unit must never silently replace an earlier unit's source, terminology, or citations without recording the change.

Before exporting, validate that the lesson has no source transcript dump, no unsupported claims, no duplicate language fields, no raw internal classification, no XML, and no forbidden automatic-generation disclaimer. Then continue to [export.md](export.md).
