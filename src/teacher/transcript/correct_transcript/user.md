# Transcript correction

| Field | Value |
| --- | --- |
| Language | {{ language }} |
| Source time range | {{ start_seconds }}s to {{ end_seconds }}s |

## Canonical terminology

{{ terminology_xml }}

## Source segments

{{ transcript_xml }}

Return only this XML shape, with one paragraph per segment:

```xml
<CorrectedTranscript><Segment><Timestamp>{{ start_seconds }}</Timestamp><Content><![CDATA[Clean prose for one coherent topic.]]></Content></Segment></CorrectedTranscript>
```

Keep all substantive reasoning, use source timestamps, and write prose rather than notation or symbol chains.
