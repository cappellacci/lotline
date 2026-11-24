### LB-NNN · 2026-11-24 · Review · Does every report and decision the analysis plan cites exist on `main`? (thread 17)

- **Question:** Thread 17's cleanup lists found that `docs/analysis_plan.md` cites reports and a decision (D-086)
  that existed only on unmerged branches. A judge following those references would find nothing.
- **Outputs:**
  - `reports/review/2026-11-code-review.md`: the thread's review log, with the Part B cleanup lists (PRs,
    Dependabot, issues, local clutter) proposed for Ben and findings A1 to A4.
  - `docs/analysis_plan.md`: the D-086 entry from #421 with a dated outcome; #411's "Confirmed by Ben, before the
    run" lines in D-079.
  - Reports brought from their branches: `reports/adu-joint-refit-2026-11/` (#411),
    `reports/{mn,nc,tx,or}/mm-rule-checks-2026-11.md` and `reports/or/mm-first-events-2026-11.csv` (#395, #397,
    #398, #401), `reports/adu-rule-history/` (#422 to #425, each with a note that its config rows were not
    merged), `reports/adu-covariate-screen-final-rows/` (`ws/adu-screen-new-rows`), with their logbook fragments.
  - `scripts/dev/adu_covariate_screen.py`: the `--m-owner` and `--m-other` flags the screen's README uses
    (defaults unchanged).
- **Decisions:** none new. A1 (D-060's calibration range never reached `main`; partly cancelled by D-091's own
  counts) is put to Ben in the review log.
- **What Claude did and how it was checked:** Claude Code compared every open PR's files with `origin/main` by
  content, and listed every `reports/` path cited in `docs/` that does not exist. The remaining misses are build
  outputs that are gitignored, `xx` placeholders, a URL fragment and D-060's `reports/adu-d060-range/` (A1). No
  config, parameter or engine code changed, so no model number moves. Checked with ruff on the script and
  `compliance_check.py`.
