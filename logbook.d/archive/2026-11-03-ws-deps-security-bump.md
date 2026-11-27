### LB-NNN · 2026-11-03 · [core] · Clearing the Dependabot alerts on `main`
- **Question:** GitHub reported 42 open Dependabot alerts on `main` (6 critical). Dependabot is one of the Rules
  §7 gates, so they need clearing before judging.
- **What I did:** listed the open alerts through the GitHub API; all 42 come from two packages in `uv.lock`:
  Pillow 12.3.0 (41 alerts; matplotlib's image dependency; fixed in 13.0.0) and certifi 2026.7.22 (1 critical;
  fixed in 2026.10.18). Ran `uv lock --upgrade-package pillow --upgrade-package certifi`, which gives Pillow 13.0.0
  and certifi 2026.10.23. Nothing else changed; no new dependency; licenses unchanged (certifi's MPL-2.0 is
  already in `docs/disclosures.md`).
- **Outputs:** `uv.lock`.
- **AI:** Claude Code (Opus 5.5). Checked with a clean `uv sync` and the full suite on `main` plus the bump
  (1,303 passed), and `compliance_check.py` (0 FAIL). The alerts should close when GitHub rescans `main`
  after the merge.
