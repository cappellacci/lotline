### LB-NNN · 2026-11-10 · Data (NC): accepted ADU rule rows into nc.csv
- **Question:** can the ADU rule rows Ben accepted from the Cary, Asheville, Wilmington, Winston-Salem, Charlotte
  and Chapel Hill scout reports go into `config/reforms/nc.csv` as written?
- **What I did:**
  - Transcribed the proposed rows from each report's proposed-rows section (four of them read from open PR
    branches with `git show`). No new research and no source re-reads.
  - Added 9 rows: `NC-3710740-adu-pre2019`, `NC-3702140-adu-1997`, `NC-3702140-adu-2026a`,
    `NC-3774440-adu-pre2021`, `NC-3774440-adu-2021`, `NC-3775000-adu-2017`, `NC-3711800-adu-2003`,
    `NC-3711800-adu-2023` and `NC-3711800-adu-2026`.
  - Changed 4 rows: `NC-3710740-adu-2025` (source URL, `owner_occ` False, `adus_per_lot` 1, size-cap notes);
    `NC-3702140-adu-2015` (notes only, kept as an in-window event); `NC-3775000-adu-2022` (date correction
    in the notes, `owner_occ` False, `supersedes` the 2017 row); `NC-3712000-adu-2023` (notes only).
  - Each touched row's `coding_notes` says "Accepted by Ben 2026-11-10, from <report path>".
- **Inputs:** `reports/nc/cary-adu-scout.md` §6 and `reports/nc/charlotte-adu-counts.md` §4 (on main);
  `reports/nc/asheville-adu-scout.md` §5, `reports/nc/wilmington-adu-scout.md` §5,
  `reports/nc/winston-salem-adu-scout.md` §3 plus the PR #359 body, and `reports/nc/chapel-hill-adu-scout.md` §4
  (on PR branches).
- **Outputs:** `config/reforms/nc.csv` (92 to 101 rows).
- **Findings:**
  - The schema requires `effective_date`. Two `[predates]` rows (Cary pre-2019 and Wilmington pre-2021) had
    none in their reports, so they use 2010-01-01, the "allowed before the window" placeholder from
    `lotline.model.rule_tags`. Both move to 1990 in the panels either way.
  - The tag matcher matches the literal `[predates]` anywhere in `coding_notes`. A note saying a row is
    "not [predates]" would tag it, so the Asheville 2015 note avoids the literal tag.
- **Decisions:** none new. The PR body lists the transcription choices for Ben to check.
- **AI:** Claude Code transcribed the rows with a one-off script (not committed). Checks: pandas load (101 rows,
  36 columns, unique `reform_id`), `rule_tags.flags` on every touched row, the reform/rules/NC tests and the
  full suite, and `compliance_check.py`. No engine, scenario, calibration or fit runs.
- **Open / next:**
  - Wilmington: set `NC-3774440-adu-2024`'s `supersedes` to the 2021 row once the 2021 LDC text is read
    (the report lists this as a check to make, so it was not applied).
  - Unincorporated Mecklenburg (37119) still needs the ETJ check before it gets a row.
