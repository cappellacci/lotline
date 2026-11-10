### LB-NNN · 2026-11-10 · Data (OH): ADU coverage, the flag undercount and Cleveland
- **Question:** can Ohio run NC's D-074 ADU steps (coverage, the flag undercount k from two rolls, more
  places), so all five states are comparable before one joint refit?
- **What I did:**
  - **Coverage audit:** `scripts/dev/oh_adu_coverage.py` (non-overlapping eligible lots, as the ADU scenario
    sums them).
  - **Roll rule:** looked at the 12 Columbus flagged permits from 2017 to mid-2019 on the Franklin Auditor's
    Dec 2016 and Dec 2019 `Dwelling.xlsx` and `Improvement.xlsx`. Then wrote and committed the detection rule
    (c38920b) before any count.
  - **Roll counts:** `src/lotline/adapters/states/oh/franklin_roll_diff.py` (reuses NC's `wilson`, `chapman`
    and `k_undercount`) and `scripts/dev/oh_franklin_roll_adu_diff.py`. These count Dec 2019 → Dec 2024 and
    Columbus's D-074 quantities.
  - **Scouting:** a research subagent checked Toledo, Akron, Parma, Youngstown, Canton, Lorain, Hamilton,
    Springfield and their counties.
  - **Cleveland:** built `src/lotline/adapters/states/oh/cle_permits.py` (ODbL, fetched at run time, S7
    approved 2026-10-23) with 16 synthetic tests. Registered it in `config/states/oh.yaml` and added only its
    row and section to `docs/data_provenance.md`. Fetched 79,906 permits.
- **Inputs:**
  - Franklin Auditor appraisal files 2016-12-22, 2019-12-18 and 2024-12-30 (`raw/franklin_auditor/`, manifest
    `dev.oh_franklin_roll_adu_diff`);
  - `processed/oh/{eligible_parcels,jurisdictions,parcels,permits}`;
  - `raw/cle_permits/2026-11-10/`.
- **Outputs:**
  - `reports/oh/adu-coverage-and-undercount.md`;
  - `reports/oh/franklin-roll-adu-diff.json` (aggregates only);
  - `processed/oh/permits/cle_permits.parquet` (outside the repo).
- **Findings:**
  - **Coverage:** 15.4% of Ohio's 3.42 million eligible ADU lots sit in places with flagged permits (17.8%
    with Cleveland).
  - **The Franklin roll can't measure k.** The Auditor cards carriage houses as detached garages: 1 of 13
    Columbus flagged permits on single-family lots shows a second home, and 7 show only a new garage. So
    |P∩R| = 1 and k = 2.0 (90%: 1.14–8.27), which is not usable. Raleigh's 1.07 stays the only measured k.
  - Franklin roll gains are 70 of 287,374 single-family lots over 5.03 years (0.048 per 1,000 a year), mostly
    unit or use changes.
  - Columbus's Council variances (90 for 2020–24) against 23 flagged permits give about 3.9 approvals per
    flag. This is an upper-bound check on the parser.
  - **Cleveland is the only other open record-level permit source in Ohio.** It has 15 ADUs 2015–2025, 0.017
    per 1,000 lots a year under its 2010 "no ADU use" row, so it joins the ADU panel as an untreated city.
  - Hand check: 15/15 matches are ADUs, 0/30 random non-matches, and 0–1 of 30 near-misses.
  - Montgomery's CAMA second test was not run, because the county has only 7 flags in all.
- **Decisions:** none made. Proposed in the PR:
  - a k_parser of about 1.0–1.07 for Cleveland;
  - shared roll-diff helpers.
  No rule rows are proposed: Cleveland's existing row covers it, and the FBC/HID ADU question stays open.
- **AI:** Claude Code wrote the rule, code, tests and report; a subagent did the source scouting.
  - Every count was produced by the committed scripts.
  - The rule was committed before the count, and the learn-on cohort (2017–mid-2019) was kept apart from the
    test window (2020–mid-2024).
  - All 15 Cleveland matches and 60 non-matches were read by hand.
  - Cleveland's new houses were checked against Census BPS (1,115 against 1,231 over 2017–25).
- **Open / next:**
  - Ben confirmed the Cleveland ODbL run-time fetch on 2026-11-10 (`oh-readiness.md` updated).
  - Answer whether Cleveland's FBC districts allow ADUs.
  - WS-CORE: consider moving the roll-diff interval helpers to a shared module.
