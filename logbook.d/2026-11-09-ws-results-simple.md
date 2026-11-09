### LB-NNN · 2026-11-09 · Deliverables: Results page as a simple data story, one tab per policy (WS-RESULTS-SIMPLE)
- **Question:** Can a non-technical reader answer "how many more homes, compared with what, how sure" from the
  first screen of Section 1? (Office hours 2026-11-09, action items 5–7.) Ben then asked for each policy on its
  own tab (overlap adds too much complexity) and for the page built and published to Pages for QC.
- **What I did:**
  - Wrote the Section 1 copy (`src/lotline/app/copy/results.md`, about 285 words of page text against a 300-word
    cap), every number a slot mapped to a results-bundle field, with open questions Q1–Q6.
  - Rebuilt Section 1 of `src/lotline/app/template.html`: policy tabs (ADUs, missing middle, fee reduction; no
    stacked or combined view), a two-worlds bar chart with an enlarged strip for the added homes, the headline
    sentence, the backtest line (fallback until a scorecard row exists), four funnel sentences, "What this can't
    tell you", the sliders and the old detail cards behind folds, the state map moved below the story.
  - Per-policy words in `src/lotline/app/copy/scenarios.yaml`, loaded by `build.policy_copy()`, which refuses a
    number written into the copy. Wrote the 60-second usability check (`docs/build/usability-check.md`).
- **Inputs:** `docs/build/workstreams/WS-RESULTS-SIMPLE.md`; `docs/research/office-hours-2026-11-09-greg-miller-notes.md`;
  `src/lotline/model/results.py`; the fixture bundle; release `app-2026-11-09` bundles (MN, NC, OH, OR, TX).
- **Outputs:** `src/lotline/app/copy/results.md`, `src/lotline/app/copy/scenarios.yaml`, `src/lotline/app/template.html`,
  `src/lotline/app/build.py` (`policy_copy`), `tests/app/test_results_simple.py`, `tests/app/test_build.py` (two
  assertions), `docs/build/usability-check.md`; a QC release and Pages deploy from branch `ws/results-simple`.
- **Findings:**
  - The reform's homes are a small slice of all building (NC ADUs: about 260 on about 348,000), so the two bars
    look alike; the enlarged strip carries the difference. A same-type baseline (e.g. 2–4 unit permits for
    missing middle) would show the change better: a design call for Ben.
  - The bundle can't yet give an honest with-reform range (no per-draw baseline, Q1) or the backtest number (no
    scorecard row, Q3); three of the four sliders the brief asks for need a pre-computed grid (Q4).
  - The headline +N at default sliders equals the bundle's `permits_added` P50 (tested on the fixture).
- **Decisions:** Ben, 2026-11-09: one tab per policy, no combined view on the results page (drops the brief's
  combined small multiples). Proposed for HANDOFF. Q1, Q3 and Q4 are contract changes for WS-ENGINE/WS-CORE.
- **AI:** Claude drafted the copy and built and tested the page. Checks: app tests (55 pass), a mutation check
  that a number written into a sentence fails its test, and a browser check of NC (all three tabs; a slider moves
  the headline and resets).
- **Open / next:** Ben QCs the Pages build and answers Q1–Q5; run the 60-second test on the published page.
