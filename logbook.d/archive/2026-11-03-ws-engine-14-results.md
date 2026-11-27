### LB-NNN · 2026-11-03 · [engine] · What do D-024 and D-025 find on the four-state data?
- **Question:** thread 14, task 3, plus the task 4 proposal. With 27 treated missing-middle places (against 7 in
  October) and Texas added to the ADU panel, do the pre-registered models now give a credible effect?
- **What I did:**
  - Wrote and pushed the dated "Four-state refresh" entries for D-024 and D-025 in `docs/analysis_plan.md`
    before any fit (on #265), then ran each once on Ben's go-ahead ("let's run the engine", 2026-11-02),
    with one tag sensitivity (firm dates only), as he asked.
  - **D-025 (ADU):** no estimate. The main fit's BFGS hit its 500-iteration limit, so the convergence guard
    stopped the run before any coefficient was reported. A diagnosis that read convergence information only
    (no coefficients) found no dropped columns, no separation and nothing at a bound. Recorded as such; not
    re-run (a re-run needs a new dated entry and Ben's decision).
  - **D-024 (missing middle):** converged. Overall 1.75 (0.27 to 3.27) on the log scale, but randomization
    inference p = 0.29, the 5+ unit placebo fails at the same size, out-of-sample A fails, and El Paso (in
    force all panel long) supplies 54% of the added homes. Leads, placebo dates and leave one out pass. Firm
    dates only: 0.93 (−0.25 to 2.87). Reading, for Ben to confirm: still no credible estimate; the in-state
    estimate stays validation only.
  - Task 4: wrote a proposed V5 freeze method and file format; nothing frozen, no prediction computed.
- **Inputs:** `config/reforms/{mn,nc,oh,tx}.csv`; `~/lotline-data/processed/{mn,nc,oh,tx}` through the holdout
  filter.
- **Outputs:** `docs/analysis_plan.md` (outcome entries under D-024 and D-025); `reports/mm-d024-4state/`
  (11 CSVs and the log); `reports/adu-d025-4state/run-2026-11-02-log.txt`;
  `reports/engine14/v5_freeze_proposal.md`.
- **Decisions:** none made. Proposed: D-024's reading above; how to handle D-025's non-convergence; the V5
  method (three questions in the proposal).
- **AI:** Claude Code (Opus 5.5) wrote the entries, ran both models with a background runner and wrote up
  the results. The figures in the entries were read from the run's CSVs and log. No held-out row was read
  or printed; no `--unblind`.
