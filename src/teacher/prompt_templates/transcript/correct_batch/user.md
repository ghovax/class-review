# Transcript batch {{ index }}

Language: {{ audio_language }}
Source time range: {{ batch_start_seconds }}s to {{ batch_end_seconds }}s

## Canonical terminology

{{ glossary_xml }}

## Source segments

{{ source_segments_xml }}

Return only this XML shape, with one paragraph per segment:

```xml
<CorrectedTranscript>
  <Segment>
    <Timestamp>{{ batch_start_seconds }}</Timestamp>
    <Content><![CDATA[Clean prose for one coherent topic.]]></Content>
  </Segment>
</CorrectedTranscript>
```

Keep all substantive reasoning, use source timestamps, and write prose rather than notation or symbol chains.
