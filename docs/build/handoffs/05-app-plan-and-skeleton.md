# Thread 5: App plan rewrite and skeleton (WS-APP)

**Precondition:** Ben has approved Streamlit (Apache-2.0) as a dependency. If not, stop after step 1.

**Goal:** a task-centred plan for the interactive tool (deliverable D1; Usability is 20% of the score) and a working skeleton on placeholder results.

**Read first:** `docs/build/workstreams/WS-APP.md` (current brief); the usability judge's report in `reports/judging/2026-10-19-0518-e31b4ed/judge-usability.md` (gitignored, local); `docs/model_and_assumptions.md`; the result tables the scenarios produce (`model/scenarios/adu.py` totals: P10/P50/P90 per place and state).

**Deliver:**
1. **PR A, plan:** rewrite `docs/build/workstreams/WS-APP.md` around user tasks:
   - the landing page compares scenarios side by side for a state;
   - plain-language labels and units;
   - sliders for the key assumptions, with reset;
   - always show ranges, never a single number;
   - "what this can't tell you" on every view;
   - place and region results only (≥20 eligible parcels, D-015).

   Also cover: which data the hosted app loads (a small precomputed results bundle, not raw data), a speed target, and accessibility. Propose the HANDOFF decision in the PR.
2. **PR B, skeleton (after Ben's OK):**
   - **Structure:** `app/` Streamlit app with the plan's pages, reading a placeholder results bundle (`app/sample_results/`, synthetic and clearly labelled as such).
   - **Tests:** a smoke test that the app imports and renders each page function.
   - **Disclosures:** add Streamlit to `docs/disclosures.md` and refresh the SBOM/licence scan.

**Done when:** PR A open (and PR B if approved), CI green.
