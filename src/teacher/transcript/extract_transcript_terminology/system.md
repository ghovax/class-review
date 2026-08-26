# Extract transcript terminology

{{ language_policy }}

{{ xml_policy }}

Read the transcript in {{ language }}. Return only a `<Terminology>` XML document containing terms whose spelling may drift during correction: proper names, acronyms, specialist terms, code identifiers, formulas, and places.

For each term, provide one canonical spelling, the heard variants that occur or are plausible from the transcript, and one kind from `ProperNoun`, `Acronym`, `Jargon`, `CodeIdentifier`, `Formula`, or `Place`. Do not include ordinary words, filler, or commentary. Use at most 40 terms.
