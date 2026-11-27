### LB-NNN · 2026-10-27 · WS-OH · Real yearly eligible-lot counts for Franklin County places (S6a follow-up)

**Question.** The S6a check (#237) found that D-035's scaled history follows ACS rather than parcels in Franklin
County. Ben asked (2026-10-27) to replace the scaled years with the real yearly Franklin counts.

**Outputs.** `src/lotline/adapters/states/oh/oh_parcels.py` (`FRANKLIN_ROLLS`, `franklin_share`, `franklin_roll`,
`franklin_yearly_rolls`, `download_franklin_roll`; docstring and PROVENANCE); `tests/states/oh/test_oh_parcels.py`.
Rebuilt processed Ohio `parcels`, `jurisdictions` and `eligible_parcels` in `LOTLINE_DATA_DIR`.

**What changed.** The Auditor's year-end `Parcel.xlsx` files for 2016–2025 (other than 2023, the statewide roll's
year) became extra `oh_parcels` vintages for the jurisdictions with at least 99% of their houses in Franklin
County. `build.eligible` now counts those years from parcels and scales only 2010–2015 (D-035, as for Wake's 2019
roll). 14 jurisdictions changed: Bexley, Brice, Gahanna, Grandview Heights, Grove City, Groveport, Hilliard,
Marble Cliff, New Albany, Obetz, Upper Arlington, Whitehall, Worthington and unincorporated Franklin. Rows outside
Franklin County did not change. Columbus (97.7% in Franklin), Dublin, Westerville, Reynoldsburg and Canal
Winchester keep one roll. Tiers are unchanged (72 tier 1).

**How Claude worked and checked.** Claude (Claude Code) wrote the code and tests on synthetic rows: roll versus
district placement at the 95% edge, card-suffix duplicates, the archive's own land use, the 99% county-share
gate, skipping the roll year, and year built from the dwelling file. The rebuild diffed the eligible table against
a backup: only Franklin rows changed. The first rebuild dropped Whitehall to tier 2: its renumbered parcels had no
year built in its latest roll (2025). Year built now also comes from the Auditor's dwelling file, and the rebuild
restored tier 1.
