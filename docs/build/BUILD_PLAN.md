# Lotline: Build plan and Claude Code transition (v1, 2026-10-04)

**Purpose:** take Lotline from research to working code for four states (MN, NC, TX, OH), with each state's data ingested, prepared and validated, all managed through the Lotline GitHub repo.
**Audience:** Ben, and every Claude Code instance working on the repo. Each instance reads `CLAUDE.md` first, then this file, then its own brief in `docs/build/workstreams/`.
**Builds on:** `docs/research/`, especially:
- `lotline-validation-plan.md` (the V0–V7 ladder)
- `lotline-causal-diagram*.md` and `lotline-confounder-register.csv`
- `lotline-statistical-protocol.md`
- `lotline-mn-scouting.md` §5 (state roles)
- `lotline-state-reassessment.md`

---

## 0. Read this first: three timing rules

1. **The Rules have a gap.** Submission work must be "created during the Registration and/or Coding Periods" (Official Rules, rechecked 2026-10-04).

   | Period | Start | End |
   |---|---|---|
   | Registration | Sept 14, 9:00 a.m. ET | **Oct 7, 9:00 a.m. ET** |
   | Coding | **Oct 14, 9:01 a.m. ET** | Dec 16, 11:59 p.m. ET |

   The Rules say nothing about **Oct 7 9:00 a.m. → Oct 14 9:01 a.m.** Commit timestamps are our evidence. So:
   - **Phase 0 (repo bootstrap) must be committed and pushed before Oct 7, 9:00 a.m. ET.**
   - **No commits between Oct 7, 9:00 a.m. and Oct 14, 9:01 a.m.** unless the organizers confirm in writing that gap-week work counts. Ben emails them on landing (draft in §9).
   - Planning, reading, mentor conversations and data-access emails are fine during the gap. So is saving **public data** locally (public data is an explicit exception). Nothing gets committed.
2. **Rolling-window datasets lose history every week**: Minneapolis CCS permits, St. Paul permits, Bozeman-style city feeds. Take a manual CSV export **now** into a local folder outside the repo; scripted snapshots start in week 1.
3. **Blind tests need blinding from day one.** St. Paul 2023 (MN) and Charlotte 2023 (NC) are blind forward tests. Their post-reform outcome years must be in a holdout registry *before* any instance loads those datasets (§5.4).

---

## 1. Phases at a glance

| Phase | Dates (ET) | What | Who | Exit gate |
|---|---|---|---|---|
| **0 Bootstrap** | Oct 5 → **Oct 7, 9:00 a.m.** | GitHub repo, first commit, CI, Python env, skeleton, issues and milestones | Ben + 1 Claude Code instance (WS-00) | `compliance_check.py` shows 0 FAIL except items that need code (T3/T4 may WARN); repo public; security features on |
| **Gap** | Oct 7 → Oct 14 | No commits. Organizer clarification; data-access emails; manual exports of public data; mentor office hours; review briefs | Ben | Organizer answer logged; Met Council and Durham requests sent |
| **1 Core** | Wk 1: Oct 14–20 | Contracts (schemas), config, cache and manifest, HTTP/ArcGIS/Socrata helpers, national adapters (BPS, ACS, FHFA, FRED, PPI), holdout registry, CLI, test harness | 1 instance (WS-CORE) | `schemas v1` tagged; CI green; BPS ingest for all 4 states |
| **2 MN + NC + Engine** | Wk 2–4: Oct 21–Nov 10 | MN and NC ingestion → V0; model engine (baseline V1, funnel/pro forma/hazard) on MN data | 3 parallel instances | V0 reports for MN, NC; V1 baseline run on all 4 states (BPS-only) |
| **3 TX + OH + Evidence** | Wk 3–5: Oct 28–Nov 17 | TX and OH ingestion → V0; out-of-state comparables (Portland, Seattle, CA APR, LA) + estimators | 3 parallel instances (MN/NC instances move to validation) | V0 for TX, OH; comparables table v1 |
| **4 Validation** | Wk 4–7: Nov 4–Dec 1 | `prereg-v1` tag → V2–V6 per state; **freeze St. Paul and Charlotte predictions by Nov 17**; unblind week 7 | State instances + Engine | Scorecard per state; **official benchmark state chosen by Nov 10** |
| **5 Product** | Wk 6–9: Nov 18–Dec 16 | Scenarios incl. combined runs, statewide aggregation, Monte Carlo, Streamlit app, docs, deck, video | Engine + WS-APP + Ben | All deliverables D1–D9; compliance 0 FAIL; submit by Dec 16 |

