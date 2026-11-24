# Thread 17: Thorough code review and repo cleanup (2026-11-24)

**Goal:** before the docs push and submission, (1) review the whole codebase for correctness, consistency with
the methodology docs and dead code, and fix what is real; (2) clear out stale PRs, issues, dependency bumps and
scratch files so the public repo reads cleanly to a judge. **No model result should change** unless the review finds
a real bug; any change to a number is raised with Ben first, with before/after.

**Read first:** `CLAUDE.md`, `docs/build/handoffs/README.md` (shared rules), `docs/analysis_plan.md` (dated
deviation entries D-0xx through D-105), `docs/schemas.md`, `.claude/judging/RUBRIC.md`.

**Ben's working rules for this thread:**
- **One heavy job at a time.** His machine froze repeatedly from parallel runs and a full disk. Before any full test
  run or `lotline results`, check `df -h /` (stop below 15 GB free) and `memory_pressure` (stop below 25% free).
  Don't run several subagents that each run the test suite.
- **Merging is Ben's call.** Ask "merge on green?" in chat; never merge or turn on auto-merge without his yes.
- **Raise every decision in chat in plain words, with a recommended pick.** Don't settle it silently in a PR comment.
- Holdouts, data, secrets and logbook rules as in `CLAUDE.md`. St. Paul is released (#442). Wisconsin V8 is frozen
  and scored as a fail; don't rescore it. Never open
  `~/lotline-data/manual/adu-rules-2026-11/MN/StPaul_StaffToCNPC_ADU_survey.pdf`.

## State at handoff

- `main` at the #516 merge (f3961ec3) plus the Wisconsin-label PR (branch `ws/wi-ingestion-label`, if merged).
- Live app: https://cappellacci.github.io/lotline/ (release `app-2026-11-24c`, five core states; Wisconsin joins
  as a "Data-ingestion test (not core)" once its PR is merged and republished).
- Publishing: `scripts/publish_app.py --results <dir> --data-summary <file> --go --tag <tag>` from a clean
  checkout of `origin/main`; the data summary comes from the previous release (`gh release download <tag>`).
- 845+ tests; `compliance_check.py` at 0 FAIL.

## Part A: code review

Review area by area, smallest risk of churn first. For each area: read it against the methodology text that governs
it, run its tests, and log findings in `reports/review/2026-11-code-review.md` (one row per finding: file:line, what
is wrong, how it fails, severity, fix or "leave"). Fix real bugs in small PRs, one area per PR. Ask Ben which review
depth he wants (`/code-review` at high, or deeper) before starting; it is his call, not a default.

| Area | Paths | What to check |
|---|---|---|
| Engine: ADU | `src/lotline/model/scenarios/adu.py` | D-025/D-037 equations vs code; D-102(b) remainder priors; coverage rule (#508); mean-1 drift (#509); dead branches left by refits |
| Engine: missing middle | `src/lotline/model/scenarios/mm.py` | dose pools, `remainder_pool_key`, shared inputs (#490) |
| Engine: fees | `src/lotline/model/scenarios/fees.py` | D-073/D-076/D-077; lot-feasibility vs elasticity route; `change_grid` |
| Baseline | `src/lotline/model/baseline.py` | Fay-Herriot shrinkage, `benchmark_levels` (V8 fix) |
| Results bundle | `src/lotline/model/results.py`, `aggregate.py`, `schemas.py` | rng order, `fee_types_with_stops`, schema history vs `docs/schemas.md` |
| App | `src/lotline/app/template.html`, `aggregate.js`, `build.py` | JS/Python parity (`tests/app/test_aggregate_parity.py`), dead UI code, labels in plain language, a11y |
| Adapters | `src/lotline/adapters/states/*` | each has a synthetic-row test; no hard-coded parameters |
| Rule agents | `src/lotline/rule_agents/*`, `.claude/agents/rules-*` | product feature (users switch it on per state); no internal session routing |
| Scripts | `scripts/`, `scripts/dev/` | which dev scripts are dead or superseded (e.g. `fee_knobs_export.py` after fees moved into the bundle) |
| Config | `config/params/*.yaml` | every value has a source; no unused parameters (`params_table.py --check`) |

Also check: parameters hard-coded in code that belong in `config/params/`; tests that pass without testing the
equation they name; TODO/FIXME comments; leftover fixtures.

## Part B: cleanup

1. **Open PRs (22 on 2026-11-24).** For each, say in one line: merge, close as superseded/obsolete, or keep, with
   the reason; get Ben's yes on the list, then act. The likely-stale ones are the research/coding PRs from
   2026-11-15 and earlier (#439, #433, #421–#425, #411, #401, #395–#398, #354, #350, #327, #213), whose content may
   already be on `main` through later PRs; check before proposing a close. #507 and #464 are small app/publish fixes;
   check whether they still apply.
2. **Dependabot (#219, #236, #267, #268, #269).** Rebase or recreate each; run the full suite once per bump, one at
   a time; check each license stays permissive. pandas 3.1 and pillow 13 are the riskier ones.
3. **Issues (46 open).** Close the ones done or superseded (link the PR); relabel the rest. List for Ben first.
4. **Scratch and local clutter** (not in the repo, but on Ben's disk): `.measure/` scratch in the
   `adu-types-checked` worktree; merged worktrees under `.claude/worktrees/` and `.worktrees/`
   (use the app's worktree cleanup, merged ones only); `~/lotline-data-backup/` copies older than a week (ask
   first). Untracked files in the main checkout (`.claude/launch.json`, `docs/build/handoffs/16-*.md`,
   `docs/build/workstreams/WS-NC-GUTCHECK.md`, `WS-NEED-AMI.md`, `WS-RESULTS-SIMPLE.md`,
   `docs/research/lotline-ami-method.md`, office-hours notes, three `logbook.d/` fragments, `Claude outputs/`,
   `.handoff/`): ask Ben which to commit through a PR and which to delete.
5. **HANDOFF status table:** draft the refresh as a PR description proposal; Ben folds it (only thread 6 edits
   `HANDOFF.md`).

## Done looks like

- `reports/review/2026-11-code-review.md` with every finding and its outcome.
- Small fix PRs, each green, each with a `logbook.d/` fragment, merged on Ben's yes.
- Open PRs and issues down to the ones Ben chose to keep; Dependabot bumps merged or closed with a reason.
- A short closing note to Ben: what changed, any number that moved (with before/after), and what was left.
