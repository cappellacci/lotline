### LB-NNN · 2026-11-19 · Validation: why Wisconsin's V8 forecast starts below 2019 (D-106)
- **Question:** Why does the frozen baseline start about 12% below Wisconsin's 2019 permits?
- **What I did:** traced the baseline step by step for Wisconsin at origin 2019, using the blind tables only,
  then checked the same step in the other states.
- **Outputs:** `scripts/dev/v8_baseline_diagnosis.py`, `reports/wi/V8-baseline-diagnosis.md`,
  `docs/analysis_plan.md` D-106.
- **Finding:**
  - The shrinkage step removes 11% of the statewide total (duplexes and apartments about −20%), and it does so
    in every state.
  - The low start explains under a third of the V8 miss; most of the rest is apartment growth after 2019.
- **Decisions:** Ben 2026-11-19: diagnose only. The proposed fix (benchmark the shrunk levels) is a separate
  decision.
- **AI:** Claude wrote the script, report and entry. Checks: the step totals were reconciled with the frozen
  2021 mean (15,460, identical).
- **Open / next:** Ben decides on benchmarking; if yes, rerun V1 with statewide totals scored.
