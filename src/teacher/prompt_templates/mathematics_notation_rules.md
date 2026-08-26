## The Critical Rule: Use Math Only Where Genuinely Required

**General Rule:** Math delimiters (`$…$`) and `\mathrm{…}` exist for genuine mathematical objects only: variables with indices, units with values, equations, relations, and symbols (Greek letters, charged species). They are NOT a font switch for making ordinary text look "technical" or render upright. Wrapping a plain word, name, acronym, or literal code in `$…$`, `\mathrm{}`, or italics is the single most common and most damaging defect in this output. Use math only where it is genuinely required; everywhere else, write plain prose.

> **ABSOLUTE RULE — never a raw Unicode/UTF-8 math glyph.** Under **no condition** may a raw Unicode glyph for a mathematical symbol appear anywhere in the output — not in prose, headings, list items, table cells, or citation CDATA. This covers Greek symbols (`α`, `β`, `σ`, `μ`, `Δ`, `Ω`), super/subscripts (`²`, `³`, `₁`, `₂`, `⁺`, `⁻`), operators and relations (`×`, `÷`, `±`, `−`, `≈`, `≠`, `≤`, `≥`, `→`, `←`, `↔`, `°`, `′`), and set/logic/calculus glyphs (`∑`, `∫`, `∈`, `√`, `∞`, `∂`, `∇`). Every one is written **only** as its LaTeX command inside `$…$` — `$\alpha$`, `$x^2$`, `$n_1$`, `$\geq$`, `$45^\circ$`, `$\sum$`. A raw math glyph renders at the wrong baseline, breaks spacing, and corrupts copy-paste; it is a defect with no acceptable instance. The only Unicode letters that belong in the prose are the ordinary alphabet of the **target language** — and the sole Greek carve-out is a real Greek *word* (or a Greek-language lesson), never a Greek *symbol* such as `α-helix` or `σ factor`.

**The One Decision Test (apply to every token before wrapping anything):** mentally strip the `$…$` and any `\mathrm{}`. If what remains is a grammatical prose token (a word, an acronym, a name, a code, a sequence) that reads identically as plain text, then it was never math: write it as plain prose, with no delimiters, no `\mathrm{}`, and no italics. A token earns math delimiters only if it carries real mathematical substructure (a subscript index, a superscript exponent or charge) OR participates in a real expression (an operator, an equality, an inequality).

**This test is supreme and governs every character — chemical symbols, codes, and names alike.** A token is math by its **function in the sentence, never by its category**, and where any specific rule below seems to conflict with this test, the test wins (the tables are illustrations of it, not independent absolutes). **One categorical rule the test does not relax: Greek letters used as symbols.** A Greek letter standing for a symbol — a variable, an index, or a symbolic name-prefix — is always math and always wrapped in `$…$` (`$\alpha_1$` receptor, `$\sigma = 2.3$`, `$\alpha$`-helix, `$\sigma$` factor), even when the surrounding token reads as a name, because a bare Unicode Greek glyph renders at the wrong baseline and corrupts copy-paste. The strip-and-read test does **not** exempt a Greek symbol. The **only** time a Greek letter stays bare is when it is genuinely a letter of **Greek-language text** — a Greek word, an etymology or quotation, or a lesson whose target language is Greek — where the letters spell actual words and are ordinary prose.

### Plain Prose, Never Math (The Recurring Abuse To Eliminate)

**General Rule:** Words, names, acronyms, and literal codes are prose in every field; they render correctly as plain text. The "Wrong" column below shows the wide range of ways this gets abused; never produce any of them.

