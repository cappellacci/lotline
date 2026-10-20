### LB-NNN · 2026-10-19 · Build: WS-MN Met Council regional parcels (2021-2025 + current)
- **Question:** Can the 7-county metro get real parcel denominators by roll, with St. Paul kept blind after 2023?
- **What I did:**
  - Added `metc_parcels`: the 7-county parcel point layers (`Parcel_Points_2021..2025`, `Parcel_Points_Aggregate`),
    downloaded per county and OBJECTID range with an explicit non-personal field list.
  - `vintage` = service-name year, `vintage_date` = county's latest `EXP_DATE` (Ben, 2026-10-19); jurisdictions by
    `geo.place_or_township`, checked against `CTU_NAME`; holdout snapshot rule on both before attributes are read.
  - Land-use crosswalks `config/crosswalks/mn_land_use.csv` (use class, ordered regex rules per county) and
    `mn_land_use_dwelling.csv` (dwelling type), refined by unit counts.
  - Checked that pre-2021 year-end services (`ds1/GISParcels/...`) are token-locked (HTTP 499): not usable.
- **Inputs:** Met Council `data1/rest/services/parcels`; TIGERweb ACS 2025 boundaries; MN jurisdictions table.
- **Outputs:** `src/lotline/adapters/states/mn/metc_parcels.py`, `tests/states/mn/test_metc_parcels.py` (+ fixture),
  the two crosswalks, `config/states/mn.yaml`, `docs/data_provenance.md`; processed `parcels/metc_parcels.parquet`.
- **Findings:** 6,576,148 parcel-rolls (2021 1.12M ... current 1.07M). The "2025" roll is a mid-2025 export
  (June-July), not year-end; the "2023" roll was exported 2023-10-01 (Scott) to 2024-01-08 (Hennepin). St. Paul has
  ~83.3k parcels in each of 2021-2023 and none after. Point placement agrees with `CTU_NAME` for 99.94% of parcels.
  Units are populated in Dakota, Ramsey, Washington only; Hennepin also has no building area; Hennepin sales are
  dated by month, so they get no multi-parcel flag.
- **Decisions:** Proposed in the PR (crosswalk reading of class 4b(1) "1-3 units" as DUPLEX unless units say otherwise).
- **AI:** Claude wrote the adapter, crosswalks and synthetic tests, ran the real fetch and the checks; St. Paul rows
  from 2024+ rolls were never summarized (only post-filter counts).
- **Open / next:** Ramsey and Minneapolis parcel sources (task 3); eligible parcels from these rolls (task 4).
