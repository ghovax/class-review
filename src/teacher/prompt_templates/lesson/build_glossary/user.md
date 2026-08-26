# Lesson Glossary Request

Distil the glossary for the finished lesson below and return a single `<Glossary>` XML document and nothing else.

**Language:** {{ language }} (BCP47) — every `<Short>`, `<Long>`, and `<Description>` in this language.

---

## Lesson

**Title:** {{ lesson_title }}

{{ lesson_markdown }}

---

## Output

- Return exactly one well-formed `<Glossary>` and nothing else — no Markdown, no commentary, no code-fence.
- Include only genuinely glossary-worthy acronyms and key technical terms the lesson defines or relies on; merge variants, exclude passing mentions.
- Emit only `<Short>`, optional `<Long>` (acronyms only), and `<Description>` per term — no key or identifier element; omit `<Long>` on any entry that is not an acronym.
- Ground every definition in the lesson; invent nothing. Inline math only; obey the math-notation rules.