| Token kind | Wrong (a wide array of abuses, across fields) | Write exactly as |
| --- | --- | --- |
| Literal codes & sequences | `$GTGTG$`, `$\mathrm{GTGTG}$`, `*GTGTG*` (DNA); `$\mathrm{AAPL}$` (stock ticker); `$\mathrm{Nf3}$` (chess move); `$\mathrm{EAX}$` (CPU register) | `GTGTG`, `AAPL`, `Nf3` |
| Gene / operon / product / model names | `$\mathrm{lac}$`, `$lac$`, `$\mathrm{lacZYA}$` (biology); `$\mathrm{quicksort}$`, `$\mathrm{MapReduce}$` (computing) | `lac`, `lacZYA`, `quicksort` |
| Theorem / law / method names | `$Nash$` (economics); `$\mathrm{Navier-Stokes}$` (physics); `$\mathrm{Pythagorean}$` (math) | `Nash equilibrium`, `Navier-Stokes`, `Pythagorean theorem` |
| Acronyms & initialisms | `$\mathrm{cAMP}$`, `$\mathrm{NMDA}$`, `$\mathrm{GABA}$`, `$\mathrm{AMPA}$`, `$\mathrm{GAD}$`, `$\mathrm{mRNA}$` (biology); `$\mathrm{HTTP}$`, `$\mathrm{SQL}$`, `$\mathrm{TCP}$` (computing); `$\mathrm{GDP}$`, `$\mathrm{CPI}$` (economics); `$\mathrm{RMSE}$`, `$\mathrm{OLS}$` (statistics) | `cAMP`, `NMDA`, `GABA`, `mRNA`, `HTTP`, `GDP`, `RMSE` |
| Multi-word terms & motifs | `$\mathrm{helix-turn-helix}$`, `$\mathrm{up}$` (biology); `$\mathrm{divide and conquer}$` (computing); `$\mathrm{supply and demand}$` (economics) | `helix-turn-helix`, `up element`, `divide and conquer` |
| Word with a present/absent qualifier | `$+\mathrm{inducer}$`, `$-\mathrm{inducer}$` (biology); `$-\mathrm{cache}$` (computing); `$+\mathrm{tax}$` (finance) | `with inducer`, `without inducer`, `(+ cache)`, `pre-tax` |

**Rule Of Thumb:** if you could read the token aloud as a word, or spell it out letter by letter as a code, it is prose. `\mathrm{}` is not "the upright font"; it exists solely to keep a genuine math token (a unit label, or a chemical symbol that bears a charge) upright INSIDE a larger math expression. A standalone `$\mathrm{Word}$` carrying no subscript, superscript, or operator is always wrong. A leading `+` or `-` used as a present/absent qualifier does not make a word math: keep both the sign and the word in prose.

**Never Place Math Inside an Inline-Code Span:** Backticks render their contents verbatim in monospace, so a `$…$` delimiter written inside backticks prints the literal dollar signs instead of rendering the math — `` `$5'$ TGTA $3'$` `` is always wrong and displays `$5'$` on screen. Never wrap a `$…$` math delimiter inside a backtick code span.

### Genuine Math, Do Use Delimiters

**General Rule:** A token is math when it carries mathematical substructure (an index, exponent, or charge) or sits in a relation or expression. Wrap the smallest complete math construct in `$…$`.

| Construct | Write as (across fields) | Why it is math |
| --- | --- | --- |
| Variable with an index | `$x_1$`, `$a_n$` (math); `$\beta_2$` (regression coefficient / receptor subtype); `$v_0$` (initial velocity) | the subscript is math substructure |
| Element or ion bearing a charge | `$\mathrm{Na}^+$`, `$\mathrm{Ca}^{2+}$`, `$\mathrm{Cl}^-$` (chemistry) | the charge superscript is real; `\mathrm{}` only keeps the symbol upright inside it |
| Identifier with a sub/superscript label | `$K_a$` (chemistry), `$R^2$` (statistics), `$\mathrm{GABA}_A$` (neuroscience receptor subtype), `$V_\mathrm{max}$` (kinetics / economics), `$F_\mathrm{net}$` (physics) | the index/exponent is the math; `\mathrm{}` wraps only the letters it attaches to |
| Greek letter used as a symbol | `$\alpha$` (significance level / receptor), `$\sigma$` (standard deviation / stress), `$\lambda$` (wavelength / eigenvalue), `$\mu$` (mean / friction) | a symbol, not a word |
| Value with a unit | `$30\,\mathrm{kb}$` (biology), `$9.8\,\mathrm{m/s}^2$` (physics), `$3.2\,\mathrm{GHz}$` (computing), `$-70\,\mathrm{mV}$` (electrophysiology) | a numeric quantity with a unit (thin space `\,`) |
| Angle or degree | `$45^\circ$`, `$90^\circ$` | the number stays bare in math with the degree; never `$\mathrm{90}^\circ$` |
| Power or scientific notation | `$10^{13}$`, `$2 \times 10^6$`, `$2^{32}$` (computing), `$10^{-4}$` | exponent / operator |
| Equation, relation, inequality | `$E = mc^2$` (physics), `$K_a = 10^{13}$` (chemistry), `$R^2 > 0.9$` (statistics), `$n \ge 3$` (math), `$\mathrm{pH} < 7$` (chemistry) | a mathematical relation |

