# Chapter request

Language: {{ language }}
Chapter {{ chapter.index }} of {{ chapter.total }}
Time: {{ chapter.start_seconds }}s to {{ chapter.end_seconds }}s
Concepts in this chapter: {{ chapter.concept_count }}
Earlier chapters: {{ chapter.previous_chapter_count }}
Earlier concepts: {{ chapter.previous_concept_count }}
Transcript groups: {{ transcript.group_count }}

{{ mathematics_notation_rules }}

## Chapter context

{{ chapter.chapter_context_xml }}

## Concepts to develop

{{ chapter.covered_concepts_xml }}

## Avoid repetition

{{ chapter.do_not_repeat_ledger_xml }}

## Document pages

{{ chapter.document_pages_markdown }}

## Transcript groups

{{ transcript.groups_xml }}

Write this chapter in {{ language }}. Use every relevant group, preserve the source's reasoning, and keep new material distinct from the repetition ledger. Use the notation rules supplied above where mathematical notation is genuinely needed.
