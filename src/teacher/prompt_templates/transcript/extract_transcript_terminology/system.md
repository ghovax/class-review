# Find transcript terms

{{ language_policy }}

Read the full raw transcript in {{ audio_language }}. Return only a `<Terminology>` XML document containing terms whose spelling may drift between correction passes: proper names, acronyms, specialist terms, code identifiers, formulas, and places.

For each term, provide one canonical spelling, the heard variants that occur or are plausible from the transcript, and one kind from `ProperNoun`, `Acronym`, `Jargon`, `CodeIdentifier`, `Formula`, or `Place`. Do not include ordinary words, filler, or commentary. Use at most 40 terms.
