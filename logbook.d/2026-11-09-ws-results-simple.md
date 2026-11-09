### LB-NNN · 2026-11-09 · Deliverables: Results page copy, first draft (WS-RESULTS-SIMPLE)
- **Question:** What should Section 1 say, in plain words, so a non-technical reader can answer "how many more
  homes, compared with what, how sure" from the first screen? (Office hours 2026-11-09, action items 5–7.)
- **What I did:**
  - Wrote the Section 1 copy in page order: two-worlds headline chart, one-sentence result, one backtest line,
    four funnel sentences, scenario comparison, three "can't tell you" bullets per scenario, a collapsed
    assumptions panel, the methodology link. About 285 words of page text against the 300-word cap.
  - Mapped every number slot to a results-bundle field (schemas 1.11), so no number is written by hand.
  - Wrote the 60-second usability check script and results table for Ben to run.
- **Inputs:** `docs/build/workstreams/WS-RESULTS-SIMPLE.md`; `docs/research/office-hours-2026-11-09-greg-miller-notes.md`;
  `src/lotline/model/results.py`; `tests/fixtures/results/zz/bundle.json`; `src/lotline/app/template.html`, `knobs.yaml`.
- **Outputs:** `src/lotline/app/copy/results.md`; `docs/build/usability-check.md`.
- **Findings:**
  - The bundle can't yet draw an honest "with the reform" range: the baseline has only P10/P50/P90, not draws
    (Q1). The baseline counts permits, so the headline should be `permits_added` to keep the bars comparable (Q2).
  - No scorecard row gives the "within X% on 2019–23" backtest number yet (Q3); the page will use a fallback line.
  - Three of the four sliders the brief asks for (cost, rents/values, interest rate) feed the pro forma, which
    the browser may not recompute; they need a pre-computed grid in the bundle (Q4).
- **Decisions:** none recorded; Q1–Q6 in the copy file are proposed for Ben (Q1, Q3, Q4 are contract changes for
  WS-ENGINE/WS-CORE).
- **AI:** Claude drafted the copy and the check and checked every slot against the fixture bundle's fields and the
  current template. Word count measured with `wc -w` on the page-text lines. No code, no model runs.
- **Open / next:** Ben reviews the copy and answers Q1–Q6; then build the chart, funnel sentences, comparison and
  tests against the fixture bundle; numbers wire up when WS-NC-GUTCHECK lands.
