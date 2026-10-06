# WS-MN · Minnesota ingestion and validation (primary state)

**Start:** after `schemas-v1` (target Oct 17–18). **V0 by Oct 31**, V1–V2 by Nov 10, **St. Paul prediction frozen by Nov 17**, V3–V7 by Dec 1.
**Owns:** `src/lotline/adapters/states/mn/`, `config/states/mn.yaml`, `config/reforms/mn.csv`, `config/crosswalks/mn_land_use.csv`, `tests/states/mn/`, `reports/mn/`.
**Role:** full validation ladder. Minnesota is the recommended official benchmark state. It is a low-uptake state; predicting that correctly is the point.

## Read first
- `docs/research/lotline-mn-scouting.md` (all of it)
- `docs/research/lotline-data-catalog-mn.csv`
- `docs/research/lotline-validation-plan.md`
- `docs/research/lotline-causal-diagram.md` §4 (within-place designs)
- BUILD_PLAN §5

## Sources (register each in `config/states/mn.yaml`)

| Key | Source | Access | Feeds | Notes |
|---|---|---|---|---|
| `metc_permits` | Met Council Residential Building Permits 2009–2024 | Geospatial Commons download `us-mn-state-metc-econ-residential-building-permts` | `permits` (SFD/ADU/TH/DTQ/MF5, PIN, removals) | **Core outcome.** Public domain. Check whether 2025 is posted. DTQ → `DTQ`, MF5 → `MF5` (don't split). |
| `metc_parcels` | Met Council regional parcels: current + `Parcels_2021`…`Parcels_2025` | ArcGIS REST `arcgis.metc.state.mn.us/data1/rest/services/parcels` (2,000/page) or file GDB | `parcels` | Public domain. Schema changed 2019-01-01. **Hennepin NUM_UNITS/DWELL_TYPE blank**: use `hennepin_parcels`. Pre-2021 vintages: Ben is requesting them; don't scrape token-locked services. |
| `hennepin_parcels` | Hennepin County parcels | Hennepin open data (the `gis.hennepin.us` robots rule may block generic fetchers; use the documented open-data download) | `parcels` (Minneapolis) | BUILD_YR, PR_TYP_NM1–4, SALE_PRICE/DATE |
| `ramsey_parcels` | Ramsey CAD_AttributedParcelPoint | ArcGIS REST | `parcels` (St. Paul) | YearBuilt, LivingUnit, DwellingType, SalePrice |
| `mngeo_parcels` | MnGeo opt-in parcels (59/87 counties) | FeatureServer / CSV export | `parcels` (Greater MN, tier 2) | Sparse attributes; record per-county completeness |
| `mpls_permits` | Minneapolis CCS Permits (CC0) | ArcGIS REST `services.arcgis.com/afSMGVsC7QlRK1kZ/.../CCS_Permits/FeatureServer/0` | `permits` (Minneapolis detail, fees) | **Rolling window from Dec 2016: write a dated snapshot on every fetch.** No ADU flag: infer `ADU` only when an SFD/Accessory permit adds 1 unit on a parcel with an existing house, and set `type_confidence=inferred`. |
| `stpaul_permits` | St. Paul building permits | ArcGIS REST | secondary | No unit counts; looks stale since mid-2025. Use Met Council for St. Paul outcomes. |
| `mpls_zoning` | Minneapolis primary zoning + built form (CC0) | ArcGIS REST | `parcels.zoning_raw`; FAR dose | |
| `stpaul_zoning` | St. Paul principal zoning | ArcGIS REST | H1/H2 district identification | Confirm canonical service (one item points to `_TEST`) |
| `metc_plu` | Met Council planned land use | ArcGIS REST | SF-only proxy outside the two cities | Plan ≠ zoning: tier flag |
| `mn_fees` | §326B.145 fee reports (LRL PDFs); Met Council SAC $2,485/unit | PDF parse (small sample of cities) | `fees` | Real-fee sanity check only |
| national | BPS, ACS, FHFA, FRED, PPI | WS-CORE | | |

## Tasks
- [ ] **Day 1:** snapshot `mpls_permits` and `stpaul_permits` (dated raw copies). Import Ben's manual exports from `~/lotline-data/manual/` if present, recording them in the manifest as `manual_export`.
- [ ] Adapters + contract tests for every source above. Small fixtures only in `tests/`.
- [ ] `config/crosswalks/mn_land_use.csv`: county use-class strings → `land_use_std` (Ramsey "1A/1B/4BB RESIDENTIAL SINGLE UNIT", etc.).
- [ ] `jurisdictions` for MN: cities **and townships** (MN townships issue permits), with tiers. Tier 1: 7-county metro. Tier 2: opt-in counties. Tier 3: the rest.
- [ ] `config/reforms/mn.csv`, coded with the protocol §5.4 rubric. Two-coder rule: Claude codes, Ben spot-checks.
  - Minneapolis ADUs (2014; owner-occupancy change 2021, verify);
  - Minneapolis 3-unit amendment (eff. 2020-01-01);
  - 2040 injunction windows (2022-06-17; status quo ante effective ~2023-11-04 → reversed 2024-05-13);
  - St. Paul ADU (2016 University Ave; 2018 citywide);
  - St. Paul Ord. 23-43 (H1/H2, 2023);
  - **ADU ordinance adoption dates for metro suburbs.** Research task: start with the 20 largest; this unlocks the staggered ADU design.
- [ ] **V0 report** (`reports/mn/V0.md`):
  - coverage and null rates;
  - Met Council vs BPS by city-year and size class;
  - Minneapolis CCS vs Met Council for Minneapolis;
  - ADU counts vs published figures (≈300 metro ADUs 2016–24; Minneapolis 232 through 2022);
  - recording-regime breaks (C32).
- [ ] **V1 baseline** with WS-ENGINE: fit through 2018 and forecast 2019–24 for non-reforming metro cities.
- [ ] **V2 mechanism** (with WS-ENGINE): regional parcels 2021 year-end as the baseline state, Met Council permits 2022–24 as outcomes.
- [ ] **V3 causal** (after `prereg-v1`):
  - (a) **staggered ADU DiD across metro cities** (Callaway–Sant'Anna, not-yet-treated controls, NB with eligible-parcel offset);
  - (b) Minneapolis MM: synthetic control vs metro and Midwest cities, plus the border contrast. Injunction window as a sensitivity only.
- [ ] **V5 blind test:** predict St. Paul DTQ/MF5 units on H1/H2 lots for 2024–26 from data ≤2023. Freeze to `results/frozen/V5-MN-STPAUL.json` by **Nov 17**. Unblind in week 7.
- [ ] **V7:** overlap diagnostics for Greater MN places vs the calibration set.

## Acceptance
- All MN adapters conform to `schemas-v1`; provenance rows exist.
- `reports/mn/V0.md` meets validation plan V0 thresholds or explains every gap.
- The holdout test passes.
- Reform CSV has a source URL for every row.

## Gotchas
- PIN formats differ by county; normalize to a `county_fips + local_pin` string.
- Repeated SALE_VALUE across multi-parcel sales: flag sale groups.
- ADU tracking start year in Met Council data is unknown: check for a recording break (C32) before using early years.
- DTQ lumps 2–4 units; 5–6 units sit in MF5 with large buildings. Report MM outcomes as DTQ (+ MF5 sensitivity).
