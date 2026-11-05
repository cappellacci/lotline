### LB-NNN · 2026-11-05 · validation · Can Portland's and Bend's own pre-2018 ADU permits sharpen the V9 prediction?

- **Question:** the D-046 dry run gave Portland 0–1,864 ADU permits over 2018–2025, almost all of it from the
  unknown place multiplier. Ben asked (2026-11-05) to add a variant updated on each place's own pre-2018 counts
  and freeze both.
- **Outputs:**
  - `docs/analysis_plan.md` D-049 (method, before any freeze).
  - `src/lotline/validation/v9.py`: `AduHistory`, `load_history`, `adu_history`, `posterior_u`,
    `history_expected`; `adu_draws(history=)`; per-place Poisson streams; `prediction` tags ADU targets by variant.
  - `scripts/dev/v9_or_predict.py` runs both variants.
  - `config/validation/or_adu_history.csv` and its README.
  - `tests/core/test_v9.py`: 5 new tests, including the hand-worked gamma-Poisson posterior.
- **Data:** Portland 2009 (24), 2010 (86) and 2016 (615) from Ord. 189050's findings (BPS data). Bend has no
  official count found yet (the city site rate-limited fetches). The loader refuses any year from 2018 on.
- **Dry run (1,000 draws, not committed), 2018–2025 totals P10/P50/P90:**
  - Portland: transfer 0 / 50 / 1,470; own history 3,263 / 6,422 / 13,171.
  - Bend: 0 / 8 / 241 in both variants (no counts).
- **What Claude did and how it was checked:**
  - A research subagent searched city sources under the blind rule. It reported search summaries that showed
    post-2017 counts, without the numbers.
  - The main session checked the three Portland figures in the ordinance PDF text with a filter that withheld
    any sentence naming 2017 or later.
  - Tests use synthetic inputs only.
  - Full suite, ruff and `compliance_check.py` were run.
