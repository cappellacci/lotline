### LB-NNN · 2026-11-10 · Data feasibility: Minnesota ADU coverage, Minneapolis flag undercount k, outstate scouting (D-074 for MN)
- **Question:** How much of Minnesota's ADU-eligible land do the ADU-flagged permits reach? How much do
  Minneapolis's ADU-typed permits undercount the ADUs the assessor coded? Can any uncovered outstate city be
  added?
- **What I did:**
  - Coverage audit: eligible lots (theme `adu`, rule 1.1, newest roll ≤ 2024) summed over non-overlapping
    units with `adu.non_overlapping`; permits through `holdout.apply` (date and year columns, so Met Council's
    year-only St. Paul rows through 2023 count).
  - Wrote the Minneapolis detection rule and committed it before any count (9e4b5390). The rule: the assessor's
    ADU building-use codes on 2017 single-family parcels, 2017 → 2026 rolls; P = CCS ADU-typed permits issued
    2017-01-01 to 2025-06-30. Groups (a) and (b) follow D-074. Versions fixed beforehand: as written, duplexes
    removed (central), wide (a), strict R, and the 2017 → 2024 rolls.
  - Implemented it as pure functions (`mpls_roll_diff.py`, importing NC's `k_undercount` and `chapman`) with
    7 hand-worked tests on a synthetic fixture, plus a read-only runner.
  - A subagent scouted outstate permit sources (metadata, counts and robots.txt only). Moorhead's scope text
    was checked by count-only queries and its 7 hits were read.
- **Inputs:** `processed/mn/eligible_parcels`, `jurisdictions`, `parcels` (2017 Minneapolis land use) and
  `permits` (`mpls_permits`, `metc_permits`). The Minneapolis assessor tables 2017–2026 are cached raw pages,
  non-personal fields only, not re-downloaded.
- **Outputs:**
  - `reports/mn/adu-coverage-and-undercount.md`, `reports/mn/adu-coverage.json`,
    `reports/mn/mpls-roll-adu-diff.json` (aggregates only);
  - `src/lotline/adapters/states/mn/mpls_roll_diff.py`, `tests/states/mn/test_mpls_roll_diff.py`;
  - `scripts/dev/mn_adu_coverage.py`, `scripts/dev/mn_mpls_roll_adu_diff.py`.
  - No processed table was written and nothing was downloaded.
- **Findings:**
  - **Coverage:** 47% of 1,688,996 eligible lots are in a covered jurisdiction, all of them metro. Only 20% are in
    the 53 places that ever recorded an ADU permit. County remainders: 0%.
  - **Minneapolis k (central):** 1.04 (90% 1.02–1.10), from |P∩R| 94, |a| 4, |b| 21, |P\R| 81. As written:
    1.06 (1.03–1.12). Wide: 1.10. 79% of the ADUs on the roll carry an ADU-typed permit. Chapman total ÷ P:
    1.27 (1.20–1.33).
  - Met Council's field records 110 Minneapolis ADU units over 2017–2025, against 191 parser-typed parcels
    (about 58%). Its rows have no PIN, so it can't be parcel-matched.
  - The assessor's ADU label drops out on about 65 parcels in the 2022–2024 tables and comes back in 2025. This
    was found after the count. It affects only the 2024 sensitivity.
  - **Outstate:** none of the uncovered places has an open, record-level source that can mark ADUs.
    - Rochester has monthly spreadsheets with no stated license.
    - Duluth needs a login. St. Cloud and Sherburne are blocked by robots.txt.
    - Moorhead's text has no ADUs. Olmsted's layer has no description text.
    - No adapter was built and no rule rows were proposed.
- **Decisions:** none added to HANDOFF. Proposed in the PR:
  - Minneapolis k_parser = 1.04 (1.02–1.10).
  - A Met Council field sensitivity of about 1.8, or treat the suburbs as a floor.
  - Rochester's spreadsheets as a no-license public-records source, if Ben accepts that.
- **AI:** Claude Code wrote the rule, functions, tests, runners and report. Checks:
  - the hand-worked tests;
  - running the rule only after its commit;
  - every version's counts reported side by side;
  - a subagent's source scouting, spot-checked by direct count queries (Moorhead).
- **Open / next:**
  - A Rochester adapter if Ben accepts its terms.
  - Whether Met Council's suburban ADU reporting can be checked against any city's own permits (Bloomington,
    Minnetonka and Edina have open data portals; not scouted here, since they are already covered).

### LB-NNN · 2026-11-10 · Data: Rochester (MN) permit adapter; suburbs as a floor; shared undercount code
- **Question:** Ben's replies on PR #367: can Rochester's public permit spreadsheets be added? He decided the
  Met Council suburbs are a floor and approved moving the undercount functions to shared code.
- **What I did:**
  - Built `rochester_permits`:
    - folder-listing walk of the city's public Laserfiche archive;
    - one `lotline.io.http.fetch` per monthly .xlsx sheet (113 files, 2017-04 to 2026-10; the 139 .xls sheets
      before that are skipped, since no dependency reads them);
    - header labels matched by pattern, with personal columns (address, contractor, owner) unmatchable;
    - Census construction codes for type and units;
    - an ADU rule reusing `mpls_permits`' patterns. A new house built with an attached ADU, which Rochester
      files as two-family, becomes a house row plus an ADU row.
  - Ran `lotline fetch --state MN --source rochester_permits` (24,813 rows) and added the provenance row and the
    `config/states/mn.yaml` source entry.
  - Hand-checked every ADU text hit (13) and two draws of 30 non-matches.
  - Moved `wilson`, `chapman`, `flag_share`, `k_undercount` and `Z90` to `lotline.validation.undercount`, with
    `nc.wake_roll_diff` re-exporting them. The sibling OH/TX/OR branches import them through it, so they keep
    working.
- **Inputs:** `lf.rochestermn.gov` archive (public; robots.txt 404; no license stated; Ben accepted it
  2026-11-10); Census BPS for Rochester (sanity check only).
- **Outputs:** `src/lotline/adapters/states/mn/rochester_permits.py`, `tests/states/mn/test_rochester_permits.py`,
  `src/lotline/validation/undercount.py`, `tests/core/test_undercount.py`, `config/states/mn.yaml`,
  `docs/data_provenance.md` (Rochester rows only), report §3.3, §4.1, §5 and §6.
- **Findings:**
  - Rochester has 5 ADU permits since 2017, all after the 2023 UDC (3 in 2023, 2 in 2024, 0 in 2025): 0.04 per
    1,000 eligible lots a year.
  - Hand check: precision 5/5; no clear miss in either draw of 30; 5 ambiguous cases. All 4 trade permits that
    name a new ADU sit on a flagged parcel.
  - New SFD/TH permits track BPS single-family units within about 10% in most years.
  - Coverage of MN eligible lots rises from 47% to 50%.
- **Decisions:**
  - Met Council suburbs are a floor (Ben, 2026-11-10); proposed for HANDOFF in the PR.
  - Rochester accepted as a public-records source (Ben, 2026-11-10).
- **AI:** Claude Code wrote the adapter, tests, shared module and report. Checks:
  - synthetic-sheet tests (13 Rochester, 3 shared, 1,178 in the states and core suites);
  - the BPS comparison;
  - the hand check;
  - a scan of the sibling branches' imports before the move.
- **Open / next:**
  - `xlrd` (BSD-3) would add 2005–2017-03 for Rochester; ask Ben before adding it.
  - The parcel number is the city's own, so there is no roll match and no Rochester k.

### LB-NNN · 2026-11-10 · Data: Rochester's pre-2017 sheets (xlrd)
- **Question:** Ben approved adding `xlrd` (BSD-3-Clause), confirmed in this session. With it, can Rochester's
  139 `.xls` sheets (2005-09 to 2017-03) be read?
- **What I did:**
  - Ran `uv add xlrd` (2.0.2). The license scan (`compliance_check.py --deps`) passes. BSD needs no exception
    entry; `docs/disclosures.md` gained the `lf.rochestermn.gov` service row.
  - `rochester_permits` now downloads every sheet (252) through `lotline.io.http.fetch` and reads `.xls` with
    `xlrd`.
  - Two more header patterns ("WorkDescription", "Occupancy Type").
  - A `read_legacy` reader for the 2005-09 to 2007-10 extract from the old permit system (field names, read by
    position; address, subdivision, owner and contractor never read).
  - The report month stands in where a sheet's issue dates are blank (2014-11, 127 permits).
  - Fixed a date-parsing bug found on the rebuild: mixed date formats across sheets had coerced most dates to
    missing. Fixed with `format="mixed"` and a test.
  - Rebuilt with `lotline fetch` (51,040 rows) and updated report §4.1.
- **Findings:**
  - New SFD/TH permits track BPS 1-unit counts from 2006 on (within about 10% in most years).
  - The `.xls` years add no ADU (10 word hits, all hotels or trade work). Rochester stays at 5 ADU permits, all
    in 2023–2024.
- **AI:** Claude Code wrote the reader, tests (18 Rochester: synthetic legacy grid, `.xls` dispatch with a
  stubbed reader, blank-date fallback, mixed formats) and report changes.
  - Nothing in the project writes `.xls`, so the `.xls` test stubs `pandas.read_excel`. The real files were
    checked by reading all 252 and comparing against BPS.
