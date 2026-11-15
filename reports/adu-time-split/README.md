# ADU within-state forecast test (D-090), run 2026-11-14

**What this is:** one run of D-090 as accepted on 2026-11-14 ("Accept D-090"). Each state is fitted on its own
2016–2019 ADU counts, and its 2021–2025 counts are forecast under the rules actually in force. 2020 is the
lead year and is not scored.

**Results page:** https://claude.ai/artifact/Bfz5915ng524v1tJu1mW1o (built by `scripts/dev/adu_time_split_page.py`).

## How it ran

- **Command,** from the main checkout so that `.env` loads:
  `PYTHONPATH=<wt>/src .venv/bin/python <wt>/scripts/dev/adu_time_split.py --out <wt>/reports/adu-time-split --workers 7`.
- **Code:** committed at `62669bd5` before any fit, together with `places.csv` (`--inputs-only`).
- **Settings:** offline, 20,000 draws, D-084's seed. The run took 3 minutes. Log: `run-log.txt`.
- **A smoke run came first** (2 × 2 grid, 500 draws), with its outputs in a scratch folder.
  - I saw its per-state history lines before the full run.
  - The only change after it was fitting the grid cells in parallel. It changes speed, not method.
- **Holdouts:** St. Paul is out of every fit and score. ACS rows went through `holdout.apply_acs`. No `--unblind`.
- **Config:** nothing is written to it.
- **Deviations and clarifications:** listed in D-090's "Built" note (items 1–10).
  - A "thin history" class: Raleigh and Cary have only 2019 before the window.
  - No separate undercount draw.
  - θ_s intervals are profiled at the chosen cell.
  - The u update is drawn jointly with the blank-field combination.

## Headline: the pre-set rule reads against own-history forecasting

| Rule | Result | Verdict |
|---|---|---|
| 1. F1 useful in ≥ 3 of 4 states | useful in **1** (NC) | own history is not enough to forecast within ×2 |
| 2. F1 beats persistence by > 2 SE | F1 − F0 = **−5.5**, 2 SE = 204 | F1 forecasts no better than persistence |
| 3. F2 replaces F1 | F2 − F1 = **−41.9**, 2 SE = 88; useful in 0 states | F1 stays |

**The medians are closer than the verdict suggests. The ranges are what fail.**

## Places with history, 2021–2025 totals

| State | Places | Observed | F0 P10–P50–P90 | ÷ | F1 | ÷ | F2 | ÷ | F1 + trend | ÷ |
|---|---|---|---|---|---|---|---|---|---|---|
| MN | 27 | 119 | 147–172–198 | 0.69 | 295–339–388 | 0.35 | 213–248–285 | 0.48 | 128–151–176 | 0.79 |
| NC | 11 | 790 | 425–468–510 | 1.69 | **751–830–917** | **0.95** | 839–932–1034 | 0.85 | 304–340–379 | 2.32 |
| TX | 2 | 366 | 395–431–468 | 0.85 | 448–487–527 | 0.75 | 450–489–529 | 0.75 | 406–442–480 | 0.83 |
| OR | 3 | 1,464 | 2660–2763–2867 | 0.53 | 3366–3504–3647 | 0.42 | 3666–3827–3992 | 0.38 | 1216–1277–1340 | 1.15 |

**Within ×2 by forecaster:**
- persistence: 4 of 4 states;
- F1: 2 (NC, TX);
- F2: 2;
- trend: 3.

**Inside P10–P90:** only F1 in North Carolina.

**The P10–P90 half-widths average 9% of the median.** Four years of a place's own counts pin its rate, and
nothing lets that rate drift from one period to the next, so the ranges are far too narrow.

## What drives it

- **Rule changes split by state.**
  - **Where F1 priced a rule change correctly:**
    - Wilmington: observed 141, against F1 163 and F0 22.
    - Charlotte: observed 174, against F1 164 and F0 55.

    The NC rule-change line is useful for F1, at obs/P50 0.96.
  - **Where F1 over-predicted:**
    - Minneapolis: F1 expected the 2021 change to raise output, but output fell. Observed 72, against F1 328 and F0 146.
    - Bend: its stronger rule began partway through the fit years. Bend 2016–17 required parking, the case that sets m_x. So F1 projected the full-rule rate: observed 290, against F1 984.
- **Per-state log-score differences, F1 − F0:**
  - MN −48 (SE 42);
  - NC +108 (SE 64);
  - TX −3;
  - OR −62 (SE 59).

  Eight places make up about 90% of the absolute per-place differences, and they nearly cancel.
- **Housing age within states:** β_a = +1.31 (SE 0.32) on the fit years, which is in-sample. Held out, it makes
  forecasts worse.
- **The trend sensitivity:** every state's 2016–2019 trend is downward: MN ×0.85, NC ×0.85, TX ×0.98 and OR
  ×0.82 a year.
  - It helps Oregon and Minnesota.
  - It doubles North Carolina's miss, because NC surged after 2020.
  - Trend − F1 log score: +185 (SE 276).
- **Raleigh and Cary** (thin history) came in about 5 times above F1's median.

## Fits (46 places, 168 place-years, 2016–2019)

| | F1 | F2 |
|---|---|---|
| θ per 1,000 lots: MN | 0.21 (0.11–0.43) | 0.05 |
| NC | 1.86 (0.93–4.54) | 1.68 |
| TX | 2.18 (0.49–39.2) | 6.44 |
| OR | 3.57 (1.00–31.7) | 7.76 |
| α | 2.71 | 1.46 |
| m_o, m_x | 0.5 (judgment), 0.4 (estimated) | 0.7 (estimated), 0.3 (judgment) |
| β_age | — | +1.31 (SE 0.32) |
| log-likelihood | −311.76 | −303.23 |

## Files

| File | What |
|---|---|
| `places.csv` | Class, fit and window years, rule-change years and z_age per place (written before any fit) |
| `housing_age.csv` | D-087's housing-age reader output |
| `fits.csv` | F1, F2 and the trend fits by state |
| `totals.csv` | Per state and line (history, rule change, no rule change, new, thin) and per forecaster |
| `place_scores.csv` | Per place: observed, P10/P50/P90 per forecaster, held-out log scores |
| `summary.json` | Split, classes, rule changes, fits, the verdict |
| `results.html` | The results page |
| `run-log.txt` | The run's log |
