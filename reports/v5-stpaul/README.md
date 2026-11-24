# V5 St. Paul blind forward test: scored

*Analysis plan D-098. Frozen 2026-11-15 in #436 (`results/frozen/V5-MN-STPAUL.json`, code 9ee70aa, C4's values)
before any outcome was read; unblinded and scored on 2026-11-16 on Ben's go-ahead ("Yes, unblind"). Reproduce
with `uv run python scripts/dev/v5_stp_score.py` (it first regenerates the frozen draws and stops if they
differ).*

**Result: miss.** St. Paul (BPS 2758000) got **55** new 2–4 unit buildings in 2024–2025. The frozen range was
**9 to 28** (P10–P90), with a median of 15. The observed count sits at the 98th percentile: the model
under-predicted by 3.7× at the median.

| BPS 2758000, 2–4 unit buildings | Observed | P10 | P50 | P90 | Percentile | Result |
|---|---:|---:|---:|---:|---:|---|
| **2024–2025 (pass rule)** | **55** | 9 | 15 | 28 | 98 | above the range |
| 2024 | 33 | 3 | 7 | 12 | 100 | above |
| 2025 | 22 | 4 | 8 | 18 | 93 | above |

**Against no reform.** The no-reform benchmark is the baseline part of the same draws (about 6.3 buildings a
year, the 2021–2023 mean). The model's CRPS on the two-year total is 32.8, against 40.0 for no reform (lower is
better), and it beats no reform in each year. So the reform part points the right way but is far too small.

**Homes (secondary).** 123 homes in 2–4 unit buildings, against 21–65 (median 36): also above the range.

**What it says.** D-098 wrote before the freeze: "This is a test of C4's slow ramp: if St. Paul built many more
2–4 unit buildings in 2024–2025, the slow ramp is wrong." It did. St. Paul's building jumped in the first full
year (33 against about 6 a year before), which a half-way point of 4 years cannot produce: C4 puts only 1% and 3%
of the mature rate into years 1 and 2.

**Post-hoc check (written after the score was read; reported only, not a re-score;
`posthoc_ramp.json`).** The same frozen inputs, draws and seed, with only the ramp or the values changed:

| Variant | P10 | P50 | P90 | 55 inside? |
|---|---:|---:|---:|---|
| C4 as frozen (half-way 4.0 years) | 9 | 15 | 28 | no (98th pct) |
| C4's θ, half-way 1.0 year (the low end of C4's own range) | 17 | 55 | 308 | yes (50th) |
| C4's θ, half-way 0.5 year (D-055's ramp) | 19 | 66 | 391 | yes (44th) |
| D-055's values (θ 0.12 per 1,000, fast ramp, Poisson years) | 9 | 14 | 36 | no (94th) |

Read as a rate, St. Paul's excess over its baseline implies a mature θ of 0.85 per 1,000 lots at a half-way
point of 0.5 years, or 1.09 at 1.0 year, close to C4's 1.04. So St. Paul agrees with C4's **level** and
disagrees with its **timing**: the effect came fast. The old D-055 values missed too, for the opposite reason
(a fast ramp but a level 8× lower).

**How to read this.**
- One case: a demonstration, not proof (validation plan V5). Charlotte passed with the older values.
- The fit pins the ramp poorly (C4's 90% range is 1.0–6.0 years); St. Paul points to the fast end.
- Changing the ramp now would use St. Paul, so it would need a new dated entry, and St. Paul would no longer
  be a blind test for the changed model.
- Known exposure (D-013): post-reform St. Paul figures were seen in a research document during scouting. They
  were not used, and the forecast missed, so the exposure did not help it.

Files: `score.json` (every measure, each year, both targets), `posthoc_ramp.json`.
