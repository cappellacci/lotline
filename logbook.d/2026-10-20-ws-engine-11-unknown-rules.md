### LB-NNN · 2026-10-20 · Build + calibration: unknown rules (D-022), rule coverage (D-021), ADU fit 3 (D-019), state totals
- **Question:** With uncoded rules treated as unknown, rule coverage, graded rule shares and place effects,
  what ADU uptake do our post-reform places support, and what does the Handbook ADU reform add per state?
- **What I did:**
  - D-022: five rule types (none, owner occupancy only, other restrictions, both, Handbook); blank fields
    and uncoded places sampled from coded rules (by field; by state and size band); citywide parking reforms
    settle blank ADU parking.
  - D-021: coverage from zones and lot minimums on parcels (judgment where rolls can't measure it); county
    rows mix coded places filed under them (Wilmington).
  - Fit 3 pre-registered (pushed as commit 4aa1113) and run once after the NC rebuild: Poisson-gamma place
    effects, blank fields per place, graded shares on a grid. Fit 2's first run had a variable-name bug
    (observed counts overwritten); discarded, fixed with a regression test, re-run once.
  - `run(..., summary_by="state")`: state totals as percentiles of summed draws over non-overlapping places;
    place effects drawn per place.
- **Inputs:** config/reforms (main after #166, #168–#170); permits flagging ADUs; NC rebuilt (onemap_parcels,
  eligible; Wake's roll needs a hand download and was left as is).
- **Outputs:** `src/lotline/model/scenarios/adu.py`, `src/lotline/model/calibrate_adu.py`,
  `config/params/{adu,hazard}.yaml`, `scripts/dev/{calibrate_adu,adu_dev_run,adu_current_rules_check}.py`,
  tests, `docs/analysis_plan.md` (D-019 fits 2–3, D-021 note, D-022), `docs/model_and_assumptions.md`.
- **Findings:** anchor 1.04 per 1,000 (90% 0.45–3.17), place-effect variance 4.7, owner-occupancy share
  1.0 (0.9–1.0, estimated), other share not identified (0.3 kept). Test: Raleigh 230 vs mean 141 (0–687),
  Durham 239 vs 172 (0–865). State totals 2026–30, ADU permits added P10/P50/P90: MN 1,457/2,719/5,065;
  NC 1,727/3,850/8,101; OH 1,046/2,276/5,233; TX 7,731/14,972/29,445.
- **Decisions:** D-019 fit 3 results applied; D-021 implemented; D-022.
- **AI:** Claude designed and wrote the code, tests (hand-worked likelihoods, recovery on simulated data,
  type and coverage cases) and docs; pre-registered and ran each fit once; reported misfits without refitting.
- **Open / next:** most rules are still uncoded (drawn); Minneapolis's post-2020 decline isn't captured;
  m_x is not identified; Wake roll needs a manual download.
