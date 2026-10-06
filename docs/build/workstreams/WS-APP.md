# WS-APP · Interface and deliverable documents (weeks 6–9)

**Start:** Nov 18, once the engine API (`run(...)`) is stable.
**Owns:** `src/lotline/app/`, `docs/model_and_assumptions.md`, `docs/policy_scenario_comparison.md`, `docs/slides*`, `README.md` (user sections).

## Read first
- `HANDOFF.md` §2–3 (D1–D9, scoring rubric)
- `docs/research/podcast-upzoned-301-notes.md` (what the sponsors want)
- `docs/research/lotline-validation-plan.md` §5 (scorecard)

## Tasks
- [ ] **Streamlit app:**
  - state picker (benchmark state first; the other three labeled "portability runs");
  - scenario toggles incl. combined;
  - plain-language assumption sliders, each with source and range;
  - P10–P90 ranges, never single numbers;
  - tornado chart;
  - "in this place vs net statewide";
  - data-tier and confidence flags;
  - "How well has this held up?" link to the scorecard;
  - Legal → Pencils → Built funnel view.
- [ ] **Deploy** (Streamlit Community Cloud or similar, free). Put the URL in `challenge.toml`. Test it in a private window.
- [ ] **Model & Assumptions Overview** (≤25 pages, 7 required sections), generated where possible from config and reports.
- [ ] **Policy Scenario Comparison** (≤4 pages, non-technical).
- [ ] **Slide deck PDF** (≤30 slides) and demo-video script (≤5 min).
- [ ] Final `compliance_check.py --all`. Export the SBOM. Check disclosures.

## Acceptance
D1–D9 complete; compliance 0 FAIL; Ben's sign-off.
