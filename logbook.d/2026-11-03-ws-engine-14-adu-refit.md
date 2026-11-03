### LB-NNN · 2026-11-03 · [engine] · What ADU uptake do our own four states show, and can it predict a city it hasn't seen?
- **Question:** after D-037's amendment (calibrate on our own states), refit the ADU anchor on the four states
  and backtest it the way Ben described: predict each reformed place without having seen it.
- **What I did:**
  - Counted the qualifying place-years by state, before any fit.
  - Wrote and pushed D-039 (fit set by state, test set, leave-one-place-out backtest, scores and benchmarks)
    before running.
  - Added `--four-state` to `scripts/dev/calibrate_adu.py` (fit, test-set predictions and 51 parallel
    leave-one-out refits) and ran it once.
  - Wrote the results into D-039.
  - Separately, cleared the Dependabot alerts in its own PR (#273, see its fragment).
- **Results:**
  - θ = 1.11 per 1,000 eligible parcels a year (0.74–1.74), close to fit 3's 1.04 with an interval a third as
    wide.
  - Raleigh and Durham, held out, fall inside their ranges, but the medians are far low.
  - Backtest coverage is 94% of place totals: too wide. The median's error equals "no effect", and Austin is
    missed high.
  - Reading: the average rate is well identified; which places take off is not, yet.
- **Correction:** the Portland benchmark first ignored `ramp_blank`. The code is fixed, the benchmark column
  is recomputed, and both the as-run and corrected numbers are recorded in D-039.
- **Outputs:** `docs/analysis_plan.md` (D-039); `scripts/dev/calibrate_adu.py`; `reports/adu-anchor-4state/`
  (fit, backtest CSVs, log).
- **AI:** Claude Code (Opus 5.5). Fit run once after the entry was pushed. No held-out outcome read; Raleigh
  and Durham stayed out of every fit.
