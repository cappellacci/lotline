### LB-NNN · 2026-11-20 · ADU · Why is NC's no-reform ADU forecast so far above its history, and are the "zero" places real?

- **Question:** NC's no-reform ADU forecast (~650 a year) sits far above the counted history (~290). What
  drives the gap, and are the places counted as having zero ADUs really zero?
- **Outputs:**
  - Measured split (in chat, 2026-11-19): counted places P50 453 (their own medians sum to 306, against a pace
    of 298); per-place drift adds ~150; places with no counts add ~140. Ben chose to keep the drift and
    explain it, then later asked another session to re-centre it (branch ws/adu-drift-mean).
  - Coverage fix: `src/lotline/model/scenarios/adu.py` (`observed_per_year`, `observed_terms_by_k_row`) and
    tests in `tests/model/test_nc_gutcheck.py`. Dated deviation in `docs/analysis_plan.md` (2026-11-20),
    proposed as a D-entry.
- **What Claude did and how it was checked:** ran the ADU engine for each state before and after (one state at a
  time, stored inputs, 1,000 draws), hand-worked unit tests for the new window rule, and the window and
  undercount test files. Peak memory per state was 3.7-7.2 GB. Running two full `place_inputs` rebuilds at
  once is the likely cause of the 2026-11-19/20 freezes on the 16 GB machine.
