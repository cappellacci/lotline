# WS-NC · North Carolina ingestion and validation

**Start:** after `schemas-v1`. **V0 by Oct 31**, **Charlotte prediction frozen by Nov 17**, V3–V6 by Dec 1.
**Owns:** `src/lotline/adapters/states/nc/`, `config/states/nc.yaml`, `config/reforms/nc.csv`, `config/crosswalks/nc_land_use_*.csv`, `tests/states/nc/`, `reports/nc/`.
**Role:** second full ladder. It has the cleanest **within-city contrasts** (Raleigh R-1 lots; Durham urban vs suburban tier), a blind test (Charlotte 2023) and a fee shock (*Carthage* 2016).

## Read first
- `docs/research/lotline-validation-plan.md` §1–4 (written for NC; the NC roles table lives there)
- `docs/research/lotline-causal-diagram-mm.md` §3
- `docs/research/lotline-causal-diagram-fees.md` §3
- `docs/research/lotline-data-catalog.csv` (rows `state=NC`)
- BUILD_PLAN §5

## Sources

| Key | Source | Access | Feeds | Notes |
|---|---|---|---|---|
| `onemap_parcels` | NC OneMap NC1Map_Parcels (100 counties) | ArcGIS REST (2,000/query) or statewide FGDB | `parcels` | Current only; `parusecode` is county-native, so build crosswalks for the **10 largest counties** first. `structyear` completeness varies. |
| `onemap_dates` | NC1Map_Parcels_Transform_Dates | REST | per-county vintage | Record per-county source dates |
| `wake_realestate` | Wake County real estate files + qualified sales (incl. pre-reval Dec 2023 file) | Bulk xlsx/txt | `parcels` (Raleigh, V2 baseline), prices | Verify the record layout PDF |
| `raleigh_permits` | Raleigh Building Permits FeatureServer | ArcGIS REST | `permits` | Has `adu_type`, `missing_middle` flags. **`housingunitstotal` nearly empty from 2024 and anomalous in 2013**: derive units from `censuslandusecode` and flag. |
| `durham_permits` | Durham All Building Permits (MapServer layer 12) | ArcGIS REST (no outStatistics) | `permits` | `DWELLING_UNITS`, CO date, PIN. **Check freshness first** (last modified Nov 2024?). |
| `meck_permits` | Mecklenburg Building Permits | Open-data download | `permits` (Charlotte) | **No unit counts**: infer from `usdcdesc`/`typeofbldg` (Census codes); `zonecode` identifies N1 lots |
| `zoning_ral`, `zoning_dur`, `zoning_clt` | City zoning layers | ArcGIS Hub/REST | R-1 vs other; urban vs suburban tier; N1 | Pre-reform maps may need archive retrieval |
| `nc_fees` | Raleigh Development Fee Guide; Charlotte Water SDFs; S.L. 2026-59 disclosure (when published) | PDF | `fees` | Real fees ≈ $7k–$7.4k/unit vs the $50k Handbook assumption |
| `carthage_towns` | List of towns that lost "future service" water/sewer impact fees after *Quality Built Homes v. Carthage* (2016-08-19) | Research (UNC School of Government) | V6a | Manual CSV with sources |

## Tasks
- [ ] Adapters + contract tests.
- [ ] Crosswalks for the 10 largest counties' `parusecode` → `land_use_std`.
- [ ] `jurisdictions` with tiers: tier 1 for counties with year built and use codes, tier 2 for use codes only, tier 3 for neither.
- [ ] `config/reforms/nc.csv`, every row with source:
  - Durham EHC 2019-09-03 and SCAD 2023-11-21;
  - Raleigh TC-16-19 (ADU, 2020-07-07);
  - Raleigh TC-5-20 (MM, 2021-07);
  - Raleigh TC-20-21 (MM 2.0, 2022-08-08);
  - Charlotte UDO (2023-06-01);
  - Greensboro ADU (2024-04-16);
  - **S.L. 2026-59 ADU mandate from 2027-01-15** (goes into the baseline for non-coastal cities >50k).
- [ ] **V0:**
  - coverage;
  - Raleigh/Durham/Mecklenburg vs BPS by size class;
  - ADU undercount estimate (local ADU vs BPS 1-unit);
  - Raleigh unit-field repair documented.
  - **For Charlotte, V0 covers only years before 2023-06-01** (holdout).
- [ ] **V1 / V2** with WS-ENGINE. V2 uses the Wake pre-reval Dec 2023 roll as baseline and 2024–26 Raleigh permits as outcomes.
- [ ] **V3** (after `prereg-v1`):
  - Raleigh MM: eligible lots vs **R-1** lots, matched on lot size and value;
  - Durham EHC: urban vs suburban tier;
  - Raleigh ADU: synthetic control;
  - all with the full check list in validation plan V3.
- [ ] **V4:** backtests for Durham 2019, Raleigh 2020 and Raleigh 2021, calibrated without each place.
- [ ] **V5:** Charlotte duplex/triplex units on N1 lots, June 2023–2025. Freeze `results/frozen/V5-NC-CHARLOTTE.json` by **Nov 17**.
- [ ] **V6a:** *Carthage* DiD (exploratory) once the town list exists.

## Acceptance
Same as WS-MN: conformity, provenance, V0 thresholds or explained gaps, holdout test, sourced reform rows.

## Gotchas
- County land-use codes differ.
- Durham MapServer lacks outStatistics, so page through objectIds.
- Mecklenburg permits include 6 towns besides Charlotte; filter by jurisdiction.
- No open statewide zoning: outside the three cities, assume SF-only unless known, and flag the tier.
