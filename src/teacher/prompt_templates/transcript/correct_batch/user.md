## Transcript Correction Batch {{ index }}

Correct one batch of transcribed lecture segments and return a single `<CorrectedTranscript>` XML document. Re-segment the batch's content into fine, sub-topic `<Segment>` units (one coherent idea each), every unit anchored to a true `<Timestamp>` drawn from the source.

**Critical Language Directive:** Treat **{{ audio_language }}** (BCP47) as the target language for every `<Content>`.

**Batch context:**

- **Batch index:** {{ index }} (0-based)
- **Source Time Range:** {{ batch_start_seconds }}s to {{ batch_end_seconds }}s — every `<Timestamp>` you emit must fall inside this range and be non-decreasing across the sequence.

---

## Canonical Glossary

Apply these canonical spellings consistently across every `<Content>`. An empty `<Glossary></Glossary>` means none were found — rely on your own judgement.

```xml
{{ glossary_xml }}
```

---

## Source Segments

Each `<Source>` carries the true start time `<Beginning>` (seconds) and the raw `<Spoken>` fragment. Re-organize this content into meaning-based units; set each unit's `<Timestamp>` to the `<Beginning>` of the source fragment where that unit's content starts.

```xml
{{ source_segments_xml }}
```

---

## Output

Return exactly one well-formed `<CorrectedTranscript>` and nothing else:

```xml
<CorrectedTranscript>
  <Segment>
    <Timestamp>{{ batch_start_seconds }}</Timestamp>
    <Content><![CDATA[First sub-topic, rewritten as one fluent academic paragraph that preserves the full explanation.]]></Content>
  </Segment>
  <Segment>
    <Timestamp>[Next sub-topic start timestamp.]</Timestamp>
    <Content><![CDATA[Next sub-topic, in chronological order.]]></Content>
  </Segment>
</CorrectedTranscript>
```

- **Single Prose Paragraph Per Segment:** One `<Content>` paragraph per `<Segment>` — no lists, tables, headings, or code blocks inside it.
- **Preserve the Full Reasoning:** Keep all reasoning and examples; remove only filler, false starts, deixis, and classroom logistics.
- **Prose-Only Output:** Zero mathematical notation — no LaTeX, no `$…$`, no Unicode math glyphs; spell every symbol, operator, and formula out in words exactly as the professor said them. Never use a "?" in the output.
