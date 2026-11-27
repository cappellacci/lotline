### LB-NNN · 2026-11-19 · Validation: V8 Wisconsin scored against the Census permits (D-105)
- **Question:** Did the frozen national-data-only prediction for Wisconsin (D-104) cover what was actually
  permitted in 2021-2025?
- **What I did:**
  - Wrote `scripts/dev/v8_score.py`. It checks the rebuilt baseline equals the frozen file, unblinds
    Wisconsin's Census place permits in memory, and scores the D-104 reading rules.
  - Ran it from a fresh GitHub clone, because the local `main` ref was behind #500.
- **Outputs:** `scripts/dev/v8_score.py`, `reports/wi/V8-score.json`, `reports/wi/V8-score.md`,
  `docs/analysis_plan.md` D-105.
- **Result:** fails the pass rule. Observed 112,166 permitted homes vs P50 75,347 (P10-P90 53,126-103,715),
  ×1.49.
  - Single-family is inside (×1.14).
  - 5+ units (×2.43) and 2 units (×1.98) are well above the range.
  - Overlap is low: almost every place sits outside the calibration range, as flagged.
- **Decisions:** Ben 2026-11-19: unblind and score Wisconsin. No fix is made; the method questions go to Ben in
  the PR.
- **AI:** Claude wrote the script and the entries. Checks:
  - the rebuilt baseline and overlap were checked equal to the frozen file;
  - the observed counts were cross-checked against the 2010-2019 history;
  - the permit rows with no place code were counted (50 units).
- **Open / next:** Ben decides whether and how to look into the low start and the apartment miss.
