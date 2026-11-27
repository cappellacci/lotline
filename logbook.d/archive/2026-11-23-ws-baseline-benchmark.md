### LB-NNN · 2026-11-23 · ENGINE · Does keeping each shrinkage group's total fix the baseline's low start?

- **Question:** D-106 found the Fay-Herriot step lowers state totals (Wisconsin −11%). Does benchmarking the
  shrunk levels fix it without hurting place-level accuracy?
- **Outputs:**
  - `benchmark_levels` in `src/lotline/model/baseline.py`;
  - the switch in `config/params/baseline.yaml` (off);
  - tests in `tests/model/test_baseline_model.py`;
  - dated deviation in `docs/analysis_plan.md` (2026-11-23).
- **What Claude did and how it was checked:**
  - Hand-worked tests: ratio, totals kept, weights unchanged.
  - V1 back-test off and on for the five development states.
  - Wisconsin after the fact from the blind tables (off reproduces the frozen 75,347 exactly).
  - Today's effect per state.
  - A first measurement script patched only one module's settings and showed zero change. That was caught
    and rerun with both modules patched; the V1 runs pass settings directly and were not affected.
