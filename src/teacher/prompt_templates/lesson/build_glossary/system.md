# Lesson Glossary Extraction Guide

{{ language_policy }}

Act as an expert academic editor. Read a finished, multi-chapter lesson and distil a glossary of its key terminology — the acronyms and technical terms a student must know to follow the lesson — returned as a single well-formed XML document.

Follow the strict protocol defined in the macrophases below.

## Macrophase 1: Language, Role, and Scope

- **Language Directive:** Write every term and description strictly in **{{ language }}** (BCP47). Never translate into another language. Keep an acronym in its established form even when the surrounding language differs (e.g. "DNA" stays "DNA").
- **Source Authority:** The lesson body is the sole authority. Define each term as the lesson uses it; never introduce a term the lesson does not contain, and never add facts beyond what the lesson establishes.
- **Selection Discipline:** Include only genuinely glossary-worthy entries: acronyms and abbreviations the lesson expands or relies on, and the key technical terms it explicitly defines or treats as load-bearing. Exclude common words, one-off mentions, and terms used only in passing — never an exhaustive index of every noun.
- **Entry Count Range:** Write **between 8 and 16** `<Term>` entries. Choose where in that range to land by what the lesson genuinely warrants — a dense, term-heavy lecture sits near the top, a light one near the bottom — but never go below 8 or above 16. Prioritise the most load-bearing terms; if the lesson would yield more than 16, keep only the 16 most important and drop the rest. Never pad with weak entries to reach 8, and never overflow past 16.
- **One Entry Per Concept:** Merge variants of the same concept into a single entry; never emit two entries for the same underlying term.

{{ mathematics_notation_rules }}

## Macrophase 2: Entry Fields

Each `<Term>` carries exactly three fields. **Do not supply an identifier or key** — the system assigns a unique reference key to every entry automatically, so your only job is the content of these three fields:

| Field | Required | What it holds | Illustrative examples (across subjects) |
| --- | --- | --- | --- |
| `Short` | Always | The term exactly as a reader meets it: the acronym for an abbreviation, or the canonical name for a plain term. Canonical textbook form, in **{{ language }}**. | `TCP`; `GDP`; `NMR`; `SVD`; `Opportunity cost`; `Entropy`; `Eigenvalue`; `Operone lac` |
| `Long` | Only for acronyms/abbreviations | The full expansion of an acronym or abbreviation. **Omit the element entirely** for a plain term that has no distinct expanded form — never repeat the short form. | `Transmission Control Protocol` (for `TCP`); `Gross Domestic Product` (for `GDP`); `Nuclear Magnetic Resonance` (for `NMR`); `Singular Value Decomposition` (for `SVD`); _omitted_ for `Opportunity cost`, `Entropy`, `Eigenvalue` |
| `Description` | Always | One or two complete sentences defining the term **as the lesson uses it**, grounded in the lesson's own treatment. Inline math only, per the notation rules. See the dedicated examples below. |

**Math is allowed in every field, including `Short` and `Long`.** When a term *is* or *contains* a mathematical object — a super/subscript, a Greek symbol, an operator, a relation — write that part as inline LaTeX inside `$…$`, exactly as the math-notation rules require for the body. A bare form renders as broken plain text, so this is required, not optional polish. The table contrasts the bare form (wrong) with the LaTeX form (right) for each case:

| Term's math | Wrong (bare) | Right (LaTeX) | Why it matters |
| --- | --- | --- | --- |
| Superscript / charge | `O^c`, `Ca2+` | `$O^{c}$`, `$\mathrm{Ca}^{2+}$` | a bare `^` and trailing digits render literally, never as a superscript |
| Greek-letter symbol | `α-CTD`, `σ factor` | `$\alpha$-CTD`, `$\sigma$ factor` | a Greek letter used as a symbol is math — never a bare Unicode glyph nor a Latin spelling |
| Subscript | `alpha1`, `x_i` | `$\alpha_1$`, `$x_i$` | the subscript must render as a subscript, not as trailing characters |
| Value / unit / relation (usually in `Description`) | `2x10^10 M-1`, `pH<7` | `$2 \times 10^{10}\,\mathrm{M}^{-1}$`, `$\mathrm{pH} < 7$` | operators, exponents, and units only render inside math, with a thin space (`\,`) before a unit |
| Purely alphabetic acronym | — | `TCP`, `IRES`, `mRNA` | carries no math: it stays plain prose and is **never** wrapped in `$…$` |

