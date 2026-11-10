### LB-NNN · 2026-11-10 · `data` · Texas ADU counts under D-074 / D-075: coverage, Austin's k, the HOME rule, College Station
- **Question:** can Texas run NC's ADU counting steps (D-074, D-075 step 1)? That means: how much of Texas sits
  in places with ADU-flagged permits; whether Austin's flag undercount k can be measured; how to count
  Austin's ADUs after HOME; and which other places have open permit sources.
- **Decided by:** Ben reopened WS-TX for this task only (2026-11-10). The detection rule and the HOME rule were
  committed before any count (8d1e7c3d). The deviations after the counts are labelled in the report.
- **Outputs:**
  - `reports/tx/adu-coverage-and-undercount.md` (coverage table, k, HOME rule and estimate, College Station,
    scouting, proposed rule row) and `reports/tx/austin-adu-roll.json` (aggregates only).
  - `src/lotline/adapters/states/tx/austin_adu_roll.py` with `tests/states/tx/test_austin_adu_roll.py`:
    TCAD improvement reader (positional, no personal fields), improvement year, universe and groups, the
    HOME rule, the R/P match.
  - `src/lotline/adapters/states/tx/cstx_permits.py` with `tests/states/tx/test_cstx_permits.py`: new College
    Station source (Socrata `hrbn-znt6`); a row in `config/states/tx.yaml` and in `docs/data_provenance.md`.
  - `scripts/dev/tx_adu_coverage.py`, `scripts/dev/tx_austin_adu_k.py`, `scripts/dev/tx_austin_additions_fetch.py`.
- **Results:**
  - 13.8% of TX's 7.32 M eligible lots are covered (14.1% with College Station); TX has no overlapping units.
  - Austin k = 1.13 (90% 1.09–1.18), from |P∩R| = 242 and |a| = 31. StratMap has no building detail;
    TCAD's 2026 improvement records stand in for a second roll.
  - Austin ADU permits after HOME are a range: 104–217 (2024) and 53–290 (2025), against 330–375 flagged a
    year in 2019–22.
  - College Station: 0.14 ADU permits per 1,000 lots a year (2021–24).
- **What Claude did and how it was checked:**
  - Wrote the rules, code, tests and report.
  - Checked k's inputs by hand against the roll: improvement segment types, parcel-ID survival (532 of 1,605
    flagged parcels), addition permits on group-(b) lots, and the HOME rule's recall and precision on pre-HOME
    R-102 and R-101 permits.
  - Hand-checked College Station's 30 matches and 30 non-matches.
  - A source scout ran as a subagent (web, small queries only).
  - Unit tests on synthetic fixtures pass; `compliance_check.py` 0 FAIL.
  - No engine, scenario, calibration or fit run.
- **Open:**
  - Wiring the HOME rule into `austin_permits` (WS-TX/WS-CORE).
  - Ben's acceptance of College Station's rule rows, and the check of a pre-2018 row.
  - Denton needs Ben's browser download, then an adapter.
  - An older TCAD export would allow a two-roll k.
  - Proposed HANDOFF decision: Austin k = 1.13 (1.09–1.18) is the second measured field-flag source under
    D-075 §2, beside Raleigh's 1.07.
