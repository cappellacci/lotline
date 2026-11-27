### LB-NNN · 2026-10-20 · Validation: V1 re-run on the rebuilt tables (D-012 note)
- **Question:** After the Mecklenburg holdout fix (D-012) and the data rebuilds, does V1 still pass 13 of 48?
- **What I did:** re-ran `python -m lotline.model.backtest --state MN NC OH TX --spec B`; made the backtest's
  `--rule-version` default follow `build.eligible.RULE_VERSION` (the pinned 1.0 no longer exists); wrote a
  dated re-run note under D-012 in `docs/analysis_plan.md`.
- **Inputs:** processed BPS (NC rebuilt, 37119 ends 2022), eligible parcels rule 1.1, market tables.
- **Outputs:** `src/lotline/model/backtest.py`, `docs/analysis_plan.md` (D-012 note).
- **Findings:** 17 of 48 cells pass (was 13): beats 39, coverage 34, bias 25; MAE 11.62 / 0.370 / 0.188 / 2.13
  (1 / 2 / 3–4 / 5+). The change mixes D-012 with D-014, D-017, #158 and new parcel rolls; it can't be split
  after the fact because the old tables were rebuilt in place.
- **Decisions:** none new (dated note under D-012).
- **AI:** Claude ran the backtest and compared it with the D-011 figures recorded in PR #131.
- **Open / next:** to attribute future changes, keep the previous run's long CSV next to each re-run.
