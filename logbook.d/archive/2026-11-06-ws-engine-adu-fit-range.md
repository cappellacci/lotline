### LB-NNN · 2026-11-06 · engine · Where should the ADU calibration range come from?

- **Question:** the ADU anchor is fitted on our own five states, but the calibration range that drives the
  extrapolation widening still describes Portland, Seattle and Los Angeles, and 96–99% of eligible parcels in
  MN, NC, TX and OH sit outside it. How should the range be rebuilt from the fit set, and how will we know it
  doesn't make the intervals too narrow?
- **Outputs:** D-060 in `docs/analysis_plan.md` (method only, before any run). The range is the
  eligible-weighted 5th–95th percentile of rent and home value over D-053's 316 fit place-years, with the
  rate at its min/max over 2016–25. The test is leave one state out over five states with widening, current
  range against the fit-set range recomputed per fold. The rule adopts it if no more states are missed and
  place-total P10–P90 coverage is at least 70%. Frozen V9 stays on the old range.
- **Decisions:** D-060 approved by Ben ("Approve D-058", given under its first number; renumbered D-060 because main and #323 took D-058 and D-059), before any code or run.
- **AI:** Claude Code (Opus 5.5) drafted the entry. The fit set was read from `scripts/dev/calibrate_adu.py`
  and `adu_anchor.yaml`, where the widening applies from `hazard.py`, `validation/v9.py` and D-043/D-053, and
  the D-number from every local and remote branch.
