### LB-NNN · 2026-11-10 · Data (OR): ADU coverage, Portland's flag undercount k, Salem and Medford
- **Question:** can North Carolina's ADU count steps (D-074) run for Oregon, so all five states are comparable
  before one joint refit? Where are Oregon's ADU-eligible lots, can Portland's ADU flag be checked against an
  independent list, and which places outside Portland have open permit records?
- **What I did:**
  - Coverage audit (`scripts/dev/or_adu_coverage.py`): eligible lots as `adu.places_from_store` takes them
    (origin 2026), made non-overlapping with `adu.non_overlapping` (which removes nothing in Oregon: every
    jurisdiction is in BPS).
  - A research subagent scouted 23 cities and 6 counties, DLCD/OHCS reporting and Portland ADU lists
    (metadata and count queries only). It found Metro's RLIS Housing inventory, which has ADU rows by tax
    lot and the data source of each row.
  - Wrote Portland's k detection rule into the report and committed and pushed it (ba8a8b7d) before any
    match was counted. Then wrote `src/lotline/adapters/checks/rlis_housing.py` (check-only source, listed
    in `registry.documented_only`), reusing NC's `k_undercount` and `chapman`, and
    `scripts/dev/or_portland_adu_k.py`.
  - Built two permit adapters: `mwvcog_permits` (Salem, Keizer, Turner, unincorporated Marion and Polk since
    1998; jurisdiction from the permit's city, since Marion County issues Keizer's permits) and
    `medford_permits` (TRAKiT since 2020; house + ADU permits split for D-041).
  - Synthetic tests for all three; sources added to `config/states/or.yaml`; three provenance rows (others
    left alone).
- **Inputs:** `processed/or/eligible_parcels`, `processed/or/permits` (Portland, Bend), RLIS Housing ADU rows,
  MWVCOG and Medford layers (downloaded 2026-11-10 through the IO layer), Census BPS for checks.
- **Outputs:** `reports/or/adu-coverage-and-undercount.md`, `reports/or/portland-adu-k.json` (aggregates only).
- **Findings:**
  - Portland and Bend hold 16.9% of Oregon's 1,164,771 eligible lots; with Salem and Medford, 22.5%.
  - **Portland k = 1.06 (90%: 1.05–1.07); 1.07 (1.06–1.08) as written** (|P∩R| 1,949, |a| 114, group (b)
    891). That agrees with Raleigh's 1.07. 922 flagged lots (20%) are not in the inventory at all.
  - 2021–23 flagged ADUs per 1,000 lots a year: Salem 0.87, Medford 1.75 (Portland 1.52, Bend 2.14).
  - Salem's MWVCOG houses match BPS within 2% in 11 of 14 years to 2023; 2024–25 are incomplete. Keizer and
    the Marion remainder are partial and stay out.
  - Medford hand check: first sample 28/30 flagged were new ADUs (2 were remodels of an existing ADU) and
    30/30 non-flagged were not ADUs. The rule was fixed; a second sample was 30/30.
  - No open state ADU table by year: DLCD's survey is dashboard-only; one OHCS layer has ADUs for 68 cities
    with no year field.
  - Blocked: Salem's own layer (terms bar copying), Eugene (bot check, "all rights reserved"). Jackson County
    needs a city assignment.
- **Decisions:** proposed for HANDOFF in the PR:
  - Portland's k (1.06, range 1.05–1.08) as Oregon's field-flag k.
  - Salem and Medford enter the ADU panel under D-074 step 2.
  - Three local rule rows (Salem's 2021 ADU code, Medford's ADU SDC reduction 2020 and 2022).
- **AI:** Claude Code wrote the code, tests and report; a research subagent scouted the sources, and each
  source used was re-queried by Claude before use. All hand-check rows were read by Claude; descriptions were
  read in memory and not kept. The k rule was committed before counting; the Medford rule change after the
  first hand-check sample is disclosed in the report.
- **Open / next:**
  - Confirm MWVCOG's terms before Salem's counts are published as final.
  - Salem's first ADU ordinance; Medford's SDC program after June 2023.
  - Ask OHCS for the survey periods of `OHNA_Cities_production_data_periods_1_2`.
  - Jackson County: place permits in cities (coordinates against city limits).
