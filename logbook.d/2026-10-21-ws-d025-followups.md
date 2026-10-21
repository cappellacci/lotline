### LB-NNN · 2026-10-21 · Validation: D-025 corrected household-growth refit (does growth matter?)
- **Question:** the D-025 main model measured household growth after adoption for 2010–15 adopters (D-031
  (b)). Does correcting it change the ADU result, and do the remaining stages compute on the corrected
  panel?
- **What I did:**
  - Added `build_panel(hh_growth="corrected"|"as_run")` and `--hh-growth` to `scripts/dev/estimate_pooled_adu.py`.
  - Wrote the plan and the "matters" rule (overall moves > 0.5, its interval's zero status changes, or the
    transport verdict changes) as a dated note under D-031 before running.
  - Ran `--full --hh-growth corrected` once (Ben approved): the main model, randomization inference with dose
    paths moved, checks, robustness, D-031 sensitivity runs and transport.
- **Inputs:** D-025, D-031; the as-run main (`reports/adu-d025/run-2026-10-20-log.txt`); WS-ENGINE's as-run
  transport (`reports/adu-d025/transport-2026-10-21-log.txt`).
- **Outputs:** `reports/adu-d025/corrected-2026-10-21-log.txt`, `reports/adu-d025/corrected-2026-10-21/*.csv`
  (panel.csv gitignored), the D-031 dated notes in `docs/analysis_plan.md`.
- **Findings:**
  - 5 places changed. Overall 2.37 (0.12–4.51) vs 2.26 (0.22–4.21); θ_hh 0.17 vs −0.37, both
    uninformative. By the pre-set rule, household growth does not matter for this test.
  - Randomization inference computed this time: p = 0.111 (970 of 999). Leads still fail (p = 0.052).
    Transport still fails (1 of 3 totals, 15% yearly).
  - Additive imputation is not estimable (2 contributing places). All three sensitivity runs sit inside the
    main interval (≈ 2.9–3.0).
- **Decisions:** none new (dated notes only; Ben's option (i)).
- **AI:** Claude Code wrote the switch, the plan and the results note, ran the job once and transcribed the
  numbers from the committed log. Tests: 884 passed; ruff clean; compliance 0 FAIL.
- **Open / next:** HonestDiD for the corrected main once WS-ENGINE pushes `pooled_adu.honest_bounds`.
