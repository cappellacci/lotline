### LB-NNN · 2026-11-13 · ADU model · Does ADU uptake drift by calendar year, and can the model forecast places it has seen? (D-085 proposed)

- **Question:** Ben asked to try a time trend with a time-split test ("Cool let's try both of those"). The
  model has no year term, and no test fits early years and scores later ones, which is the scenario's job.
- **Outputs:** D-085 (proposed) in `docs/analysis_plan.md`, on `ws/adu-time-trend`.
- **What Claude did and how it was checked:**
  - Re-read the D-045 audit and corrected an earlier chat claim: its year pattern (observed ÷ expected 2.92 in
    2016 to 0.48 in 2025) means early years were under-predicted, and it was read under the logistic ramp that
    D-048 dropped. So D-085 assumes no sign for the trend.
  - Counted inputs only for test D: 37 places, 323 place-years with years on both sides of 2020 (MN 21, NC 10,
    OR 4, TX 2). No residual or count was read.
  - Nothing fitted yet; waits for Ben to accept.
