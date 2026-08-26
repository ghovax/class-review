# Glossary request

| Field | Value |
| --- | --- |
| Language | {{ language }} |
| Lesson title | {{ lesson_title }} |

## Completed lesson

{{ lesson_markdown }}

Return only:

```xml
<Glossary><Term><Short><![CDATA[Term as used in the lesson]]></Short><Long><![CDATA[Expansion for an acronym]]></Long><Description><![CDATA[Short, useful definition]]></Description></Term></Glossary>
```

Omit `Long` for ordinary terms and omit weak or repeated entries.
