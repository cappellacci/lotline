# D-100 run 1: missing middle's ramp after St. Paul (one ramp or one per adoption route)

Pre-registered in `docs/analysis_plan.md`, D-100 (2026-11-16). Ben: "Approve, run the refit" (2026-11-16).

    uv run python scripts/dev/mm_ramp_d100.py --out reports/mm-d100/run1      # 49 min, cached tables only
    uv run python scripts/dev/mm_ramp_d100_summary.py reports/mm-d100/run1    # the summary (see below)

The run stopped at its last step, writing summary.json, on a JSON key bug (route counts keyed by tuples), after
fits.csv, place_scores.csv and routes.csv were written. The bug is fixed in `mm_ramp_d100.py`; the summary was
rebuilt from those files by `mm_ramp_d100_summary.py`, which fits nothing. It was not rerun because a rerun
needs St. Paul's released rows in the shared Minnesota permit table, which was put back to its blinded state
for other sessions until #442 reaches main.

## Result: C4 (R0) stays

| Fit | θ per 1,000 (90%) | Half-way point, years | Five-year rate per 1,000 a year |
|---|---|---|---|
| **R0** C4, 93 places | 1.04 (0.13–19.4) | 4.0 (1.0–6.0) | 0.24 |
| **R1** + St. Paul, one ramp | 0.76 (0.12–19.8) | 3.5 (0.5–6.0) | 0.24 |
| **R2** + St. Paul, one per route | 0.94 (0.38–2.09)* | state-required 4.0; local 0.5 (0.5–4.0) | state 0.22; local 0.79 |

\* R2's θ interval is conditional on its best pair of half-way points, so it is narrower than the others'.

**Held-out comparison** (leave one state out, 94 places scored with every model; D-092 §5's 2-SE rule):

| Comparison | Δ log score | Paired SE | Beats by 2 SE? |
|---|---:|---:|---|
| R1 against R0 | −2.68 | 1.70 | no (worse) |
| R2 against R1 | −0.15 | 1.01 | no |
| R2 against R0 | −2.83 | 1.99 | no |

So no candidate replaces C4, and §7's tests are not rerun. Nothing goes to config.

## What it says

- **In the fit, the hypothesis shows up clearly.** Given its own ramp, the locally adopted group reaches half
  speed at 0.5 years (the grid floor; range 0.5–4.0), and the state-required Oregon group at 4.0. Every
  leave-one-state-out fold that has both groups finds the same split (4.0 or 4.5 against 0.5).
- **But it doesn't forecast better held out.** The local ramp rests on 37 places with 64 post-reform years,
  most of them small Oregon towns with one or two years, so it doesn't carry to a held-out state.
- **Adding St. Paul with one ramp makes held-out scores worse.** One fast place pulls the shared ramp and θ
  for the slow Oregon majority.
- **The scenario's ramp doesn't change either way.** The Handbook rule is a state law; the state-required
  ramp in R2 (4.0 years) equals C4's.
- **St. Paul itself:** R2 scores it a little better than C4 held out (121.2 against 120.5), as expected from its
  fast start, but one place can't move the rule.

Files: fits.csv (full and per-fold fits), place_scores.csv (held-out scores per place and model), routes.csv
(each place's route), summary.json, run-log.txt, results.html.
