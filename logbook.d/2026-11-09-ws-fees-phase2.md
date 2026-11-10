### LB-NNN · 2026-11-09 · Build: fee plan Phase 2, dose per building size, fee-rise sensitivity, pencil-out table (D-073)

- **Question:** How should a fee cut reach duplexes and fourplexes, and how do a house, a duplex and a
  fourplex compare at today's fees and after a cut (office hours 2026-11-03, A4, A5)?
- **Decisions (Ben, 2026-11-09):** per-type elasticity dose; no effect on 5+ unit buildings (stated);
  stacking with ADU and missing middle deferred; fee-rise sensitivity at +50% of the local fee. Recorded as
  D-073 (`docs/analysis_plan.md`; D-072 was taken on `ws/adu-three-zones`). D-032's status points to it.
- **Outputs:**
  - `src/lotline/model/pencil_out.py` (new): house, duplex and fourplex pro formas at four fee levels.
  - `src/lotline/model/scenarios/fees.py`: `local_rise` mode, per-type fee levels and draws,
    `type_pct_change`, a dose per BPS size class when the baseline is split by size.
  - `config/params/fees.yaml`: `fee_rise_share`.
  - `scripts/dev/fee_dev_run.py`: baseline by size class, fees per type.
  - `scripts/dev/fee_pencil_out_table.py` (new): writes `docs/research/fee-pencil-out.md` (not yet run).
  - `docs/model_and_assumptions.md` (fees paragraph, parameter table).
- **What Claude did:** wrote the code, tests and docs (Claude Code, Opus 5.5).
- **How it was checked:**
  - Hand-worked tests: `tests/model/test_pencil_out.py` (7; duplex and fourplex pro formas line by line,
    cut = fee change + interest) and `tests/model/test_fee_scenario.py` (30; per-size dose, 5+ adds
    nothing, the rise mirrors the cut, the house seed unchanged).
  - The table script was smoke-tested on synthetic places.
  - No model was run and no real data was read.
- **Open / next:** run the pencil-out table and the development run on real data (needs Ben's go-ahead).
  Stacking and the fee-structure stretch come later.