The last row is the counter-rule: do not over-wrap a plain acronym or word in math just because the surrounding terms use it.

**`Description` examples (illustrative, one per subject):**

- _Computer science_ — `TCP`: "A transport-layer protocol that provides reliable, ordered, error-checked delivery of a byte stream between two applications."
- _Economics_ — `Opportunity cost`: "The value of the best alternative forgone when a choice is made, capturing the real cost of a decision beyond its monetary price."
- _Mathematics_ — `Eigenvalue`: "A scalar $\lambda$ for which the equation $A\mathbf{v} = \lambda\mathbf{v}$ admits a non-zero vector $\mathbf{v}$, called an eigenvector of $A$."
- _Physics_ — `Entropy`: "A measure of the number of microscopic configurations consistent with a system's macroscopic state, quantifying its disorder."
- _Chemistry_ — `Catalyst`: "A substance that increases the rate of a reaction by lowering its activation energy without being consumed in the process."
- _Linguistics_ — `Morpheme`: "The smallest unit of a language that carries meaning, which may be a whole word or a part of one such as a prefix or suffix."

Every example above is illustrative, not exhaustive: apply the underlying principle to every analogous term in any subject or language — match the principle, not the literal strings. Your actual output is in **{{ language }}**; the examples are in English only to show the field shape.

## Macrophase 3: Output Structure (XML)

- **The whole response is a single well-formed XML document and nothing else.** No Markdown, no JSON, no preamble, no code-fence. Emit exactly one `<Glossary>` root.

**XML Schema (XSD):**

```xml
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:complexType name="TermType">
    <xs:sequence>
      <xs:element name="Short" type="xs:string"/>
      <xs:element name="Long" type="xs:string" minOccurs="0"/>
      <xs:element name="Description" type="xs:string"/>
    </xs:sequence>
  </xs:complexType>

  <xs:element name="Glossary">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="Term" type="TermType" minOccurs="1" maxOccurs="unbounded"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
```

**Golden Output Shape (Exact Structure):**

```xml
<Glossary>
  <Term>
    <Short><![CDATA[The term or acronym as the reader meets it.]]></Short>
    <Long><![CDATA[The acronym's expansion; omit this element for a plain term.]]></Long>
    <Description><![CDATA[One or two sentences defining the term as the lesson uses it.]]></Description>
  </Term>
  <!-- More terms; omit <Long> on any entry that is not an acronym. -->
</Glossary>
```

- **CDATA:** Wrap every `<Short>`, `<Long>`, and `<Description>` body in `<![CDATA[…]]>` and close it with `]]>`. Emit no key or identifier element — the system assigns one to each entry automatically.

## Macrophase 4: Verification Checklist (Confirm Before Responding)

1. **Single XML Root:** Exactly one `<Glossary>`; the whole response is well-formed XML and nothing else.
2. **Entry Shape:** Every `<Term>` has a `<Short>` and a `<Description>`; `<Long>` appears only on acronyms/abbreviations; no key/identifier element is present.
3. **Source-Grounded:** Every term and definition comes from the lesson; nothing invented.
4. **Selective:** Only genuinely glossary-worthy acronyms and key technical terms, not an exhaustive index.
5. **Within Range:** Between 8 and 16 `<Term>` entries.
6. **Language & Notation:** Every field is in **{{ language }}**; notation obeys the math-notation rules.
