# D-092 deviation (b), run 8: choosing the no-reform baseline (2026-11-15)

**What this is:** the pre-registered comparison of eight baseline candidates, scored on run 7's uncoded places,
which no fit and no §7 test uses. **Nothing was refit or written to config.**

- **Go-ahead:** Ben, 2026-11-15, "Yes, run it".
- **Pre-registration:** commit 5890ce71 (`docs/analysis_plan.md`, D-092 "Deviation 2026-11-15 (b)"). It was
  pushed before any scoring code existed.
- **Command:**

  ```bash
  uv run python scripts/dev/mm_baseline_choice_d092.py --out reports/mm-d092/run8-baseline
  ```

  It reads cached tables only and takes about 2 minutes.
- **Data:** each candidate's parameter is fitted on the 2016 origin (473 places, 2016–20). It is then scored,
  held out, on the 2021 origin (468 places, 2021–25). Every candidate uses the same places.
- **Files:**
  - `candidates.csv`: the table below.
  - `place_scores.csv`: held-out log score per place and candidate.
  - `summary.json`.
  - `run-log.txt`.

## Result: the rule picks C0-year

C0-year keeps today's three-year baseline and adds a separate negative binomial for each year, with φ = 9.1.

| Candidate | Baseline | Noise | Parameter | Held-out log score vs best | Paired SE | 2021 coverage (P10–P90) |
|---|---|---|---:|---:|---:|---:|
| **C0-year** | 3 yrs, own growth | per year | φ 9.13 | −197 | 103 | 0.79 |
| C2-year | 6 yrs, state growth | per year | φ 8.96 | **best** | — | 0.81 |
| C3-year | 6 yrs, no growth | per year | φ 12.1 | −279 | 73 | 0.76 |
| C1-year | 6 yrs, own growth | per year | φ 8.74 | −312 | 110 | 0.78 |
| C2-w | 6 yrs, state growth | per place | κ 5.35 | −1,593 | 367 | 0.83 |
| C0-w | 3 yrs, own growth | per place | κ 4.90 | −1,672 | 396 | 0.80 |
| C3-w | 6 yrs, no growth | per place | κ 7.16 | −1,736 | 377 | 0.76 |
| C1-w | 6 yrs, own growth | per place | κ 5.10 | −1,767 | 389 | 0.81 |

- **Why C0-year and not the top scorer:** C2-year scores best, but C0-year is within 2 paired SE of it (197
  against 2 × 103). The rule then prefers fewer changes. **This is close: the margin is 1.9 SE.**
- **Stop rule:** C0-year's coverage is 0.79, above the 0.5 stop line, so the refit may go ahead.

## What it says, in plain language

1. **Lumpiness is the problem, not the baseline window.**
   - Modelling each year's count as lumpy (per-year negative binomial) beats one multiplier per place by about
     1,500 log points, at about 4 SE, under every construction.
   - That fits run 7's finding that building arrives in projects: many years with nothing, then a burst.
2. **A longer window or a different growth index doesn't help much.**
   - Six years with the place's own growth (C1) and six years with no growth (C3) both score worse than today's
     three years.
   - The state's growth index (C2) scores best but not decisively.
3. **The ranges are now honest.** Every candidate's P10–P90 holds about 79% of 2021 outcomes, against a nominal
   80%. Runs 4–5 had 37% for test C's no-reform places.
4. **The ranges are also wide for a single place.**
   - With φ = 9, a place's median forecast is about a third of its baseline: half of all place-forecasts have a
     median under 32% of the baseline.
   - Its mean stays at the baseline, because a year with a project lifts it.
   - This is how 2–4 unit building behaves at the scale of one place. State totals sum hundreds of places, so
     their ranges will be much narrower.

## Next (pre-registered; needs Ben's go-ahead)

1. **Code the per-year negative binomial in the main likelihood:** y_t ~ NB(mean B_t + θ u k_t, φ), inside the
   u integral, with its own tests.
2. **Estimate φ for the chosen construction (C0) on both origins**, as run 7 did, and fix it in the refit.
3. **Refit M and C4 and rerun §7** (the first deviation's plan, with Ny in place of Nw).
