# Thread 1: Missing-middle panel and D-024 pre-registration (WS-ENGINE-MM)

**Goal:** build the data panel for estimating the effect of allowing 2–4 unit homes in single-family zones, and write its pre-registration (D-024) **before** any estimate is run. Mirror the ADU design (D-023, and D-025 if approved), adapted to missing middle.

**Read first:** `docs/analysis_plan.md` D-023 (and its notes on the aborted run: separation, thin data); `docs/research/lotline-causal-diagram-mm.md`; `docs/research/lotline-statistical-protocol.md` §5.6–5.7; `src/lotline/model/estimate_adu.py` (reuse its panel and estimator patterns; don't duplicate code: factor shared pieces out if needed and say so in the PR).

**Data already in the repo/data dir:**
- **Outcome:** permits for duplexes, triplexes and fourplexes by place-year. Met Council `metc_residential_permits` flags building types (DTQ) by parcel from 2016. Also available: Minneapolis CCS, Austin, Raleigh and Durham permits (building_type_std U2/U3_4/DTQ); BPS 2-unit and 3–4-unit counts by place.
- **Treatment:** missing-middle rows in `config/reforms/*.csv` (theme `missing_middle`), plus "when 2–4 units became legal" in `docs/research/ordinances/batch1-2026-10-20.json` (`missing_middle_legal`: Minneapolis, St. Paul, Duluth, St. Louis Park, Austin, Raleigh, Durham). St. Paul is a holdout: rules OK, outcomes never.
- **Exposure:** MM-eligible parcels (eligibility rule 1.1, D-014: SF-zoned houses and vacant residential lots).

**Deliver (one PR, no real-data estimates):**
1. `model/estimate_mm.py` panel builder: place-years, outcome, exposure offset, adoption year, dose (units allowed: 2, 3, 4; by right vs permit), pre-adoption modifiers (price-to-cost from the pro forma's plex prototypes, home value, pre-reform 2–4 unit permit rate, demand index from thread 3 when available, household growth meanwhile), ADU-rule indicator (the reverse substitution).
2. A smoke script printing counts only: places, adopters per year, comparisons, places with zero outcomes in every year (the D-023 lesson: say upfront whether the data can support fixed effects).
3. **D-024 in `docs/analysis_plan.md`**: estimand, sample, model (state why fixed effects or a hierarchical NB, given the zero counts), checks with pass rules, out-of-sample test (e.g. predict Durham/Raleigh from Minnesota or vice versa), forecast use. Written before any estimate.
4. Synthetic tests for the panel builder, including mostly-zero panels.

**Done when:** PR open with green CI, D-024 written, smoke counts in the PR. Do not run estimates; Ben approves D-024 first.
