### LB-NNN · 2026-10-20 · Fix: D-023 estimator separation and numerical guards (first real run aborted)
- **Question:** Why did the one-time D-023 run diverge, and how is the estimator made safe without looking at
  its results?
- **What I did:** treated the run as aborted and did not read its log (moved, unread, to
  `reports/adu-d023/aborted-2026-10-20-log.txt`). In `src/lotline/model/estimate_adu.py`: separation removed
  before fitting (all-zero places, years and one-signed indicator columns, then the Correia-Guimarães-Zylkin
  iterated rectifier), repeated until stable, every drop recorded; modifiers as z-scores (θ per SD);
  `EstimationError` on non-convergence, |η − offset| > 30, |b| > 20 or a zero SE, with the same guards in the
  bootstrap, randomization inference, leave-one-out and transport (which also refuses means above 5% of
  eligible parcels a year). `scripts/dev/estimate_adu.py --out` writes named CSVs to a directory only after
  every stage succeeds. Dated note under D-023.
- **Inputs:** coordinator's description of the failure (not the log).
- **Outputs:** the module, script, tests, `docs/analysis_plan.md`, the aborted log.
- **Findings:** on synthetic panels with all-zero cohort cells the cells are dropped and β and θ still covered
  (≥ 15 of 20 panels); a separating modifier is found by the rectifier (no single column reveals it); the
  diagnostics raise on a non-convergent fit, a saturated fit and an absurd transport draw.
- **Decisions:** none new (dated note under D-023).
- **AI:** Claude wrote the fix and tests; no real-data estimate was looked at.
- **Open / next:** the one rerun.
