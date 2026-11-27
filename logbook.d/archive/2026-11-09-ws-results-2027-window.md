### LB-NNN · 2026-11-09 · Engine: first results run on the 2027–2031 window
- **Question:** What do the five states' ADU and missing-middle results look like after D-061 (window), D-064
  (rules date) and the housing-need change, and what did each change do?
- **What I did:** Ben said "Yes, rerun". After #339 merged, I ran `lotline results --all` at commit 5b86238
  (5 bundles and the app page, gitignored). I also made two comparison runs with the same code: A, the old
  setup, using config overrides in a scratch copy; and B, the new window with end-2025 rules, with the rules
  date patched. Then I diagnosed the place-level drivers and wrote the results page.
- **Findings:**
  - The window only relabels: A and B agree to the home.
  - D-064 lowers NC ADUs by 37% and missing middle in MN and NC by 11% and 6%. OH, OR and TX missing middle
    do not move.
  - 70–88% of each change comes from places that borrow their rules (D-022 priors and the dose pool).
  - The pre-registered "small" ADU effect was wrong for NC, because coverage moves from 0.75 to 1.0 in the
    S.L. 2026-59 cities.
  - One decision is open for Ben: which rule mix borrowers should see.
- **Outputs:** `reports/results-2026-11-09/results-2027-window.html` (published at
  https://claude.ai/artifact/WF92C89mxGCqRajaa8CXNs), `summary.csv` and `data.json` in the same folder; the
  results bullet in D-064 (`docs/analysis_plan.md`).
- **How Claude helped and how it was checked:** Claude (Claude Code) ran the bundles, wrote the comparison and
  diagnosis scripts (scratch, not committed) and the page.
  - Every A/B/C number on the page comes from the bundles.
  - The own/borrowed split comes from `places_from_store` at both dates, at central values. It is an
    approximation of the draw-based change.
  - The page's estimate for the recommended option is derived from that split, not run.
  - The page was checked once in the browser before publishing. No code changed.
- **Follow-up, D-067 (2026-11-09):** Ben chose the end-2025 mix for places that borrow their rules. Claude
  wrote and pushed D-067 before any code (bf563eb). The code change followed (96a5de2): `adu.rule_inputs`
  gained `prior_as_of`, and missing middle gained `pool_dose`, each with a hand-worked test. Then Claude
  reran the official bundles (run D) and republished the page as version 2, with a "Decided" panel and
  Finding 6.
  - NC ADUs 105, TX 1,356, MN missing middle 460, NC missing middle 773.
  - The estimates were close, except NC, where they ran 7–12 homes high.
  - The scenario tests (61), ruff and `compliance_check.py` (0 FAIL) pass.
