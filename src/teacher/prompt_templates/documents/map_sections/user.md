# Document Section Grouping

Group the pages of this document into semantic sections.

---

{{ page_list_markdown }}

---

## Output Format

Output a single XML document, starting with `<DocumentSections>` and ending with `</DocumentSections>`.

Coverage rules:

- Make section page ranges contiguous.
- Allow small overlap between adjacent sections, but keep it minimal.
- Cover every page of the document at least once across all sections, with no gaps.

Include in each section:

- `<StartPage>`: first page number in this section (1-based)
- `<EndPage>`: last page number in this section (1-based, must be >= `StartPage`)
- `<SectionTitle>`: short descriptive title wrapped in CDATA
- `<Description>`: straight-to-the-point prose description wrapped in CDATA. Embed key topics naturally within the flowing, but straight-to-the-point narrative—do not list them separately.

```xml
<DocumentSections>
  <Section>
    <StartPage>
      […]
    </StartPage>
    <EndPage>
      […]
    </EndPage>
    <SectionTitle>
      <![CDATA[Section Title Here]]>
    </SectionTitle>
    <Description>
      <![CDATA[Straight-to-the-point prose precise and accurate description here, with key topics mentioned naturally within the narrative. All written in one unique line.]]>
    </Description>
  </Section>
  <Section>
    <StartPage>
      […]
    </StartPage>
    <EndPage>
      […]
    </EndPage>
    <SectionTitle>
      <![CDATA[Another Section]]>
    </SectionTitle>
    <Description>
      <![CDATA[Straight-to-the-point prose precise and accurate description here.]]>
    </Description>
  </Section>
</DocumentSections>
```
