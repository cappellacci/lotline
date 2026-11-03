# D-038 run: missing-middle uptake calibrated on MN, NC, OH and TX (2026-11-03)

One run of `uv run python scripts/dev/calibrate_mm.py --out reports/mm-d038`, as pre-registered in
`docs/analysis_plan.md` D-038 (method pushed in 699537c and 60b7a89 before the run). The reading is in D-038's
results bullet. No outcome panel is written; files hold place totals and fits only. Charlotte, Mecklenburg and
St. Paul are excluded by the panel builder; the D-037 test places appear only in `test_places.csv`.

| File | What |
|---|---|
| `summary.json` | Main fit, realized hazard and ages, BPS homes per building, settings |
| `fits.csv` | Main fit and pre-registered checks 1-5 |
| `exploratory_fits.csv` | Without Houston; without Houston and Austin (exploratory, not pre-registered, not used) |
| `places.csv` | Per fit place: dose, PCR, F ratio, baseline, observed, excess and implied mature rate per 1,000 |
| `profile_half.csv` | Profile log-likelihood over the ramp's half-way grid |
| `backtest.csv`, `backtest_growth_held.csv` | V4 leave-one-place-out: fit vs no effect vs outside rate |
| `test_places.csv` | D-037 out-of-sample tests (Minneapolis, Durham city, Durham County, Raleigh) |
| `units_per_building.csv` | Local permit files' homes per 2-4 unit row (unusable: one permit per unit) |
| `eligible_lots.csv` | Check 6: no parcel matches (not done) |

Runtime about 35 minutes.
