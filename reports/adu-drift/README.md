# ADU forecast drift (D-091), run 2026-11-14

**What this is:** one run of D-091.
- **Accepted:** by Ben on 2026-11-14, on two conditions: we can roll back, and the report shows clear
  evidence on whether the drift improves predictive power.
- **What it does:** D-090's own-history forecasts for 2021–2025 get one random multiplier per place,
  d = exp(σz) with median 1. σ is learned for each state from the other three states' windows.

**Results page:** https://claude.ai/artifact/G4sRpudCfVVXt8PyWV2asM (built by `scripts/dev/adu_drift_page.py`).

## How it ran

- **Command:** run from the main checkout, so it loads `.env`:
  `PYTHONPATH=<wt>/src .venv/bin/python <wt>/scripts/dev/adu_drift.py --d090 <wt>/reports/adu-time-split --out <wt>/reports/adu-drift --workers 7`.
- **Code:** committed at `d8429d88` before the run. D-090's fits, draws and classes are reused unchanged
  (D-090 at `d03ec95e`).
- **Settings:** 20,000 draws, D-084's seed, offline. The run took 2 minutes. Log: `run-log.txt`.
- **Smoke run first:** 500 draws, outputs to a scratch folder. Only its status lines were shown, not its
  results.
- **Holdouts:** St. Paul is out. No `--unblind`.
- **Config:** nothing is written to it.

## Rollback (Ben's condition 1)

- **No drift reproduces D-090 exactly.** With drift off, the draws are D-090's (unit test). Each place's score
  at d = 1 matches D-090's `place_scores.csv` to 3.6 × 10⁻¹⁵ (`run-log.txt`).
- **Nothing reaches the tool.** Nothing is in config or the tool. Dropping D-091 means closing PR #430.

## Evidence on predictive power (Ben's condition 2): with against without drift

| Places with history (43) | F0 no drift | F0 + drift | F1 no drift | F1 + drift |
|---|---|---|---|---|
| Places inside their own P10–P90 (honest ≈ 80%) | 58% | **81%** | 58% | **77%** |
| States whose total is inside P10–P90 (of 4) | 0 | **4** | 1 | 2 |
| Useful states (inside and within ×2; bar 3) | 0 | **3** | 1 | 2 |
| Summed per-place log score (higher is better) | −823 | −394 | −829 | −387 |
| Gain with drift, against the 2-SE bar | | +429 vs 551 | | +442 vs 571 |
| Places better / worse with drift | | 17 / 22 | | 20 / 20 |
| Gain without Portland | | +158 | | +163 |
| Summed per-place CRPS (lower is better) | 2,235 | **1,938** | 2,920 | **2,563** |
| Summed state-total CRPS | 1,649 | **1,533** | 2,309 | 2,879 (worse) |

**Reading, as fixed before the run:**
- **The pre-set test is not met.** That test is a log-score gain of more than 2 paired SE. The gains are large
  (+429 and +442), but Portland alone gives about +270. Place by place, about as many places get slightly
  worse as better, so the paired SE is larger than the gain.
- **What clearly improves:**
  - calibration: 58% to 81% of places inside their band;
  - state totals inside their range: 0 to 4 of 4 for persistence;
  - per-place CRPS: down 13%.
- **What gets worse:** F1's state-total CRPS. Independent drift lifts a state total's median (a sum of
  skewed draws), and F1's σ learned without NC is the widest fold, at 1.43. So NC's F1 median rose from
  830 to 1,493, against 790 observed.
- **The ×2 part of "useful" cannot improve place by place,** because the median of d is 1.

## D-091's rules

| Rule | Result | Verdict |
|---|---|---|
| 1. Useful in ≥ 3 of 4 states | F1+d: 2 (NC, TX); **F0+d: 3 (MN, NC, TX)**. Oregon is inside its range at 0.47 | only persistence with drift passes |
| 2. F1+d beats F0+d by > 2 SE | +7.6 against 31 | no |
| 3. Coverage 65–95% | F0+d 81%, F1+d 77% | pass |

**The tool outcome D-091 fixed for this case** ("only persistence with drift passes"):
- the no-reform range for a state with history is persistence with the drift band;
- a bill's effect is F1's ratio (with the bill ÷ without), applied to that range and labelled as unchecked
  within ×2.

This takes effect only after Ben's separate approval.

## σ, leaving one state out

| Fold | F0 σ | F1 σ |
|---|---|---|
| without MN | 1.000 | 0.725 |
| without NC | 0.850 | 1.425 |
| without TX | 1.100 | 1.150 |
| without OR | 1.075 | 1.075 |
| all four states (reported only) | 1.025 | 1.075 |

- **F0's folds** are stable (within a factor of 1.3).
- **F1's folds** span about a factor of 2: 0.725 to 1.425, just inside the "not stable" flag.

## Sensitivities (not used to choose)

- **One drift shared by every place in a state** (the correlated bound) does as well or better on state totals:
  - persistence is useful in 4 of 4, with total CRPS 1,456;
  - F1's total CRPS is 2,257.
- **The log-mean learned as well** shifts every median up and is worse on CRPS (persistence 2,828), so the
  median-1 choice holds.

## Files

| File | What |
|---|---|
| `place_scores.csv` | Per place, variant and forecaster: observed, P10/P50/P90, inside, percentile, CRPS, log score |
| `totals.csv` | Per state, line, variant and forecaster |
| `logscore_grids.npz` | Each place's log score at fixed drifts (log d −8 to 8, step 0.02) |
| `summary.json` | σ per fold, the evidence, the verdict, the rollback check |
| `results.html` | The results page |
| `run-log.txt` | The run's log |
