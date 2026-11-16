# D-092 deviation, run 7: κ, the baseline's own spread (2026-11-15)

**What this is.** This is the first run under D-092's deviation of 2026-11-15. It estimates κ, the variance of
w: one rate multiplier per place, with y_t ~ Poisson(w B_t). The estimate uses "uncoded" places that neither the
fit nor any §7 test uses. **Nothing was refit or written to config.**

- **Go-ahead:** Ben, 2026-11-15: "Once tests pass, run the κ estimate".
- **Command:**

  ```bash
  uv run python scripts/dev/mm_kappa_d092.py --out reports/mm-d092/run7-kappa
  ```

  It reads cached tables only and downloads nothing. It took 90 s.
- **Places:** 483 uncoded places in MN, NC, OH and TX. The 11 that are test C places were removed, and no
  holdout is in the panel. Each place is scored at two origins: 2016 (scored 2016–20, 473 places) and 2021
  (scored 2021–25, 468 places). That is 941 pseudo-forecasts and 4,685 place-years.
- **Files:**
  - `summary.json`: κ and its intervals.
  - `places.csv`: observed against baseline for each place and origin.

## Result

| Fit | κ̂ | 90% interval | Pseudo-forecasts |
|---|---:|---|---:|
| **Main (both origins)** | **7.65** | 7.02–8.35 | 941 |
| 2021 origin only | 10.08 | 8.99–11.34 | 468 |
| MN | 4.41 | 3.56–5.49 | 186 |
| NC | 5.04 | 3.69–6.99 | 80 |
| OH | 4.83 | 4.02–5.82 | 289 |
| TX | 11.04 | 9.77–12.53 | 386 |

Log-likelihood: 14,283 with w against 1,780 without. The Poisson baseline is far too sure of itself, as runs 4–5
found.

## What κ = 7.65 means, and why it is not usable as it stands

A gamma multiplier with mean 1 and variance 7.65 has these quantiles:

| P10 | P25 | P50 | P75 | P90 | P(w < 0.1) |
|---:|---:|---:|---:|---:|---:|
| 0.0000001 | 0.0001 | 0.024 | 0.56 | 2.9 | 0.60 |

Read plainly, **the median place would be forecast at 2% of its baseline**, and 60% of places at under a tenth of
it. That isn't a widened baseline: the multiplier has become a switch for whether a project happens at all.
Refitting with this κ would pass test C because the ranges would cover almost anything, and the forecasts would
say little. **So the refit was not started.** The pre-registration asks for it, but Ben decides whether to go on.

## Why it is so large: the counts come in projects

- **The totals agree; single places don't.**
  - Over all 941 pseudo-forecasts, observed is 10,337 and baseline is 10,131.
  - But the median place lands at about half its baseline (median log ratio −0.68).
  - Only 26–39% of places land within 2× of their baseline, in every size band, the largest included.
- **Big places miss too.** A three-year pre-period with one burst carries forward through the growth index (capped
  at ×4):

  | Place | Origin | Baseline | Observed |
  |---|---|---:|---:|
  | Forney, TX | 2021 | 178 | 0 |
  | Grapevine, TX | 2016 | 175 | 0 |
  | Princeton, TX | 2016 | 214 | 1 |
  | Sherman, TX | 2021 | 224 | 13 |

  Others swing up instead:

  | Place | Origin | Baseline | Observed |
  |---|---|---:|---:|
  | Alton, TX | 2021 | 315 | 523 |
  | Temple, TX | 2021 | 150 | 335 |
  | Harker Heights, TX | 2021 | 87 | 198 |

- **47% of pseudo-forecasts saw zero 2–4 unit buildings in five years.** Building in a place arrives in
  developments, not as a steady rate. One w per place has to cover both "no project this window" and "a
  different market", and it can only do that by becoming bimodal.

## What would fix it (for Ben to decide; not done)

Choose the baseline's construction on these same uncoded places, before touching the fit or the tests. These
places are training data for the baseline only, so nothing leaks into §7.

1. **Steadier baseline inputs:** a longer pre-window (D-058's six years), the growth index from the state's
   comparison places instead of the place's own (noisy) 1-unit and 5+ series, or no growth index at all.
2. **Project lumpiness modelled directly:** year-level overdispersion (a negative binomial per year), with a
   smaller place-level w on top.

Pre-register the candidates and score each by held-out log score on the uncoded places (2016-origin fit, 2021
scored). Take the best and its κ, then do the refit and §7 as planned.
