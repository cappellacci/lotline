### LB-XXX · 2026-11-17 · WS-NEED-AMI (part A) · Housing need as a bar, real local fees by default

**Question:** Can a reader see from one card how many homes the state needs, how much the three reforms cover and which covers the most, without reading a table of percentages (office hours 2026-11-17, B1 and B2)?

**Output:** `src/lotline/app/template.html` (`needHtml`: one bar per kind of need; fee view default), `tests/app/test_need_card.py` and `tests/app/need_card_harness.js` (the page's own script under node).

**What happened:**
- **Fee default.** The fee view now starts on real local fees halved (`fees_local_half`) and falls back to the Handbook benchmark when a bundle has no local-fee run. The benchmark stays on the same switch, in the every-state chart and on the fee card. The headline, the range boxes and the share of need all follow the switch, so the headline's default number is now lower than the live site's: its fee part uses real local fees halved, not the $25,000 benchmark cut.
- **Need chart.** One bar for each kind of need the bundle carries (household growth over the five years; the standing shortage), headline kind first and never mixed. Each reform's net new homes midpoint is filled in from the left in its colour; a line marks the likely range of the three together, added run by run as in the headline; the rest is labelled as the gap that remains. Above it: "[State] needs about N homes by 2031" (or "is short about N homes today" for the shortage), then the three-together range. The per-reform rows and the "if the need is x to y instead" line stay.
- **Which reform adds the most.** One generated sentence ranks the reforms by midpoint, each with its range, and says when the top two ranges overlap.
- Ohio's bundle carries only the shortage (its household growth is negative), so it shows one bar.

**Claude's part and checks:** Claude (ADU session) wrote the card and tests. The tests build the page from a synthetic bundle (the fixture's ADU draws plus scaled missing-middle and fee runs) and check every number against hand-computed values from the draws and need rows, that every midpoint has its range, the fee default and fallback, two separate bars, and the no-need pending note. Rendered the card for MN, NC, OH and TX from the local ef37f59a bundles. Part B (who the homes serve) waits for Ben's two decisions.
