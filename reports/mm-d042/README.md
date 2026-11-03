# D-042 run: missing-middle uptake, second pre-registered fit (2026-11-03)

One run of `uv run python scripts/dev/calibrate_mm_d042.py`, as pre-registered in `docs/analysis_plan.md` D-042
(method in d096c3c, code and tests in 9fa6d25, both pushed before the run). The script was named
`calibrate_mm_d039.py` and wrote to `reports/mm-d039/` while it ran; both were renamed to D-042 (35980b2), with
no rerun. The reading is in D-042's results bullet. No outcome panel is written; files hold place totals and
fits only. Charlotte, Mecklenburg and St. Paul are excluded by the panel builder; the D-037 test places appear
only in `test_places.csv`.

| File | What |
|---|---|
| `summary.json` | Main fit, backtest scores, reading-rule verdict, places dropped, settings |
| `fits.csv` | Main fit and pre-registered checks 1-8 |
| `events.csv` | Event year and prior cap per place |
| `places.csv` | Per fit place: dose increase, PCR, F ratio, capacity, z, baseline, observed, excess |
| `profile_half.csv`, `profile_b.csv` | Profile log-likelihood over the ramp half-way grid and the capacity slope grid |
| `land_share.csv` | Check 6: median land share and its vintage per place |
| `backtest.csv`, `backtest_index_held.csv` | V4 leave-one-place-out: fit vs no effect vs outside rate vs D-038 spec |
| `test_places.csv` | D-037 out-of-sample tests (Minneapolis, Durham city, Durham County; Raleigh has no cap rise) |

Runtime about 2 h 20 min.