**Concurrency cap: 3 Claude Code instances at once.** The bottleneck is Ben's review time, not compute. Every instance works through pull requests; Ben merges.

---

## 2. Workstreams (one Claude Code instance each)

| ID | Brief | Owns (write access) | Depends on | Active |
|---|---|---|---|---|
| WS-00 | `workstreams/WS-00-bootstrap.md` | repo root config, `.github/`, `pyproject.toml`, skeleton | — | Phase 0 |
| WS-CORE | `workstreams/WS-CORE.md` | `src/lotline/{schemas,config,io,cli}`, `src/lotline/adapters/national/`, `src/lotline/validation/holdout.py`, `tests/core/` | WS-00 | Wk 1 (then maintainer of contracts) |
| WS-MN | `workstreams/WS-MN.md` | `src/lotline/adapters/states/mn/`, `config/states/mn.yaml`, `config/reforms/mn.csv`, `tests/states/mn/`, `reports/mn/` | WS-CORE `schemas-v1` | Wk 2–7 |
| WS-NC | `workstreams/WS-NC.md` | same pattern for `nc` | `schemas-v1` | Wk 2–7 |
| WS-TX | `workstreams/WS-TX.md` | same pattern for `tx` | `schemas-v1` | Wk 3–7 |
| WS-OH | `workstreams/WS-OH.md` | same pattern for `oh` | `schemas-v1` | Wk 3–7 |
| WS-ENGINE | `workstreams/WS-ENGINE.md` | `src/lotline/{build,model}/`, `config/params/`, `tests/model/` | `schemas-v1`; MN data from wk 3 | Wk 2–9 |
| WS-EVIDENCE | `workstreams/WS-EVIDENCE.md` | `src/lotline/adapters/comparables/`, `src/lotline/evidence/`, `tests/evidence/` | `schemas-v1` | Wk 3–7 |
| WS-APP | `workstreams/WS-APP.md` | `src/lotline/app/`, `docs/*.md` deliverables | Engine outputs | Wk 6–9 |

**Ownership rule:** an instance edits only its own paths. If it needs a change to a shared contract (`schemas.py`, `config` loaders, CLI), it opens an issue labeled `contract-change` and WS-CORE (or Ben) makes the change. This is what makes parallel work safe.

---

## 3. Recommended stack (WS-00 sets it up; deviations need an ADR in `docs/adr/`)

