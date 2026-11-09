# V5 Charlotte blind forward test: scored

*Analysis plan D-071. Frozen 2026-11-09 in #353 (`results/frozen/V5-NC-CHARLOTTE.json`, code 77e8710) before any
outcome was read; unblinded and scored the same day on Ben's go-ahead. Reproduce with
`uv run python scripts/dev/v5_clt_score.py` (it first regenerates the frozen draws and stops if they differ).*

**Result: pass.** Mecklenburg County (BPS 37119, where Census files Charlotte's permits) got **119** new 2-4
unit buildings in 2023-2025. The frozen range was **89 to 172** (P10-P90), with a median of 104. The observed
count sits at the 77th percentile. D-040's verdict is "useful": inside the range, and within a factor of two of
the median.

| BPS 37119, 2-4 unit buildings | Observed | P10 | P50 | P90 | Percentile | Verdict |
|---|---:|---:|---:|---:|---:|---|
| **2023-2025 (pass rule)** | **119** | 89 | 104 | 172 | 77 | useful |
| 2023 | 27 | 27 | 35 | 52 | 11 | useful |
| 2024 | 48 | 27 | 35 | 60 | 85 | useful |
| 2025 | 44 | 27 | 35 | 64 | 78 | useful |

**Against no reform.** The no-reform benchmark is the 2020-2022 average (33 buildings a year) held flat. The
model's CRPS on the three-year total is 10.1, against 14.5 for no reform (lower is better). It beats no reform
in 2024 and 2025. In 2023 no reform does better (CRPS 3.5 against 5.3): the BPS year includes January to May,
before the UDO, and the 2023 count (27) was below the baseline.

**Homes (secondary).** Homes in 2-4 unit buildings: 256 observed, against a range of 213 to 402 (median 249).
That is inside the range. Year by year, 2023 (62) falls below P10 (65). On the three-year total, no reform's
CRPS (11.4) beats the model's (13.0). Builders put up mostly duplexes in 2024-2025 (86 of 94 buildings were
2-unit), so homes per building ran below the 2.08 the model assumes for the added buildings.

**How to read this.**
- This is one case, so it is a demonstration, not proof (validation plan V5).
- The count is county-wide: it includes the six towns and the unincorporated county, so the model gets them
  through the flat baseline. The excess over the baseline (119 against about 99) fits a modest UDO effect, but
  this test cannot attribute it to N1 lots.
- Other building in the county moved a lot during the window. One-unit buildings fell from about 6,900 in 2023
  to 3,747 in 2025. The flat baseline did not foresee this, so the pass is partly luck in the baseline.
- The pass is not tight: the range is wide because Charlotte is one place with a large place-to-place spread
  (α 8.4).

Files: `score.json` (every measure, each year, both targets).
