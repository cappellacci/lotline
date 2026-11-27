### LB-NNN · 2026-11-25 · Review · Data adapters and app build reviewed; four adapter bugs fixed (thread 17, part A)

- **Question:** Do the data adapters and the app build do what their docstrings and methods say?
- **Outputs:** `src/lotline/adapters/states/tx/austin_permits.py`, `tx/v0_austin.py` (A4),
  `or/portland_permits.py` (A22), `nc/raleigh_permits.py` (A23), `mn/mpls_permits.py` and
  `mn/stpaul_permits.py` (A24); tests in `tests/states/{tx,or,nc,mn}/`; review log rows A4 and A22–A30 in
  `reports/review/2026-11-code-review.md`.
- **Decision:** Ben, 2026-11-25: "Yes, fix them" (the bugs; tidy-ups A26–A30 stay proposed).
- **What Claude did and how it was checked:** Claude Code reviewed `src/lotline/app/` itself and had two
  read-only subagents review the adapters (national, checks, MN, NC; and OH, TX, OR, comparables). Every
  reported bug was re-read in the code before fixing; one (A25, Austin HOME demolition window) was checked
  against the pre-registered rule and found correct, so it was not changed. The Minneapolis and St. Paul date
  reading was checked against the cached raw data (issue times cluster 08:00–16:00 read as UTC). Before/after
  counts were built from the cached 2026-11-11 raw files with the network blocked: Portland 9 permits split
  (9 homes move from ADU to house, total unchanged); St. Paul one permit with no new homes moves year; Austin,
  Raleigh and Minneapolis unchanged. Adapter tests for the four states pass; full suite and compliance check
  run before the PR.
