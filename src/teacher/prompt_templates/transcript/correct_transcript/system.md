# Correct transcript material

{{ language_policy }}

Rewrite the supplied transcript material in {{ language }} as fluent academic prose. Preserve every substantive explanation, example, qualification, and causal connection. Remove filler, false starts, classroom logistics, and references that depend on seeing a slide. Keep the meaning and technical terms; do not summarize.

Return only one `<CorrectedTranscript>` XML document. Each `Segment` has a non-negative `Timestamp` taken from a source beginning and one paragraph of CDATA `Content`. Timestamps must be non-decreasing and within the supplied time range. Split at meaningful topic boundaries rather than copying arbitrary ASR cuts. Do not put headings, lists, tables, or mathematical markup inside `Content`.
