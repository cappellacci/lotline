### LB-NNN · 2026-11-17 · Build: WS-SCALE task 3 (part 2), one aliases file per state
- **Question:** Can the fixed name-to-GEOID lists hard-coded in adapters live in one data file per state?
- **What I did:**
  - `config/crosswalks/{nc,or,tx}_aliases.csv` (`source,field,raw,geoid,notes,source_url`; `field` added to
    the #455 draft because mwvcog maps two source columns with different lists) and `geo.aliases(state,
    source, field)`.
  - Moved: Mecklenburg tax jurisdictions (CSV, 7), Cary (dict, 2), Wilmington districts (dict, 2), mwvcog
    cities and offices (dicts, 10), TCAD entities (CSV, 1). Deleted `nc_meck_tax_jurisdictions.csv` and
    `tx_tcad_entities.csv`. Name matching against the jurisdictions table (Met Council, RLIS) stays as is
    and Wake keeps its file (Ben, 2026-11-17: fixed lists only).
  - Kept `or_metro_cities.csv`: the audit called it unused, but `scripts/dev/or_state_reform_rows.py` reads
    it (Metro membership, not aliases).
- **Inputs:** the old dicts and CSVs (git).
- **Outputs:** the three aliases files, `src/lotline/geo.py`, five adapters, tests, guide step 8,
  `docs/data_provenance.md` (one path).
- **Findings:** every new lookup equals the old dict or CSV exactly (6 of 6). `docs/data_provenance.md` was
  already stale against the shared manifest before this change (not regenerated here).
- **Decisions:** none new.
- **AI:** Claude wrote the files, code and tests; checked as above.
- **Open / next:** regenerate `docs/data_provenance.md` from a clean manifest (separate).
