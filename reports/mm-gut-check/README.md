# Missing-middle gut check (2026-11-17)

Report only: no model run, no config change. Asked by Ben (via the ADU session) after the NC ADU gut check
(`docs/build/workstreams/WS-NC-GUTCHECK.md`, tasks 1–3). Page: `results.html`
(published at https://claude.ai/artifact/VPPb52Mxzc4yTd1Ue6yLzb).

**Question.** Do the app's missing-middle numbers for MN, NC, OH, TX and OR hold up against Census BPS homes in
2–4 unit buildings for 2019–2025?

**Inputs.** The five results bundles from `lotline results --all` at main ef37f59a (schemas 1.15, 1,000 draws,
seed 20261106, origin 2025). The bundles are gitignored; `summary.json` holds every number the page uses.

**Reproduce.**

```bash
uv run lotline results --all
uv run python scripts/dev/mm_gut_check_data.py
uv run python scripts/dev/mm_gut_check_page.py
```

**Findings.**

1. **Units.** The app's headline is net new homes: a 2027–2031 five-year total, added over the no-reform
   baseline, statewide (BPS places cover 97–99.9% of permits). It is permits × completion × the share not replacing
   a torn-down house × (1 − displacement), about 40% of the extra permits. The added homes are back-loaded
   (2027 about 1% of the total, 2031 about 57%). The Method card asked how many homes "would be permitted";
   the ADU session changed it to "would it gain" in PR #474.
2. **Baseline vs history.** No-reform five-year midpoints are 78–96% of five years at the 2023–2025 pace
   (Minnesota lowest, 2,182 against 2,807); means are 89–107%. The yearly midpoint drifts down because the cycle
   spread widens; yearly means are flat. No state is far below history.
3. **Reform vs history.** `historical_floor:missing_middle` passes in every state (with-reform median a year ÷
   2023–2025 mean: MN 1.98, NC 2.14, OH 1.60, TX 1.59, OR 1.10). Added permits at the median are about the state's
   whole recent five-year 2–4 unit output in MN (1.05×) and NC (0.95×), with P90 5–6×. In line with St. Paul
   (about 6 to 33 buildings a year after its reform; the V5 blind test said the model undershoots).
4. **Funnel.** Legal lots and the pencil-out share barely vary across draws; uptake (θ, pooled across states)
   spans about 41-fold and carries the range. A state's added homes next to its history follow lots that pencil out
   per home it already builds (MN 660, NC 594, OH 334, TX 328, OR 85). The pencil-out share's P10–P90 is within
   2 points, so cost and price uncertainty adds little to the range.
5. **One line per state** is on the page.

**Decisions.** Ben approved the Method card wording (applied in #474). Nothing else proposed.
