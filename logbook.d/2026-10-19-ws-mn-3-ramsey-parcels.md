### LB-NNN · 2026-10-19 · Build: WS-MN Ramsey County parcel points (current roll, outside St. Paul)
- **Question:** What does Ramsey County's own parcel layer add for the metro, and can it be read without touching
  the St. Paul holdout?
- **What I did:**
  - Added `ramsey_parcels` (`CAD_AttributedParcelPoint_ViewOnly`): explicit non-personal fields; St. Paul's site-city
    parcels excluded server-side; holdout snapshot rule on point and site-city jurisdictions before attributes.
  - Crosswalk `config/crosswalks/mn_land_use_ramsey.csv` for the county's detailed land-use descriptions.
  - The county firewall answers HTTP 403 to "... OR ... IS NULL" in one where clause, so two queries.
- **Inputs:** Ramsey County GIS; TIGERweb ACS 2025 boundaries (cached); MN jurisdictions table.
- **Outputs:** `src/lotline/adapters/states/mn/ramsey_parcels.py`, `tests/states/mn/test_ramsey_parcels.py` (+ fixture),
  the crosswalk, `config/states/mn.yaml`, `docs/data_provenance.md`; processed `parcels/ramsey_parcels.parquet`.
- **Findings:** Only a current roll exists (property data 2026-10-08), so St. Paul has no rows here: its parcel state
  through 2023 comes from `metc_parcels`. 84,406 suburban parcels; 99.9% match the Met Council 2026 roll by PIN, land use
  agrees for 94.6% and units for 100%. New: lot frontage for 97% of single-family lots (median 83 ft).
- **Decisions:** Proposed in the PR (St. Paul options).
- **AI:** Claude wrote the adapter and synthetic tests, ran the real fetch and compared it with Met Council's roll.
- **Open / next:** Minneapolis assessor parcels in place of Hennepin's layer (separate PR).
