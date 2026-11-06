# WS-APP · Interface and deliverable documents (weeks 6–9)

**Start:** Nov 18, once the engine's results bundle (WS-ENGINE, "results export") is stable.
**Owns:** `src/lotline/app/`, `scripts/build_app.py`, `docs/model_and_assumptions.md`, `docs/policy_scenario_comparison.md`, `docs/slides*`, `README.md` (user sections).
**Revised 2026-11-06** (Ben): the app is a **static page built from pre-computed results**, not a Streamlit server. See HANDOFF decisions of 2026-11-06 for why.

## Read first
- `HANDOFF.md` §2–3 (D1–D9, scoring rubric) and the 2026-11-06 decision rows
- `docs/research/office-hours-2026-11-03-tomasso-notes.md` (A1–A5: headline = statewide 5-year total vs baseline as a P10–P90 range; share of housing need; SFD/duplex/fourplex pencil-out table)
- `docs/research/lotline-validation-plan.md` §5 (scorecard) and V8/V9 (transfer tests)
- `docs/research/podcast-upzoned-301-notes.md` (what the sponsors want)
- `src/lotline/dashboard/` (data dashboard) and `src/lotline/model/dashboard.py` (engine results dashboard): both already embed JSON in one self-contained HTML page and draw with plain SVG/d3 in the browser. **The app follows the same pattern.** Reuse their template conventions (light/dark, no server, no network beyond the pinned CDN libraries already disclosed).

## Shape of the product

One page, `reports/app/index.html` (gitignored; rebuilt by `scripts/build_app.py`, published by CI to GitHub Pages or similar), with a **state picker** and **three sections** that map onto the deliverables:

| Section | Audience | Deliverable it mirrors | What it shows |
|---|---|---|---|
| **1. Results** | legislators, staff, press | D6 Policy Scenario Comparison | Statewide 5-year net new homes vs baseline per scenario and combined, as P10–P90 ranges (never a point alone); the same as % of projected 5-year household growth / housing need (A2); the Legal → Pencils → Built funnel for the chosen scenario; the SFD / duplex / fourplex pencil-out table with per-unit connection fees named (A5); plain-language assumption sliders with source and range; "in this place" vs "net statewide"; the overlap/confidence flag for the state. |
| **2. The data** | judges, analysts, anyone asking "what is this built on?" | D7 provenance; Rules §8 "data available vs. used" | The existing data dashboard (coverage map, sources table, ordinance timeline, growth, data checks), plus the per-state "available vs. used" table and data tier. |
| **3. How well does it hold up?** | judges, skeptical staff | Validation plan §5 scorecard; D4 | The scorecard front and center: backtests, the frozen blind forward tests (St. Paul, Charlotte; Oregon V9) with predicted range vs observed, the overlap check, and the tornado chart. The technical model internals (draw distributions, effect terms, calibration fits) sit beneath a clearly labeled "Technical detail" fold or link to the engine results dashboard. |

Trust comes from "we predicted this before we could see it"; section 3 leads with that, not with model internals.

### Any state in `config/states/`
The build is state-agnostic: every state with a results bundle under `reports/results/<state>/` appears in the picker, labeled by its role (benchmark state first; development states; unseen-state transfer runs; and, if the gate below passes, national-data-only states). A US map colors states by data tier; states without a bundle are grey with a "bring your own state" link to the onboarding guide. No state names in app code.

### Sliders without a server
The engine runs offline and exports per-state parameter **draws** (uptake rate, pencil-out share, completion factor, net-new share, displacement, overlap) in the results bundle. The page recomputes the headline across draws in the browser on every slider move: eligible parcels × uptake × pencil-out share × completion × net-new, with the combined-scenario overlap correction. This is the only model arithmetic in JavaScript. **Contract:** `tests/app/test_aggregate_parity.py` runs the JS aggregation (via node, or a Python port with a shared fixture) against `model/aggregate.py` on the same fixture and asserts P10/P50/P90 match to rounding. If the parity test can't be kept green, the sliders fall back to a pre-computed grid over each knob's low/mid/high and the page says so.

### Not a mockup (D1)
Every results bundle carries `commit_sha`, `run_at`, engine version and the config hash; the page footer shows them, and the README gives the one command that regenerates the bundles and the page (`uv run lotline results --all`, which writes every bundle and builds the page; decided 2026-11-06, contract with WS-CORE). The live sliders and the parity test are the proof that the numbers come from the engine, not from a spreadsheet.

## Tasks
- [ ] **Agree the results bundle schema with WS-ENGINE** (issue labeled `contract-change`): per state, per scenario (incl. combined), per draw; funnel stages; housing-need denominator with source; overlap flag; scorecard rows; metadata (SHA, run time, config hash, data tier, role).
- [ ] **`scripts/build_app.py` + `src/lotline/app/`:** load bundles, embed as JSON, render the three sections; reuse `dashboard/` for section 2 and `model/dashboard.py` output for the technical fold of section 3.
- [ ] **Section 1:** headline range chart; % of housing need; funnel; pencil-out table; sliders (each with source, range, one-line "why it matters"); combined scenarios with no double counting; place vs statewide; confidence flag.
- [ ] **Section 2:** data dashboard embedded; "available vs. used" table per state; data tier badge.
- [ ] **Section 3:** scorecard table; blind-test charts (frozen range vs observed, once unblinded in week 7); overlap check; tornado; technical fold.
- [ ] **State map and picker**, roles and tiers from config; grey states link to the "bring your own state" guide.
- [ ] **Parity test** for the browser aggregation; a smoke test that the page builds from the fixture bundle and contains every section.
- [ ] **Deploy** the static page (GitHub Pages from CI, or similar, free). URL in `challenge.toml`. Also document opening `reports/app/index.html` locally (no server needed). Test both in a private window.
- [ ] **Model & Assumptions Overview** (≤25 pages, 7 required sections), generated where possible from config, bundles and reports; section 3 of the app and D4 share the scorecard source.
- [ ] **Policy Scenario Comparison** (≤4 pages, non-technical); section 1 of the app and D6 share the headline numbers (one source, rendered twice).
- [ ] **Slide deck PDF** (≤30 slides) and demo-video script (≤5 min): lead with the statewide range and the transfer test, per the office-hours critique.
- [ ] Final `compliance_check.py --all`. Export the SBOM. Check disclosures (CDN libraries, any new JS).

## Acceptance
D1–D9 complete; compliance 0 FAIL; page builds from a clean clone with the fixture bundle; parity test green; every state in `config/states/` with a bundle appears without code changes; Ben's sign-off.

## Don'ts
- No server-side app (Streamlit, Flask); nothing the judge has to keep running.
- No model arithmetic in the browser beyond the aggregation step above.
- No single numbers without a range; no parcel-level outputs (S10).
- No state-specific branches in app code.
