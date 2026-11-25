# Code review and cleanup, November 2026 (thread 17)

Branch `ws/code-review`, from `main` at f3961ec3 (#516). Review depth: `/code-review` at **high**, one area at a
time (Ben, 2026-11-24). Part B lists were drawn up first, so the review runs against a stable `main`.

Status key: **proposed** = waiting for Ben's yes; **done** = acted on, with the PR or issue linked.

## Part A: findings

| # | Area | File:line | What is wrong | How it fails | Severity | Fix or leave | Status |
|---|---|---|---|---|---|---|---|
| A1 | Engine: ADU | `config/params/hazard.yaml:40-80`, `src/lotline/model/scenarios/adu.py:1182` | D-060 (approved 2026-11-06) passed its pre-registered gates in #327, which never merged, so `main` kept the West Coast range (rent $1,573–2,034, value $519k–836k). The plan recorded no result, and no later entry replaced it. A first reading here said D-091's own counts would cancel most of the effect. **That was wrong:** the observed floor is not widened, so the widening passes through to added ADUs. | The ADU P50s were held down and the ranges were too wide: P50 rises 26–30% in MN, NC and TX and 101% in OH once ported; means move under 4%; P90 ÷ P10 halves. | important | Ben, 2026-11-24: "Port it, show before/after". Ported on today's fit set (rent $1,204–1,826, value $218k–590k); V9 stays pinned; before/after in D-060 | fixed on `ws/d060-port` |
| A2 | Docs | `docs/analysis_plan.md` (D-086 cited in D-087, D-088 and later) | D-086 is cited as a decision, but its entry existed only on #421 (conflicting). The four rule-history reports it rests on (#422–#425) were not on `main`. | A reader following D-088 back to D-086 found no entry. | important (transparency) | D-086 entry added with a dated outcome; the four reports added, each with a note that their config rows were not merged; no config change | fixed on `ws/code-review` |
| A3 | Docs | `docs/analysis_plan.md` D-079, D-082, D-087, D-092 follow-up | The plan cited `reports/adu-joint-refit-2026-11/` (#411), `reports/{mn,nc,tx,or}/mm-rule-checks-2026-11.md` (#395, #397, #398, #401) and `reports/adu-covariate-screen-final-rows/` (branch `ws/adu-screen-new-rows`, no PR), but those files were only on branches. | Broken references for a judge. | important (transparency) | Brought onto `ws/code-review` with their logbook fragments and #411's D-079 confirmation lines; the screen's two script flags too (defaults unchanged), so its README's commands run | fixed on `ws/code-review` |
| A4 | Adapters: TX | `src/lotline/adapters/states/tx/austin_permits.py` | Under pandas 3.1, `test_home_use_flag` and `test_dates_parcel_and_raw_class` error with "boolean value of NA is ambiguous" (CI on #236, 2026-10-27). | A pandas upgrade breaks the Austin adapter; the lock pins 3.0.6, so nothing fails today. | nit | Fix the NA handling during the adapters review, then take pandas 3.1 | proposed |
| A5 | Engine: ADU | `src/lotline/model/scenarios/adu.py` `rule_inputs`, `apply_priors` | A state outside `REFORM_STATES` had no priors rows, so its uncoded places all took one all-bands mean. | Wisconsin's cities and villages borrowed the same rule mix; size bands were skipped for any new state. | important | Borrow from every coded place by size band | fixed on `ws/adu-review-fixes` (WI ADU P50 591 → 527) |
| A6 | Engine: ADU | `adu.py` `type_probs` | One missing p_* sent every place back to its coarse `rule_class`. | One gap silently re-types a whole state. | important | Fall back row by row | fixed on `ws/adu-review-fixes` (no number moved) |
| A7 | Engine: ADU | `adu.py` `rule_priors`, `no_state_rule_priors` | Coded county remainders also fed the city size-band pools, though D-102 (b) gives them their own row. | Uncoded cities borrowed partly from county zoning. | important | Leave remainders out of the band pools | fixed on `ws/adu-review-fixes` (MN, NC, OH within 2%) |
| A8 | Engine: ADU | `adu.py` `coverage_map` | Review said amendments drop their predecessor's zone and lot limits. | Checked the rows: Cass County 2016a and Medford 2018a each widen coverage on purpose. | — | No change needed | closed |
| A9 | Engine: ADU | `adu.py` module docstring | Docstring left out D-099's ν; a stray line break. | Reader misses a factor. | nit | Added | fixed on `ws/adu-review-fixes` |
| A10 | Engine: ADU | `adu.py` 456, 508, 517, 571 | 0.5 used as the unknown-field share and the parcel-measurement threshold, in code rather than config (CLAUDE.md). | Not tunable or cited. | nit | Move to `config/params/adu.yaml` with a source | proposed |
| A11 | Engine: ADU | `adu.py` observed-rate draws, proxy scaling, `draw_rule_share` rounding | Edge cases: missing k-row terms give 0; proxy scaled differently from own rate; cumsum rounding can pick the last type. | None hit today's numbers. | nit | Leave; recheck if a state lacks the terms | proposed |
| A12 | Engine: MM | `src/lotline/model/scenarios/mm.py` `dose_pools` | Coded county remainders also fed the city band and "all" dose pools. | Uncoded cities drew doses partly from county zoning. | important | Leave remainders out (as A7) | fixed on `ws/mm-review-fixes` (NC within 1%) |
| A13 | Engine: MM | `mm.py` `simulate`, `run` | A new state with no coded MM rule gave every place dose 0. | Wisconsin was treated as banning 2–4 homes everywhere; the full Handbook effect was added. | important | Borrow the five states' coded doses by size band (`borrowed_pool`) | fixed on `ws/mm-review-fixes` (WI MM P50 2,757 → 1,327) |
| A14 | Engine: MM | `mm.py` `places_from_store` | Missing cost-index year silently used the latest year. | A backtest origin before the series priced with today's costs. | nit | `cost_index_at`: nearest earlier year; error if empty | fixed on `ws/mm-review-fixes` |
| A15 | Engine: MM | `mm.py` `log_sd` | low > high silently gave no range. | A config typo removes θ's uncertainty. | nit | Raise | fixed on `ws/mm-review-fixes` |
| A16 | Engine: MM | `mm.py` docstring | Said "median rent"; code fills median F(PCR). | Reader misled. | nit | Docstring corrected | fixed on `ws/mm-review-fixes` |

## Part B: cleanup lists (proposed 2026-11-24)

### B1. Open pull requests (23, counting #517)

"On main" was checked file by file against `origin/main`, by content, not by file name.

| PR | What | Content on main? | Proposal | Reason |
|---|---|---|---|---|
| #517 | Wisconsin as ingestion test; holds this handoff | no | **merge** (green) | Base for this thread; puts handoff 17 on `main` |
| #464 | `publish_app.py` refuses `--go` without the data summary | no | **rebase, merge** | Still applies: the publish step needs the summary from the previous release |
| #507 | App data tab shows only states with results | no | **rebase on #517, merge** | Still applies; Wisconsin now has a bundle, so it stays visible as the ingestion test |
| #411 | D-079 joint refit results (report) | no; plan cites it | **merge** | A3 |
| #395, #397, #398, #401 | MM rule checks, MN/OH, OR, TX, NC (docs) | no; plan cites them | **merge** | A3 |
| #439 | ADU count sources in TX, OR, OH (research) | no | **merge** | Docs only; a research record of sources tried |
| #421 | D-086 method entry (conflicting) | no; plan cites D-086 | **close**, carry the entry into the A2 PR | A2 |
| #422, #423, #424, #425 | D-086 first-coder rule histories + `config/reforms` rows | in-force rows mostly yes (later PRs); 41 history and prior-state rows no | **close**; reports go into the A2 PR, config rows stay out | D-086 stopped at the first coding (g = 0). Adding the rows would change model inputs, against the thread's no-number-change rule |
| #327 | D-060 run: fit-set calibration range (code + config) | no (D-060's method only) | **decision** | A1. Either way the branch is too stale to merge as is |
| #354 | D-072 two-step zone model (proposed) | no | **close** | Never accepted; replaced by D-079, D-088 and D-089 |
| #350 | Results page copy draft (draft PR) | no | **close** | Replaced by the home-screen and model-tab design; also delete the untracked `WS-RESULTS-SIMPLE.md` |
| #433 | ADU handoff "what we tried" (14 Nov) | no | **close** | Out of date since D-088 and D-089; the plan's D-entries tell the same story. Its file number 16 also clashes with `16-need-ami-part-b.md` |
| #213 | NC development run, 2026-10-22 | no | **close** | Development run whose numbers are long out of date; could mislead a judge |
| #219 | Dependabot: pillow 13.0.0 | **yes** (lock has 13.0.0) | **close** | Already on main (#273) |
| #267, #268, #269 | Dependabot: ruff 0.17.3, pytest 9.2.0, pandera 0.35.0 | no | **rebase, full suite once each, merge** | All MIT. CI was green on 2026-11-03 but is stale |
| #236 | Dependabot: pandas 3.1.0 | no | **close for now** | CI fails (A4). Reopen after the adapter fix. BSD-3 |

**Outcome (2026-11-24, Ben: "Close the PRs then republish the app", then "close out the other 6 PRs").**
No pull requests are open.
- **Merged:** #517, #518 (carries #411, #395, #397, #398, #401, #421–#425), #519 (D-060, carries #327), #507
  (test conflict resolved: both tests kept), #464, #439, #268 (pytest 9.2.0), #269 (pandera **0.36.0**: it
  rebased onto a newer release, still MIT) and #267 (ruff **0.17.6**, MIT). Each was green on CI before merging.
- **Closed with a reason:** #327, #354, #350, #433, #213, #219, #236 (#425 also closed as carried). #411,
  #395, #397, #398, #401 and #421–#424 were already closed when this list was acted on.
- **App republished:** release `app-2026-11-24e`, from `main` 058069a9. It has six bundles (five core
  states plus Wisconsin as the ingestion test) built at 97e2436b with the D-060 range. The live data was
  checked: MN ADU additional permits P10 325, P50 601, overlap "high".

### B2. Open issues (46)

**Keep (13):**

| Issue | Why |
|---|---|
| #40 Choose official benchmark state | **Still open in HANDOFF** ("Choice still open; MN recommended"). The submission needs it. |
| #56 Model & Assumptions Overview; Policy Scenario Comparison | Docs exist; the docs push finishes them |
| #57 Slides PDF, demo video, SBOM, final compliance | Submission work |
| #54 Scenario modules … Monte Carlo + Sobol | Everything is built except Sobol (no Sobol in `src/`). Retitle to "which assumptions matter most (sensitivity ranking)" or close; Ben's call |
| #247 Texas fees per-place range | Left open on purpose when Texas closed |
| #506 Bundle field: built after the test | Not built |
| #406 Optional `site_key` on Permits | Not built; keep labeled `later`, or close if the D-082 building collapse is dropped |
| #448 Bundle sensitivity table for MM fast ramp (D-100) | The engine runs it (`mm.py` `ramp="fast"`), but no bundle table yet |
| #186 Schemas 1.8: demand index columns | No `demand_index` column on main; check whether #187 shipped it under another name, then close or keep |
| #138 PROVENANCE `reid_risk` key | Not built; #139 made the D7 table. Close as won't-do, or keep |
| #351 Two-worlds outcomes in results_totals | Schemas 1.15 has `base` and `added` for ADUs; likely done for ADU only. Check MM, then close |
| #11, #9 | → close (see below) |

**Close as done (with PR link):**
#94 (Durham annexation, #206) · #455 (geography, aliases, place_inputs: #463, #465, #467, #468, #478) ·
#472 (evidence columns `source_quote`/`verified_by`, #470) · #404 (shared permit theme classifier,
`build/permit_theme.py`) · #258 (`registry.documented_only`) · #333 (window from the bundle, #338) ·
#22 (#118) · #23 (#144–#146) · #24 (#152) · #25 (#149) · #26 (#121, #140) · #28, #34, #36 (V0 reports on main) ·
#33, #35 (TX and OH adapters on main) · #43, #50 (St. Paul frozen and released, #442) · #51 (Charlotte, #355) ·
#48 (leave-one-place-out, #274) · #10 (gap week settled)

**Close as superseded:**
#55 Streamlit app (static page instead, #334) · #32 hazard + V2 harness · #37, #38 comparables (D-037: outside
studies only check) · #39 estimators (D-024 gave no credible estimate; D-037 route) · #41 `prereg-v1` tag (no tag;
the dated D-entries are the pre-registration) · #42, #44, #47 V3 studies · #46 V6a Carthage DiD (V6b done, #513) ·
#52, #53 V7 · #11 data requests and #9 manual exports (no records requests, per Ben)

