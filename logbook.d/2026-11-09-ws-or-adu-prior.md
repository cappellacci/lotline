### LB-NNN · 2026-11-09 · `engine` · Oregon's exempt small towns (D-068), run E with the baseline, and actual permits
- **Question:** why does Oregon's ADU scenario add exactly 0, and what does it add when the places its state
  law leaves out stop borrowing the rule of the cities it covers? Alongside the forecasts, how many ADUs and
  2–4 unit homes were actually permitted in 2021–2025 (Ben)?
- **Decided by:** Ben, 2026-11-09: "No-state-rule prior" (D-068), and the sequencing after PRs #341 and #342.
- **Outputs:**
  - D-068 in `docs/analysis_plan.md`, pushed before any code (f4ea9fa), then its results;
  - `StateConfig.adu_state_law_rows_complete` (additive state-config change) and Oregon's flag;
  - `adu.no_state_rule_priors` and its use in `rule_inputs`, with hand-worked tests;
  - `scripts/dev/observed_permits.py` (ADUs where permit data flag them; 2–4 unit homes from BPS) and
    `scripts/dev/results_run_summary.py`;
  - `reports/results-2026-11-09/run-e.json` and `observed.json`;
  - Finding 7 on `reports/results-2026-11-09/results-2027-window.html`, republished as version 3 at
    https://claude.ai/artifact/WF92C89mxGCqRajaa8CXNs.
- **Findings:**
  - Oregon ADUs 0 → 5 (2–12); the other states are unchanged from run D.
  - Each reform's median is under 1% of the state's baseline.
  - Permitted 2021–2025: ADUs MN 215, NC 620, OH 115, OR 1,388 and TX 1,317, counted only where permit data
    mark ADUs (21–64% of each state's people). Homes in 2–4 unit buildings: MN 2,738, NC 4,486, OH 7,317,
    OR 3,283, TX 37,095. The missing-middle medians add 2–17% to those.
  - Austin's ADU permits fall from 243 (2023) to 9 (2025) while its file runs to October 2026, probably
    because HOME-era ADUs are filed as 2–3 unit permits. Flagged on the page as an undercount.
- **What Claude did and how it was checked:**
  - Found the 50 uncoded places and their prior, wrote D-068 first, then the code and hand-worked tests, and
    ran the full suite and ruff.
  - Rebuilt the five bundles and checked that MN, NC, OH and TX reproduce run D exactly.
  - Traced the Texas ADU drop by source and year. Built the page table from the JSON and read it in the
    in-app browser.
  - Earlier the same day, a duplicate five-state run on PR #342 was reverted (2ab6021), because #341 held the
    official run.