**The Contrast That Trips People Up:** a lone number is prose (`11 nucleotides`, `chapter 3`, `404 responses`, `50 employees`), but a number bearing a unit, degree, or exponent is math (`$11\,\mathrm{nt}$`, `$9.8\,\mathrm{m/s}^2$`, `$45^\circ$`). When a numeral is genuinely inside a math expression it is written bare in math (`$90^\circ$`), never wrapped in `\mathrm{}` (`$\mathrm{90}^\circ$` is wrong: `\mathrm{}` is for letters kept upright, not for digits).

**The Same-Root Trap (The Over-Wrap That Leaks Most):** when one entity appears BOTH as a bare name and with a genuine sub/superscript label, only the *labeled* form is math — the bare form stays plain prose, and writing the labeled form must never pull the bare form into `$…$`. Decide each occurrence independently with the strip-and-read test; the same root can be prose in one sentence and math in the next. Across fields:

| Bare root — plain prose | Same root, labeled — genuine math | Why they split |
| --- | --- | --- |
| the neurotransmitter `GABA`; the receptor `NMDA` (neuroscience) | the receptor subtype `$\mathrm{GABA}_A$`, `$\mathrm{GABA}_B$` | only the subtype subscript is real substructure |
| the `beta` coefficient written out in prose (statistics) | the coefficient `$\beta_2$` | a spelled-out word vs an indexed symbol |
| the enzyme `GAD`, the protein `PLC` (biology) | the constant `$K_a$`, the rate `$k_\mathrm{cat}$` | a name has no substructure; a labeled symbol does |
| the element `calcium` / `Ca` inside a name (chemistry) | the ion `$\mathrm{Ca}^{2+}$` | only the charge is math |

Having correctly written `$\mathrm{GABA}_A$` once, do **not** then write `$\mathrm{GABA}$` for the bare acronym a sentence later: that is the single most common over-wrap, because the labeled form "feels" like it should propagate. It must not.

### Bare Math Left In Prose (The Opposite Defect)

**General Rule:** The mirror image of over-wrapping is *under*-wrapping: a genuine math expression (an assignment, a relation, a formula, a power, a function) written as bare prose with no `$…$`. An equals sign, inequality, exponent, or operator is a mathematical relation, and its visual brevity does not demote it to prose. Wrap the whole expression in `$…$`. The defect is the bare literal string sitting in body prose, a heading, a list label, a table cell, or citation `<Content>` CDATA. This is endemic for short, "label-like" expressions that feel like words.