### B3. Local clutter (Ben's disk, not the repo)

- **Disk:** 34 GB free (2026-11-24); above the 15 GB floor.
- **`.measure/` in `adu-types-checked`:** 161 MB of scratch. Delete after #517 merges (it is that PR's worktree).
- **`~/lotline-data-backup/`:** every copy is from 2026-11-19 to 2026-11-24, so nothing is older than a week.
  Nothing to delete under the brief's rule; `d107` is the largest (134 MB).
- **Worktrees (40):** use the app's cleanup for merged or closed ones. Five have uncommitted work and need a look
  first:
  - `scale-bench` (#512, merged): **28 staged changes** to params, plan and schemas. Possibly live work; ask
    before removing.
  - `mm-run1` (#410, closed): untracked `reports/mm-d082/`.
  - `scale-488` (#488, closed): edited `docs/analysis_plan.md`.
  - `lotline-mn13`: `.venv` only.
  - `mm-before`: `results.log` only.
- **Main checkout** (`~/Engineering/lotline`, at e35fb193, 140 commits behind `origin/main`):
  - `LOGBOOK.md` has **~1,120 uncommitted lines** (nightly scan at 2026-11-24T13:51Z). Leave it to the nightly
    review's own PR.
  - Untracked files that are **already on main, in a newer version**: `handoffs/16-need-ami-part-b.md`,
    `WS-NEED-AMI.md`, `lotline-ami-method.md`, the Tomasso office-hours notes,
    `logbook.d/…-office-hours-amy.md`. These local copies can be deleted.
  - Untracked files **not on main**: `WS-NC-GUTCHECK.md`, `WS-RESULTS-SIMPLE.md`, the Greg Miller office-hours
    notes, `logbook.d/2026-11-09-cowork-office-hours-greg.md`, `logbook.d/2026-11-17-cowork-judging-panel.md`.
    Proposal: commit the notes and the two fragments through a PR, and delete the two workstream briefs (both
    workstreams are finished).
  - `Claude outputs/` (three logo option PNGs), `.handoff/fees-coverage`, `.worktrees/` (`adu-drift-mean`, an
    old PR body), `.claude/launch.json`: local only. Proposal: keep `launch.json`, delete the rest.

### B4. HANDOFF status table

To be drafted as a PR description once B1–B3 are settled (thread 6 folds it).
