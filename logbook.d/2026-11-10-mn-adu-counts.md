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
