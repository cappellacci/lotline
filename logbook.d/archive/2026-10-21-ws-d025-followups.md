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
- **Open / next:** see the HonestDiD addendum below.
- **Addendum (HonestDiD, same day):**
  - Merged WS-ENGINE's `honest_bounds` (68c7ae6) into #193 and #198 and reviewed it against 3f0d5e2: the
    formulas, grids and interval match.
  - Ran `--honest` once per main (plan note first). Both leads refits dropped δ_−1, because the year before
    adoption had 0 ADU permits in 22 place-years. `event_study_inputs` had counted it as 0, so the printed
    bounds are invalid. Fixed: it now raises, with a test.
  - Valid result: the pooled effect's interval includes 0 even with no trend violation (breakdown M̄ = 0);
    only the 0–1-year band excludes 0, and its robustness can't be computed.
  - Charts: `reports/adu-d025/figures/asrun_vs_corrected.png`, `event_study.png`,
    `permits_by_event_time.png`.
  - Also: the merge into #193 (ce75952) swept in an untracked run `panel.csv`; removed in 3032805 and
    ignored. It remains in that branch's history.
  - Options for Ben (pool leads, the announcement-dated model, or report as not identified) are in D-031.
- **Decision (Ben, 2026-10-21):** option 3. HonestDiD is recorded as not identified (dated note under D-031); the
  inference rests on randomization inference (p = 0.111) and the failed leads test. It is rerun with the tested
  `--honest` stage once the multi-state panel provides adopting places with permits in the years just before
  adoption and longer pre-periods. Nothing else run.
