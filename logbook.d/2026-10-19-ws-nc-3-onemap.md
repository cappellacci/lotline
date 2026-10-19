### LB-NNN · 2026-10-19 · Build: NC OneMap parcels for the ten largest counties
- **Question:** Can NC OneMap give parcel denominators (land use, year built, vintage) for the ten largest NC
  counties, and which data tier is each?
- **What I did:**
  - Wrote `onemap_parcels` (non-personal fields only; vintage per county from the Transform Dates layer) and a
    per-county config: field order, how many fields describe a building, the built signal (`improvval`, or
    `structyear` for Union, which sends no building values), the vacant rule and the data tier.
  - Built crosswalks for Wake, Durham and Mecklenburg, then Buncombe, Cabarrus, Cumberland, Forsyth, Gaston,
    Guilford and Union from each county's distinct codes; reviewed every mapping and fixed keyword traps
    (manufacturing ≠ manufactured homes, "Indoor" ≠ industrial, solar farms ≠ agriculture).
  - Downloaded all ten counties (about 1.79 million parcel points); for Mecklenburg only distinct code lists
    were looked at, with no counts, until Charlotte can be excluded.
- **Inputs:** NC1Map_Parcels layer and NC1Map_Parcels_Transform_Dates (2026-10-19); Wake Code Descriptions PDF.
- **Outputs:** `src/lotline/adapters/states/nc/onemap_parcels.py`, `config/crosswalks/nc_land_use_*.csv` (10
  counties + `nc_land_use_counties.csv`), tests.
- **Findings:** tier 1 Wake, Guilford, Cumberland, Gaston (Mecklenburg provisional); tier 2 Durham, Forsyth,
  Buncombe (no `structyear`) and Union (year built, but one RES class); tier 3 Cabarrus (no use code, no year).
  OneMap's Wake codes do not separate townhouses from detached houses (the Dec 2023 county roll does).
- **Decisions:** proposed: Union tier 2 (coarse codes) rather than 1; Guilford MULTI-FAMILY<4 → TRI_QUAD.
  Ben decided: Mecklenburg DUPLEX-TRIPLEX → DUPLEX and patio homes → SF_ATTACHED (2026-10-19).
- **AI:** Claude (WS-NC) wrote the adapter, crosswalks and synthetic tests and reviewed the distributions.
- **Open / next:** the processed table needs place assignment (TIGERweb), blocked while census.gov rejects requests
  from this network; Mecklenburg's figures and the provenance section follow once it is back.
