### LB-NNN · 2026-11-10 · Data (NC): Asheville ADU permits
- **Question:** can record-level ADU permit counts for Asheville (3702140) come into Lotline, to widen the
  NC ADU base beyond Raleigh, Durham, Greensboro and the Mecklenburg towns?
- **What I did:**
  - Scouted Asheville's open data: the city's Accela Permits View (ArcGIS, every permit since the November
    2013 Accela launch, nightly, Open Data Commons PDDL 1.0) is usable; nothing else adds to it.
  - Wrote `src/lotline/adapters/states/nc/asheville_permits.py`: ADUs from the city's "ADU Detached" /
    "ADU Attached" types (2022 on), else from the shared description parser on house, accessory and
    alteration permits only, with an "existing ADU" exclusion. Registered in `config/states/nc.yaml`.
  - Fetched it through the IO layer (`lotline fetch --state NC --source asheville_permits`; 46,686 permits
    kept) and added its section to `docs/data_provenance.md` (only Asheville's lines, to avoid churn from
    other sessions' re-fetches in the shared manifest).
  - Hand-checked two draws of 30 description matches and 30 likely-word non-matches; measured recall
    against the city's own ADU flag.
  - Read the 1997 UDO adoption minutes, the 2015 ADU news item and the city's text-amendment table for the
    rule history.
- **Inputs:** Accela Permits View (2026-11-10); `processed/nc/eligible_parcels/eligible.parquet`; BPS place
  rows (cross-check only).
- **Outputs:** `reports/nc/asheville-adu-scout.md`; the adapter; `tests/states/nc/test_asheville_permits.py`
  (12 tests, synthetic fixture); `config/states/nc.yaml` source entry; `docs/data_provenance.md` section.
- **Findings:**
  - 361 ADU permits 2014 to 2026-11-08, 13-49 a year: about 1-2.7 per 1,000 eligible lots, peaking in
    2016-2018 after Ordinance 4431 (June 2015).
  - Description rule: precision 27/30 (90%) on the final rule; recall 63% against the city's flag (74%
    detached, 41% attached), so pre-2022 counts are a floor.
  - 2024 permits (199 houses + 56 townhouses + 30 ADUs = 285) match BPS's fully reported 279 single-unit
    homes. BPS Asheville rows are imputed in 2015-2022, which raises this source's value.
  - No issue date (years are application years) and no county PIN.
- **Decisions:** proposed for HANDOFF in the PR: add `asheville_permits` as an NC ADU outcome source;
  treat the 2015 Asheville ADU row as an in-window event; proposed reform rows (1997 `[predates]`, 2026
  Ord. 5175) wait for sibling sessions to merge before going into `config/reforms/nc.csv`.
- **AI:** Claude Code scouted, wrote the adapter, tests and report, and did the hand check (each match and
  non-match read in full). Checked by the tests, the schema validation on the real pull, the BPS
  cross-check, and `compliance_check.py`.
- **Open / next:** shared-parser misses ("no longer ... ADU", in-law suites without a kitchen,
  "additional dwelling unit"); code the proposed rule rows; read Ordinance 5175.
