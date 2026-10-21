# Handoffs for parallel threads (2026-10-20)

Each file is a self-contained brief for one Claude Code session. Start a session in this repo and say:
"Read `docs/build/handoffs/<file>` and do it." Every thread follows the shared rules below.

## Shared rules (all threads)
- Read `CLAUDE.md` first. Work in **your own git worktree and branch** (`git worktree add ../lotline-<name> -b <branch> origin/main`); never in the main checkout.
- **gh account:** run gh commands as `GH_TOKEN=$(gh auth token --user cappellacci) gh ...`. Never run `gh auth switch`. Never merge; open PRs for Ben.
- **Holdouts are sacred:** never open or count St. Paul (2758000) outcomes from 2024 on, or Charlotte (3712000) / Mecklenburg (37119) outcomes from 2023-06-01. The holdout filter in the IO layer applies; never bypass it.
- **Downloads** go through the IO layer (`lotline fetch`, manifest). Check robots.txt first; never work around a block (403, bot challenge); mark it for Ben instead.
- **No new dependencies** without Ben's OK (state the license in the PR).
- **Every parameter** lives in `config/params/` with a source; every equation gets a hand-worked test; tests use synthetic fixtures, never downloaded data.
- **Before each commit:** `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`, `python compliance_check.py` (0 FAIL), `uv run python scripts/dev/params_table.py --check`.
- **One logbook fragment per PR** in `logbook.d/` (template in `logbook.d/README.md`). Don't edit `LOGBOOK.md` or `HANDOFF.md` (except thread 6).
- **Commits end with** `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; **PR bodies end with** `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- **Web research is expensive:** none of these threads needs broad web searching. Use public APIs and data already in the repo.
- **Plain language:** a non-technical policymaker is the primary reader.

## Threads
| File | Thread | Depends on |
|---|---|---|
| `01-missing-middle-panel.md` | Missing-middle panel and D-024 pre-registration | — |
| `02-fee-table-and-scenario.md` | Fee table from pipeline records; first fee scenario | — |
| `03-demand-index.md` | Local demand index (shift-share employment) | — |
| `04-d6-and-deck-outline.md` | Policy Scenario Comparison skeleton and deck outline | — |
| `05-app-plan-and-skeleton.md` | App plan rewrite and skeleton | Ben's OK for Streamlit |
| `06-logbook-and-handoff.md` | Fold logbook fragments; refresh HANDOFF | — |
| `07-adu-estimation-d025.md` | ADU estimation, D-025 (pooled hierarchical NB) | Running in the main session |
| `08-minnesota-data-complete.md` | Finish Minnesota's data for statewide end-to-end simulation | — |
| `10-north-carolina-data-complete.md` | North Carolina end-to-end data collection: assess, plan subtasks, work them | Plan approved by Ben before heavy work |
| `09-combine-and-aggregate.md` | Combine scenarios on the same lots; aggregate to county and state; demand cap | Best after D-025; works with stubs before |
