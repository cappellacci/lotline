### LB-NNN · 2026-11-10 · Data feasibility: Wilmington (New Hanover County) ADU permits
- **Question:** Can Lotline get record-level ADU permit counts for Wilmington, NC (3774440)? Wilmington has no
  BPS row of its own, and NC's ADU rate rests on permits covering only about 8% of the state's eligible lots.
- **What I did:**
  - Scouted the city, the county Hub, the county's ArcGIS server and the COAST portal. New Hanover County
    issues every building permit in Wilmington and publishes them, one row each, on
    `gis.nhcgov.com/…/Thematic/BuildingPermits/FeatureServer/0` (2014 on; no license stated, county as-is
    disclaimer, no reuse limit).
  - Built `wilmington_permits`. It downloads building-permit types only, drops sign-off holds, applications
    and the converted system's "Job master" duplicates, places permits by point in Census place polygons,
    joins PID → NC PIN through the county parcel layer, and reads ADUs from the work description (no ADU field
    and no unit field exist).
  - Hand-checked the ADU rule over five rounds of 30 matches + 30 non-matches. Rounds 1–4 built the rule;
    round 5 ran on unseen permits with the rule frozen.
  - Coded Wilmington's ADU rule history from the LDC, ordinances and WHQR, as proposed rows only.
- **Inputs:** NHC BuildingPermits layers 0 and 4; `eligible_parcels` (theme `adu`); `bps_place_year` (37129)
  for a sanity check; LDC Article 1; LDC-7-424; WHQR articles of 2021-06-17, 2021-07-07, 2021-08-18,
  2024-04-30 and 2024-05-09.
- **Outputs:** `src/lotline/adapters/states/nc/wilmington_permits.py`, `tests/states/nc/test_wilmington_permits.py`
  (23 tests, synthetic rows), `reports/nc/wilmington-adu-scout.md`, a `config/states/nc.yaml` source entry, and the
  `docs/data_provenance.md` row and section. Data: `processed/nc/permits/wilmington_permits.parquet`
  (48,930 permits) in `LOTLINE_DATA_DIR`, not in the repo.
- **Findings:**
  - Wilmington has **291 ADU permits from 2014 to 2026 (279 parcels)**. The rate rises from about 0.2 per 1,000
    eligible lots a year before 2022 to 1.5–2.2 from 2023, after the Dec 2021 LDC (parking minimum dropped)
    and the May 2024 amendment. Unincorporated New Hanover has 64.
  - Round-5 precision is 27/30 (90%), with an estimated 30 or so ADUs missed. The totals are close; the year
    pattern is a little noisier. The county's standard note "Not to be used as an accessory dwelling unit",
    used from 2025, would have added about 30 false ADUs without a veto.
  - Coverage of NC eligible lots by ADU-flagged permits goes from 8.1% to 8.9% with Wilmington, and to 9.9%
    with unincorporated New Hanover. 1-unit homes run at 0.75–1.23 of BPS for the county row.
- **Decisions:** proposed in the PR: (1) add `NC-3774440-adu-2021` (LDC effective 2021-12-01, parking and lot
  minimum removed) and a `[predates]` row for the old code to `config/reforms/nc.csv`; (2) the ADU rule for
  description-only sources asks for an ADU term plus vetoes, not the shared parser's full reading (the parser
  returns no type for "SFR … ADU").
- **AI:** Claude (Opus) scouted the sources, wrote the adapter, the tests and the report, and did the hand check
  by reading sampled descriptions. Checks: tests on synthetic rows; five rounds of hand checks, the last on
  unseen permits with the rule frozen; a BPS comparison; `compliance_check.py` 0 FAIL. A web-fetch subagent
  read the WHQR articles for the rule history.
- **Open / next:** enter the proposed rule rows after second coding (read the 2021 LDC ADU section); a
  Wilmington S.L. 2026-59 row is missing; optional recall fixes listed in the report §4; a panel caller that
  reads `wilmington_permits` (engine thread).
