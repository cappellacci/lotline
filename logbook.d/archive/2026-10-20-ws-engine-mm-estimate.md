### LB-NNN · 2026-10-20 · Study design: D-024 missing-middle estimate, run once
- **Question:** Under the pre-registered D-024 design, how many extra 2–4 unit homes follow a rule allowing them on single-family lots?
- **What I did:** Built the D-024 estimator and its pieces:
  - PPML with place and state × year effects, with the pre-specified fallback;
  - wild bootstrap, randomization inference that reassigns treatment packages;
  - eight checks, robustness fits including D-025's negative binomial run unchanged on a relabelled panel;
  - two out-of-sample tests and added homes.
  Proved it end to end on simulated panels (`--dry-run`, `--dry-run --fallback`) and measured interval coverage (`--coverage`). Then ran it on the real panel.
  The first run (17:06) aborted on an uncaught error after its main estimates were printed. After a mechanical fix, the one rerun (20:35) completed.
- **Inputs:** D-024, D-023 and D-025 (`pooled_adu`); the panel from LB (missing-middle panel); `docs/research/ordinances/batch1-2026-10-20.json` for check 7b.
- **Outputs:**
  - code: `src/lotline/model/estimate_mm.py` (estimation), `scripts/dev/estimate_mm.py` (`--full`, `--dry-run`, `--coverage`), `tests/model/test_estimate_mm_fit.py`, `config/params/mm.yaml` (3 run parameters);
  - results: `reports/mm-d024/` (CSVs, run log, aborted log);
  - the Run note under D-024 in `docs/analysis_plan.md`.
- **Findings:**
  - PPML diverged, so the fallback (Poisson-gamma place random effects) is the main model: overall 0.77 (90%: 0.07 to 1.54). The intervals are too narrow: 68–85% coverage in simulation.
  - Randomization inference p = 0.70. The placebo-dates and placebo-outcome checks fail. Without Minneapolis the effect is −0.02.
  - D-025's negative binomial gives −0.25 (−1.10 to 0.77). Both out-of-sample tests fail.
  - Houston supplies 2,422 of the 2,650 added homes.
  - **No credible missing-middle estimate.**
- **Decisions:** Ben to decide whether D-025's estimator (D-024's wording) replaces the Poisson-gamma fallback as D-024's main estimate; and what the missing-middle scenario uses instead (a new dated entry).
- **AI:** Claude Code (WS-ENGINE-MM) wrote the estimator, tests and run script, ran the analysis and wrote the Run note. Checked by synthetic recovery and coverage tests, two dry runs, a gradient check of D-025's fit on the real panel, and the full test suite, ruff, the compliance check and the params-table check.
- **Open / next:**
  - D-025's mode search needs safeguarding: it fails on synthetic panels with many never-permitting places; two tests are skipped until then.
  - WS-MN codes St. Louis Park 2025 and the explicit "no" rows.
