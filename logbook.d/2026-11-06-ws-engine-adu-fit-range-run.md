### LB-NNN · 2026-11-06 · engine · Does the fit set's range hold up as the ADU calibration range? (D-060 run)

- **Question:** with D-060's pre-registered rule, does re-basing the ADU calibration range on the anchor's
  own fit places keep states covered and place intervals at least 70% calibrated?
- **Outputs:**
  - `scripts/dev/adu_reference.py --fit-set [--write]`, the generator that writes the range into
    `config/params/hazard.yaml` with sources;
  - `scripts/dev/calibrate_adu.py --range-test` and, in `model/calibrate_adu.py`, `weighted_percentile`,
    `fit_set_range`, `place_distances` and widening in `predict_unseen_state`;
  - `reports/adu-d060-range/` (log, statewide, places, summary and ranges CSVs, plus D-053's command
    rerun);
  - the D-060 results in `docs/analysis_plan.md`;
  - `hazard.yaml` (now the fit-set range), the regenerated parameter table, `hazard.py` and
    `docs/model_and_assumptions.md` text, and the `aggregate.yaml` overlap-flag notes;
  - `hazard.PRE_D060_CALIBRATION`, pinned in `validation/v9.py` so the frozen V9 prediction keeps its range.
- **Result:** no state missed under either range. Place P10–P90 coverage is 73.6% under the fit set
  against 74.1% under the West Coast range. **F adopted.** Half the held-out eligible parcels now sit
  inside the range, against 13% before. Every fit state's overlap flag now reads high; the thresholds were
  not retuned and are left to Ben.
- **Deviation:** the no-widening check doesn't match D-053's published table, but it equals D-053's own
  command rerun on the same tree. D-053's table no longer reproduces on today's main (recorded in D-060).
- **Decisions:** D-060 adopted by its pre-registered rule; nothing new proposed for HANDOFF. Open for
  Ben: whether to retune the overlap-flag thresholds, and whether D-053's table should be regenerated.
- **AI:** Claude Code (Opus 5.5) wrote the code, tests, run and write-up. Checks:
  - hand-worked unit tests for the weighted percentile, the fold range, place distances, mean-keeping
    widening (and exact reproduction at distance 0) and the V9 pin, which a mutation check showed catches
    removal;
  - D-053's command rerun, matching the no-widening arm exactly;
  - the overlap medians recomputed under the old range, matching PR #311's values;
  - the full test suite and `compliance_check.py`.
