### LB-NNN · 2026-11-17 · Deliverables: publishing the app can no longer drop the data dashboard
- **Question:** Why did the published app lose its embedded data dashboard, and how do we stop it happening again?
- **What I did:** Found that releases `app-2026-11-17` and `app-2026-11-17b` were published without `data-summary.json`, because `scripts/publish_app.py` ran from a worktree with no `reports/data_dashboard/summary.json`. It skipped the file silently, so the page built a data tab with sources only. `publish_app.py --go` now refuses to publish without the summary. A check-only run warns. `--no-data-summary` publishes without it on purpose. Ben republished with the summary as `app-2026-11-17c`.
- **Inputs:** release assets of `app-2026-11-09b`, `-17`, `-17b`, `-17c`; the live page.
- **Outputs:** `scripts/publish_app.py`; two tests in `tests/app/test_build.py`.
- **AI:** Claude Code traced the cause from the release assets and the served page, and wrote the change and tests. Checked with `tests/app/test_build.py` (47 app tests passed), ruff and `compliance_check.py`. The full suite is left to CI.
- **Open / next:** none.
