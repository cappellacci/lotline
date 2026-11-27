### LB-NNN · 2026-11-05 · validation · V9 unblinded: how did the blind Oregon prediction do on 2–4 unit buildings?

- **Question:** Ben said "unblind and score" (2026-11-05). This entry scores the frozen V9 missing-middle
  targets against Oregon's 2018–2025 Census BPS.
- **Outputs:**
  - `scripts/dev/v9_or_score.py`;
  - `reports/v9-oregon/` (totals, places, headline by year, run log);
  - results under D-051 in `docs/analysis_plan.md`.
- **Result:**
  - The headline 2018–2025 total is 1,753 against P10 1,738 / P50 2,658 / P90 6,469. That's inside the
    range, a "useful" verdict and D-051's pass rule, but only by 15 buildings.
  - The model over-predicts HB 2001's response: observed building stays at about 165–268 a year, while the
    model's P50 rises to 712 by 2025.
  - The no-reform benchmark beats the model over 8 years (CRPS 279 against 691), but not over 2018–2022
    (174 against 62).
  - Place ranges are too narrow: mean randomized coverage is 0.57.
- **ADU targets:** not scored yet. The Portland and Bend permit adapters don't exist; WS-OR was asked to build
  them.
- **What Claude did and how it was checked:**
  - The script regenerates the frozen draws and refuses to score unless their summaries are identical to the
    freeze file; they were.
  - Unblinding was in memory only: the processed tables on disk stay blind.
  - Checked that the 74 place-years with no BPS row are all in places with a zero baseline.
  - Nothing was tuned after unblinding.
