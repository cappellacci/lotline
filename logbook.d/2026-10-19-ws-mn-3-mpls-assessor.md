### LB-NNN · 2026-10-19 · Build: WS-MN Minneapolis assessor parcels (2017-2026) in place of Hennepin's layer
- **Question:** How do we get units, dwelling type and year built for Minneapolis parcels when Hennepin County's
  layer can't be read under our rules?
- **What I did:**
  - Checked Hennepin: `gis.hennepin.us/robots.txt` disallows `/` for all agents; the Hub download of "County Parcels"
    is a whole-file export with owner and taxpayer names (no field selection) and its metadata lists no unit field.
  - Added `mpls_assessor_parcels`: the city's CC0 assessor tables, one per assessment year 2017-2026 (three layouts
    mapped to one set of names), explicit non-personal fields; per-building rows (2025-2026) collapsed per PIN.
  - Crosswalks `config/crosswalks/mn_land_use_mpls.csv` (property type) and `mn_land_use_mpls_building.csv`
    (building use: ADU houses, apartment sizes), refined by TOTAL_UNITS.
- **Inputs:** City of Minneapolis open data (ArcGIS Online, org afSMGVsC7QlRK1kZ).
- **Outputs:** `src/lotline/adapters/states/mn/mpls_assessor_parcels.py`, `tests/states/mn/test_mpls_assessor_parcels.py`,
  the crosswalks, `config/states/mn.yaml`, `docs/data_provenance.md`; processed `parcels/mpls_assessor_parcels.parquet`.
- **Findings:** 1,309,636 parcel-years (about 131k a year). Units known for 99.7% of parcels 2018-2024 (215,148 units
  in 2023), but the 2025-2026 tables report 0 units for single-family houses (81% null). Land use agrees with Met
  Council's 2023 roll for 97.8% of parcels. Houses/duplexes with an ADU: 51 (2017) to 145 (2021), then 80 (2022) after a
  relabelling of building uses: a recording break to check (C32).
- **Decisions:** Proposed in the PR: replace `hennepin_parcels` with this source for Minneapolis.
- **AI:** Claude found the source, wrote the adapter and synthetic tests, ran the real fetch and compared it with Met Council.
- **Open / next:** suburban Hennepin units remain unavailable (null); eligible parcels (task 4).
