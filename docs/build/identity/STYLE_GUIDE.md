Lotline is a civic instrument: an open-source simulator that shows a state what three housing reforms (ADUs, missing middle, fee reduction) would do to housing production over five years, as a range, never a single number. The identity makes a technical, uncertainty-heavy model feel clear, credible and calm to a non-technical policymaker. Design to three words: **clear, honest, grounded.**

The name comes from the lot line, the boundary of a parcel on a plat map. The model counts lots, asks which are legally eligible, which pencil out, and which get built, then adds them up to a state. Everything in the system comes from that: survey-paper neutrals, square corners, hairline rules, one blue, one brass, and a dimension line with a marked midpoint that is both the wordmark's underline and the chart mark for every result.

## Voice and content

- Write like a careful public servant, not a startup: plain words, short sentences, active voice. "Allowing one ADU per lot would add 9,400 to 21,000 homes." Never "unlock", "supercharge", "game-changing".
- State the range first, the midpoint second, the source third. A number without a range is off-brand; a chart without a source line is incomplete.
- Say what the model cannot tell the reader. Honesty about limits is written as a strength ("The model has not seen a state like this; treat the range as wide"), never as an apology.
- Name the reforms exactly as the competition handbook does: **ADUs**, **Missing middle**, **Fee reduction**, and **Baseline** for no policy change. "Combined" means all three together.
- Sentence case for every heading and label. Uppercase only in the `eyebrow` style.
- No emoji. No exclamation marks. Use the real units: homes, lots, permits, five years, P10–P90.
- Politically neutral in every word and colour: the tool must read the same to a lawmaker of either party.

## Colour

- Set every page on `paper` with text in `ink`. Raise a card with `paper-raised` and a 1px `rule` border; sink a code block or technical fold into `paper-sunken`. Never use shadow to separate surfaces; `shadow-tooltip` is for tooltips only.
- `survey` is the one brand colour: links, primary buttons, the active slider thumb, the midpoint of the wordmark's rule. Use `on-survey` for text on it.
- `brass` is the one accent and is rationed: eyebrows, the short lot-line tick under a slide title, a highlighted figure at 24px or larger. Never body text in light mode.
- Scenario colours are fixed slots and never change order or meaning: `scenario-baseline` (neutral), `scenario-adu`, `scenario-missing-middle`, `scenario-fees`, `scenario-combined` (full ink). The three reform hues are validated colour-blind-safe against each other in both themes (worst CVD ΔE 9.7 light, 8.8 dark). Every series is also labelled by name; colour never carries identity alone.
- The confidence flag uses `confidence-inside`, `confidence-edge` and `confidence-outside` with a glyph (filled, half, open circle) and the word. It is deliberately not green/amber/red.
- The US map uses `tier-1` to `tier-5` as a single-hue sequential ramp and `tier-none` for states without a results bundle. The dark ramp is re-stepped, not inverted.
- Dark mode is a second, equal theme: every token has its own dark value and every pair in this book holds 4.5:1 for text and 3:1 for marks in both.

## Typography

- Headings and UI in `sans` (Public Sans, the typeface designed for US government sites; SIL OFL). Styles `display`, `h1`, `h2`, `h3`, `eyebrow`, `body`, `body-small`, `caption`.
- Running text in the two written reports in `serif` (Source Serif 4; OFL), styles `report-body` and `report-lead`. Headings in those documents stay in `sans`.
- Every number in `mono` (IBM Plex Mono; OFL): `figure-large` for the headline range, `figure` in tables and tiles, `code` for commands and the commit SHA. Set `font-variant-numeric: tabular-nums` wherever digits line up.
- Keep running text at 60 to 70 characters a line. Headings get `text-wrap: balance`. Tighten display sizes with the letter-spacing in each style; never track body text.
- All three families load from Google Fonts in the app and ship as files in the repository for print; all are OFL and may be committed.

## Layout, rules and shape

- Lotline is square: `radius-0` on cards, tables, slides and the mark; `radius-sm` (2px) only on buttons, inputs, chips and the slider thumb.
- Hairlines do the work shadows would elsewhere: `stroke-hair` in `rule` for borders, gridlines and table rules. The plat grid (a faint 48px grid of `rule` hairlines) may sit behind a slide title or the app masthead, never behind running text.
- Space on an 8px scale, `space-1` to `space-8`. Slides use `space-7` margins; reports `space-8`.
- The lot-line rule is the recurring motif: a `stroke-line` horizontal rule in `ink` with `space-1`-tall end ticks and a square `survey` midpoint marker. It underlines the wordmark, closes a slide title, and is the shape of every range bar.

## Charts

- Every result is a **range bar**: a `survey-band` P10–P90 band, a `stroke-line` rule in the scenario colour, a `stroke-mark` midpoint tick, and the three numbers in `figure`. Never a lone point, never a bar from zero for a single estimate.
- One y-axis per chart. Gridlines in `rule`, axis text in `ink-muted` and `caption`. Series labelled directly at their end; a legend is present for two or more series.
- The funnel (legally eligible → pencils out → built) is three nested horizontal bars in `survey`, `survey` at 60% and `scenario-*`, each labelled with its count.
- Baseline is drawn first and in `scenario-baseline`, so the reforms read as additions to it.
- A source line in `body-small` and `ink-muted` sits under every chart, naming the dataset and access date.

## Wordmark and mark

- Use `assets/Wordmark/lotline-wordmark-light.svg` on light paper and `lotline-wordmark-dark.svg` on dark; `lotline-wordmark-mono.svg` for one-colour print and stamps. Minimum height 16px (the rule stays legible). Clear space equals the height of the "L" on every side.
- The compact mark (a square lot with a dimension line) is for favicons, the video corner bug and social avatars, never beside the wordmark on the same line. Minimum 16px.
- Never recolour the wordmark outside `ink` + `survey`, never stretch it, never set it on a photograph.

## Iconography and imagery

- Icons: Lucide (ISC), 1.5px stroke, in `ink` or `ink-muted`, 16 or 20px, always beside a word. No house, key or rooftop icons; a lot is drawn as a square.
- Imagery: none by default. Where a picture is needed (video title, deck opener), use a plat-map or cadastral drawing in `rule` and `ink` on `paper`, or a simple drawn diagram. No stock photography, no skylines, no gradients.

## Motion

- Slider changes update the range bar in 200ms ease-out; nothing else animates. Respect `prefers-reduced-motion` by removing the transition.
