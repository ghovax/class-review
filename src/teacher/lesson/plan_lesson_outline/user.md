# Lesson outline request

| Field | Value |
| --- | --- |
| Language | {{ language }} |
| Lesson time | {{ metadata.lesson_start_seconds }}s to {{ metadata.lesson_end_seconds }}s |
| Lesson duration | {{ metadata.lesson_duration_seconds }}s |
| Documents | {{ metadata.document_count }} |

## Document explanations

{{ section_explanations_xml }}

## Document section map

{{ document_section_map_xml }}

## Corrected transcript

{{ transcript_segments_xml }}

Create the outline using only this material. Keep concept spans within the transcript, cover the entire timeline, and use section indices rather than page numbers in `DocumentSpan`.
