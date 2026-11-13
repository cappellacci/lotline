### LB-fragment · 2026-11-13 · ADU model · Does fitting a separate effect per ADU rule detail fix the joint refit's misses?

- **Outputs:** `reports/adu-version-c-2026-11/` (PLAN.md, README.md, results.html, run/), `scripts/dev/adu_version_c.py`,
  `scripts/dev/apply_adu_rules_proposed_2026_11.py`; branch `ws/adu-version-c` (unmerged; config there holds PR #417's
  proposed rows for the test only).
- **Answer:** no. Version C (separate effects for not by right, 1 and 2+ parking spaces, other restrictions, size) fits
  the past slightly better than Form A on the same rows (AIC 11 better) but predicts held-out places no better, passes
  no data tier, and its effects depend on North Carolina. Form A on the new rows alone passes test C in all five states.
- **HANDOFF:** no decision added. Ben dropped version C as a predictor on 2026-11-13 (code kept on the branch).
  Still open for Ben: accept #417's rows.
- **What Claude did:** wrote the plan before fitting, applied the rows on a branch, wrote and ran the fit and scoring
  wrapper on `adu_joint_refit`, added two exact speedups (each checked equal to the originals), built the results page.
  Disclosed: a timing smoke test showed C's estimates before the main run; nothing changed after it.
