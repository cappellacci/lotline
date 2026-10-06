# WS-TX · Texas ingestion and Austin validation

**Start:** week 3 (Oct 28), after MN/NC V0 lands. **V0 by Nov 10**; V3/V4 (Austin) by Dec 1.
**Owns:** `src/lotline/adapters/states/tx/`, `config/states/tx.yaml`, `config/reforms/tx.csv`, `config/crosswalks/tx_*.csv`, `tests/states/tx/`, `reports/tx/`.
**Role:** proves two things:
1. The **"no sale prices" path.** Texas is a non-disclosure state, so the pro forma must run on appraisal values, flagged as such.
2. A clean missing-middle test on the best city permit data we have (Austin HOME).

Texas's ladder is deliberately lighter: V0, V1, V3/V4 for Austin, statewide run, V7.

## Read first
`docs/research/lotline-data-catalog.csv` (rows `state=TX`), `docs/research/lotline-state-reassessment.md` §3, BUILD_PLAN §5.

## Sources

| Key | Source | Access | Feeds | Notes |
|---|---|---|---|---|
| `austin_permits` | Austin Issued Construction Permits (`3syk-w9eu`) | Socrata SODA | `permits` | 1970–2026. Permit Class R-101 SF, **R-102 secondary unit (ADU)**, R-103 two-family. Units, completed date, demolitions, TCAD ID. Validate that R-102 = ADU and how additions are coded. Public domain. |
| `austin_units_summary` | New Residential Units summary (`2y79-8diw`) | Socrata | V0 cross-check | |
| `tcad` | Travis CAD certified roll exports 2022–2026 (2020 via TDL Dataverse) | Zip/JSON | `parcels` (Austin) | Values, improvements; no sale prices |
| `stratmap` | StratMap land parcels (2019, 2022, 2024, 2025 collections) | DataHub downloads by county; some REST vintages token-gated | `parcels` statewide | `stat_land_use` (PTAD codes, A1 = SF) is the standard field; `year_built` sparse |
| `hcad` | HCAD PDATA | Bulk tab-delimited | Houston parcels | Houston has **no zoning**: "SF-restricted" means deed-restricted. Treat Houston as a special case; document the assumption. |
| `sa_permits` | San Antonio building permits 2020+ (CKAN, CC-BY) | CSV | `permits` | Confirm the unit field |
| `austin_fees` | Austin Water impact fees ($7,700/LUE) + Ch. 395 CIP reports | Web/PDF | `fees` | |

## Tasks
- [ ] Adapters + contract tests; PTAD state-code crosswalk → `land_use_std`.
- [ ] `jurisdictions` with tiers. 254 counties; most are tier 2–3.
- [ ] `config/reforms/tx.csv`, each row sourced:
  - Austin HOME phase 1 (Dec 2023, 3 units/lot) and phase 2 (May 2024, small lots);
  - Houston lot-size reforms (1998 inside the Loop, 2013 citywide);
  - San Antonio ADU (2023);
  - **check 2025 state laws** for anything that changes headroom (e.g., small-lot or ADU bills).
- [ ] **V0:** Austin permits vs BPS for Austin by size class; R-102 counts vs Austin's ADU dataset (`687g-qcqy`); TCAD coverage.
- [ ] **V1:** baseline for TX places (BPS).
- [ ] **V3/V4 Austin** (after `prereg-v1`): HOME phase 1 effect on 2–3 unit permits in SF-3 vs comparison zones; backtest calibrated without Austin. Post-period is ~2.5 years; say so.
- [ ] **Price path:** pro forma inputs from appraisal market values + ACS rents, with a stated caveat and a sensitivity (± appraisal-to-market ratio).
- [ ] Statewide run with tier flags.

## Gotchas
- Dallas open permits stopped in 2020.
- Houston publishes only monthly aggregates; use HCAD parcel changes for Houston outcomes.
- StratMap schemas differ by county and year.
