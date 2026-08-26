# Section Explanation

Write one cohesive Markdown explanation that aggregates the pages of this single section into one continuous narrative.

## Section Metadata

- **Document:** `{{ section.document_file_name }}` (documentIndex `{{ section.document_index }}`)
- **Section:** `{{ section.section_index }}`—*{{ section.section_title }}*
- **Page Range:** {{ section.start_page }} – {{ section.end_page }}
- **Section Description:** {{ section.section_description }}

---

## Section Pages

{{ section.pages_markdown }}

---

## Output Format

Output one block of plain Markdown—the cohesive explanation of this entire section. Omit XML, code fences, preamble, and headings of any level. Use paragraphs by default. Use bulleted lists only where the source itself enumerates discrete items. Mark the first substantive mention of each key term with Markdown bold.
