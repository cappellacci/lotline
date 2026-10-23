### LB-NNN · 2026-10-23 · Build: San Antonio permit adapter (Texas plan S1b)
- **Question:** can San Antonio's open permits give the ADU estimate (D-025) a treated Texas city, and do
  they line up with Census BPS?
- **What I did:**
  - Wrote `sa_permits` (two Open Data SA CSVs, 2020-07 on, CC-BY) through the IO layer; robots.txt allows the
    `/dataset/` CSV links and disallows the API, which is not used.
  - Kept building-type permits, collapsed revisions to one row per permit number, ADUs from the city's
    "Res Accessory Dwelling Permit" type, new houses as one unit, ETJ permits under the Bexar remainder.
  - Compared annual counts with BPS for San Antonio (4865000).
- **Inputs:** Texas data plan (`docs/build/tx-data-plan.md`, approved by Ben 2026-10-23); BPS place table.
- **Outputs:** `src/lotline/adapters/states/tx/sa_permits.py`, `tests/states/tx/test_sa_permits.py`,
  `config/states/tx.yaml` (source entry), `docs/data_provenance.md` (San Antonio section).
- **Findings:**
  - 35,695 permits kept (33,110 city, 2,585 ETJ). New houses, city plus ETJ, are 94–102% of BPS one-unit
    homes in 2021–2025, so BPS files ETJ permits under San Antonio.
  - 295 ADU permits after removing revisions (129 of the 421 ADU rows were revisions): 39, 41, 50, 60 and 60
    a year in 2021–2025, against the UDC change of 2023-01-01.
  - No unit field: 2–4 and 5+ unit homes stay with BPS.
- **Decisions:** proposed: ETJ permits go to the county remainder, not the city (the city's parcels are the
  denominator); BPS comparisons add them back.
- **AI:** Claude wrote the adapter and tests (synthetic rows) and ran the BPS comparison on the downloaded
  files; counts printed only, nothing stored beyond the processed table.
- **Open / next:** ETJ permits outside Bexar County are filed under Bexar; 2020 is a part year.
