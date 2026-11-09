### LB-NNN · 2026-11-09 · `engine` · The baseline forecast in the results bundle and on the Results tab
- **Question:** the app showed reforms as homes *added* but never the level they add to. How many homes does
  each state permit over 2027–2031 with no policy change, and can the page show it from the same bundle?
- **Decided by:** Ben, 2026-11-09: a new bundle table rather than rows in `totals`; export and show it in one PR.
- **Outputs:**
  - `src/lotline/schemas.py` 1.11: `results_baseline` (state, size_class all/1/2/3_4/5p, period, P10/P50/P90,
    mean, places, coverage_share, basis); `docs/schemas.md` regenerated. Additive (schemas-v1 line).
  - `src/lotline/model/results.py`: `baseline_table` sums every place's `baseline.forecast_draws` per draw
    and year (D-061 window), "all" summed within each draw across size classes; `build_bundle` loads the
    same panel V1 uses (`theme="adu"`, holdout-filtered) and adds the `baseline` part.
  - `src/lotline/app/template.html`: a "With no policy change" card on the Results tab (five-year range,
    per-year midpoint, a table by building size, places and coverage, the counting basis); the Baseline row
    in the range chart now reads "0 added, by definition".
  - Tests: `tests/model/test_results_baseline.py` (statewide sums and percentiles by hand, "all" is not the
    sum of the class percentiles, window labels, coverage by hand, agreement with
    `baseline.baseline_forecast` means on a real simulation, other states ignored); the fixture bundle
    regenerated with a synthetic baseline; `tests/app/test_build.py` checks the card and the state file.
- **What Claude did and how it was checked:** Claude Code (Opus 5.5) wrote the schema, function, page card
  and tests. Checked by the tests above, the full suite, ruff and `compliance_check.py` (0 FAIL), and by
  building the page from the fixture and reading the card in the in-app browser (no console errors).
- **Not done (in the first commit):** no real bundle was built. The fee scenario can now read the baseline
  but is still pending. The coverage share is against BPS places in the panel; BPS rows with no GEOID are
  outside it.

### LB-NNN · 2026-11-09 · `engine` · First real results bundles for five states, and D-064's effect
- **Question:** what do the five states' bundles say under the 2027–2031 window and D-064's rules date, with
  the new baseline beside them, and how much did D-064 change?
- **Decided by:** Ben, 2026-11-09 ("Yes, build bundles").
- **Outputs:** `reports/results/<st>/bundle.json` for MN, NC, OH, TX (development) and OR (transfer), gitignored;
  the app page built from them (`reports/app/`, gitignored); `reports/results-run-2026-11-09/` (summary.json,
  d064_sensitivity.csv, run log, `run-results.html`, published at
  https://claude.ai/artifact/4ArC6Uxh1TJKFpCfPLQvz2); `scripts/dev/results_run_summary.py`,
  `scripts/dev/d064_sensitivity.py`; D-064 results in `docs/analysis_plan.md`.
- **Findings:**
  - Baseline, 2027–2031 midpoint a year: TX 190k, NC 70k, OH 29k, MN 17k, OR 12k homes permitted. Each starts
    at its 2025 pace; coverage 96.7–99.9% of 2025 panel units.
  - Net new homes, five-year midpoint: missing middle TX 3,006, NC 740, OH 689, MN 410, OR 61; ADUs TX 1,302,
    MN 206, OH 173, NC 79, OR 0. Each is under 1% of the baseline.
  - D-064: NC ADUs −37% (S.L. 2026-59), MN missing middle −12%, NC −6%, TX ADUs −4%; OR unchanged.
  - To check: Oregon ADUs are 0 because uncoded places borrow the coded (Handbook-equivalent) prior, though
    SB 1051 skips cities under 2,500; NC, TX and OR are labelled tier 3 because the bundle's tier is the single
    tier with the most parcels (NC: 1.6M tier 3 against 1.6M in tiers 1 and 2 together).
- **What Claude did and how it was checked:** ran `lotline results` per state (NC failed on a missing Census
  key in the worktree and was rerun after linking `.env`); compared the baseline with 2019–2025 observed totals;
  traced the Oregon zero to the rule inputs; ran the same-seed sensitivity, whose 2025 arm reproduces D-063
  exactly; built the app from the bundles and read the Results tab in the in-app browser.
