### LB-NNN · 2026-11-05 · validation · V9 ADU targets: how did the blind Portland and Bend prediction do?

- **Question:** score the frozen V9 ADU targets (D-051, D-052) against Portland's and Bend's 2018–2025 ADU
  permits, now that #300 added their adapters. Ben said "merge and commit".
- **Outputs:**
  - `scripts/dev/v9_or_score.py` now scores ADU targets too;
  - `reports/v9-oregon/adu_scores.csv`, `adu_by_year.csv` and `adu_posthoc_history.csv`;
  - ADU results under D-051 and a result line under D-052 in `docs/analysis_plan.md`.
- **Result:** every ADU target missed, so V9 fails its pass rule.
  - Portland: 1,930 observed, against a transfer range of 3–1,418 and an own-history range of 4,070–17,832.
  - Bend: 414 observed, against 0–206.
  - Portland's permits fell by half after 2018, and the model has no mechanism for that.
  - The own-history variant scored worse than transfer for Portland (CRPS 4,934 against 1,242).
  - A labelled post-hoc re-run on the adapters' own 2010–2017 counts still misses.
- **What Claude did and how it was checked:**
  - Draws are regenerated and checked identical to the freeze before any score.
  - Outcomes were unblinded in memory only, with the adapters' default left blind.
  - D-041 counts come from the shared `calibrate_adu.adu_counts`.
  - Flagged-permit counts were checked as a sensitivity.
  - Nothing was tuned.
