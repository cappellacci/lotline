# Lotline: Analysis plan (pre-registration)

**Status: DRAFT, not yet pre-registered.** Per the validation plan (§2, integrity rule 1), §3 of
`docs/research/lotline-validation-plan.md` (tests and pass/fail criteria) is copied here, reviewed by Ben, committed
and tagged `prereg-v1` **before any V3 outcome model runs**. Until then this file only records decisions made
ahead of pre-registration, so they aren't lost.

## Decisions and deviations log

Dated, append-only. Each entry says what changed from the research documents, why, and who decided.

### D-001 · 2026-10-06 · V0 BPS reconciliation tolerance
- **Was (validation plan §3, V0, proposed):** "BPS totals match exactly."
- **Now:** our BPS place sums must be **within 1% of Census's state total in every compared year**; years outside
  1% are listed in the V0 report for explanation. Exact matches are still counted and reported.
- **Why:** Census revises state and county totals after the annual survey with late reports and corrections that
  the place files don't always carry (Census BPS methodology), so exact agreement isn't achievable even with a
  correct pipeline. First run (2026-10-06): exact match MN 10/32, NC 28/31, OH 20/34, TX 6/34 years; within 1%
  MN 30/32, NC 29/31, OH 34/34, TX 21/34. The check is read as directional evidence that the pipeline counts what
  Census counts.
- **Decided by:** Ben, 2026-10-06 (PR #66).
- **Open:** Texas 2003–2014 runs 1–2% high (Denton County unincorporated, 2014); for WS-TX to explain.

### D-002 · 2026-10-14 · V1 baseline specification B (variance floor from a place's own history)
- **Was (WS-ENGINE spec A, declared before the first run):** a place's level and its uncertainty from its last 5 years only.
- **Now (spec B):** the same, plus a floor on a place's year-to-year variance from its own longer history, so a one-off subdivision year in a tiny township isn't read as its normal pace.
- **Why / how decided:** added **after** the first Minnesota run showed the problem. It is logged here as a deviation for that reason. On the V1 windows, A passes 19 of 48 cells and B 17, but B has 13% lower error for 5+ unit buildings. Both are reported (PR #93).
- **Decided by:** Ben, 2026-10-14.

### D-003 · 2026-10-14 · V1 coverage uses randomized coverage for whole-number outcomes
- **Was (validation plan V1):** "P10–P90 coverage 70–90%", read as the share of outcomes inside the interval.
- **Now:** randomized (probability-integral) coverage. For counts that are mostly 0, the inclusive check reads ≥90% almost everywhere and flatters any model. The inclusive share is still reported.
- **Decided by:** Ben, 2026-10-14 (PR #93).

### D-004 · 2026-10-14 · V1 bias is judged on the model's mean
- **Was:** "no systematic bias in the post-2022 window" (statistic unspecified).
- **Now:** mean signed error of the model's **mean** forecast (not its P50) for 2023 on, within ±25% of the model's post-2022 MAE. Means add up to state totals; medians of skewed counts don't.
- **Decided by:** Ben, 2026-10-14 (PR #93).

### D-005 · 2026-10-14 · V1 scores only places with at least 20 eligible parcels
- **Was:** every non-reforming place scored.
- **Now:** places with fewer than `v1_min_eligible_parcels` = 20 eligible parcels at the forecast origin are still forecast (and rolled into their county for reporting) but left out of V1 scoring: a few lots swing their rates for every method.
- **Effect (2026-10-14 run):** still 17 of 48 cells pass. Single-family model MAE 10.08 vs 9.66 for the 3-year mean, so the model now loses on single-family. 5+ units: 2.82 vs 3.29 (3-year mean) and 3.94 (trend).
- **Decided by:** Ben, 2026-10-14 (PR #93).

### D-006 · 2026-10-14 · Pre-declared next V1 specification: two demand signals (before any run)
- **Why:** every method under-forecasts NC and TX single-family building in 2023–25 (model mean 70–87% of observed). Recent pace alone can't anticipate a demand surge.
- **Specification C, fixed now, run once:** spec B with the place's level multiplied by `exp(β_h · g + β_p · q)`, where
  - `g` = growth of occupied housing units in the place's county: ACS B25003_001 for the 5-year window ending at the forecast origin vs the **non-overlapping** window ending 5 years earlier, annualized;
  - `q` = FHFA house-price change over the 3 years to the origin, from the panel's fallback chain (county → CBSA → state non-CBSA → state), annualized;
  - `β_h`, `β_p` are estimated by pooled Poisson regression on **fit years only** (all years ≤ origin, within state), never on the forecast years;
  - no other changes; same windows, parameters and pass criteria (D-003 to D-005).
- **Reporting:** spec C is compared with spec B and both benchmarks in every cell. Whichever passes more cells is not automatically adopted; Ben decides, and the choice is logged as D-007.
- **Decided by:** Ben, 2026-10-14 (choice of signals proposed by Claude Code, approved before running).

### D-007 · 2026-10-15 · Baseline stays spec B; spec C (demand signals) not adopted
- **Compared (PR #95, both runs from `python -m lotline.model.backtest --spec B|C`, fits ending 2016/2018/2020,
  MN NC OH TX):** B and C each pass 17 of 48 V1 cells. Single-family MAE 10.08 (B) vs 10.01 (C); 5+ units 2.82
  vs 2.92. NC/TX single-family post-2022 bias of the mean −8.00/−11.08 (B) vs −7.16/−9.53 (C); every NC/TX
  single-family cell still fails under both.
- **Decision:** keep spec B as the baseline. C's gain is small, it is worse for 5+ units, and its fitted
  coefficients are unstable (signs flip across states and windows; |β| up to 66 for 2–4 unit buildings, where
  household and price growth are correlated).
- **Kept for reproducibility:** spec C remains available as `--spec C` (default B).
- **Open:** a more stable demand form (one combined signal, or a statewide cycle term), pre-declared before
  any run, to address the NC/TX single-family under-forecast.
- **Decided by:** Ben, 2026-10-15.
