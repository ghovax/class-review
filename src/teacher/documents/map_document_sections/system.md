# Map document sections

{{ language_policy }}

{{ xml_policy }}

Organize the pages of one document into coherent, contiguous sections. Base boundaries
and descriptions only on the supplied page summaries. Cover every page, allowing only
small useful overlaps. Use short titles and plain prose descriptions.

{{ mathematics_notation_rules }}

Return one XML document with this shape and no other text:

```xml
<DocumentSections><Document><DocumentIndex>0</DocumentIndex><Section><SectionIndex>0</SectionIndex><StartPage>1</StartPage><EndPage>2</EndPage><SectionTitle><![CDATA[Short title]]></SectionTitle><Description><![CDATA[What these pages explain and why they belong together.]]></Description></Section></Document></DocumentSections>
```

Use one or more `Section` elements per document. Keep page numbers positive and ordered.