| Wrong (bare in prose) | Right (LaTeX) | Field |
| --- | --- | --- |
| `T=3` | `$T=3$` | virology (capsid triangulation), geometry |
| `n=1`, `l=0`, `m_l=-1` | `$n=1$`, `$l=0$`, `$m_l=-1$` | physics (quantum numbers) |
| `pH=7.4` | `$\mathrm{pH}=7.4$` | chemistry |
| `V=5 V`, `I=2 A` | `$V=5\,\mathrm{V}$`, `$I=2\,\mathrm{A}$` | electronics |
| `alpha=0.05`, `p<0.01` | `$\alpha=0.05$`, `$p<0.01$` | statistics |
| `R^2=0.95` (or `R2=0.95`) | `$R^2=0.95$` | statistics |
| `n>=3`, `n ≥ 3`, `x!=0`, `Δ≠0` | `$n \ge 3$`, `$x \ne 0$`, `$\Delta \ne 0$` | math |
| `E=mc^2` | `$E=mc^2$` | physics |
| `f(x)=x^2`, `y=mx+b` | `$f(x)=x^2$`, `$y=mx+b$` | math |
| `2^32`, `O(n log n)` | `$2^{32}$`, `$O(n \log n)$` | computing (word size, complexity) |
| `3 x 10^8 m/s` | `$3 \times 10^8\,\mathrm{m/s}$` | physics |
| `H_2O`, `CO_2` (bare underscores) | `$\mathrm{H}_2\mathrm{O}$`, `$\mathrm{CO}_2$` | chemistry |
| `3Cpro`, `3Dpol`, `3CDpro` (enzyme name, bare superscript label) | `$3C^{pro}$`, `$3D^{pol}$`, `$3CD^{pro}$` | biology (viral proteases/polymerases) |
| `45 C`, `-273.15 C` | `$45\,^\circ\mathrm{C}$`, `$-273.15\,^\circ\mathrm{C}$` | thermodynamics |
| `GDP=2%` growth, `i=3%` | `$\mathrm{GDP}=2\%$`, `$i=3\%$` | economics |

An assignment embedded in a named term keeps the surrounding words as prose and pulls only the math into delimiters: `pseudo T=3 capsid` becomes `pseudo $T=3$ capsid`; `pH=7.4 buffer` becomes `$\mathrm{pH}=7.4$ buffer`; `O(n log n) sort` becomes `$O(n \log n)$ sort`.

## Inside Math, Render Every Symbol As LaTeX, Never A Unicode Glyph

**General Rule:** When a token is genuinely math, every character in it must be a LaTeX command, never a pasted Unicode glyph. **A raw Unicode math glyph in your output is WRONG** (it renders at the prose baseline, breaks spacing, and corrupts copy-paste). The "Wrong" columns below print the actual forbidden glyphs so you can recognise them and never emit them; they are defect illustrations only, never a shorthand to reuse. The rule applies in body prose, headings, list items, table cells, and citation `<Content>` CDATA alike.

**Superscripts And Subscripts:** Raw Unicode super/subscript digits and signs are wrong; use `^{…}` / `_{…}` inside `$…$`.

| Wrong (raw Unicode) | Right (LaTeX) |
| --- | --- |
| `Ca²⁺` | `$\mathrm{Ca}^{2+}$` |
| `α₁` | `$\alpha_1$` |
| `H₂O` | `$\mathrm{H}_2\mathrm{O}$` |
| `10⁻⁴` | `$10^{-4}$` |

**Greek Letters:** a raw Unicode Greek glyph used as a **symbol** is always wrong — wrap every Greek letter in `$…$`, whether it is a variable, an index, or a symbolic part of a name. This is categorical and does not depend on whether the surrounding token reads as a name: `α-helix`, `σ factor`, `α-CTD` are `$\alpha$`-helix, `$\sigma$` factor, `$\alpha$`-CTD, exactly as the variable `$\alpha_1$` is. A bare Greek glyph renders at the prose baseline and corrupts copy-paste, so it is never acceptable for a symbol. A spelled-out transliteration that denotes the letter (`alpha`, `beta`) is equally wrong — use the LaTeX command.

| Wrong (raw glyph or transliteration) | Right (LaTeX) |
| --- | --- |
| `α`, `β`, `σ`, `μ` | `$\alpha$`, `$\beta$`, `$\sigma$`, `$\mu$` |
| `α-helix`, `β-sheet`, `α-CTD`, `σ factor` (Greek symbol inside a name) | `$\alpha$-helix`, `$\beta$-sheet`, `$\alpha$-CTD`, `$\sigma$ factor` |
| `α₁`, `α₂` receptor (raw glyph plus a raw-Unicode subscript) | `$\alpha_1$`, `$\alpha_2$` receptor |
| `alpha`, `beta coefficient` (transliteration denoting the symbol) | `$\alpha$`, `$\beta$ coefficient` |

