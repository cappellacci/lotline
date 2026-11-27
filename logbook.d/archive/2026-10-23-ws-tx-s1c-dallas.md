### LB-NNN · 2026-10-23 · Build: Dallas permit adapter (Texas plan S1c)
- **Question:** can Dallas's permits give the ADU estimate (D-025) a large Texas comparison city, and how well
  do they match Census BPS?
- **What I did:**
  - Followed a lead from Ben's notes on public Dallas sources (disclosed in `docs/disclosures.md`; no code,
    configuration or data from that work used) to the City's "New Permits 1971-2024" ArcGIS layer, a one-time
    POSSE extract of 1,798,425 permits; profiled it myself (fields, statuses, unit coding by decade).
  - Wrote `dallas_permits`: residential new construction and additions, issued statuses only, units from the
    land-use crosswalk and UNITS, ADUs from the description parser. Chose it over the Socrata set planned in
    S1c (2018-2025, no unit field).
  - Compared units with BPS for Dallas (4819000) and measured the parcel-free repeated-total rule (#221).
- **Inputs:** Texas data plan (`docs/build/tx-data-plan.md`, S1c approved by Ben 2026-10-23); BPS place table.
- **Outputs:** `src/lotline/adapters/states/tx/dallas_permits.py`, `tests/states/tx/test_dallas_permits.py`,
  `config/crosswalks/tx_dallas_land_use.csv`, `config/states/tx.yaml`, `docs/data_provenance.md` (Dallas
  section), `docs/disclosures.md`; Dallas evidence added to issue #221.
- **Findings:**
  - 134,124 permits kept of 145,944 requested rows. 1-unit homes are 0.84-1.01 of BPS in 2005-2024; 2-unit
    homes within about 10% of BPS from 2014.
  - 5+ units as reported run up to 3.3x BPS (2023) and 7.5x (2024, a part year): projects repeat their total
    on every building's permit. Grouping same-day permits with the same count brings 2010, 2019 and 2022
    to 0.98-1.02.
  - One ADU in the window, as expected with no by-right ADU. The layer ends 2024-11-12: 2025 is not covered.
- **Decisions:** none new (#221 open for WS-CORE and Ben).
- **AI:** Claude found and profiled the layer, wrote the adapter and tests (synthetic rows) and ran the BPS
  comparison on the downloaded table (counts only).
- **Open / next:** 2025 for Dallas (City monthly workbooks or a records request); #221.
