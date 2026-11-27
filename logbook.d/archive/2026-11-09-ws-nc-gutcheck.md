### LB-NNN · 2026-11-09 · `engine` · Why NC's ADU forecast looked lower than NC's history (WS-NC-GUTCHECK)
- **Question:** at office hours, NC's ADU-reform result read as "a median of about 50" against roughly 100–150
  ADUs a year in history. Is that a units mismatch, a calibration bug, or both?
- **Decided by:** the brief `docs/build/workstreams/WS-NC-GUTCHECK.md` (Ben, 2026-11-09). The parameter change
  is proposed as D-070 (`docs/analysis_plan.md`) for Ben's review in the PR.
- **Outputs:**
  - `reports/diagnostics/nc/README.md`: units audit; baseline vs 2019–25; funnel with P10/P50/P90; BPS vs city
    permits; MAF note; guardrail; TX spot check. Plots are in `reports/diagnostics/nc/` (before) and `after/`.
  - `scripts/dev/gutcheck_diagnostics.py <ST>`: the two worlds (no reform / with reform), the funnel and
    baseline-vs-history for any state.
  - Fix: `adu_observed_years` (4) replaces the fixed 2019–2022 floor window (`config/params/adu.yaml`,
    `adu.observed_per_year`, `adu.holdout_stops`). `adu.run(return_draws=True)` now also returns `current`
    (no-reform ADUs) and `rule_share`.
  - Guardrail: `src/lotline/model/gutcheck.py` (`historical_floor`), wired into the bundle scorecard
    (`results.historical_floor_rows`); `historical_floor_years` (3) in `aggregate.yaml`; reasons in
    `config/historical_floor_reasons.yaml` (empty).
  - Tests: `tests/model/test_nc_gutcheck.py` (11, synthetic and hand-worked).
- **Findings:**
  - The headline 40 / 105 / 301 is 5-year, added over baseline, net homes (about 0.40 of permits),
    statewide. "About 50" matches no exported figure (closest: about 52 added permits a year).
  - Like for like (11 ADU-flagging places, holdouts out of both sides), the no-reform forecast was 78 a year
    against 126 observed in 2023–25. The cause: a floor fixed at 2019–22, before NC's ADU take-off. After the
    fix: 135 without the reform, 137 with it. Statewide over 2027–31: about 2,000 without, about 2,300 with.
  - The added effect is small because 81% of NC lots already allow ADUs at or near the Handbook and NC's
    per-lot uptake is low. That matches NC's own record.
  - BPS vs city permits, 2019–25 totals: Raleigh 0.98, Durham 1.10, Greensboro 0.94. No sign of an undercount.
  - TX: Austin's HOME reclassification lowers its trailing floor (232 vs about 371 a year). That needs a WS-TX
    adapter rule.
- **What Claude did and how it was checked:** ran the ADU engine at 1,000 draws for NC, TX, MN and OH before
  and after the change. The diagnostic's net-homes arithmetic reproduces the bundle's (40/105/301), and NC and
  TX bundles were rebuilt with `lotline results` to read the new scorecard rows (NC ADU 1.09, MM 1.30; TX 1.70,
  1.15). Unit tests were hand-worked; `compliance_check.py` shows 0 FAIL. No holdout was bypassed: everything
  read the holdout-filtered store.
- **Open:**
  - Bundle outcomes for the two worlds need a contract change (`RESULT_OUTCOMES`; WS-CORE). Proposed in the PR.
  - The Austin HOME adapter rule (WS-TX).
  - Verify the Census Address Count Listing Files as a public MAF-derived source (lead only).
  - The official bundles and the app are not rebuilt in this PR.
