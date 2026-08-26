# Write one lesson chapter

{{ language_policy }}

{{ xml_policy }}

Write chapter {{ chapter.index }} of {{ chapter.total }} in {{ language }}. Use the transcript excerpts as the primary source and use document pages only for the concepts that name them. Explain the reasoning, evidence, examples, and limitations present in the material. Follow each concept's intent and depth.

Avoid repeating material already covered by earlier chapters or earlier concepts. Use prose for connected reasoning, lists for real parallel items, and tables for genuine comparisons. Keep the chapter readable and do not add unsupported claims.

{{ mathematics_notation_rules }}

Return Markdown with an optional level-one title followed by the chapter body. A source citation is an inline XML block in this exact shape, placed after the sentence it supports:

```xml
<Citation><DocumentIndex>0</DocumentIndex><Page>1</Page><Content><![CDATA[Claim supported by this page.]]></Content></Citation>
```

Do not add a bibliography or commentary outside the chapter.
