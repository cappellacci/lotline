### LB-NNN · 2026-10-23 · Build: Fort Worth permit adapter (Texas plan S1a)
- **Question:** can Fort Worth's open permits give the ADU estimate (D-025) a Texas comparison city, and how
  well do they match Census BPS by building size?
- **What I did:**
  - Wrote `fw_permits` (ArcGIS table `CFW_Open_Data_Development_Permits_View`, CC-BY 4.0, filed 2001 on):
    residential building and accessory-structure permits and residential commercial permits only.
  - Found the table holds status snapshots (one row per status a permit passed through) and has no issue
    date: rows collapsed by permit number, permits dated by filing year.
  - Use-type crosswalk `config/crosswalks/tx_fw_use.csv`; ADUs from the description parser only, because the
    source's "Accessory Dwelling" use also holds storm shelters and game rooms.
  - Compared annual units with BPS for Fort Worth (4827000) and measured a parcel-free version of D-008.
- **Inputs:** Texas data plan (`docs/build/tx-data-plan.md`, approved by Ben 2026-10-23); BPS place table.
- **Outputs:** `src/lotline/adapters/states/tx/fw_permits.py`, `tests/states/tx/test_fw_permits.py`,
  `config/crosswalks/tx_fw_use.csv`, `config/states/tx.yaml`, `docs/data_provenance.md` (Fort Worth
  section); issue #221 (contract-change for WS-CORE).
- **Findings:**
  - 297,362 permits kept from 329,678 rows. 1-unit homes are 0.94–1.10 of BPS in every year 2002–2025.
  - 5+ unit homes run up to 2.6× BPS (2020, 2023, 2024): projects repeat the project total on each
    building's permit and there is no parcel for D-008 to group on. A same-filing-date rule brings 2024 to
    1.19× and 2020 to 1.39×; 2022 (1.80×) has another cause.
  - 113 ADU permits in 25 years (garage apartments, "mother-in-law suites"; about 2 in a sample of 29 are
    false positives). Fort Worth allows them only when not rented, so they are non-rental units.
- **Decisions:** proposed in #221: a parcel-free D-008 branch keyed on the filing date.
- **AI:** Claude wrote the adapter and tests (synthetic rows), ran the BPS comparison and the D-008 measure
  on the downloaded table (counts only), and read a sample of ADU descriptions for precision.
- **Open / next:** #221; the 2022 5+ excess and the 2-unit excess in 2022 and 2024 (636 and 1,132 vs BPS 78
  and 794).