| Need | Choice | License | Note |
|---|---|---|---|
| Python | 3.12 | — | `compliance_check.py` needs 3.11+ |
| Env + lock | **uv** (`uv.lock`) | MIT/Apache | Satisfies T9 (pins) |
| Tables | pandas 2.x, pyarrow, **duckdb** | BSD, Apache, MIT | Parquet everywhere |
| Spatial | geopandas, shapely, pyproj, pyogrio | BSD, BSD, MIT, MIT | Parcel–zoning joins |
| HTTP | httpx | BSD | Pulls in **certifi (MPL-2.0)**: disclose in `docs/disclosures.md` |
| Contracts | pandera | MIT | Schema validation on every adapter output |
| Config | pydantic + YAML (PyYAML) | MIT | Parameters carry `source` (E-ids) and `range` |
| Stats | statsmodels, scipy, linearmodels | BSD, BSD, NCSA | NB/Poisson with offset, panels |
| Staggered DiD / SC | `differences` (Callaway–Sant'Anna), `pysyncon` | **verify licenses** before adding | Fall back to own implementation if license unclear |
| Sensitivity | SALib | MIT (verify) | Sobol / Morris |
| App | Streamlit | Apache-2.0 | Phase 5 |
| Dev | pytest, ruff, pip-licenses | MIT | |

**CI gotcha for WS-00:** the existing workflow runs `pip-licenses` in the runner's system Python. With uv, packages live in `.venv`, so the license scan must run inside it (`uv run pip-licenses ...` or install via `uv pip install --system`). Adjust `compliance.yml` and `challenge.toml` together.

---

## 4. Repository layout (target)

```
lotline/
├── CLAUDE.md  HANDOFF.md  LOGBOOK.md  README.md  LICENSE  challenge.toml  compliance_check.py
├── pyproject.toml  uv.lock
├── config/
│   ├── states/{mn,nc,tx,oh}.yaml     # sources, tiers, cut-off dates, holdouts
│   ├── params/*.yaml                 # model parameters: value, range, source (E-ids), notes
│   └── reforms/{mn,nc,tx,oh,comparables}.csv   # coded reform vectors (rubric, protocol §5.4)
├── src/lotline/
│   ├── schemas.py                    # canonical tables (pandera), versioned
│   ├── config/  io/  cli.py
│   ├── adapters/national/            # bps, acs, fhfa, fred, ppi, census geographies
│   ├── adapters/states/{mn,nc,tx,oh}/  # parcels, permits, zoning, fees, reforms
│   ├── adapters/comparables/{portland,seattle,ca_apr,la}/
│   ├── build/                        # eligible parcels, jurisdiction-year panels, data tiers
│   ├── model/                        # baseline, funnel, proforma, hazard, scenarios/, combine, aggregate, uncertainty
│   ├── evidence/                     # did, synth, pooling, transport
│   ├── validation/                   # ladder V0..V7, holdout registry, freeze/unblind
│   └── app/                          # Streamlit (phase 5)
├── scripts/fetch_data.py             # single entry for automated acquisition (T10)
├── scripts/dev/                      # create_issues.py, merge_logbook.py
├── tests/{core,states/*,model,evidence}/   # small synthetic fixtures only, no real data
├── reports/{state}/                  # generated V0..V7 reports (markdown + small PNGs)
├── docs/  (analysis_plan.md, adr/, build/, research/, deliverable docs)
└── logbook.d/                        # one fragment per PR; merged into LOGBOOK.md
```

**Data never goes in the repo.** All downloads go to `LOTLINE_DATA_DIR` (default `~/lotline-data`), shared across worktrees:

```
~/lotline-data/
  raw/{source}/{vintage}/...          # exactly as downloaded, never edited
  interim/{state}/...                 # parsed, typed
  processed/{state}/{table}.parquet   # canonical tables
  manifest.jsonl                      # one line per download
```

Each manifest line records: url, access time, sha256, bytes, license text, adapter version. `docs/data_provenance.md` is **generated** from the manifest plus adapter metadata, never hand-edited.

---

## 5. Shared contracts (WS-CORE freezes `schemas-v1` in week 1)

### 5.1 Canonical tables
Every state adapter must emit these. Columns marked † may be null where a source lacks them; every null is counted in the V0 coverage report.

| Table | Grain | Key columns |
|---|---|---|
| `jurisdictions` | one row per permit-issuing place / county / township | `state, geoid, name, kind, county_geoid, bps_id, pop_2020, data_tier (1/2/3)` |
| `parcels` | parcel × vintage | `state, parcel_id, vintage, jurisdiction_geoid, lot_sqft, land_use_std, land_use_raw, units†, year_built†, land_value†, bldg_value†, last_sale_price†, last_sale_date†, homestead†, zoning_raw†, sf_only_zoned† (bool), source` |
| `permits` | permit (or permit-type × year where only aggregates exist) | `state, permit_id, parcel_id†, jurisdiction_geoid, issue_date, final_date†, building_type_std, units_new, units_removed, is_demolition, is_conversion, source, type_confidence (high/inferred/unknown)` |
| `bps_place_year` | place × year | `geoid, year, units_1, units_2, units_3_4, units_5p, bldgs_*, imputed (bool)` |
| `market_geo_year` | geography × year | `geo, year, hpi, median_value†, median_rent†, ppi_resid_inputs, mortgage_rate` |
| `reforms` | reform component | `state, jurisdiction_geoid, theme, component, effective_date, announced_date†, by_right, owner_occ, unit_cap, far_cap†, lot_split, parking, fee_change_usd†, coverage, source_url, coder` |
| `fees` | jurisdiction × year × fee type | `geoid, year, fee_type, basis, amount_per_unit_usd, source` |

`building_type_std` enum: `SFD, ADU, TH, U2, U3_4, U5_6, U7P, DTQ (2–4 combined), MF5 (5+ combined), OTHER, UNKNOWN`. The combined codes exist because sources like Met Council and BPS can't split further. Never guess a finer category; mark `type_confidence`.

### 5.2 Canonical outcome (protocol §5.1)
Net new units permitted per 1,000 eligible parcels per year, in event time. **Store numerator and denominator separately, always.**

### 5.3 Eligible-parcel rule
`build/eligible.py` implements one versioned rule, applied to every state and comparable:
1. existing single-family structure;
2. residential use;
3. zoned single-family-only where zoning is known;
4. lot-size floor as a parameter;
5. exclusions where data allow.

Each state supplies a `land_use_raw → land_use_std` crosswalk in config, and the tier records which inputs were available.

### 5.4 Holdouts and blinding (validation plan §2)
- `config/states/*.yaml` lists `holdouts:` entries, for example `{place: "St. Paul", outcome_years: [2024, 2025, 2026], reason: "V5 blind test"}`.
- Loaders filter holdout rows **by default**. Reading them requires `--unblind`, which only succeeds if `results/frozen/<test_id>.json` exists and its commit hash is on `main`.
- A test asserts the filter works. **Set up the MN and NC holdouts in WS-CORE week 1, before any state ingestion.**

### 5.5 Parameters
Every number lives in `config/params/*.yaml` with:
- `value`
- `low` and `high`
- `unit`
- `source` (E-ids or a dataset)
- `notes`

The code never hard-codes a parameter (CLAUDE.md design principle).

---

## 6. Per-state plan (details in each brief)

| | MN (primary) | NC | TX | OH |
|---|---|---|---|---|
| **Role** | Full ladder; staggered ADU design across ~180 metro cities; low-uptake test; **recommended benchmark state** | Full ladder; within-city contrasts; Charlotte blind test; *Carthage* fee shock | Austin HOME test; "no sale prices" path | Sparse evidence: transport-only run |
| **Outcome data** | Met Council permits 2009–24 (ADU/DTQ/MF5, PIN); Minneapolis CCS (units); BPS | Raleigh (ADU + MM flags; units from land-use code after 2023); Durham (units, CO); Mecklenburg (zonecode, no units); BPS | Austin permits 1970–2026 (ADU class R-102, units, completions, demolitions); San Antonio 2020+; BPS | Columbus (units, CC0); Cincinnati (units, CO); Cleveland (ODbL, runtime only); BPS |
| **Parcels** | Met Council regional (2021–25 open + current); Hennepin, Ramsey; MnGeo 59/87 counties | NC OneMap (current, county codes → crosswalk); Wake files | StratMap (unstandardized); TCAD exports 2022–26; HCAD | Ohio statewide (StateLUC + area); Franklin auditor archives since 2014 |
| **Prices** | Last sale (regional, county layers) | Wake sales; county files | **None** (appraisal values) | Franklin sales |
| **Zoning** | Minneapolis CC0; St. Paul; Met Council planned land use | Raleigh, Durham, Charlotte layers | Austin; Houston has none | Columbus CC0 |
| **Ladder** | V0–V7 | V0–V6 | V0, V1, V3/V4 (Austin), V7 | V0, V1, V7 |
| **Blind test** | St. Paul 2023 (holdout 2024–26) | Charlotte 2023 (holdout Jun 2023–2026) | (optional) San Antonio ADU 2023 | — |

---

## 7. How to run Claude Code instances

### 7.1 One-time setup (Ben, Phase 0)

**The repo lives on Ben's personal GitHub account `cappellacci`: `https://github.com/cappellacci/lotline`.**
Every command names the owner explicitly, so it can't land on another account or organization.

```bash
cd ~/Engineering/lotline

# 1. Make sure gh is acting as cappellacci (not a work account)
gh auth status                        # look for: "Logged in to github.com account cappellacci" and "Active account: true"
gh auth login                         # only if cappellacci isn't listed; choose GitHub.com, sign in as cappellacci
gh auth switch --user cappellacci     # only if another account is active

# 2. Repo-local commit identity, so commits are attributed to the personal account
git config user.name  "Ben Cappellacci"
git config user.email "<email verified on the cappellacci account, or its @users.noreply.github.com address>"

# 3. Create the public repo under cappellacci and push (Rules require public; free security tooling)
gh repo create cappellacci/lotline --public --source . --remote origin --push \
  --description "Lotline: transparent simulator of state housing reforms (Housing Data & Technology Innovation Challenge)"

# 4. Verify before doing anything else
git remote -v                         # must show github.com/cappellacci/lotline
gh repo view cappellacci/lotline --json owner,visibility -q '.owner.login + " " + .visibility'   # cappellacci PUBLIC
# WS-00 instance does the rest (see brief)
```

If the `--push` step fails because nothing is committed yet, WS-00 task 1 makes the first commit and pushes with `git push -u origin main`.

### 7.2 Parallel instances with git worktrees
```bash
# one worktree + branch per workstream
git worktree add ../lotline-ws-mn   -b ws/mn
git worktree add ../lotline-ws-nc   -b ws/nc
git worktree add ../lotline-ws-eng  -b ws/engine
export LOTLINE_DATA_DIR=~/lotline-data      # shared download cache (put in ~/.zshrc)
cd ../lotline-ws-mn && claude               # start Claude Code in that worktree
```

Kickoff prompt for each instance (paste, swapping the brief name):

> Read `CLAUDE.md`, `docs/build/BUILD_PLAN.md`, and `docs/build/workstreams/WS-MN.md`. Work only in the paths your brief says you own. Start with the first unchecked task in the brief. Open a draft PR early, push small commits, and keep the brief's checklist updated in the PR description. Before every commit run `python compliance_check.py` and the tests. Add a logbook fragment in `logbook.d/` for each PR. Stop and ask me before changing any shared contract, adding a dependency, or loading any holdout data.

Claude Code's built-in worktree mode works too. What matters is **one branch and one owned directory set per instance**.

### 7.3 Working rhythm
- **Small PRs** (≤ ~400 changed lines where possible), each linked to an issue (`Closes #NN`).
- **CI must pass:** tests + compliance + license scan. Ben reviews and merges, usually daily.
- **Rebase often.** When `schemas.py` changes, WS-CORE announces it in the PR and bumps the `schemas` version.
- **Logbook:** each PR adds `logbook.d/<date>-<branch>.md` using the LOGBOOK template. `scripts/dev/merge_logbook.py` folds fragments into `LOGBOOK.md` weekly, which avoids merge conflicts. Instances never edit `LOGBOOK.md` or `HANDOFF.md` directly; they propose decisions in the PR description and Ben records them.
- **Cowork stays the research and planning desk.** Research docs in `docs/research/` are canonical for Claude Code. When Cowork updates a research doc, it writes both the project copy and the repo copy.

---

## 8. Quality gates

| Gate | Checked by | When |
|---|---|---|
| Schema contract tests pass for every adapter | pytest (`tests/states/*/test_contract.py`) | every PR |
| No data files, no secrets, pinned deps, permissive licenses | `compliance_check.py` in CI | every PR |
| Every dataset has a manifest entry and a provenance row | `lotline provenance --check` | every PR that adds a source |
| V0 report exists and passes thresholds | `lotline validate --state X --step V0` | end of state ingestion |
| `docs/analysis_plan.md` committed and tagged `prereg-v1` | Ben | **before any V3 outcome model runs** |
| Frozen predictions committed before unblinding | holdout test + git hash | V4/V5 |
| Tests prove the method: each model equation has a unit test against a hand-worked example | pytest | Phase 2 onward |

---

## 9. Ben's landing checklist

**Before Oct 7, 9:00 a.m. ET (registration window):**
1. Copy the research docs that exist only in the Cowork project into `docs/research/` (Claude Code can't read the project):
   - `lotline-methods-review.md`
   - `lotline-evidence-register.csv`
   - `lotline-methods-extraction.csv`
   - `lotline-statistical-protocol.md`
   - `lotline-two-prong-design.md`
   - `lotline-data-availability.md`
   - `lotline-data-catalog.csv`
   - `lotline-data-summary.csv`
   - `podcast-upzoned-301-notes.md`

   Or ask Cowork to do it.
2. Create the repo on the **`cappellacci`** account: run the §7.1 commands (check `gh auth status` → `gh repo create cappellacci/lotline --public ...` → verify `git remote -v`).
3. Start one Claude Code instance on `WS-00-bootstrap.md`. Review and merge. Push by **Oct 6 evening** to leave margin.
4. Enable on GitHub (Settings → Code security): secret scanning, push protection, Dependabot alerts, CodeQL default setup. Add branch protection on `main` (PR + CI required).
5. Run `python scripts/dev/create_issues.py --apply` to create labels, milestones and the issue backlog.
6. Manual CSV exports of the **Minneapolis CCS permits** and **St. Paul building permits** layers into `~/lotline-data/manual/` (public data; not committed).

**During the gap (Oct 7–14), no commits:**

7. Email the organizers. Suggested text:

   > The Rules say Submission work must be created during the Registration and/or Coding Periods. Does work done between Oct 7 (9:00 a.m.) and Oct 14 (9:01 a.m.) count, or should teams pause commits in that window?

8. Email Met Council GIS for pre-2021 year-end regional parcel vintages, and confirm whether 2025 residential permits are posted.
9. Check Durham permit data freshness (last update Nov 2024?) and compile the *Carthage* affected-towns list (NC School of Government blog is the likely source).
10. Decide the open items in validation plan §8: thresholds, integrity rules, real-fee display.
11. Book a mentor slot to stress-test the ADU uptake curve and transport assumptions.

**Oct 14, 9:01 a.m.:** start WS-CORE. When `schemas-v1` is tagged (target Oct 17–18), start WS-MN, WS-NC and WS-ENGINE.

---

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Organizers say gap-week work doesn't count | Plan already avoids commits in the gap |
| Four states overrun nine weeks | MN and NC are full ladders. TX and OH are deliberately thin (V0, V1, statewide run). Drop TX V3/V4 first if behind. |
| Rolling-window data disappear | Manual export now; scripted snapshots week 1 |
| Parallel instances collide | Path ownership, contract-change issues, ≤3 concurrent, daily merges |
| Accidental unblinding | Holdout filter on by default; `--unblind` needs a frozen file on `main`; CI test |
| License trap in dependencies | License scan in CI; certifi disclosed; new deps need a brief note in the PR |
| Low uptake in MN makes all effects look like zero | Out-of-state comparables (WS-EVIDENCE) set the upper range; report low-uptake prediction as a strength |
| Public repo copied by others | Accept: required by the Rules; commit history proves authorship |