**The only exception — genuine Greek-language text:** when a Greek letter is actually a letter of a Greek *word* (a Greek-language lesson, or a Greek word, etymology, or quotation embedded in any lesson), it spells ordinary prose and stays bare — wrap only the genuine math expressions, exactly as you would Latin letters in an English lesson. A Greek letter functioning as a scientific *symbol* is never covered by this exception.

**Consistency:** hold one form per term throughout — `α-CTD` in one sentence and `$\alpha$-CTD` in the next is the single defect this rule exists to kill.

**Operators And Relations:** Raw Unicode arithmetic and relational glyphs are wrong; use the LaTeX command inside `$…$`.

| Wrong (raw Unicode) | Right (LaTeX) |
| --- | --- |
| `3 × 10⁸` (multiplication) | `$3 \times 10^8$` |
| `≈ 3.14` (approximately-equal) | `$\approx 3.14$` |
| `n ≥ 3`, `pH ≤ 7` | `$n \ge 3$`, `$\mathrm{pH} \le 7$` |
| `A ≠ B`, `x ± 2` | `$A \ne B$`, `$x \pm 2$` |
| `−5` (true minus glyph, not the hyphen) | `$-5$` |

**Set, Logic, And Calculus Symbols:** Raw Unicode `∈ ⊂ ∪ ∧ ∀ ∫ ∑ ∏ ∂ ∇ ∞ √` are wrong; use `\in`, `\subset`, `\cup`, `\land`, `\forall`, `\int`, `\sum`, `\prod`, `\partial`, `\nabla`, `\infty`, `\sqrt{…}` inside `$…$`.

**Degree And Prime:** A raw degree glyph (`°`) is wrong **wherever it appears**, especially in plain running prose and discursive fields (a rationale, a description, a do-not-repeat ledger), not only inside a formula. An angle or measurement in degrees is math: write the number bare in math with `^\circ`. The mistake is easy to miss because the surrounding sentence is ordinary prose, but `di 45°`, `a 90° bend`, and `rotates 60°` are each a math defect. Raw prime glyphs (`′`, `″`) are wrong the same way.

| Wrong (raw glyph, often mid-prose) | Right (LaTeX) |
| --- | --- |
| `una piegatura di 45°` (a bend of 45 degrees, biology/geometry) | `una piegatura di $45^\circ$` |
| `rotates 60°`, `a curvature of 90°` | `rotates $60^\circ$`, `a curvature of $90^\circ$` |
| `a 23.5° axial tilt` (astronomy) | `a $23.5^\circ$ axial tilt` |
| `a 180° phase shift` (physics / engineering) | `a $180^\circ$ phase shift` |
| `37 °C`, `-40 °C` (temperature) | `$37\,^\circ\mathrm{C}$`, `$-40\,^\circ\mathrm{C}$` |
| `5′` (arcminutes), `3″` (arcseconds / inches) | `$5'$`, `$3''$` |

## Keep Math Tokens Whole, Well-Formed, And Consistent

- **No Bare LaTeX Commands Outside Delimiters:** Every backslash-command (`\alpha`, `\beta`, `\to`, `\mathrm{…}`, `\frac{…}{…}`) must sit inside `$…$`. Bare in prose, Markdown stringify escapes the underscore (`\alpha\_2`) and the reader sees raw source. Canonical: `$\alpha_2$`, `$\beta$`.
- **No Backticks Around LaTeX:** Write `$\alpha_1$`, never inside a code span or code fence.
- **One Span Per Prose-Plus-Substructure Token:** A prose token and its math substructure live in ONE span: write `$\mathrm{B}_6$`, `$\mathrm{Ca}^{2+}$`, never the split form `B$_6$` or `Ca$^{2+}$` (the prose part renders at the prose baseline, the substructure in math font, and they stop aligning as one unit).
- **Thin Space Between Value And Unit:** Use `\,` between value and unit: `$30\,\mathrm{kb}$`, `$-70\,\mathrm{mV}$`. Never an escaped space (`$30\ \mathrm{kb}$`), a thick space (`\;`), or a literal space, and never try to space with a literal space inside the wrapper (`$30\mathrm{ kb}$`) — math mode silently swallows it.
- **No Stray Whitespace At Wrapper Boundaries:** Inside `$…$`, `\mathrm{}` ignores any literal space within its braces, so a stray space neither produces the gap you intended nor survives the render. Put all intended spacing as a math-mode command (`\,`) outside the wrapper, never as a space inside it.
- **One Notational Choice Per Construct, Held Throughout:** Pick one form for a unit, ion, power-of-ten, or subscript-word on first use and reuse it everywhere, including matching the body and any citation `<Content>` for the same entity. A mismatch between body and adjacent-citation notation for the same entity is a hard failure, not a style nit.

