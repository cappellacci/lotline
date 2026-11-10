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
  - The table script was smoke-tested on synthetic places. Full suite: 1,712 passed.
- **Development run (Ben: "Yes, run it"):** `scripts/dev/fee_dev_run.py --origin 2025 --state MN NC OH TX`
  -> `reports/fees-phase2-run/` (log, totals, summary). Pencil-out table on real data ->
  `docs/research/fee-pencil-out.md`. Results page published at
  https://claude.ai/artifact/LN5G4rajXAxVi3uhEXtwDs. The benchmark adds +0.8% to +1.4% of the baseline;
  real fees halved add +0.1% to +0.2%; the rise mirrors the cut. Numbers in D-073. Checked: state sums
  against the per-place totals; the page's statements against `totals.csv`; the page rendered once with no
  console errors. No outcome was read.
- **Open / next:** a better new-home value for NC, OH and TX (the pencil-out land values rest on the ACS
  median); stacking and the fee-structure stretch.
- **Addendum (2026-11-10):** results page rebuilt after Ben's review and the 2026-11-09 office hours (two
  worlds side by side, plain bars, method folded; then a "why believe it" part). Found that the headline
  mean (848) implied ε ≈ 0.7 because the triangular elasticity draw is lopsided; Ben chose to lead with the
  central estimate (about 418) and the range. Recorded in D-073. Page republished (v3) at the same link.
- **Addendum 2 (2026-11-10), D-076:** elasticity drawn lognormal (median 0.3, p95 1.75); statewide fee
  run over every baseline place in MN, NC, OH, TX (2,937 places) -> `reports/fees-statewide-run/`.
  Halving real fees adds about 1,480 homes statewide (0.09%); the benchmark about 13,200 (0.8%). Checked:
  the draw's median and p95 by test (31 fee tests pass); each state's P50 against its central path; the
  page's numbers against `summary.json`; the page rendered with no console errors. Results page v4 at
  the same link.

