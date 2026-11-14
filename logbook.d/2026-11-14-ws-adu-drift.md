### LB-fragment · 2026-11-14 · ADU model · How wide should an own-history ADU forecast be?

- **Outputs:** D-091 (proposed) in `docs/analysis_plan.md`, on branch `ws/adu-drift` (stacked on `ws/adu-time-split`,
  #429).
- **Answer:** a method entry, written before any run.
  - It adds a per-place period drift d = exp(σ z) to the forecast window, with median 1.
  - σ is learned for each held-out state from the other three states' windows.
  - Rules carried over from D-090: rule 1 (3 of 4 states) and rule 2 (beat persistence by 2 SE).
  - New rule 3: calibration, with 65–95% of places inside their own P10–P90.
- **HANDOFF:** proposes D-091. Ben to accept or amend, including what the tool does in each outcome.
- **What Claude did:**
  - After D-090's run, measured how far large places moved from persistence (SD of log ratio 1.07, about
    ×2.9, 9 places).
  - Disclosed that this was computed on the windows to be scored, which is why the spread is learned leaving
    one state out.
  - Ben chose the leave-one-state-out route.
- **How it was checked:** the entry was read against D-090's code and outputs. Nothing was run for D-091.