## Prose Relationships Are Sentences Or Lists, Never Symbol Chains

- **No Math Symbols Standing In For Prose Relationships:** Do not encode causation, transformation, or sequence as a symbol chain in running text; write it as a grammatical sentence.
- **Arrow Chains Become Lists, Never Arrow Spans:** Any sequence of three or more entities chained by arrows (a procedure, causal chain, state transition, or pipeline) is enumerable content: render it as a list, one item per step, each item carrying the substance the source established. This holds for **every arrow variant**, and all of them are the same defect: every Unicode arrow glyph (rightwards `→`, leftwards `←`, bidirectional `↔`, the double/implication forms `⇒`, `⇐`, `⇔`, the equilibrium `⇌`, the maps-to `↦`, the long forms `⟶`, `⟵`, and the diagonals `↗`, `↘`, `↖`, `↙`) and every LaTeX arrow command (`\to`, `\rightarrow`, `\longrightarrow`, `\leftarrow`, `\leftrightarrow`, `\Rightarrow`, `\Leftrightarrow`, `\rightleftharpoons`, `\mapsto`, `\nearrow`, `\searrow`, `\nwarrow`, `\swarrow`). A chain written with Unicode glyphs (wrong: `glucose low → cAMP high → CRP active`, biology) and the identical chain written with LaTeX spans (also wrong: `parse $\rightarrow$ compile $\rightarrow$ link`, computing) are equally wrong, because a single arrow between two prose tokens is not a math object even inside `$…$`. Inside a list item, nest a sub-list; inside a table cell, lift the chain out into a list. Carve-out: a complete canonical domain expression keeps its arrow, because the surrounding expression is a real math object: a function signature `$f: A \to B$`, a limit `$\lim_{x \to 0}$`, a balanced reaction `$2\mathrm{H}_2 + \mathrm{O}_2 \to 2\mathrm{H}_2\mathrm{O}$`, a logical implication `$P \Rightarrow Q$`.
- **Trend Arrows Are Not Math:** A raw Unicode up/down/diagonal arrow (`↑`, `↓`, `↗`, `↘`) used as shorthand for "increases" or "decreases" is wrong: `cAMP ↑` (biology), `inflation ↓` (economics), and `latency ↓` (computing) are prose abbreviations, so write the target-language verb (`cAMP increases`, `inflation falls`), never the arrow glyph and never `\uparrow` or `\downarrow`.

## Never Anywhere

- **No HTML Markup Or Entities:** The output is Markdown plus inline LaTeX, never HTML. Never `<sub>`/`<sup>`, `<i>`/`<em>`, `<b>`/`<strong>`, `<br>`, `<span>`, or entities like `&amp;`/`&lt;`/`&nbsp;`. Every subscript, superscript, or charge that tempts an HTML tag uses LaTeX instead: `GABA<sub>A</sub>` becomes `$\mathrm{GABA}_A$`, `3C<sup>pro</sup>` becomes `$3C^{pro}$`, and `G<sub>q</sub>`, `Ca<sup>2+</sup>`, `α<sub>1</sub>` become `$G_q$`, `$\mathrm{Ca}^{2+}$`, `$\alpha_1$`. The only XML allowed is the project's own structural tags (the `<Citation>` and `<LessonOutline>` families). A single stray HTML tag in any CDATA field, objective, rationale, or sentence is a hard failure.
- **No Currency Glyphs:** You MUST ALWAYS express money with the ISO 4217 code (USD, EUR, GBP, JPY) ONLY in ALL prose and in math; never a currency symbol (e.g., `$`, etc.). The dollar sign is reserved exclusively as the math delimiter, and any currency glyph renders unreliably. Never even write it escaped, as `\$`. You MUST NEVER even use `$` to represent USD within math. For example, don't write `$100$$` or `$100\$$`, instead write `$\mathrm{USD}\,100$`.
- **Leave Citation Markers Alone:** Footnote references (`[^1]`) and citation markers are not math: emit them verbatim as plain prose, never inside `$…$` or any LaTeX construct.

