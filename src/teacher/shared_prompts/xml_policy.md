Use XML only as a compact transport format. Return one root element, no prose, no code
fence, and no indentation or line breaks between tags. Keep text in `CDATA` when it may
contain markup, symbols, or angle brackets. Use the exact tag names requested, repeat a
tag for a list, and omit optional empty elements. Example:
`<Root><Item><Name><![CDATA[Example]]></Name><Value>1</Value></Item></Root>`.
