### LB-NNN · 2026-10-22 · Build: eligible-parcel history for places counted from a parcel roll (#208)
- **Question:** how do places counted from a parcel roll get a denominator in the years their roll doesn't cover
  (2010–2024), so baselines, V1 backtests and the fee scenario can use them?
- **What I did:**
  - `build/eligible.scale_history` (option 1 in #208, approved by Ben): each roll year anchors a scale factor
    parcels / ACS one-unit-detached homes (ACS end year = roll year, or the nearest within `scale_max_year_gap`
    = 3); other ACS years get ACS × factor, linear between two or more anchors and flat outside. Real roll years
    keep their counts. `combine` adds the filled rows.
  - New `denominator_source` value `parcels_scaled_acs` (schema; `docs/schemas.md` regenerated). The ADU
    scenario's overlap step treats it like `parcels` (`eligible.PARCEL_SOURCES`).
  - New parameter `scale_max_year_gap` in `config/params/eligibility.yaml`; parameter table regenerated.
    Decision log D-035 and assumption A2 updated.
  - Rebuilt NC `eligible_parcels` (`lotline fetch --state NC --source eligible`) to check; no model runs.
- **Inputs:** processed NC parcels (NC OneMap 2026, Wake Nov 2019 and Dec 2023), ACS B25024 via the IO layer.
- **Outputs:** `src/lotline/build/eligible.py`, `src/lotline/schemas.py`, `src/lotline/model/scenarios/adu.py`,
  `config/params/eligibility.yaml`, `tests/core/test_eligible.py`, `docs/analysis_plan.md` (D-035),
  `docs/model_and_assumptions.md`, `docs/schemas.md`.
- **Findings:**
  - All 218 parcel-counted NC jurisdictions now have all 15 years 2010–2024 (6,488 filled rows); no real roll
    row and no ACS-fallback row changed.
  - ADU scale factors: median 1.00, middle half 0.91–1.11. Raleigh 0.93/0.92 (2019/2023 anchors), Durham 0.97,
    Greensboro 1.01. Outliers are mostly county remainders (Bladen 0.42, Union 0.46).
  - Year-built backcast check (option 2): Greensboro within 5% of the scaled series in 2010–2024; Durham's roll
    has year built for 0.5% of eligible parcels, so it can't be checked.
- **Decisions:** D-035 (ACS scaled to the roll; Ben approved option 1 on 2026-10-21).
- **AI:** Claude Code (Opus 5.5) wrote the code, tests and docs. Hand-worked tests cover one anchor, two anchors
  (interpolated and flat), per-theme factors, the year-gap limit, zero or missing ACS and the nearest-year tie
  rule; the NC rebuild was diffed against the previous table.
- **Open / next:** the county-remainder outliers (Bladen, Union) look like roll assignment, not scaling: worth a
  WS-NC look. Rolls newer than ACS anchor ACS 2024, so the filled 2024 equals the 2026 roll count.
