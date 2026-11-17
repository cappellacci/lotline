### LB-NNN · 2026-11-17 · Missing middle: run 13 rerun after the Minneapolis permit fix (D-092)

- **Question:** with Minneapolis's repair permits no longer typed as new 2–4 unit buildings (#450, #451), does
  run 13's clustering finding change?
- **Decisions:** Ben: "rerun run 13's Minneapolis row" and "publish the run 13 results page" (2026-11-17).
- **Outputs:** `reports/mm-d092/run13-projects-mpls-fix/` (summary.json, coverage.csv, run-log.txt, README,
  results.html); `scripts/dev/mm_projects_page.py` takes `--dir` and shows a correction note; D-092 gained a
  dated "Run 13 corrected" bullet; `docs/model_and_assumptions.md` and the `mm_year_spread_phi` note in
  `config/params/mm_hazard.yaml` now say 39–44% (was 34–44%). Values in config unchanged. Page updated at
  https://claude.ai/artifact/BvoadqpTCF3itcSBYUYdgq.
- **Result:** Minneapolis 1,042 → 179 buildings by lot (inflation 1.13 → 1.03); every other source unchanged;
  pooled by lot 12.8 → 14.3 (34% → 39% in projects of 3+), by day 5.3 → 5.6 (42% → 44%). Verdict unchanged.
- **What Claude did and how it was checked:** reran the script from main after #451; compared every source
  with the original run (only Minneapolis differs); checked Minneapolis's 2017–2025 permit-file count against
  BPS (175 vs 165); checked the page in the browser before publishing.
