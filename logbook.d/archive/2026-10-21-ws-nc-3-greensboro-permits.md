### LB-NNN · 2026-10-21 · Build: Greensboro building permits adapter (NC thread 10, S3)
- **Question:** can Greensboro's permits give the NC ADU estimate (D-025) a third adoption (2024-04-16) and
  the baseline a third NC city with local permits?
- **What I did:**
  - Found the city's open permit table with one ArcGIS search (the catalog said there was none) and checked
    its fields, values and yearly counts with statistics queries before downloading.
  - Wrote `greensboro_permits` (types and units from the occupancy and `NumUnits`, ADUs from the shared
    description parser) with synthetic tests; downloaded it through the IO layer (127 files).
  - Compared yearly units with Census BPS for Greensboro and fixed a double count it exposed.
- **Inputs:** https://gis.greensboro-nc.gov/arcgis/rest/services/OpenGateCity/OpenData_HRES_DS/MapServer/2;
  processed NC BPS.
- **Outputs:** `src/lotline/adapters/states/nc/greensboro_permits.py`, `config/crosswalks/nc_gso_occupancy.csv`,
  `tests/states/nc/test_greensboro_permits.py`, `config/states/nc.yaml` (source entry), catalog row,
  `docs/data_provenance.md`.
- **Findings:**
  - 111,648 permits kept (1990–2026). New single-family plus townhouse units are within about 5–10% of BPS
    one-unit in 2010–2025 (2025: 924 vs 906); duplexes match BPS two-unit; apartments from 2020 match BPS
    5+ closely (2024: 1,332 vs 1,332).
  - Per-apartment permits sometimes repeat the building's unit count (144 in 2021: 3,456 extra units), so
    apartments are counted from shell permits only; before 2019 the source has no multifamily units.
  - ADUs named in descriptions: 35 in all, rising after the 2024 reform (3, 3, 5 in 2023–2025; 14 so far in
    2026). Likely an undercount ("guest house", "in-law suite" are not read).
- **Decisions:** none.
- **AI:** Claude Code (Opus 5.5) wrote the adapter, tests and comparison; checked against BPS by year and by
  synthetic tests of every rule in the docstring.
- **Open / next:** V0 for Greensboro (size-class table vs BPS) and its use in the D-025 panel (WS-ENGINE).
