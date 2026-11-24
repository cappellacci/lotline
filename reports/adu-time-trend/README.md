# ADU calendar-year trend and test D (D-085), run 2026-11-13

**What this is.** One run, as D-085 pre-registers it. Ben accepted D-085 on 2026-11-13 ("Accept both").
- **Form T:** the base form × exp(γ (t − 2020)), with one γ shared by every place. The bases are Form A and
  Form A′ (D-084); which base is in use is still Ben's call.
- **Test D (new):** refit on 2016–2020, then forecast each place's 2021–2025 counts from its own early
  counts. A carry-forward benchmark (each place's early rate per eligible lot) is reported beside it.

**How it ran**
- **Command:** `uv run python scripts/dev/adu_trend_refit.py --out reports/adu-time-trend --workers 7`.
- **Commit:** `f7689e84`, where the code and the "Built" note in D-085 were committed before any fit.
- **Offline,** with seed 20261111 and 20,000 draws. St. Paul stays out; ACS through `holdout.apply_acs`; no
  `--unblind`.

## Headline

- **D-085's rule keeps no trend, for either base.**
  - A vs A + T: the test D gain is 4.2, below 2 SE (16.3).
  - A′ vs A′ + T: the test D gain is 0.7, below 2 SE (15.3), and A′ + T passes fewer of tests A–B (0 vs 1).
  - "Held flat after 2020" was the version scored: continuing the trend scored 32 worse (SE 11).
- **In sample, the trend is large:** γ −0.128 a year (−0.136 to −0.120), likelihood ratio 664. **Most of it is
  Oregon:** without Oregon, γ is −0.044 (−0.057 to −0.030) and the likelihood ratio is 26.
- **Test D, read for its own sake:** no form forecasts 2021–25 reliably. Every form over-forecasts Minnesota
  5–15×; only North Carolina is useful (inside the range, within ×2). The carry-forward benchmark scores
  −146.2 against Form A's −151.0 (difference 4.8, SE 11): the model does not beat it.
- **Minneapolis drives Minnesota's miss.** Fitted on 2016–20, the owner-occupancy share m_o is 0.1, so the 2021
  removal of Minneapolis's owner rule is forecast as a ~10× step. Form A forecast 1,583 permits for 2021–25;
  72 were counted (carry-forward: 145).
- **Nothing is written to config.**

## Fits (all 64 places, 395 place-years)

| | Form A | A + T | Form A′ | A′ + T |
|---|---|---|---|---|
| θ per 1,000 (2020 rate for T) | 0.756 | 1.538 | 0.654 | 1.429 |
| α | 1.918 | 1.834 | 1.558 | 1.666 |
| β_o | 0 | 0 | −0.546 | −0.372 |
| γ a year (90%) | 0 | −0.128 (−0.136, −0.120) | 0 | −0.128 (−0.136, −0.120) |
| m_o, m_x | 1.0, 0.4 | 1.0, 0.2 | 1.0, 0.4 | 1.0, 0.2 |
| log-likelihood | −1,347.71 | −1,015.66 | −1,344.00 | −1,014.13 |

γ leaving out each state (A + T): MN −0.128, NC −0.145, OH −0.128, TX −0.140, **OR −0.044**.

On 2016–2020 only: γ −0.236 (−0.256 to −0.216); m_o 0.1–0.2 and m_x 0.2 for every form.

## Test D (2021–2025, 37 places)

`test_d_states.csv` (by state) and `test_d_places_scores.csv` (by place, with log scores).

| Forecast | MN (21) | NC (10) | TX (2) | OR (4) | Σ log score |
|---|---|---|---|---|---|
| Form A | 0.07 | **1.10** | 0.83 | 0.53 | −151.0 |
| A + T, flat | 0.10 | **1.53** | 1.34 | 0.79 | −146.8 |
| A + T, continued | 0.18 | 3.12 | 2.10 | 1.49 | −179.2 |
| Form A′ | 0.13 | **1.14** | 0.82 | 0.53 | −154.9 |
| A′ + T, flat | 0.20 | **1.56** | 1.33 | 0.79 | −154.2 |
| Carry-forward | 0.61 | 1.98 | 0.89 | 0.62 | −146.2 |

Cells are observed ÷ P50. **Bold** is useful (inside P10–P90, within ×2).

## Data-tier test and tests A–B

No form passes any tier. Useful states per tier: A and A + T 0/0/0; A′ and A′ + T 1/1/1. Tests A–B passed:
A 1, A + T 1, A′ 1, A′ + T 0. `tiers.csv`, `test_a.csv`, `test_b.csv`.

## Outlook (reported, not used)

Rule age (oldest rule in force, capped at 10) instead of the trend, on Form A′: δ −0.051 a year
(−0.064 to −0.037), likelihood ratio 23 against A′.

## Files

`run-log.txt`, `summary.json`, `fits.csv`, `test_d_places.csv`, `test_d_places_scores.csv`,
`test_d_states.csv`, `tiers.csv`, `test_a.csv`, `test_b.csv`, `results.html`.
