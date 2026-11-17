### LB-NNN · 2026-11-16 · Method: missing middle's ramp after St. Paul (D-100, proposed; method only)
- **Question:** St. Paul's blind test missed because the effect came faster than C4's ramp. Should the ramp
  change, and is it one ramp or one for local reforms and one for state mandates?
- **Decisions:** Ben: "Draft a ramp entry" (2026-11-16). The entry is a proposal; the run needs his go-ahead.
- **What Claude did:**
  - Read run 10's fits (`reports/mm-d092/run10-refit-phi/fits.csv`, `structure.csv`): the half-way point is
    4.0 (1.0–6.0) with Oregon and unpinned without it. 25 of 86 Oregon events are in 2025.
  - Wrote D-100: R0 (C4), R1 (one ramp, St. Paul added) and R2 (a ramp per adoption route: HB 2001-covered
    Oregon places against locally adopted ones), chosen by D-092 §5's 2-SE rule. The scenario would use the
    state-required ramp; a cheaper option keeps C4 with a fast-ramp sensitivity.
- **How it was checked:** the event counts and ramp values were read from the run 10 files; no fit or count
  was run.
- **Outputs:** D-100 in `docs/analysis_plan.md`.
- **Run 1, approved and run:** Ben said "Approve, run the refit".
  - **Code:** `lotline.model.mm_routes` (HB 2001 route rule, age shift, `fit_routes`; 5 hand-worked tests),
    `estimate_mm.build_panel(include=)` (refuses a blind holdout; 2 tests), `config/crosswalks/or_hb2001_metro.csv`,
    `scripts/dev/mm_ramp_d100.py` (with `--dry`), `mm_ramp_d100_summary.py`, `mm_ramp_page.py`. D-092's scripts
    now drop their listed places instead of asserting none are in the panel.
  - **Dry run:** 57 state-required and 37 locally adopted fit places (29 small Oregon towns, 7 elsewhere, St. Paul).
  - **Result: C4 stays.** In the fit, local adopters reach half speed at 0.5 years and state-required places at
    4.0, in every fold. Held out, neither R1 (−2.68, SE 1.70) nor R2 (−0.15 against R1, SE 1.01) beats the one
    before it by 2 SE. The scenario's ramp is unchanged.
  - **A mistake and its fix:** the run stopped at its last step on a JSON key bug; the summary was rebuilt from the
    saved fits and scores, without refitting.
  - **Shared data incident:** rebuilding MN BPS with St. Paul's released rows broke `main`-based runs in the ADU
    session (a holdout-leak check stopped them). Rebuilt blind from a clean `main` checkout and told that session;
    after #442 merges, MN BPS needs one more offline rebuild.
  - **Outputs:** `reports/mm-d100/run1/` (README, fits, scores, routes, summary, run log, page). Page:
    https://claude.ai/artifact/GNK6HcwX39PvgsdWwkisJ5