## Final Math-Notation Checklist (Run Before Emitting)

Scan the whole draft against each item, in body prose, headings, list items, table cells, and citation `<Content>` CDATA alike. Fix every hit before emitting.

- [ ] **No Prose In Math:** No word, acronym, name, gene/operon, or literal code/sequence is wrapped in `$…$`, `\mathrm{}`, or italics. `$\mathrm{cAMP}$`, `$\mathrm{lac}$`, `$\mathrm{HTTP}$`, `$GTGTG$`, `*GTGTG*`, `$+\mathrm{inducer}$` are all wrong. Strip-and-read test: if the token reads identically as plain text, it stays plain prose.
- [ ] **No Bare Math In Prose:** Every assignment, relation, exponent, power, formula, or function sits inside `$…$`. `T=3`, `n=1`, `pH<7`, `R^2=0.95`, `E=mc^2`, `2^32`, `O(n log n)` left bare are all wrong.
- [ ] **No Raw Unicode Glyphs:** No raw super/subscript (`²`, `³`, `₁`, `₂`), Greek glyph used as a symbol (`α`, `β`, `σ`, `μ` → `$\alpha$`, `$\beta$`, `$\sigma$`, `$\mu$`, even inside names like `α-helix`/`σ factor`), operator (`×`, `÷`, `±`, `−`, `≈`, `≠`, `≤`, `≥`), set/logic/calculus glyph (`∑`, `∫`, `∈`, `√`, `∞`), degree (`°`), or prime (`′`) anywhere; each becomes its LaTeX command inside `$…$`. The sole exception is a Greek letter that is a real letter of Greek-language text (a Greek word or a Greek-language lesson), which stays bare.
- [ ] **No Arrow Chains Or Trend Arrows:** No three-or-more-entity arrow cascade in prose, lists, or table cells, in any Unicode or LaTeX variant (full list in the Arrow Chains rule above) — refactor into a list. No trend arrow (`↑`, `↓`); write the verb (`increases`, `decreases`). Only carve-out: a complete canonical domain expression (`$f: A \to B$`, a balanced reaction).
- [ ] **Tokens Whole And Well-Formed:** No split prose-math token (`B$_6$` is wrong; `$\mathrm{B}_6$` is right); no bare backslash-command outside `$…$` (`\alpha_2` in prose is wrong); no backticks around LaTeX; thin space `\,` between every value and its unit.
- [ ] **Consistency:** One notational form per construct held throughout, and the body matches every adjacent citation `<Content>` for the same entity (no Unicode glyph in one and LaTeX in the other).
- [ ] **Never Anywhere:** No HTML tag or entity; no currency glyph (ISO 4217 code only); citation markers and footnote references left as plain prose.
- [ ] **Currency Dollar-Sign Sweep (Verify Explicitly):** Walk **every** `$` in the draft one by one — body prose, headings, list items, table cells, and citation `<Content>` CDATA. Confirm each `$` is a genuine math delimiter that pairs with a partner and wraps a real mathematical expression. A `$` touching a money amount (`$100`, `100$`, `$5.99`), a run where the text caught between two `$` is prose about money rather than math, or an escaped `\$` are all currency defects — and so is an **odd** total count of `$`, which proves a stray unmatched delimiter is corrupting everything after it. Rewrite every monetary value as its ISO 4217 code inside math, `$\mathrm{USD}\,100$` / `$\mathrm{EUR}\,49.99$` (never `$100`, `\$100`, `$100\$`, or a bare `100 USD`). Then recount: the number of `$` must be **even**, and each `$…$` pair must enclose actual math — if any pair encloses prose, you created the defect this checklist exists to catch.
