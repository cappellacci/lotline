### LB-NNN · 2026-11-12 · Calibration: the five-state ADU joint refit (D-079), run once
- **Question:** Under D-079's pre-registered rule, which ADU model form wins the five-state refit, and how
  well does each predict a state it has not seen at data tiers 0, 1 and 2 (D-075), with tests A–C (D-074)?
- **What I did:**
  - Ran `scripts/dev/adu_joint_refit.py` once on `main` at `1c7ad001` (the merge of #409), offline, with seed
    20261111 and 20,000 draws.
  - An earlier start on the same commit was stopped before any fit, at Ben's request, so he could review the
    year windows; its output was discarded unread.
  - The windows were then confirmed unchanged, as were the other four "Built" choices. These are recorded in
    the D-079 "Built" note.
  - Wrote the README, a results page and this fragment. Nothing was tuned after a score was read.
- **Inputs:** the processed tables on `main`; `config/params/adu.yaml` (#400's undercount table, Dallas out);
  `config/validation/adu_roll_counts.csv`; `reports/adu-joint-refit-2026-11/fit_set.csv` and `events.csv`
  (written before any fit). St. Paul (MN V5) stayed blind, and no `--unblind` was passed.
- **Outputs:**
  - `reports/adu-joint-refit-2026-11/`: README.md, results.html, run-log.txt, summary.json, fits.csv,
    tiers.csv, logscores_tier1.csv, test_a.csv, test_b.csv, test_b_towns.csv, test_c.csv, event_check.csv.
  - Results page: https://claude.ai/artifact/WUDTnwJ4hXMNXwy5nrUUcr
  - Docs: Ben's 2026-11-12 confirmations, in the D-079 "Built" note in `docs/analysis_plan.md`.
- **Findings:**
  - **Form A is kept.** Neither form passes D-075's claim rule at any tier, so the tool shows tier-2 ranges.
    - Form A predicts no state usefully at any tier.
    - Form B predicts 2 states usefully at tier 0, 1 at tier 1 and 0 at tier 2. Ohio cannot be scored, so 4
      of the 4 other states were needed.
  - Form A's median is off by more than ×2 in every scored state: Minnesota is over-predicted about 2.7×; NC,
    OR and TX are under-predicted 2.7–15×.
  - Tests A–C, counted state by state:
    - Form A passes 1 (test A, Texas). Form B passes 0.
    - Test B fails in NC and OH for both forms: the model expects far more suburban ADUs than the rolls show.
    - Test C (Form A only) fails in all five states: 43 of 73 places fall below their counted rate.
  - Refit Form A: θ 0.756 per 1,000 (0.554–1.112), α 1.92, m_o 1.0, m_x 0.4. Leaving out Minnesota doubles θ.
  - Form B's tier-2 update collapses to 1–3 effective draws in MN, NC and OR.
  - The sensitivities don't change the decision: no tier passes at the field k's 5th or 95th percentile or
    without the low-recall rows.
  - Fort Worth's ADU count (not in the fit): central 64, no-kitchen 108 (2015–2026).
- **Decisions:**
  - None made here. The PR proposes HANDOFF entries for the form (A, by D-079's rule) and the test results.
  - Writing the refit values to config, and what to do about the failed tests, are put to Ben.
- **AI:**
  - Claude Code ran the script and wrote the README, page and fragment from its outputs.
  - Every number in the README and page was read from the run's CSV and JSON files.
  - One README sentence that misread `summary.json` was caught and removed before commit.
- **Open / next:**
  - Ben's calls on config and on the failed tests.
  - τ's profile was not saved by the run.
  - Building Austin's HOME-rule inferred counts is a later follow-up.
