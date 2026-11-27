### LB-NNN · 2026-11-15 · Housekeeping: missing middle's method renumbered D-082 → D-092
- **Question:** two decisions had the same number. On `main`, D-082 is the ADU observed floor (merged 2026-11-12).
  The missing-middle method (#392) and the six PRs built on it (#403, #405, #407, #408, #410, #414, #415) also
  called themselves D-082. How do we fix this before they merge?
- **What I did:**
  - Claimed D-092, the first number free on every open branch (the highest in use was D-091). I told the ADU
    session so that it doesn't take D-092 too.
  - Ran one deterministic script on each missing-middle branch, so that stacked branches got identical edits and
    still merge cleanly. Force-push is denied, so each branch got a new commit; nothing was rebased.
    - It changed only files the branch had changed against `main`.
    - It renamed `D-082` → `D-092` and the paths `*_d082*` → `*_d092*` (`reports/mm-d092/`, `scripts/dev/*_d092.py`,
      `tests/model/test_calibrate_mm_d092.py`).
  - What the script left alone:
    - every line that `main` holds with ADU's D-082;
    - Ben's quoted approval "Approve D-082", kept verbatim;
    - hex runs in hashes.
  - Added "(was D-082)" to the entry heading in `docs/analysis_plan.md`, and replaced its "Number: provisional"
    note with the renumbering record.
- **Outputs:** one renumbering commit on each of `ws/mm-review`, `claude/permit-theme-classifier-24b07a`,
  `claude/mm-counts-code-c627c7`, `ws/mm-rule-rows`, `claude/mm-model-code-27dd2c`, `ws/mm-run1-coverage`,
  `ws/mm-run2-3` and `ws/mm-run5`; the PR titles and descriptions were updated to match.
- **Why it happened:** this session was opened for missing middle. It drifted into ADU work (D-083 to D-089) while
  a second session was also working on ADUs, and the two shared one D-number space. Since 2026-11-15, each model
  has one owning session: ADUs belong to "ADU statewide prediction methodology", missing middle to this session.
- **Not changed:** results pages already published as Artifacts still say D-082. No model was run and no numbers
  changed.
- **AI:** Claude (Opus 5.5) wrote the script and did the edits. Checked by:
  - a dry run on the top branch, read line by line;
  - a grep on every branch afterwards: only Ben's quotes still say D-082;
  - ruff and `compliance_check.py` (0 FAIL) on every branch;
  - the full test suite on every branch.
