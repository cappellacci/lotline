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

### LB-fragment · 2026-11-14 · ADU model · D-091 built and run: does a drift term make the ADU forecasts better?

- **Outputs:**
  - Code: `adu_forecast` drift functions, 7 new tests, `scripts/dev/adu_drift.py`, `scripts/dev/adu_drift_page.py`.
  - Results: `reports/adu-drift/`.
  - Results page: https://claude.ai/artifact/G4sRpudCfVVXt8PyWV2asM
  - D-091's acceptance, "Built" and "Result" notes.
- **Answer:**
  - **The ranges became honest.** Coverage went from 58% to 81%, and persistence with drift is useful in
    3 of 4 states.
  - **Better predictive power is not shown at the pre-set bar.** The log-score gain is +429 against 2 SE of
    551, and Portland carries most of it.
  - **CRPS:** per place it improves 13%. F1's state totals get worse.
- **HANDOFF:**
  - D-091 accepted (Ben, 2026-11-14) on two conditions: we can roll back, and the report shows clear evidence
    on predictive power. The report meets both.
  - The result awaits Ben, and so does the tool outcome it triggers.
- **What Claude did:**
  - Recorded the conditions as concrete commitments.
  - Built the drift with a rollback test. A hand-worked test caught that 40 Gauss–Hermite nodes
    under-estimate σ for large places (0.55 against 0.8), so I switched to the trapezoid rule on a fine log-d
    grid. This is disclosed.
  - Smoke-ran (status lines only), then ran.
  - Wrote the README and the page around a side-by-side evidence table.
- **How it was checked:**
  - 23 tests pass, and ruff is clean.
  - The rollback check gap is 3.6 × 10⁻¹⁵.
  - The page was rendered and read in the browser. Its claims were checked against the CSVs; one sentence
    (that the losses are small places) was corrected to name Bend.
