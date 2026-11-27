# Lotline: Logbook

A running record of **how** the Lotline entry was built: what question each step asked, what was done, what it produced and what it changed. `HANDOFF.md` says where things stand; this file says how we got there, so the process can be replayed or explained (and it backs the Transparency criterion, Rules §8, 30%).

**Conventions**
- Newest entry at the bottom. Entries are never rewritten; corrections go in a new entry that points back (e.g. "corrects LB-006").
- Every entry names its outputs by path or link so someone else can open exactly what was produced.
- "AI" lines record where Claude did the work and how it was checked, for `docs/disclosures.md`.
- Entries LB-001 to LB-009 were **reconstructed on 2026-09-30** from the docs and artifacts they produced; later entries are written as the work happens.
- Entries are added two ways: by the Claude session doing the work (rule in `CLAUDE.md`), and by a nightly review that scans the repo, project docs and artifacts for anything new since the last scan. Nightly entries are marked *(auto-review)*.

**Last scan:** 2026-11-27T08:38Z

---

## The story so far

| Phase | Dates | Question | Main output | Entries |
|---|---|---|---|---|
| 0. Rules intake | Sep 29 | What exactly must we deliver, and what disqualifies us? | `HANDOFF.md` checklist, `compliance_check.py` | LB-001 |
| 1. Scope | Sep 29 | Which reforms, judged by what? | Scenario set: Missing Middle + ADUs + Fees | LB-002, LB-011 |
| 2. Data feasibility across states | Sep 29–30 | Where can these reforms actually be measured? | Housing Data Readiness Ranking (50 states + DC) | LB-003 |
| 3. Policy analysis | Sep 29–30 | Which laws exist, where and since when? | Policy inventory, 199 laws/ordinances | LB-004 |
| 4. Study design | Sep 30 | How do real reforms inform a statewide forecast? | "Calibrate where reforms are old, apply where they aren't" | LB-005 |
| 5. Methods literature review | Sep 30 | How do researchers estimate these effects? | Methods review + 104-study evidence register | LB-006 |
| 6. Theme designs | Sep 30 | ADUs first: which natural experiments? Overall architecture? | ADU study design; two-prong design proposal | LB-007, LB-008 |
| 7. Build setup | Sep 30 | Where does the code live? | `~/Engineering/lotline` repo scaffold | LB-009 |
| 8. Statistical protocol | Sep 30 | How do we define "similar", standardize units and estimate? | Statistical protocol v0.1 + methods extraction (46 papers) | LB-012 |
| 9. Data availability check | Sep 30 | Does the data the methods need actually exist, state by state? | Data availability assessment v1 + 194-dataset catalog | LB-013 |
| 10. Causal design and validation | Oct 3–4 | What could fake or hide a policy effect, and how do we prove the model before using it? | Causal diagrams (general/ADU, MM, fees), 54-factor confounder register, in-state validation plan | LB-015, LB-016 |
| 11. Build transition | Oct 4 | How do we move to code across four states, in parallel, through GitHub? | Build plan, 9 Claude Code workstream briefs, 53-issue backlog | LB-020 |
| 12. Repo bootstrap | Oct 6 | Is the repo public, reproducible and CI-checked before registration closes? | github.com/cappellacci/lotline: uv project, CI, protected `main`, research docs, issue backlog | LB-021, LB-023, LB-024 |
| 13. Core data and contracts | Oct 6–8 | Can national data for four states flow through shared, tested contracts, with blind tests protected? | BPS, FHFA, ACS, FRED and 2020 Census adapters; holdout filter; generated provenance and data dictionary; V0 reports; tag `schemas-v1`; ArcGIS pager for state adapters | LB-027 – LB-037 |
| 14. Coding Period opens | Oct 14 | Is the repo aligned with the official rules, template and judging rubric, and does every state have a sound denominator? | Rules-PDF review; starter-template alignment; `/judge` panel; eligible-parcel rule with rest-of-county denominators; first MN/NC/engine workstreams; CBSA crosswalk; measured completion factors; permit-text parser | LB-041 – LB-056 |
| 15. City permits and the V1 baseline | Oct 14–15 | Do city permit records line up with Census counts, and does a simple baseline beat naive forecasts out of sample? | Minneapolis, Durham and Raleigh permit adapters; V1 baseline (spec B) and backtest harness; spec C tried and not adopted (D-007) | LB-057 – LB-063 |
| 16. Texas and Ohio start; shared tooling | Oct 15–19 | Can the pipeline take Texas and Ohio sources, and parcels without leaking holdouts? | TX and OH reform CSVs (second-coded sample), Columbus, Cincinnati and Austin permits, Travis CAD 2026 roll, Ohio statewide parcels; Socrata pager, parcel holdout rule, manual-download registry, pager geometry modes, place/township assignment, repeated project totals counted once (D-008); one copy of every doc (the repo) | LB-064 – LB-082 |
| 17. Effect estimation and parallel threads | Oct 20 | Can each reform's effect be estimated from real adoptions, pre-registered before any run, and what is needed to combine them statewide? | ADU estimators (D-019 fits, D-023, D-025, D-026), missing-middle panel and estimator (D-024), city fee table and fee scenario, demand index, handoff briefs 01–09 | LB-087, LB-088; most of the day's work is in `logbook.d/` fragments awaiting the fold |
| 18. North Carolina end to end | Oct 21 | What does North Carolina still need for every engine to run end to end, and can it be gathered without broad web research? | Handoff 10; NC data plan; OneMap parcels beyond 10 counties, Greensboro and Mecklenburg permits, Durham annexation rule, NC rule and fee rows, Charlotte V5 inputs | LB-089; the thread's work is in `logbook.d/` fragments on the `ws/nc-*` branches awaiting the fold |
| 19. Ohio and Texas end to end | Oct 23 | Can Ohio and Texas get the same end-to-end data as North Carolina, above all adding places to the multi-state ADU and missing-middle estimation panels? | Handoffs 11 and 12; OH and TX data plans (approved by Ben); Fort Worth, San Antonio, Dallas and Franklin County permit adapters; TX rule rows for places 21–40 | LB-090; the threads' work is in `logbook.d/` fragments on the `ws/oh-*` and `ws/tx-*` branches awaiting the fold |
| 20. Data threads close | Nov 1 | Are the Texas, Ohio and North Carolina data complete and handed off for the engine week, with reform dates that are real events? | TX and OH handoffs, OH and NC readiness reports, NC second-coder review, `[predates]` rule, D-035 interpolation between rolls, handoff 13 (NC and MN wrap-up), MN data plan approved | LB-095 – LB-097; most of the day's work is in `logbook.d/` fragments awaiting the fold |
| 21. Engine week begins | Nov 2 | Do the four states' data support the D-024 and D-025 estimators, and does the pooled ADU model fit on all four? | Minnesota and North Carolina data threads merged; handoff 14; four-state panel counts; D-025 four-state run (did not converge) | LB-098, LB-099; the threads' work is in `logbook.d/` fragments awaiting the fold |
| 22. Calibration on our own four states | Nov 3 | Once the in-state estimators give no credible four-state estimate, can scenario effects come from uptake rates calibrated on the four states and checked by backtests? | D-024 four-state run (no credible estimate); D-037 mechanism route (Ben); D-038 missing-middle anchor (kept over D-042); D-039 ADU anchor refit; D-040 statewide backtest; D-041 consistent ADU counts; Houston and Austin checks; results dashboard; D-043 unseen-state range (branch) | LB-100; the day's work is in `logbook.d/` fragments awaiting the fold |
| 23. Oregon as a fifth state; auditing the ADU fit | Nov 4 | Can Oregon serve as an unseen-state transfer test (V9) frozen before its outcomes are seen, and why does the four-state ADU fit miss? | Oregon assessment, statewide holdout and V9 setup; OR package, state-law, fee and local rule rows with readiness report; data dashboard; D-044 adopted (branch); D-045 to D-047 fit audit, D-048 no-ramp method | LB-101, LB-102; most of the day's work is in `logbook.d/` fragments awaiting the fold |
| 24. Oregon transfer test scored; no-ramp ADU model adopted | Nov 5 | Does the four-state model, frozen blind, predict Oregon, and what changes once Oregon joins the fit? | D-048 adopted (Ben) and D-050 state effect refit; V9 frozen (D-051, D-052), unblinded and scored: missing middle inside by 15 buildings, every ADU target missed, so V9 fails; Portland and Bend permit adapters; V9 holdout released; D-053 Oregon refit run (draft, not adopted) | LB-103, LB-104; most of the day's work is in `logbook.d/` fragments awaiting the fold |
| 25. The app and the missing-middle refit | Nov 6 | Can the results become one static page that could cover 50 states, and does the missing-middle model hold up when tested state by state? | Static app (WS-APP) and visual identity; ACS parcel-proxy test passed (D-056); D-053 five-state ADU fit adopted; D-055 missing-middle refit adopted, kept after D-059 (Ben); D-060 ADU range run | LB-105, LB-106 |
| 26. Forecast window and scenario definitions | Nov 7 | Which five years should the forecast cover, and how should the missing-middle scenario be defined before it is coded? | D-061 window 2027–2031 (proposed); overlap thresholds kept; app state map; Lubbock second coder; D-062 and D-063 proposed (all on branches) | LB-107 – LB-110 |
| 27. First scenario results and a public page | Nov 8 | With the window fixed, what does the missing-middle scenario add in each state, and how will the app reach a public URL? | D-061 adopted and merged; D-062 five-year rate run (config range stands); D-063 approved, coded and run on five states, homes per building narrowed; app map and per-state files merged; GitHub Pages publishing and the current-rules date (branches) | LB-111 – LB-116 |
| 28. Results on the new window, a live app and the fee model | Nov 9 | With the window and rules date fixed, what do the reforms add against a no-change baseline, can judges open it, and what do real fees by building type say? | Results runs D and E (D-064, D-067, D-068); housing need on the window; app live on GitHub Pages; fee plan and levels (D-065, D-066, D-069, D-073); NC gut check (D-070); V5 Charlotte passed (D-071); D-072 two-step ADUs (branch) | LB-117 – LB-128 |
| 29. Counting ADUs in five states | Nov 10 | Can every state count its ADUs the same way, with each permit source's undercount measured, before one joint refit? | D-074 and D-075 counting protocol; Raleigh, Austin and Portland k; new NC, MN, OH, TX and OR permit sources; D-078 undercount table; permit-level remainders and parser fixes; D-079 model form (proposed); fee knobs D-076, D-077 merged | LB-129 – LB-136 |
| 30. Parser accuracy measured; missing middle reviewed | Nov 11 | How accurate is each ADU permit source once false positives count, and can missing middle be brought to the same standard before any count? | Five-state rebuilds and `--offline` mode; D-080, D-081; two rounds of parser hand checks and the k table (merged); joint-refit code; MM method review, D-082 (proposed), second-coder rule rows and D-082 code (branches) | LB-137 – LB-144 |
| 31. Both joint refits run | Nov 12 | Do the ADU and missing-middle models, refit on five states under their pre-registered rules, pass their accuracy tests? | ADU joint refit (Form A kept, no tier passes); ADU floor to 3 years (D-082 on `main`); WS-ADU-RULES brief; MM D-082 approved, runs 1–6 (no model passes tests A–C, choice left to Ben) | LB-145 – LB-150 |
| 32. ADU model probes and rule histories | Nov 13 | Which place factors, rule details or time trends explain the ADU model's misses, and can coded rule histories supply enough rule-change events? | WS-ADU-RULES rows into config (source-checked); D-083 screen (owner share, housing age pass); version C dropped; D-084 Form A′ (narrow win, no tier); D-085 no trend kept; D-086 rule histories coded (all on branches) | LB-151 – LB-157 |
| 33. Place types and own-history forecasts | Nov 14 | Can place types shared across states, or a place's own history with drift, make the ADU model carry over, and what does the engine give on the chosen model? | D-087 (Form A stays); D-088 place types, Ben chooses Form A + place types; D-089 state profiles and town prior; D-090 own-history test (fails), D-091 drift (honest ranges); A + types in config and engine, anchor slopes; handoff 16 (all on branches) | LB-158 – LB-163 |
| 34. Missing middle settled, ADU rows fixed, stacks merged | Nov 15 | Can the missing-middle baseline carry honest uncertainty, do the ADU rule rows and reform ratio hold up, and can both model stacks reach `main`? | D-092 deviations a–d, runs 7–13, C4 to config, MM accuracy and methodology section; V5 St. Paul frozen (D-098) with a scoring script; D-082 → D-092 renumber and ADU stack rebased and merged; ADU D-093 own counts with drift, D-094 (not adopted), D-095 reform check, coverage audit and 33 rows fixed, D-096 refit to config, D-097 m_x grid and gut check; TX/OR/OH count-source search; 40 uncoded MN/OH places coded; D-099 drafted | LB-164 – LB-174 |
| 35. St. Paul scored, a faster ramp tested, final ADU config | Nov 16 | Does the frozen missing-middle model pass its St. Paul blind test, does a faster or route-specific ramp help, and is the ADU config final for the app? | D-099 run (ν stays 1); gut check corrected to medians; V5 St. Paul unblinded and scored (miss); D-100 ramp run (C4 stays); ADU stack (#418) and uncoded rules (#444) merged; final ADU config refit | LB-175 – LB-178 |
| 36. App redesign, rule agents and a pipeline for any state | Nov 17 | With the models settled and merged, can the app lead with one clear number and its evidence, can local rules be coded by reusable agents, and can a new state run with no code edits? | MM and ADU stacks merged, results rerun; fast-ramp sensitivity; Minneapolis permit fix; MM gut check; fees and ADU detail in the bundle; app home card, headline, evidence cards and Model tab; office hours with Amy and WS-NEED-AMI; MM, ADU and fee rule agent swarms and shared core; adding-a-state guide and WS-SCALE tasks 0–13, D-101–D-103 | LB-179 – LB-192 |
| 37. One run per reform, rule agents merged, an unseen state set up | Nov 18–19 | With each reform run on its own, can the rule agents run on a state never seen, and can Wisconsin be predicted blind from national data alone? | Judging panel run (64.9/100 today); combined scenarios removed and ranges in plain words (#491); rule agents on the shared core merged (#470, #471, #480, #492, #493); Burlington VT proof of concept and fixes; MM and ADU read `place_inputs`; V8 Wisconsin blind and D-104; AMI strip decisions and handoff (part B) | LB-193 – LB-198 |
| 38. Wisconsin scored, the app reviewed line by line, WS-SCALE merged | Nov 19–20 | Did the blind Wisconsin prediction hold, does each tab read clearly to a policymaker, and can the scaling and agent work reach `main`? | AMI strip and shortfall need card (#481, #497); Ben's review of Results, Data and Model tabs; rule-agent fixes on Vermont towns (#494, #498, #499); V8 frozen, scored (×1.49, fails), released, diagnosed (D-104–D-106); WS-SCALE merged; NC ADU baseline gap and D-107 drift recentring (branch); data tab limited to built states | LB-199 – LB-204 |
| 39. Code review, cleanup and the benchmark state | Nov 24 | Does `main` hold everything the docs cite and the decisions adopted, which open pull requests still belong, and which state is the official benchmark? | Thread 17 review log; D-060 ported; D-102 option (b); Wisconsin as a data-ingestion test; all open PRs cleared and the app republished; Minnesota as benchmark; range drivers (#54); deck draft 1 and the Model & Assumptions doc draft | LB-213 – LB-220 |
| 40. Review fixes, a deep inspection and calibration as code | Nov 25 | Do the engines and adapters do what the plan says, what would judges and future data break, and can every fitted value be re-derived with one command? | Engine and adapter fixes from code review part A; judging panel 69.4/100 and robustness fixes; app usability fixes; `lotline calibrate` phases 1, 2 and 4 | LB-221 – LB-225 |
| 41. Calibration finished and a modular model | Nov 26–27 | Can every fitted value be re-derived and refitted on the current model forms, and can a new reform plug in without touching the mechanics? | Calibration phases 2–6 merged (D-056, D-060, D-044/D-048/D-091 and φ/C4/D-100 refitted; 110 scripts archived); review loose ends and ingestion guards; modularity plan steps 1–3 (scenario contract, forecast vs fitting split, smaller engine files) | LB-226 – LB-228 |

---

## Entry template

```
### LB-NNN · YYYY-MM-DD · <Workstream>: <short title>
- **Question:** what this step set out to answer
- **What I did:** method, in 2–4 bullets
- **Inputs:** sources, datasets, prior entries
- **Outputs:** file paths / artifact links
- **Findings:** the 1–3 things that matter
- **Decisions:** anything added to the HANDOFF decisions log
- **AI:** what Claude did and how it was checked
- **Open / next:**
```

Workstreams: `Rules` · `Scope` · `Data feasibility` · `Policy analysis` · `Literature` · `Study design` · `Build` · `Validation` · `Deliverables` · `Admin`

---

## Entries

### LB-001 · 2026-09-29 · Rules: Read the Rules and Handbook, build the compliance checklist
- **Question:** What must the submission contain, and which gates disqualify an entry?
- **What I did:**
  - Read the Official Rules, Participant Handbook and landing page.
  - Turned every requirement into a checklist item (E eligibility, S scope, D deliverables, T technical gates, P post-submission), each marked AUTO or MANUAL.
  - Wrote a standard-library checker for the AUTO items plus a CI workflow.
- **Inputs:** https://housingchallenge.turnout.rocks/rules.html · https://housingchallenge.turnout.rocks/handbook.html
- **Outputs:** `HANDOFF.md` §2–5 · `compliance_check.py` · `challenge.toml` · `.github/workflows/compliance.yml`
- **Findings:** Transparency is weighted 30% and breaks ties; the sparse-data bonus rewards states with thin data; public repo, permissive license, SBOM, CodeQL and Dependabot are pass/fail gates; `certifi` (MPL-2.0) is a license trap.
- **Decisions:** none yet (process only).
- **AI:** Claude drafted the checklist and checker from the Rules text; Rules marked as controlling.
- **Open / next:** registration closes **Oct 7, 9:00 a.m. ET**; eligibility E1 unconfirmed.

### LB-002 · 2026-09-29 · Scope: Choose the ranking basis and scenario set
- **Question:** Which benchmark scenarios, and how should candidate states be compared?
- **What I did:** Compared the five Handbook scenarios by data needs and shared machinery; chose to rank states on measurability rather than on which reform they passed.
- **Inputs:** Handbook scenario definitions; LB-001.
- **Outputs:** HANDOFF decisions log (3 entries dated 2026-09-29).
- **Findings:** Missing Middle, ADUs and Fees all act on single-family parcels and can share one parcel-count and pro forma engine; none needs transit data, which suits sparse-data states.
- **Decisions:** Rank on data quality, not policy type · Missing Middle as lead (tentative) · Set = Missing Middle + ADUs + Fees, Parking optional 4th.
- **AI:** Claude laid out the trade-offs; choice made by Ben.
- **Open / next:** pick the state.

### LB-003 · 2026-09-29 → 30 · Data feasibility: Score all 50 states + DC
- **Question:** In which states can we observe reforms long enough, at lot level, to measure them?
- **What I did:**
  - Scored every state on reform post-period length and availability of lot-level (parcel/permit) data, with lot-by-lot weights.
  - Iterated the ranking through three versions as the policy inventory (LB-004) filled in.
- **Inputs:** state parcel portals, permit data, LB-004 inventory.
- **Outputs:** [Housing Data Readiness Ranking](https://claude.ai/artifact/PUQszFy2CYHvr2uNHTGRna) (v3, 2026-09-30).
- **Findings:** Top on lot-by-lot weights: WA #1, NC #2, CT #3; also strong MT #8, WI #9, OR #10, CO #11, TX #12, OH #18.
- **Decisions:** none final; state still undecided.
- **AI:** Claude researched and scored; low-confidence rows flagged.
- **Open / next:** choose state (NC and OR favored for local mode, see LB-008).

### LB-004 · 2026-09-29 → 30 · Policy analysis: Build the reform inventory
- **Question:** Which ADU, Missing Middle and fee laws exist, at what level, since when, and in force or not?
- **What I did:**
  - Catalogued state and local measures with effective date, status, source URL and a confidence rating.
  - Second pass filled PA, NJ, DE, DC, LA, MS, AL and resolved specific questions (below).
- **Inputs:** statutes, city ordinances, Sightline/secondary trackers.
- **Outputs:** `docs/research/lotline-policy-inventory.csv` (project: `research/lotline-policy-inventory.csv`).
- **Findings:** 199 rows: 79 ADU, 69 Missing Middle, 51 fees; confidence 129 high / 62 med / 8 low. IN HEA 1001 confirmed review-only; MD 2025 ADU law = HB 1466 (Ch. 197); Cleveland form-based code in force in 3 pilot areas.
- **Decisions:** "Policy inventory completed" (HANDOFF, 2026-09-30).
- **AI:** Claude compiled; every row links its source; low-confidence rows flagged for checking.
- **Open / next:** verify the 8 low-confidence rows before any enter a config file.

### LB-005 · 2026-09-30 · Study design: Lot-level evidence calibrates a statewide model
- **Question:** The Handbook wants statewide 5-year totals. How do real, local reforms feed that?
- **What I did:** Framed lot-level before/after evidence as a *calibration input* to a statewide model, not as the output. Then refined: calibrate on old reforms (long post-periods), apply to states that haven't reformed.
- **Inputs:** LB-003, LB-004, Handbook §statewide output.
- **Outputs:** HANDOFF decisions (2 entries, 2026-09-30).
- **Findings:** Strongest, oldest ADU evidence is West Coast (Portland 2010, LA/CA 2017 & 2020, Seattle 2019), so the curve must be transported to the chosen state by home value/rent.
- **Decisions:** "Study design" and "Calibrate where reforms are old, apply where they aren't."
- **AI:** Claude proposed; Ben accepted.
- **Open / next:** find the methods to do this (LB-006).

### LB-006 · 2026-09-30 · Literature: Methods review and evidence register
- **Question:** How do researchers estimate the effects of ADUs, Missing Middle and fee cuts, and what parameter ranges does that give us?
- **What I did:**
  - Four parallel literature sweeps (~140 searches/fetches), one per method family/scenario, plus spot checks.
  - Tagged each claim **[v]** verified at publisher/NBER/RePEc, **[d]** our own arithmetic, **[?]** unverified.
  - Logged each study (data, method, counterfactual, finding, link) in a register.
- **Inputs:** journals, working papers, city/state monitoring reports.
- **Outputs:** `research/lotline-methods-review.md` · `research/lotline-evidence-register.csv` (104 studies, citations checked 2026-09-30).
- **Findings:**
  - Two families: ex-post causal (DiD, synthetic control, spatial RD) and ex-ante simulation (pro forma, parcel hazard, elasticities). Best practice: build the simulation, calibrate to ex-post estimates, backtest.
  - Capacity overstates realized building by 10–100×; the annual **realization hazard** is the parameter that matters.
  - Evidence strength: Missing Middle strong abroad/thin in US; ADUs medium (big jumps, no formal causal study); fees weak on quantity, strong on incidence.
- **Decisions:** none logged; working parameter ranges recorded in the review (ADU 0.2/0.4/0.8% per yr; MM 0.02–0.2% per yr).
- **AI:** Claude ran the sweeps via parallel agents; one correction made in-pass (CCI 2021 net-new ADU share → 50–80%).
- **Open / next:** work the §7 open-verification list.

### LB-007 · 2026-09-30 · Study design: ADU natural-experiment design (Theme 1)
- **Question:** Which real ADU reforms, with which controls, can give an original, controlled uptake estimate?
- **What I did:** Ranked candidate natural experiments by post-period length and control quality; checked which datasets actually flag ADUs.
- **Inputs:** LB-004, LB-006.
- **Outputs:** `research/adu-study-design.md` (draft).
- **Findings:** No rigorous causal ADU-production study exists (a gap we can fill). Census BPS/ACS can't identify ADUs; CA HCD APR Table A2 is the only open multi-jurisdiction ADU-tagged source. Designs: Portland vs Clark County; LA/CA dose design vs Phoenix/Las Vegas; Seattle vs Puget Sound; weak-reform contrasts (NH, Minneapolis, DC).
- **Decisions:** "Work each theme separately, ADUs first" (HANDOFF).
- **AI:** Claude drafted; data sources linked.
- **Open / next:** pull Portland and Clark County permit data once coding opens.

### LB-008 · 2026-09-30 · Study design: Two-prong (evidence + mechanism) proposal
- **Question:** How should a state or city see results: from comparable places, or from its own economics?
- **What I did:** Designed an evidence prong ("what happened in places like you") and a mechanism prong (parcel funnel + pro forma), calibrated against each other, with the jurisdiction as the basic unit and data tiers 1–3.
- **Inputs:** LB-006 evidence register (E-numbers), LB-007.
- **Outputs:** `research/lotline-two-prong-design.md` (proposal).
- **Findings:** Comparable pool is thin (~10–15 places, mostly West Coast); fees have no clean comparables; local results aren't additive (displacement).
- **Decisions:** **not yet adopted**; proposal for discussion.
- **AI:** Claude drafted and critiqued the design.
- **Open / next:** accept/modify; choose state.

### LB-009 · 2026-09-30 · Build: Code name and repo scaffold
- **Question:** Where does the build happen?
- **What I did:** Named the entry **Lotline**; set up `~/Engineering/lotline` with license, compliance checker, doc stubs and `src/lotline/`.
- **Outputs:** repo scaffold (Apache-2.0 `LICENSE`, `CLAUDE.md`, `docs/*.md` stubs). No commits yet.
- **Decisions:** "Build moves to Claude Code in `~/Engineering/lotline`" · "Code name Lotline" (HANDOFF).
- **AI:** Claude scaffolded; `CLAUDE.md` forbids copying code from sibling repos (Rule S8).
- **Open / next:** first commit; coding period opens Oct 14.

### LB-010 · 2026-09-30 · Admin: Start this logbook
- **Question:** How do we keep a replayable record of the process?
- **What I did:** Created this file, backfilled LB-001–009 from existing docs, added a rule to `CLAUDE.md` so each working session appends an entry, and set up a nightly scheduled review (8:52 p.m. ET) that logs anything done outside a Claude session.
- **Outputs:** `LOGBOOK.md` (repo root) · project `claude/LOGBOOK.md`.
- **AI:** Claude wrote the backfill from HANDOFF and research docs; Ben to check the reconstructed entries.
- **Open / next:** —

### LB-011 · 2026-09-30 · Scope: Align the plan with a likely judge's stated goals
- **Question:** What does the Arnold Ventures housing director's registration post (likely judge) imply for our scope and tool design?
- **What I did:** Read the post against the Rules §8 rubric and our current plan; identified what already fits and what to change.
- **Inputs:** Director's launch post (shared by Ben, 2026-09-30); HANDOFF §1–2.
- **Outputs:** 4 new HANDOFF decisions (2026-09-30); HANDOFF §1 "Scenarios" row updated.
- **Findings:** Already aligned: statewide totals from public data, a framework that scales across states, ranges not point estimates. Gaps: assumptions must be user-adjustable, scenarios must be combinable without double-counting lots, and parking is one of the judge's three headline reforms.
- **Decisions:** Assumptions as plain-language sliders · Combinable scenarios on one parcel pool · Parking → planned stretch scenario · Existing state reform as labeled S7 scenario (tentative).
- **AI:** Claude analyzed the post and proposed the changes; Ben approved logging them.
- **Open / next:** reflect sliders and stacking in the two-prong design (LB-008) and the config schema.

### LB-012 · 2026-09-30 · Literature: Similarity, standardization and statistical protocol (auto-review)
- **Question:** How do the studies define comparable places, standardize outcomes and handle denominators, zeros and dose, and what protocol should Lotline follow?
- **What I did:**
  - Extracted the methods sections of 42 studies plus 4 methods-guidance papers field by field (comparison group, similarity covariates, how similarity enters, units, zeros, dose, diagnostics, cleaning); 26 read in full text, 11 working-paper versions, 9 abstract/secondary only.
  - Synthesized a working protocol: canonical unit, eligible-parcel rule, event time, reform-coding rubric, three-step similarity, estimators, pooling, gross-to-net.
  - Re-examined whether to keep the fee scenario vs. swapping in parking or TOD.
- **Inputs:** LB-006 evidence register (E-numbers), guidance papers G01–G04 (Abadie, TWFE critique, Westreich transport weighting), LB-008.
- **Outputs:** project `research/lotline-statistical-protocol.md` (v0.1) · project `research/lotline-methods-extraction.csv` · project `research/lotline-evidence-register.csv` re-uploaded alongside.
- **Findings:**
  - No housing study transfers an effect to a new target place; our evidence prong is a transportability problem (inverse-odds weighting, untested in housing).
  - Denominators and reform coding are the most neglected details and can drive results (Portland "per 1,000 lots", SB 9 simulated parcels, Stacy vs. AEI).
  - Protocol: net new units per 1,000 eligible parcels per year in event time, numerator/denominator stored separately; Callaway–Sant'Anna/Borusyak or synthetic control, no TWFE with unit trends; NB count models with parcel offset; hierarchical pooling; leave-one-place-out backtests; pre-register choices in `docs/analysis_plan.md` before outcome models.
  - Recommendation: keep fees (evidence weak on quantity, strong on incidence; low case includes zero).
- **Decisions:** none logged in HANDOFF; protocol is a working draft and the keep-fees recommendation is not yet a logged decision.
- **AI:** Claude extracted and synthesized; source depth recorded per row. Logged by nightly review from the doc contents; how the extraction was run isn't recorded.
- **Open / next:** resolve §6 data-dependent decision points once the state's data is in hand; decide keep-fees formally.

### LB-013 · 2026-09-30 · Data feasibility: Verified data availability for the top 13 states (auto-review)
- **Question:** Do the datasets the protocol needs (R1–R10) actually exist and hold the right fields in the top-ranked states, and what does that mean for choosing the state?
- **What I did:**
  - Catalogued 194 datasets (fields present/missing, vintages, access/license, quality issues, method use, 0–3 score) for the 12 top states on the "Lot-by-lot study" preset plus OH, key cities and national sources; 156 opened and checked.
  - Scored each state on requirements R1–R10 (parcels, history, zoning, permits, ADU flag, completions/demolitions, prices, fees, in-state reforms, access) and on policy headroom.
- **Inputs:** Housing Data Readiness Ranking v3 (LB-003), statistical protocol (LB-012), LB-004 inventory.
- **Outputs:** project `research/lotline-data-availability.md` (v1) · project `research/lotline-data-catalog.csv` · project `research/lotline-data-summary.csv`.
- **Findings:**
  - The desk ranking overstated data depth: no state scores ≥2 on every requirement; means 1.5–2.1. Blockers everywhere: National Zoning Atlas license bars bundling, ADUs invisible in Census BPS, BPS place-level imputation.
  - Real fees found are mostly far below the Handbook's $50k (e.g. Raleigh ~$7.4k, Beloit ~$1k; Colorado ~$51.7k the exception) — a limitation and a policy insight.
  - WA/OR/CA/VT have little headroom (reforms already in baseline) and serve better as evidence sources; **NC recommended as target** (alternates TX, OH, CT).
- **Decisions:** none logged in HANDOFF; NC is a recommendation for discussion.
- **AI:** Claude researched and verified dataset pages; licenses with no stated terms flagged for runtime fetch only. Logged by nightly review from the doc contents.
- **Open / next:** "data scouting" pass before Oct 14 (NC OneMap profiling, city permit dictionaries, license emails to Land Use Labs/WA Commerce, OR DLCD and WA OFM records requests, 5–10 real fee schedules); repo copies of these research files not yet made.

### LB-014 · 2026-09-30 · Scope: Notes from the sponsors' Upzoned #301 podcast (auto-review)
- **Question:** What did the Sponsor (Arnold Ventures) and Administrator (The Turnout) say they want from tools, and what does it imply for Lotline's design?
- **What I did:**
  - Summarized the Upzoned #301 transcript ("Can We Predict Which Housing Reforms Will Work?", Kestelman, Gordon, Reuter) with timestamps.
  - Pulled out data facts that affect our design and listed nine proposed implications for Lotline.
- **Inputs:** podcast transcript pasted by Ben (2026-09-30); LB-005, LB-007, LB-011.
- **Outputs:** project `research/podcast-upzoned-301-notes.md` (no repo copy).
- **Findings:**
  - Sponsors want no zoned-capacity totals, no black-box models: transparent, user-overridable assumptions, ranges with sensitivity (construction cost named), public data only, and a tool that can be extended to another state. Kestelman says she is not judging (corrects the "likely judge" framing in LB-011).
  - ADUs are often not counted as new units in permits, so Census BPS may undercount them; permits don't record parking; suburban parcel/zoning data is thin.
  - Reuter's three layers (legal → pencils → built) map onto our parcel funnel + pro forma + realization hazard.
- **Decisions:** none logged in HANDOFF; the nine implications (Legal→Pencils→Built pipeline, ADU undercount correction, tornado chart and evidence-vs-influence matrix, second-state portability run, state vs. local levers, ADU new-construction channel, "data we wish we had", no proprietary parcel data, mentor stress-test) are marked "proposed, not yet decided".
- **AI:** Claude summarized the transcript; timestamps cited for each claim. Logged by nightly review from the doc contents.
- **Open / next:** decide which implications to adopt; registration closes Oct 7.

### LB-015 · 2026-10-03 · Study design: Causal diagram and confounder register
- **Question:** Which background factors (rates, prices, demand, reform design, measurement) could fake or hide a policy effect, and how should the design and the forward model handle each one?
- **What I did:**
  - Worked through the distinction between confounders (fix by design), effect modifiers (model them) and mediators (never control for them) with Ben.
  - Reviewed the methods extraction, methods review, evidence register, ADU study design and podcast notes for factors we had not yet considered.
  - Built a 42-row confounder register and a causal diagram (Mermaid), and rendered the diagram with mermaid-cli to check that it parses and reads cleanly.
- **Inputs:** project `research/lotline-methods-extraction.csv`, `research/lotline-methods-review.md`, `research/lotline-evidence-register.csv`, `research/adu-study-design.md`, `research/podcast-upzoned-301-notes.md`, `research/lotline-statistical-protocol.md`.
- **Outputs:** project `research/lotline-causal-diagram.md` · project `research/lotline-confounder-register.csv` · repo `docs/research/lotline-causal-diagram.md`, `docs/research/lotline-confounder-register.csv`, `docs/research/lotline-causal-diagram.png`.
- **Findings:**
  - Rates are mainly an effect modifier: year effects in any comparison design cancel their level, but the size of the effect depends on them. They are a confounder only in single-place before/after designs.
  - The biggest confounder is selection into reform (price pressure, momentum, pro-housing politics). The strongest fix is a within-place eligible-vs-ineligible parcel contrast.
  - The review added 28 factors to the 14 we discussed. The most consequential: local opt-out and implementation, bindingness of old rules, parcel stock, land-value capitalization as a mediator, approval time, homeowner financing as the ADU rate channel, and ADU measurement that starts at the reform itself.
- **Decisions:** none logged in HANDOFF. §7 of the diagram doc proposes six changes to the statistical protocol, pending Ben's approval.
- **AI:** Claude drafted the register and diagram. Evidence IDs were checked against the evidence register, and one wrong cross-reference (C28 → C11) was fixed before saving.
- **Open / next:** approve the §7 protocol changes; check that the register fits the Missing Middle and fee themes; plan an in-state validation before the statewide run.

### LB-016 · 2026-10-04 · Validation: Theme causal diagrams and in-state validation plan
- **Question:** Does the causal framework hold for Missing Middle and fees, and how do we prove the model on jurisdictions in the target state before applying it statewide or to a new state?
- **What I did:**
  - Added 12 factors to the confounder register: C43–C49 for Missing Middle (building-code step at 3+ units, lot-split and ownership rules, developer financing, teardown economics, ADU-vs-MM lot competition, developer type, FAR/height) and C50–C54 for fees (reverse causality of fee levels, revenue-funded infrastructure, fee structure, fee share of cost, payment timing).
  - Wrote theme diagrams for Missing Middle and fees, each with adjustment rules, identification options and falsification checks; rendered both with mermaid-cli to check they parse.
  - Wrote a validation ladder (V0–V7) with proposed pass/fail thresholds, NC jurisdiction roles, integrity rules (pre-registration, frozen predictions) and a timeline to Dec 16.
- **Inputs:** LB-015 outputs; project `research/lotline-policy-inventory.csv` (NC, CA, WA, ID, OR fee rows), `research/lotline-data-catalog.csv` (NC permit and parcel fields), `research/lotline-data-availability.md`, `research/lotline-methods-review.md`.
- **Outputs:** project `research/lotline-causal-diagram-mm.md`, `research/lotline-causal-diagram-fees.md`, `research/lotline-validation-plan.md`; updated `research/lotline-confounder-register.csv` (54 rows) and `research/lotline-causal-diagram.md` (pointer to theme docs). Repo copies in `docs/research/` plus `lotline-causal-diagram-mm.png` and `lotline-causal-diagram-fees.png`.
- **Findings:**
  - Missing Middle uses the same framework with developer-side modifiers; townhouses are hidden in BPS 1-unit counts and 5–6 plexes in BPS 5+, so local permits are required.
  - Fees need a different identification strategy: fee levels respond to growth, so evidence must come from fee changes caused by something else. NC's *Quality Built Homes v. Carthage* (2016) ruling is a candidate in-state fee natural experiment; CA SB 13's 750 sq ft exemption allows a bunching test.
  - NC supports a full in-state ladder: Raleigh R-1 lots and Durham's urban/suburban tiers give within-city comparisons; Charlotte's 2023 UDO is a blind forward test (prediction to be frozen by Nov 17).
- **Decisions:** none logged in HANDOFF. The plan's §8 lists four decisions for Ben (ladder and thresholds, NC as target, integrity rules, real-fee display).
- **AI:** Claude drafted all documents. Register cross-references and evidence IDs were checked by script against the register; NC reform dates and data fields were taken from the policy inventory and data catalog. Building-code (IRC/IBC) and BPS townhouse-classification points come from Claude's general knowledge and are marked "to source" in the register.
- **Open / next:** Ben to approve §8 decisions; compile the *Carthage* affected-town list; confirm Durham permit data freshness; move approved thresholds into `docs/analysis_plan.md` and tag `prereg-v1` before V3.

### LB-017 · 2026-10-04 · Data feasibility: Re-score target states against the model design
- **Question:** NC became the working target because it ranked #2 and we discussed it most. Now that the causal diagrams and validation plan define what the model needs, is there a better target?
- **What I did:**
  - Defined eight requirements from the validation plan (headroom, in-state reforms with type-flagged permits, within-city contrast, blind forward test, statewide parcels, parcel history + prices, fee evidence, data-tier spread) and weighted them.
  - Re-scored the verified states plus desk-only candidates surfaced from the Readiness Ranking v3 data (MN, FL).
  - Spot-checked Minnesota online: Twin Cities parcel licensing and archives, Met Council permit survey, eCRV access, Minneapolis 2040 injunction dates, *Harstad v. Woodbury*.
- **Inputs:** Housing Data Readiness Ranking v3 (all 50 states), project `research/lotline-data-availability.md`, `research/lotline-data-summary.csv`, `research/lotline-data-catalog.csv`, `research/lotline-validation-plan.md`; web sources listed in the output doc.
- **Outputs:** project `research/lotline-state-reassessment.md` · repo `docs/research/lotline-state-reassessment.md`.
- **Findings:**
  - Top three are within 3 of 45 points: MN 35 (unverified), TX 34, NC 32. No state is clearly better than NC on paper.
  - Newly weighed against NC: S.L. 2026-59 requires ADUs in non-coastal cities over 50,000 from Jan 2027, which removes much of the ADU scenario's headroom in NC's largest cities within the 5-year window.
  - Minnesota offers high statewide headroom (MM/ADU bills failed 2024–26), Minneapolis 2040 as a low-uptake test with an on–off–on injunction (2022-06-17 to 2024-05-13), St. Paul ADU (2016/2018) and 1–6 unit (2023) reforms, free Twin Cities parcels with archives to 2003, and a court-driven fee cut (*Harstad*, 2018). Unknowns: sale prices (eCRV bulk restricted to local governments), permit fields, what reverted during the injunction.
- **Decisions:** none logged in HANDOFF. Recommendation: a one-day Minnesota scouting pass on five deciding facts; switch if ≥4 check out, otherwise keep NC with TX as the second-state stress test.
- **AI:** Claude defined the criteria and scores (judgment, stated as such) and checked the weighted sums by script. Minnesota facts come from web spot checks cited in the doc; the 13-state verified scores come from LB-013.
- **Open / next:** Ben to decide whether to run the Minnesota scouting pass; check whether the registration form (closes Oct 7) asks for a state.

### LB-018 · 2026-10-04 · Admin: Registration submitted
- **Question:** Is the entry registered before the Oct 7, 9:00 a.m. ET deadline?
- **What I did:** Recorded Ben's confirmation that registration is done; updated the HANDOFF status row and annotated checklist item E5.
- **Outputs:** `HANDOFF.md` §1 and §3 (E5) · project `claude/HANDOFF.md`.
- **Decisions:** none.
- **AI:** Claude updated the status files from Ben's message; E5 left unticked until the welcome email and Challenge Platform access are confirmed.
- **Open / next:** confirm welcome email and platform access; E1, E2, E3, E4 and E6 remain open (eligibility, age, conflicts, employer rules, roster). Corrects the registration item in LB-017's "Open / next".

### LB-019 · 2026-10-04 · Data feasibility: Minnesota scouting pass; four-state approach
- **Question:** Do the five facts that decide Minnesota as a target check out, and how should a four-state approach be organized?
- **What I did:**
  - Ran two research agents in parallel (parcels and prices; permits, litigation, legislation and fees). They opened live ArcGIS REST metadata, dataset pages, court opinions and statutes.
  - Re-checked the two most consequential claims myself: Met Council permit metadata (ADU and DTQ categories, public domain) and the MnGeo opt-in parcel item (59 counties).
  - Re-scored Minnesota; wrote a scouting report and a Minnesota catalog addendum; proposed state roles for the four-state approach Ben chose.
- **Inputs:** `research/lotline-state-reassessment.md` §4; web sources listed in the scouting report.
- **Outputs:** project `research/lotline-mn-scouting.md`, `research/lotline-data-catalog-mn.csv` (12 datasets), updated `research/lotline-state-reassessment.md` · repo copies in `docs/research/` · HANDOFF state row and a new decisions-log row.
- **Findings:**
  - 4 of 5 deciding facts pass (two partially); the 2040 injunction fails as a test (effective window ~Nov 2023–May 2024, scope unclear). MN re-scores 37 of 45.
  - Met Council publishes permit-level metro permits 2009–2024 flagged SFD/ADU/TH/DTQ/MF5 with PIN, public domain. Outside California's APR it is the only multi-jurisdiction ADU-flagged permit source found; it allows a staggered ADU design across ~180 metro cities.
  - Headroom confirmed: no statewide ADU or middle-housing mandate through the 2026 session. Minnesota is a low-uptake state for both reforms (Minneapolis ~15–30 new 2–4 unit permits a year by a rough web count, to recompute in code).
  - Parcels: metro fields are excellent with open year-end vintages 2021–2025 (earlier ones token-locked); Greater Minnesota is 59 of 87 counties with thin attributes. Sale prices: last sale only; eCRV bulk is agency-only.
- **Decisions:** HANDOFF 2026-10-04: develop and test on MN, TX, NC, OH, starting with MN (Ben). Official benchmark state still open; MN recommended.
- **AI:** Claude ran the agents, verified two key claims directly, and wrote the docs. The injunction-window permit counts came from a summarizing web fetch and are flagged "to recompute in code". Some agent claims are marked "not confirmed" in the report.
- **Open / next:** snapshot Minneapolis and St. Paul rolling-window permit layers; ask Met Council GIS for pre-2021 parcel vintages; check whether 2025 Met Council permits are posted; choose the official benchmark state.

### LB-020 · 2026-10-04 · Build: Build plan and Claude Code transition
- **Question:** What exactly happens next, and how do several Claude Code instances ingest data, build the model and validate it for MN, NC, TX and OH through the GitHub repo?
- **What I did:**
  - Re-checked the Official Rules and Handbook before this milestone. Found that work must be created in the Registration Period (to Oct 7, 9:00 a.m. ET) or the Coding Period (from Oct 14, 9:01 a.m. ET); the week between is not covered.
  - Inspected the local repo: no commits, no GitHub remote, no `pyproject`, and a CI workflow whose license scan would miss a uv virtualenv.
  - Wrote a build plan: phases; stack; repo layout; shared data contracts; holdout and blinding design; the parallel-instance model (worktrees, path ownership, ≤3 concurrent, logbook fragments); quality gates; landing checklist; risks.
  - Wrote nine workstream briefs (bootstrap, core, MN, NC, TX, OH, engine, evidence, app) with sources, tasks, acceptance criteria and gotchas drawn from the data catalogs and scouting docs.
  - Wrote a 53-issue backlog with 7 milestones and an idempotent `gh` script (dry run by default; tested against a stub `gh`).
  - Added multi-instance, data-directory and rules-timing sections to `CLAUDE.md`.
- **Inputs:** Official Rules and Handbook (fetched 2026-10-04); all `docs/research/` documents; `compliance_check.py`; `.github/workflows/compliance.yml`.
- **Outputs:**
  - `docs/build/BUILD_PLAN.md`
  - `docs/build/workstreams/WS-{00-bootstrap,CORE,MN,NC,TX,OH,ENGINE,EVIDENCE,APP}.md`
  - `docs/build/issues.csv`
  - `scripts/dev/create_issues.py`
  - `CLAUDE.md` (new sections)
  - `HANDOFF.md` (build-plan row, gap date)
  - project `build/BUILD_PLAN.md`, `CLAUDE.md`
- **Findings:**
  - Phase 0 has to be committed and pushed before Oct 7, 9:00 a.m. ET for its timestamps to sit inside the registration period.
  - Nine project-only research docs must be copied into `docs/research/`, because Claude Code can't read the Cowork project.
  - Baseline compliance check today: 8 FAIL (expected before bootstrap: no remote, tests, lock file, setup/test commands).
- **Decisions:** none logged; the plan, stack and concurrency cap are proposals for Ben to accept.
- **AI:** Claude wrote all files. The issue script was dry-run against a stub `gh`; `compliance_check.py` was run on the repo. Library licenses marked "verify" in the plan have not been checked.
- **Open / next:** Ben's landing checklist (BUILD_PLAN §9): copy research docs; create the public repo; run WS-00 before Oct 7 09:00; email the organizers about the gap.

### LB-021 · 2026-10-04 · Build: Pin the GitHub repo to the cappellacci account
- **Question:** How do we make sure the Lotline repo is created on Ben's personal GitHub account and nowhere else?
- **What I did:**
  - Confirmed the public GitHub user `cappellacci` exists.
  - Rewrote the setup commands to name the owner explicitly: `gh repo create cappellacci/lotline`, preceded by a `gh auth status` / `gh auth switch` check and a repo-local git identity, and followed by an owner and visibility check.
  - Added an owner check to the WS-00 brief (stop before any push if `origin` isn't cappellacci).
  - Set `repo_url` in `challenge.toml`.
  - Added an `--owner` guard (default `cappellacci`) to `scripts/dev/create_issues.py` that refuses to run against any other repo.
- **Outputs:** `docs/build/BUILD_PLAN.md` §7.1 and §9 · `docs/build/workstreams/WS-00-bootstrap.md` · `challenge.toml` · `scripts/dev/create_issues.py` · `HANDOFF.md` (GitHub repo row) · project `build/BUILD_PLAN.md`.
- **Decisions:** repo owner = `cappellacci` (Ben, 2026-10-04).
- **AI:** Claude made the edits. The owner guard was tested against a stub `gh`: it refuses a wrong owner and proceeds for `cappellacci`.
- **Open / next:** Ben confirms `cappellacci` is the right account (the public profile lists a @palantir org affiliation and one repo, slack-weather-app), then follows §7.1.

### LB-022 · 2026-10-05 · Rules: Notes from the Oct 5 data-tools webinar (auto-review)
- **Question:** What did the organizers' second (and last) pre-challenge webinar on data sources, tools and portability say, and what does it change for Lotline?
- **What I did:**
  - Summarized the webinar ("Housing data challenge: tools, sources, and portability"; Dziurlaj, Houghton, Gordon, Guayante), including answers to Ben's two questions (end users bringing their own data; expert review of methods).
  - Listed eight proposed implications for Lotline.
- **Inputs:** the Oct 5 webinar (source of the notes, e.g. transcript or live notes, not recorded in the doc); Rules §7 and §8; LB-020.
- **Outputs:** project `research/webinar-2026-10-05-data-tools-notes.md` (no repo copy).
- **Findings:**
  - Portability is a stated goal: build a normalization layer (per-jurisdiction field maps into a common schema, original values preserved). Working in more than one jurisdiction "sends a powerful signal to judges", which supports the MN/TX/NC/OH plan. End users will bring their own data, so mapping matters.
  - Judges evaluate only the submission and must run it on their own computer (Docker or setup scripts); a hosted URL is a convenience only. Data must be free to access indefinitely, with no non-commercial, proprietary, paid or restricted data. AI code generation must be disclosed. "The simplest approach … is always best."
  - A GitHub template repo (workflows, checklists, doc templates) arrives at kickoff Oct 14, so WS-00 should plan a merge with it. Scoring weights confirmed (30/25/20/15/10). Weekly mentor office hours (schedule TBD).
- **Decisions:** none logged in HANDOFF; the eight implications are proposals.
- **AI:** the notes doc was written in a Claude session that didn't log itself; this entry was added by the nightly review from the doc's content.
- **Open / next:** per the notes: revisit D1 wording (local run is the deliverable); license-audit every dataset in the catalogs (T11/D7); add GIS QA tests (CRS, geometry validity, join match rates, vintages); plan a week-1 merge with the template repo; bring the validation plan to the first office hours; consider copying the notes into `docs/research/`.

### LB-023 · 2026-10-06 · Build: Phase 0 repo bootstrap (WS-00)
- **Question:** Can the repo go from scaffold to a reproducible, CI-checked Python project before registration closes (Oct 7, 9:00 a.m. ET)?
- **What I did:**
  - First commit of the existing scaffold and research docs on `main`, then branch `ws/bootstrap`.
  - `pyproject.toml` (Python 3.12, src layout, hatchling) with week-1 runtime deps and dev deps; `uv.lock` pins everything. Empty package skeleton matching BUILD_PLAN §4; `lotline --version` and a `lotline fetch` stub, wrapped by `scripts/fetch_data.py`.
  - CI moved to uv (`compliance.yml` runs the license scan inside the venv; new `tests.yml` runs ruff + pytest); `dependabot.yml` for uv and Actions.
  - `compliance_check.py` gained `project.stage = "build"` in `challenge.toml`: until it is set to `"submission"`, the end-of-project deliverables D1–D3 report WARN instead of FAIL so CI is usable during the build. `logbook.d/` fragments + `scripts/dev/merge_logbook.py` (with tests).
- **Inputs:** `CLAUDE.md`, `docs/build/BUILD_PLAN.md` §3–4, `docs/build/workstreams/WS-00-bootstrap.md`, `HANDOFF.md` §3.
- **Outputs:** `pyproject.toml`, `uv.lock`, `src/lotline/**`, `tests/test_smoke.py`, `tests/test_merge_logbook.py`, `scripts/fetch_data.py`, `scripts/dev/merge_logbook.py`, `logbook.d/README.md`, `.github/workflows/{compliance,tests}.yml`, `.github/dependabot.yml`, `challenge.toml`, `README.md`, `docs/disclosures.md`, `.gitignore`, `.env.example`.
- **Findings:** Dependency licenses all permissive except certifi (MPL-2.0, via httpx), now disclosed with a justification. numpy bundles small CC0/0BSD/Zlib components (permissive; noted). `compliance_check.py --run` shows 0 FAIL.
- **Decisions:** Proposed: `stage = "build"` switch for D1–D3 (flip before submitting). Proposed: S4 justification text for the `permits` metric filled in `challenge.toml` (still "leaning"; revisit with the benchmark state).
- **AI:** Claude Code wrote all files in this PR. Checked by `uv run pytest -q` (5 passed), `uv run ruff check .`, `python compliance_check.py --run` and `--deps` (0 FAIL), and a fresh `git clone` + `uv sync --frozen` + tests.
- **Open / next:** Ben enables secret scanning, push protection, Dependabot alerts, CodeQL default setup and branch protection; runs `create_issues.py --apply`. No commits Oct 7 09:00 → Oct 14 09:01 ET.

### LB-024 · 2026-10-06 · Build: Copy project-only research docs into the repo
- **Question:** Can Claude Code instances read every research doc the build plan cites?
- **What I did:**
  - Ben copied the nine Cowork-only research docs (BUILD_PLAN §9 item 1) plus the Oct 5 webinar notes into `docs/research/`.
  - Claude Code checked that all nine named files were present, skimmed them for secrets or personal data before publishing to the public repo, and committed them unchanged.
- **Inputs:** Cowork project research files; LB-006, LB-008, LB-012, LB-013, LB-022.
- **Outputs:** `docs/research/{lotline-methods-review.md, lotline-evidence-register.csv, lotline-methods-extraction.csv, lotline-statistical-protocol.md, lotline-two-prong-design.md, lotline-data-availability.md, lotline-data-catalog.csv, lotline-data-summary.csv, podcast-upzoned-301-notes.md, webinar-2026-10-05-data-tools-notes.md}`
- **Findings:** Nothing sensitive. The mentors in the webinar notes are described by role, not by name. The podcast notes summarize with short timestamped quotes.
- **Decisions:** none.
- **AI:** Claude Code verified the file list, scanned for secrets (`compliance_check.py` T5 plus a keyword grep), and opened and merged the PR. Content is unchanged from the Cowork copies.
- **Open / next:** Closes #8. Commit freeze from Oct 7 09:00 to Oct 14 09:01 ET.

### LB-025 · 2026-10-06 · Admin: Project ↔ repo sync rule in CLAUDE.md (auto-review)
- **Question:** How do we stop the claude.ai project and the repo drifting apart, after 10 research docs turned out to exist only in the project (LB-024)?
- **What I did:**
  - Added a "Project ↔ repo sync (every session)" section to `CLAUDE.md`: any shared doc created or updated in one store is written to the other in the same session, with a path map (`research/` ↔ `docs/research/`, `build/` ↔ `docs/build/`, `claude/LOGBOOK.md` ↔ `LOGBOOK.md`, `claude/HANDOFF.md` ↔ `HANDOFF.md`, `CLAUDE.md`/`README.md` at the root).
  - If the other side can't be reached, the session lists the files still to copy. Images and data stay repo-only; Claude Code workstream instances stay repo-only via PRs.
- **Inputs:** LB-024; `CLAUDE.md`.
- **Outputs:** `CLAUDE.md` (uncommitted working-tree change as of this scan; the project copy of `CLAUDE.md` has not been updated).
- **Findings:** none beyond the rule itself.
- **Decisions:** none logged in HANDOFF.
- **AI:** the edit was made in a session that didn't log itself; this entry was added by the nightly review from the diff.
- **Open / next:** commit the `CLAUDE.md` change (before Oct 7 09:00 ET or after the freeze ends Oct 14 09:01 ET) and mirror it to the project's `CLAUDE.md`. Nine logbook fragments for Oct 6 work (WS-CORE adapters, jurisdictions, provenance, V0 check, schemas-v1, Durham/Carthage scouting) are waiting in `logbook.d/` for `merge_logbook.py --apply`.

### LB-026 · 2026-10-06 · Data feasibility: Gap-week scouting, Durham permits and the Carthage town list
- **Question:** Is Durham's permit feed still updated, and is there a published list of towns hit by *Quality Built Homes v. Carthage*?
- **What I did:**
  - Queried the Durham Inspections ArcGIS layer (`webgis2.durhamnc.gov/.../Inspections/MapServer/12`). It timed out with no response from this network, while `durhamnc.gov` itself answered. Checked the Hub listing instead.
  - Read the UNC School of Government posts on *Carthage* (2016) and system development fees (S.L. 2017-138), and searched for a list of affected towns.
- **Inputs:** `docs/research/lotline-data-catalog.csv` (Durham row), `lotline-causal-diagram-fees.md`, `lotline-validation-plan.md`.
- **Outputs:** this entry.
- **Findings:**
  - **Durham "All Building Permits (table only)" was last updated 2024-11-13 (77,723 records)**, so it looks stale. A separate **"Active Building Permits"** layer exists and is likely a rolling window, which would make it a manual-snapshot candidate like the Minneapolis and St. Paul layers. Fallbacks: the city's Monthly Construction Activity Reports and the LDO permit search.
  - **No published list of Carthage-affected towns.** The SOG posts name only Carthage (fees of $1,000–$30,000 per connection). Amicus municipalities were Apex, Concord, Holly Springs, Jacksonville, Kannapolis, Surf City and Winston-Salem, which is a lower bound. Key dates: ruling 2016-08-19; S.L. 2017-138 took effect 2017-10-01, and existing fees had to conform by 2018-07-01; the refund limitation period was cut to 3 years (N.C. Sup. Ct., Aug 2018).
  - **The likely source for treatment status is the UNC EFC / NCLM annual water and wastewater rates survey** (every year since 2005, about 400–500 utilities, with connection fees, downloadable spreadsheets). Comparing utilities' capacity and impact fees for 2015/16 against 2017/18 could identify which towns dropped fees.
- **Decisions:** none. Proposed: add the EFC rates survey to the NC data catalog as the source for the V6 fee-shock treatment list.
- **AI:** Claude Code ran the queries and web reads; facts come from the cited SOG and EFC pages and the Durham Hub listing. Not yet checked: whether the EFC spreadsheets actually record capacity fees by utility and year.
- **Open / next:** Ben checks Durham freshness by hand (gap-week item 9). Confirm the EFC spreadsheet fields. Consider snapshotting Durham "Active Building Permits".

### LB-027 · 2026-10-06 · Build: Core contracts, holdout filter, and the first data pull (Census BPS, four states)
- **Question:** Can we build the shared contracts and blinding safeguard, then pull national permit data for MN, NC, TX and OH through them?
- **What I did:**
  - `schemas.py` (v1.0): pandera models for the seven canonical tables (BUILD_PLAN §5.1) plus `assert_conforms`. `bps_place_year` gained `bps_id`, `county_geoid`, `months_reported` and reported-only `units_*_rep` so imputation stays visible.
  - IO layer: `LOTLINE_DATA_DIR` resolution, raw/interim/processed paths, cached downloads (ETag/Last-Modified, sha256, retries, project user agent) and an append-only `manifest.jsonl`.
  - Config: pydantic state and parameter models. `config/states/{mn,nc,tx,oh}.yaml` with the two V5 holdouts (St. Paul 2024–26, `2758000`; Charlotte from 2023-06-01, `3712000`). `validation/holdout.py` filters held-out rows by default; `--unblind` needs `results/frozen/<test_id>.json` committed on `main`.
  - BPS adapter: annual place files 1992–2025 for each region, parsed by header name (layouts change across eras), GEOIDs for places, townships and unincorporated remainders, imputed flag. `lotline fetch --source bps` built all four states.
- **Inputs:** Census BPS place files (www2.census.gov/econ/bps/Place), WS-CORE brief, BUILD_PLAN §4–5, validation plan §2.
- **Outputs:** `src/lotline/{schemas.py, io/, config/, validation/holdout.py, adapters/national/bps.py, cli.py}`, `config/states/*.yaml`, `tests/core/*`. Data (not committed): `~/lotline-data/processed/{mn,nc,oh,tx}/bps_place_year.parquet` (MN 32,418 · NC 8,075 · OH 30,772 · TX 30,507 place-years; 68 raw files in the manifest).
- **Findings:**
  - **BPS 6-digit IDs were renumbered in 1992** (Minneapolis 140500 → 497800) and old numbers were reused for other places. Linking years by ID alone gave 1990 Minneapolis the wrong GEOID. Fix: IDs link years from 1992 on; earlier rows match on county + name. Default range starts in 1992.
  - Place sums reconcile with BPS state totals **exactly** in most state-years checked; small positive gaps remain (TX 2005 +115, 2020 +835, 2025 +855; MN 2005 +13; OH and TX 1995 +6/+3), with no duplicate places, so likely release-vintage differences. To explain in V0.
  - **V0 design constraint:** in held-out state-years, state total minus place sum would reveal the held-out city by subtraction, so the reconciliation must skip MN 2024–26 and NC 2023+ until unblinding.
- **Decisions:** Proposed: continue committing through Oct 7–14 (Ben's call on 2026-10-06; record in HANDOFF, since CLAUDE.md and BUILD_PLAN §0 say otherwise).
- **AI:** Claude Code wrote the code and tests (33 passing; synthetic fixtures only) and checked the pipeline against Census's own state totals. **Holdout incident:** while smoke-testing the parser, before the filter existed, Claude printed St. Paul's 2024 BPS totals (75 single-family units, 253 in 5+ unit buildings). These are public Census totals, not the V5 outcome series (2–4 unit units on eligible lots), and the research docs already quote St. Paul 2024–25 outcomes (`lotline-mn-scouting.md`, Minneapolis Fed). Logged so the V5 write-up can note it.
- **Open / next:** ACS, FHFA, FRED/PPI and geography adapters; ArcGIS/Socrata pagers; `lotline provenance`; V0 report (with holdout-safe reconciliation); explain the TX/MN gaps; tag `schemas-v1` after review.

### LB-028 · 2026-10-06 · Build: FHFA house price indexes for four states
- **Question:** Can we add house-price trends (a key driver of whether reforms pencil out) for MN, NC, TX and OH at every geography FHFA publishes?
- **What I did:**
  - FHFA adapter for the annual all-transactions HPI at state, CBSA, county, ZIP5 and tract level. Finds the header row past FHFA's title rows, keeps the base-2000 index (comparable across places) and never interpolates suppressed years.
  - `market_geo_year` schema 1.1: level-prefixed `geo` (`county:27053` vs `zip5:27053` can't collide), plus `hpi_base2000` and `hpi_change_pct`; other market columns optional.
  - ZIP5 rows carry no state, so they are assigned by USPS 3-digit prefix ranges in `config/states/*.yaml`. CBSAs are kept if they touch the state (from FHFA's name suffix, e.g. "Duluth, MN-WI").
  - Processed output is now `processed/<state>/<table>/<source>.parquet`, so several sources can feed one table. Added `openpyxl` (MIT; et-xmlfile MIT), approved by Ben, because FHFA publishes these files only as .xlsx.
- **Inputs:** https://www.fhfa.gov/data/hpi/datasets (annual files, last updated 2026-03-31).
- **Outputs:** `src/lotline/adapters/national/fhfa.py`, schema 1.1, `tests/core/test_fhfa.py`. Data (not committed): `processed/{mn,nc,oh,tx}/market_geo_year/fhfa.parquet`. MN: 87 counties, 29 CBSAs, 583 ZIPs, 1,432 tracts. NC: 99 counties, 2,182 tracts. OH: 88 counties, 2,695 tracts. TX: 179 of 254 counties, 3,531 tracts.
- **Findings:** FHFA suppresses thin places: **TX has county indexes for only 179 of 254 counties**, and 1–9% of tract-years are missing (TX highest). The rural, sparse-data case needs a fallback (CBSA or state index), to be chosen in the build step.
- **Decisions:** none.
- **AI:** Claude Code wrote the adapter and tests (38 passing) and checked coverage against expected county counts.
- **Open / next:** FRED (mortgage rate) and the BLS PPI for construction inputs; Census ACS once Ben has a key; FHFA raw files are stored under vintage `current` (FHFA overwrites in place), so earlier vintages survive only as manifest hashes.

### LB-029 · 2026-10-06 · Build: Census ACS 5-year housing tables, with margins of error
- **Question:** Can we add housing stock by structure type, tenure, year built, median rent and median value for every place, township, county and tract in the four states, without losing the margins of error or leaking the API key?
- **What I did:**
  - New canonical table `acs_geo_year` (schemas 1.2): long format, one row per geography × 5-year vintage × variable, with estimate, 90% MOE and the label as published that year (B25034's year-built bands change across vintages).
  - ACS adapter for B25024, B25003, B25064, B25077 and B25034 at state, county, place, tract and (where townships issue permits: MN, OH) county-subdivision level, vintages 2010–2024. Census's negative codes become missing; a "controlled" MOE becomes 0.
  - `fetch()` gained `secret_params`: the key is merged into the request but kept out of the manifest, cache key and error messages. HTML error pages (invalid key) are deleted instead of cached.
- **Inputs:** Census Data API (`/data/<year>/acs/acs5`, `groups/<table>.json`); CENSUS_API_KEY from Ben (in `.env`, gitignored).
- **Outputs:** `src/lotline/adapters/national/acs.py`, `tests/core/test_acs.py`, schema 1.2, `township_permits` flag in `config/states/*.yaml`, README note on the key. Data (not committed): `processed/<state>/acs_geo_year/acs.parquet`.
- **Findings:** MN 2019–23 check: Minneapolis median value $345,600 ± $3,908, median gross rent $1,329 ± $19, 17,048 ± 937 two-unit-structure homes. 0.3–2% of estimates are suppressed (mostly small townships and places). Key verified absent from the manifest.
- **Decisions:** none.
- **AI:** Claude Code wrote the adapter and tests (45 passing), verified the key with one request without printing it, and checked the manifest for key leakage.
- **Open / next:** move medians into `market_geo_year` in the build step; FRED mortgage rate and BLS PPI; Census geographies + BPS crosswalk → `jurisdictions`.

### LB-030 · 2026-10-06 · Build: Mortgage rates, construction input prices and CPI (FRED)
- **Question:** Can we add the national cost-of-money and cost-of-building series the pro forma and the baseline need, plus a deflator for real 2025 dollars (protocol §5.9)?
- **What I did:**
  - FRED adapter (public CSV endpoint, no key): MORTGAGE30US (Freddie Mac PMMS, weekly), WPUIP2311001 (BLS PPI, residential construction inputs, monthly), CPIAUCSL (BLS CPI-U, monthly) → `market_geo_year` rows at `national:US`, annual means.
  - Complete years only; partial years (1971 mortgage, 1986 PPI, 2026) stay missing. **One stated exception:** a single missing observation between two published ones is interpolated (time-weighted) before averaging.
  - Schemas 1.3: `cpi_u` column on `market_geo_year`; year floor lowered to 1940 (CPI starts 1947).
- **Inputs:** https://fred.stlouisfed.org/graph/fredgraph.csv?id=… (pulled 2026-10-06).
- **Outputs:** `src/lotline/adapters/national/fred.py`, `tests/core/test_fred.py`. Data (not committed): `processed/<state>/market_geo_year/fred.parquet` (80 years).
- **Findings:**
  - **BLS published no October 2025 CPI** (federal shutdown). Without the single-gap rule, the 2025 base year for real dollars would be missing. With it: CPI-U 2025 = 322.19; mortgage 6.60%; PPI residential inputs 322.07 (2024: 313.70 / 6.72% / 315.20).
  - **MORTGAGE30US is Freddie Mac data** republished by FRED with permission. It needs an attribution line wherever it is shown; the license is recorded in the manifest. Flag for `docs/data_provenance.md`.
- **Decisions:** Proposed: the single-gap interpolation rule for national monthly series.
- **AI:** Claude Code wrote the adapter and tests (50 passing), found the CPI gap in the raw file, and checked values against the raw series.
- **Open / next:** Census geographies + BPS crosswalk → `jurisdictions`; `lotline provenance`; V0 report.

### LB-031 · 2026-10-06 · Build: Jurisdictions table (permit-issuing places) and BPS ↔ GEOID linkage
- **Question:** Can every building permit be tied to a named Census geography, so permits, ACS and FHFA join on one key?
- **What I did:**
  - `build/jurisdictions.py`: the universe is every GEOID in a state's BPS table (places, townships, and counties for their unincorporated areas). Names and 2020 population come from the 2020 Census redistricting file (new `adapters/national/decennial.py`). `data_tier` defaults to 3 (national data only), raised per place in state configs later.
  - BPS fixes: unincorporated-area rows now carry their county GEOID; Ohio's "<X> County Part" rows too. The GEOID backfill now falls back to (county, name), then to the name alone where it is unique in the state; it strips BPS's "@n" multi-county suffix and never guesses ambiguous names.
- **Inputs:** Census API `2020/dec/pl` (P1_001N); BPS place files.
- **Outputs:** `src/lotline/build/jurisdictions.py`, `src/lotline/adapters/national/decennial.py`, BPS adapter changes, `tests/core/test_jurisdictions.py`, more BPS tests (55 passing). Data (not committed): `processed/<st>/jurisdictions/jurisdictions.parquet` (MN 1,034 · NC 257 · OH 954 · TX 1,011). ACS pull finished: 8.9M rows across the four states, 2010–2024; API key absent from the manifest.
- **Findings:**
  - **From 2009 on, 100% of BPS units in all four states map to a jurisdiction.** Before 2009, 0.07–2.9% can't be placed (places that left the BPS universe before FIPS codes were added, e.g. Hickory NC after 2005).
  - **The BPS universe for NC has only 157 places** (of ~550 municipalities). Most small NC towns' permits are issued by county inspections and appear only in county unincorporated totals. Consequence for NC reform measurement: town-level effects need local permit data.
  - Unincorporated areas get no 2020 population: the county total overstates them, and places straddling county lines make "county minus places" unreliable from these files.
- **Decisions:** none.
- **AI:** Claude Code wrote the code and tests and traced the unattributed permits to their cause in the raw files.
- **Open / next:** `lotline provenance` (generate `docs/data_provenance.md`, with Freddie Mac attribution); V0 report per state with holdout-safe reconciliation; tag `schemas-v1`.

### LB-032 · 2026-10-06 · Build: Data provenance generated from the download manifest
- **Question:** Can the required data-provenance document (D7) be produced from what was actually downloaded, so it can't drift from the data?
- **What I did:**
  - `lotline provenance --write` builds `docs/data_provenance.md` from `manifest.jsonl` (URLs, vintages, access dates, publisher dates, bytes, licenses as recorded) plus a `PROVENANCE` block in each adapter (title, landing page, cleaning steps, known limitations, required attribution).
  - `--check` fails if the document is stale or if any processed table came from a source with no manifest entries.
  - Fixed attribution: 2020 Census downloads had been logged under the ACS source because they share its fetch helper; they now log as `census_dec_pl` (re-recorded).
- **Inputs:** `~/lotline-data/manifest.jsonl` (pulls of 2026-10-06), adapter metadata.
- **Outputs:** `src/lotline/provenance.py`, `PROVENANCE` blocks in `adapters/national/{bps,fhfa,acs,fred,decennial}.py`, CLI `lotline provenance`, `tests/core/test_provenance.py` (59 tests passing), generated `docs/data_provenance.md` (5 datasets).
- **Findings:** The compliance check now passes D7 on generated content. Freddie Mac's attribution requirement appears in the document automatically.
- **Decisions:** none.
- **AI:** Claude Code wrote the generator, metadata and tests, and found the decennial mis-attribution while building it.
- **Open / next:** V0 report per state (coverage, nulls, BPS reconciliation that skips held-out state-years); tag `schemas-v1`.

### LB-033 · 2026-10-06 · Validation: V0 national data check for MN, NC, OH, TX
- **Question:** Do our adapters count what the publishers count (validation plan §3, V0)?
- **What I did:**
  - `lotline validate --step V0` writes `reports/<st>/V0-national.md`: BPS place sums vs Census state totals by year and size; share of units tied to a jurisdiction and share imputed; coverage and null rates of every processed table; FHFA and ACS gaps; licenses.
  - **Held-out state-years are not compared** (MN 2024–26, NC 2023+): state total minus our sum would reveal St. Paul or Charlotte by subtraction. Tested.
  - New `bps_state` adapter (Census state totals, reconciliation only) with its own provenance entry.
- **Inputs:** processed tables from LB-024 onward; Census BPS state annual files 1992–2025.
- **Outputs:** `src/lotline/validation/v0.py`, `src/lotline/adapters/national/bps_state.py`, `tests/core/test_v0.py` (65 tests passing), `reports/<st>/V0-bps-reconciliation.png`, `docs/analysis_plan.md` (draft, D-001), `reports/{mn,nc,oh,tx}/V0-national.md`, regenerated `docs/data_provenance.md`.
- **Findings:**
  - **Exact match is the wrong pass rule.** Census revises state and county totals after the annual survey (late reports, corrections; BPS methodology), so place files don't always add up. Exact matches: MN 10/32, NC 28/31, OH 20/34, TX 6/34. **Within 1%:** MN 30/32, NC 29/31, OH 34/34, TX 21/34.
  - **TX runs 1–2% high in 2003–2014**, almost all single-family, concentrated in county unincorporated rows (Denton County 2014: +2,145 units vs the county file; "Denton County Unincorporated Area" alone 2,031). For WS-TX to resolve; recorded as a known limitation.
  - All states: 1992–93 gaps of 1.5–10%, right after BPS's 1992 renumbering.
- **Decisions:** **Ben adopted the 1% rule** (2026-10-06): "within 1% of Census per compared year; larger gaps explained" replaces "match exactly". Recorded as deviation D-001 in the new draft `docs/analysis_plan.md`. Under it: **OH PASS**; MN and NC fail only 1992–93; TX fails 13 years (2003–2014 pattern). Ben also approved `matplotlib` (PSF license; deps BSD/MIT/MIT-CMU) for the reconciliation chart `reports/<st>/V0-bps-reconciliation.png`.
- **AI:** Claude Code wrote the report, traced the gaps (reported-only vs imputed, then the county files), and read Census's BPS methodology for the cause.
- **Open / next:** WS-TX explains the 2003–2014 gap; tag `schemas-v1`.

### LB-034 · 2026-10-06 · Build: Contract review and schemas-v1 freeze candidate (1.4)
- **Question:** Are the canonical tables ready to freeze for the state, engine and evidence workstreams, or would they block them?
- **What I did:**
  - A read-only sweep (Claude subagent) of BUILD_PLAN §5–6, all workstream briefs, statistical protocol §5, the validation plan, causal diagrams and MN data catalog, listing every field downstream work needs. Spot-checked the key claims against the docs.
  - Probed the contract mechanics directly and found two silent-corruption bugs: text "False"/"0" coerced to True in boolean columns, and misspelled optional columns silently dropped.
  - Schemas 1.4: new `eligible_parcels` table (the denominator, by jurisdiction × year × theme × rule version, with source and quality; protocol §5.1–5.2). `permits` allows year-only dates, unknown units and demolitions (null ≠ 0), adds ADU type, zoning at permit, floor area, application and final-date types, and a unique key. `parcels` adds a fixed land-use vocabulary and eligibility inputs (HOA, floodplain, historic, lot width, value basis, sale flags, centroid). `reforms` adds `reform_id`, status, adoption/end dates, `supersedes`, rubric fields (min lot, ADU size, stories, parking per unit, zones) and two-coder fields. `fees` adds components (water/sewer separate), basis enum, percent-of-value, dollar year, building type and a key. Jurisdiction kinds add `state` and `region`; market geo adds place and county subdivision. All booleans are nullable and reject strings; misspelled columns raise.
  - Holdout filter: year-only permits now fall back to their year, and undated rows at a held-out place are hidden. This closes a leak the new permit shape would have opened.
  - Generated data dictionary `docs/schemas.md` (`lotline schemas --write`) with a CI test that fails if it drifts.
- **Inputs:** `src/lotline/schemas.py` 1.3; docs listed above.
- **Outputs:** `src/lotline/schemas.py` (1.4), `src/lotline/validation/holdout.py`, `src/lotline/cli.py`, `docs/schemas.md`, `tests/core/test_schemas.py` and `test_holdout.py` (87 tests passing).
- **Findings:** Without the denominator table, the protocol's canonical unit (units per 1,000 eligible parcels) had nowhere to live. Deferred as additive (allowed within v1): approval days, pre-approved plans, HOA share and data-regime flags on reforms (causal diagram §7.1); tier-input flags on jurisdictions; `train_until` values in state configs. BUILD_PLAN §5.1 is now out of date; `docs/schemas.md` supersedes it.
- **Decisions:** Proposed: freeze 1.4 as `schemas-v1`. Within v1 only additive changes; anything else is v2 via `contract-change`.
- **AI:** Claude Code (with a read-only subagent) did the review, schema changes and tests; Claude verified the subagent's main claims against the source docs before acting.
- **Open / next:** Ben merges, then tag `schemas-v1` on main; start WS-MN, WS-NC, WS-ENGINE.

### LB-035 · 2026-10-07 · Build: schemas-v1 merged and tagged on main (auto-review)
- **Question:** Is the 1.4 contract (LB-034) now the frozen base the state, engine and evidence workstreams build on?
- **What I did:**
  - PR #67 (`ws/core-schemas-v1`, "schemas 1.4: contract review, freeze candidate for schemas-v1") was merged to `main` on 2026-10-07 (merge commit `3583f34`).
  - Annotated tag `schemas-v1` ("canonical table contracts frozen at schemas 1.4") was created on that merge commit and pushed to `origin`.
- **Inputs:** LB-034.
- **Outputs:** `main` @ `3583f34`; tag `schemas-v1` (github.com/cappellacci/lotline). The LB-034 files (`src/lotline/schemas.py`, `docs/schemas.md`, holdout filter, tests, regenerated `reports/<st>/V0-national.md`) are now on `main`.
- **Findings:** none new; this closes LB-034's open item.
- **Decisions:** LB-034's proposal took effect: within v1 only additive schema changes; anything else is v2 via `contract-change`. Not yet recorded as a row in the HANDOFF decisions log.
- **AI:** Recorded by the nightly review from git history (merge commit and tag); the merge and tag were done in GitHub/git, presumably by Ben.
- **Open / next:** start WS-MN, WS-NC, WS-ENGINE on `schemas-v1`; WS-TX to explain the 2003–2014 V0 gap.

### LB-036 · 2026-10-08 · Build: ArcGIS REST pager (io/arcgis.py)
- **Question:** Can every state adapter download full ArcGIS layers (most MN and NC permit and parcel sources) through one tested helper that caches, logs and snapshots each page?
- **What I did:**
  - `io/arcgis.py`: reads layer metadata. Pages with `resultOffset` ordered by object ID when the layer supports pagination; otherwise falls back to object-ID chunks (e.g. Durham's MapServer).
  - Continues correctly when the server caps a page below the requested size (`exceededTransferLimit`). Raises on ArcGIS error bodies (HTTP 200) without caching them, and on duplicate IDs.
  - Optional WGS84 geometry (centroids requested only for polygon layers; point layers reject them). Epoch-millisecond date helper.
  - Each page goes through `fetch()` into `raw/<source>/<date>/<name>/`, so rolling windows get dated snapshots and every page is in the manifest.
- **Inputs:** WS-CORE brief (IO tasks); Minneapolis CCS Permits layer for a live test.
- **Outputs:** `src/lotline/io/arcgis.py`, `tests/core/test_arcgis.py` (12 tests against a fake server; 99 total passing); kickoff plan notes (uncommitted `docs/build/kickoff-2026-10-14.md`).
- **Findings:** Live test (scratch store, not the project data dir): 7,627 of 7,627 Minneapolis permits issued since 2026-08-01, 8 pages in 8 s, no duplicates. The layer carries applicant names and addresses, so adapters must request only needed fields. `dwellingUnitsNew` is text and empty in about two-thirds of rows (unknown, not 0). `returnCentroid` is rejected by point layers (fixed).
- **Decisions:** none.
- **AI:** Claude Code wrote the pager and tests and ran the live check. **Created 2026-10-08, inside the Oct 7–14 gap the Rules don't cover**, at Ben's direction after Claude flagged Rules §3/§7(a) (organizer answer pending).
- **Open / next:** state-source registry; `build/eligible.py` skeleton.

### LB-037 · 2026-10-08 · Admin: Correction to LB-035 (who merged and tagged schemas-v1)
- **Question:** Who performed the merge of PR #67 and the `schemas-v1` tag recorded in LB-035?
- **What I did:** Corrects LB-035, whose AI line says the merge and tag were "presumably by Ben". Claude Code merged PR #67 (2026-10-07 08:44 UTC, 4:44 a.m. ET, before registration closed) and created and pushed the annotated tag `schemas-v1` on merge commit `3583f34`, both at Ben's explicit request in the session.
- **Inputs:** LB-035; the session record; `git show schemas-v1`.
- **Outputs:** this entry.
- **Findings:** none.
- **Decisions:** none.
- **AI:** Claude Code wrote this correction while folding logbook fragments (LB-036).
- **Open / next:** none.

### LB-038 · 2026-10-08 · Build: Source registry, state sources plug in without touching CORE (auto-review)
- **Question:** Can state workstreams add data sources that `lotline fetch` runs and `lotline provenance` documents, without editing shared CORE code and without any way to skip the holdout filter?
- **What I did:**
  - `src/lotline/registry.py`: national sources listed explicitly; any module in `adapters/states/<st>/` defining `SOURCE`, `TABLE`, `PROVENANCE` and `load()` is discovered as a source for that state. Half-defined modules, unknown tables, incomplete provenance and duplicate names or manifest ids are errors.
  - `lotline fetch` and `lotline provenance` now read the registry; new `lotline sources` lists sources per state.
  - Central holdout guard: after every load, `lotline fetch` re-checks permits and BPS output with `holdout.assert_no_leak` and stops with `HoldoutLeak` if held-out rows got through.
- **Inputs:** kickoff plan §1 (WS-CORE day-1 items, LB-039); LB-027, LB-036.
- **Outputs:** commit `573054f` on branch `ws/core-registry` (pushed, **not yet merged to `main`**): `src/lotline/registry.py`, `src/lotline/cli.py`, `src/lotline/provenance.py`, `src/lotline/validation/holdout.py`, `src/lotline/adapters/national/__init__.py`, `tests/core/test_registry.py`, `README.md`, fragment `logbook.d/2026-10-08-ws-core-registry.md`.
- **Findings:** per the fragment: 108 tests passing; `lotline sources`, `lotline provenance` and `lotline fetch --state MN --source bps` (32,418 rows, guard passed) behave as before.
- **Decisions:** none.
- **AI:** Claude Code wrote the registry, guard and tests (commit co-authored). **Created 2026-10-08, inside the Oct 7–14 gap the Rules don't cover**, at Ben's direction (per the fragment). Logged by the nightly review from the commit and its unfolded fragment: when folding, drop `logbook.d/2026-10-08-ws-core-registry.md` rather than adding a second entry.
- **Open / next:** merge the `ws/core-registry` PR; `build/eligible.py` skeleton + `config/params/eligibility.yaml`.

### LB-039 · 2026-10-08 · Build: Day-1 kickoff plan for the Oct 14 Coding Period (auto-review)
- **Question:** What exactly do Ben and the first three Claude Code sessions (WS-MN, WS-NC, WS-ENGINE) do on Oct 14 so each lands one small, mergeable PR on day 1?
- **What I did:**
  - §0 pre-9:01 checklist for Ben: manual exports of the Minneapolis and St. Paul rolling-window permit layers (#9), record the organizer answer on gap-week work, `gh auth switch`, three worktrees with `.env` copies, `uv sync --frozen`.
  - §1 WS-CORE day-1 items: ArcGIS pager (built, LB-036), state-source registry (built, LB-038), `build/eligible.py` skeleton (still to do).
  - §2–4 a kickoff prompt and ordered day-1 checklist per workstream: MN `metc_permits` adapter and `mn.yaml` (`train_until` for St. Paul); NC freshness checks for Durham, Raleigh adapter on a synthetic fixture, `carthage_towns.csv` research; ENGINE `config/params/` skeleton, `panels.py`, V1 benchmarks and a CPI deflator, all synthetic.
  - §5 daily rhythm (small PRs, fragments, contract changes via WS-CORE) and the freezes to plan for (St. Paul and Charlotte predictions by Nov 17; `prereg-v1` before V3).
- **Inputs:** BUILD_PLAN, workstream briefs WS-MN/NC/ENGINE, validation plan; LB-026, LB-030, LB-031, LB-036.
- **Outputs:** `docs/build/kickoff-2026-10-14.md` (177 lines; **draft, deliberately uncommitted** during the gap week; no project copy).
- **Findings:** Minneapolis CCS layer carries personal data (request only needed fields) and text unit fields that are empty in about two-thirds of rows (null, not 0). BPS covers only 157 NC places, so town-level NC outcomes need local permits. Holdout reminders written into each kickoff prompt (St. Paul 2024–26, Charlotte from 2023-06-01).
- **Decisions:** none logged; the FHFA fallback order for 75 TX counties is flagged as a decision for Ben.
- **AI:** Written in a Claude Code session on Oct 8 (mentioned in LB-036 and the registry fragment as "kickoff plan notes"); this entry was added by the nightly review from the file's content.
- **Open / next:** commit with the first PR on Oct 14 or discard (per the file); Ben's §0 checklist before 9:01 a.m. ET.

### LB-040 · 2026-10-08 · Deliverables: Plain-language "Approach and Progress" doc (auto-review)
- **Question:** How do we explain Lotline's approach and progress so far to a non-technical reader?
- **What I did:**
  - Wrote a short doc: approach and goals (three reforms on one parcel pool; "calibrate where reforms are old, apply where they aren't"; ranges and sliders; validation on held-out places; four states, MN first) and 11 dated key steps from rules intake (Sep 29) to the `schemas-v1` freeze (Oct 7).
- **Inputs:** LB-001 to LB-035 and the docs they produced.
- **Outputs:** [Lotline: Approach and Progress](https://claude.ai/code/artifact/86a0a12d-1578-4ee7-a562-82648e72f4b6) (Claude Doc, dated 2026-10-08, Ben as author).
- **Findings:** none new; a summary of existing work. It does not yet mention the ArcGIS pager or source registry (LB-036, LB-038).
- **Decisions:** none.
- **AI:** Presumably drafted by Claude in a session that didn't log itself; intended audience (team, mentors, a submission write-up) isn't stated in the doc. Logged by the nightly review from the doc's content.
- **Open / next:** keep it in step with the logbook if it is meant to be shared.

### LB-041 · 2026-10-14 · Admin: Official Rules, Handbook and Data List PDFs reviewed
- **Question:** Do the official PDFs Ben added (`rules and resources/`) change anything in HANDOFF, and what does the new Official Data List mean for our state choice?
- **What I did:**
  - Extracted and read all three PDFs in full (Rules 12 pp., Handbook, Data List) and checked them against HANDOFF §2–4 (built from the web pages on 2026-09-29). Extracted the Data List's link targets.
  - Wrote the review: no conflicts; 8 under-weighted points (N1–N8); Data List table set against our earlier state scores; 6 proposed actions.
  - HANDOFF: sources line, a status row, new checklist items **S9** (four questions per scenario) and **S10** (no parcel-level precision in outputs), D7 extended (small-cell risk; per-state "data available vs. used"), "last verified" moved to 2026-10-14.
  - Added `rules and resources/` to `.gitignore`.
- **Inputs:** the three PDFs; HANDOFF; `lotline-state-reassessment.md`; `lotline-data-availability.md`; webinar notes (2026-10-05).
- **Outputs:** `docs/research/rules-pdfs-2026-10-14-review.md` (project: `research/rules-pdfs-2026-10-14-review.md`); `HANDOFF.md`; `.gitignore`. All uncommitted (written ~4 a.m. ET, before the Coding Period opens at 9:01).
- **Findings:** Handbook says parcel-level precision scores lower and wants direction, magnitude, uncertainty and drivers over precise forecasts. Rules §8 asks for what data was available in the state vs. used. The Data List covers AZ, CT, OR, HI, PA, TN, UT, VA, WI, RI, NH, none of MN/TX/NC/OH. Rules still silent on the Oct 7–14 gap.
- **Decisions:** none taken; proposed for Ben: "parcels in, regions out" as a design rule; WI as a portability state (in place of or alongside OH).
- **AI:** Claude (Cowork) read the PDFs, wrote the review and edited HANDOFF; checks were text comparisons against HANDOFF and the earlier research docs.
- **Open / next:** Ben to decide N1 rule and WI; template/reference-example diff once Platform access arrives (E5); commit these files after 9:01 a.m. ET with the day-1 PRs.

### LB-042 · 2026-10-14 · Deliverables: Simulated judging panel (`/judge`)
- **Question:** How do we get expert, evidence-based feedback on Lotline against each Rules §8 criterion, early and repeatedly, from code as well as docs?
- **What I did:**
  - Built a shared rubric (`RUBRIC.md`): sources of truth, 0–10 anchored scale with **Today** and **Ceiling** scores, evidence tags ([ran]/[read]/[inferred]), finding format with points at stake, an ownership matrix to avoid double-counting, and guardrails (read-only, temp clones, no downloads, holdouts untouched).
  - Wrote seven Claude Code subagents, each with a persona, reading order, signature probes and anchors: gatekeeper (T/D/S gates, timing, checker audit), transparency (trace-a-number, assumption census, docstring coverage, reading grade), replicability (clean clone, 5-mutant check, coverage, swap-a-state, dependency audit), usability (Streamlit AppTest task scripts, stress inputs, labels audit), methodology (Handbook definitions, feasibility/additionality/overlap, equation↔test map, property checks), policy insight (memo test, driver decomposition, sparse-data bonus), head judge (moderation, weighted total, points-per-hour action plan, trend).
  - `/judge` command runs gatekeeper + five judges in parallel, then the head judge, into `reports/judging/<run-id>/` (gitignored).
- **Inputs:** Rules §7–8 and Handbook (web, 2026-10-14); HANDOFF §2–3; rules-PDF review N1–N8; BUILD_PLAN; CLAUDE.md.
- **Outputs:** `judging-panel/{agents,commands,judging}/` (staging copy; Ben moves it into `.claude/`, which remote tools can't write); `CLAUDE.md` "Judging panel" section; `.gitignore` (`reports/judging/`).
- **Findings:** none on the entry yet; first run pending.
- **Decisions:** none.
- **AI:** Claude (Cowork) wrote the rubric, agents and command from the Rules text and repo layout; checked that frontmatter parses as YAML and that referenced repo paths exist. Not yet run end to end.
- **Open / next:** install into `.claude/`, run `/judge`, review the first SCORECARD.

### LB-043 · 2026-10-14 · Admin: Align the repo with the organizers' starter template
- **Question:** What does the official starter template (`theturnout/housing-challenge-starter-template`, published 2026-10-13) expect that Lotline doesn't have yet?
- **What I did:**
  - Read every file in the template and compared it with the repo, HANDOFF §5 and `compliance_check.py`. The eligibility gates, doc outlines, page limits and fee baseline already match; `compliance_check.py --github` showed 0 FAIL.
  - Turned on **private vulnerability reporting** (the template's setup guide, step 5; it was off) through the GitHub API.
  - README: added a Setup / Run / Test **command contract** table, a **Documentation** section that links our docs under the template's titles, and a **Team** section (Ben confirmed the roster). Added `SECURITY.md`, `NOTICE` (Apache-2.0; no third-party attributions) and `.github/PULL_REQUEST_TEMPLATE.md` carrying the CLAUDE.md commit checklist.
- **Inputs:** https://github.com/theturnout/housing-challenge-starter-template (commit `5864b73`); `HANDOFF.md` §5; `compliance_check.py --github`.
- **Outputs:** `README.md`, `SECURITY.md`, `NOTICE`, `.github/PULL_REQUEST_TEMPLATE.md`; repo setting: private vulnerability reporting on.
- **Findings:** The template says copyleft dependencies must be "flagged and resolved", which is stricter than our written justification for `certifi` (MPL-2.0); worth asking the organizers. The template's scenario-comparison stub leaves out ADUs, but its own spec lists them, so `adu` stays valid. The README Run row is a placeholder until the Phase 5 app exists. `docs/disclosures.md` still says "External APIs: none", though `fetch` calls the Census API (key) plus BPS and FHFA downloads.
- **Decisions:** Proposed: add private vulnerability reporting to HANDOFF T6 and to `compliance_check.py --github`.
- **AI:** Claude Code compared the template and wrote these files; checked by `python compliance_check.py` (0 FAIL) and a GitHub API read-back of the vulnerability-reporting setting. Written before 09:01 ET on 2026-10-14; committed only after the Coding Period opened.
- **Open / next:** fix the External APIs disclosure; replace the README Run row when the app lands.

### LB-044 · 2026-10-14 · Build: Eligible-parcel rule v1.0 (the denominator) and first parameter file
- **Question:** Can every state produce the protocol's denominator (eligible parcels per jurisdiction-year, stored apart from permits) from parcels where they exist and from the ACS where they don't?
- **What I did:**
  - `build/eligible.py` (rule 1.0): ADU-eligible = existing single-family house, ≤1 unit where known, lot ≥ floor, not excluded (HOA, floodplain, historic district where known); missing-middle adds single-family-only zoning. Unknown inputs are kept but flagged as *assumed*, and the assumed share sets `denominator_quality`. `from_parcels` writes `eligible_parcels` per jurisdiction, vintage and theme.
  - `from_acs` fallback: ACS one-unit detached homes (B25024_002) for places and townships, always quality `low` (protocol §6).
  - `config/params/eligibility.yaml`, the first parameter file: lot floors 0 (Handbook definitions set none), exclusion toggles, quality bands, each with a source.
- **Inputs:** BUILD_PLAN §5.3; statistical protocol §5.1–5.2, §6; Handbook ADU and missing-middle definitions; WS-NC brief.
- **Outputs:** `src/lotline/build/eligible.py`, `config/params/eligibility.yaml`, `tests/core/test_eligible.py` (10 tests, incl. a parcel-by-parcel hand-worked example; 109 total passing).
- **Findings:**
  - First real-data run caught a double count: ACS **county** rows matched unincorporated-area IDs, giving each the whole county's homes (NC came to 4.1M, more than the state has). Fixed: places and county subdivisions only; tested.
  - After the fix, permit-issuing places and townships hold **MN 78%, TX 70%, OH 64%, NC 32%** of each state's one-unit detached homes (ACS 2019–23). NC's low share matches its 157-place BPS universe: **a statewide total needs a "rest of county" denominator for unincorporated areas**, or most of NC's single-family stock drops out. For WS-ENGINE.
- **Decisions:** Proposed: lot-size floors stay 0 (Handbook) until a sourced sensitivity range exists; quality bands 5% / 50% to confirm at pre-registration.
- **AI:** Claude Code wrote the rule, parameters and tests, ran the real-data check and fixed the double count it revealed. Built in a separate worktree (`../lotline-ws-core`) because another session was working in the main checkout.
- **Open / next:** wire `eligible_parcels` into `lotline fetch`/`build` once the registry (#70) is merged; county-remainder denominators.

### LB-045 · 2026-10-14 · Build: eligible_parcels built by `lotline fetch` for all four states
- **Question:** Can every state get a denominator table from one command, with each jurisdiction's source and quality visible?
- **What I did:**
  - Registered `eligible` as a national build source: `lotline fetch --source eligible` builds `eligible_parcels` from processed tables, building jurisdictions or ACS first if missing.
  - One denominator source per jurisdiction (`combine`): parcels where a state has a `parcels` table, the ACS fallback elsewhere, never both.
  - V0 reports now list the `eligible_parcels` coverage with its source × quality mix.
- **Inputs:** `build/eligible.py` rule 1.0 (LB for #76), processed ACS and jurisdictions tables.
- **Outputs:** `src/lotline/build/eligible.py` (`combine`, `load`), `src/lotline/registry.py`, `src/lotline/validation/v0.py`, `tests/core/test_eligible.py` (120 tests passing), regenerated `reports/*/V0-national.md`. Data (not committed): `processed/<st>/eligible_parcels/eligible.parquet` (MN 28,636 · NC 4,710 · OH 25,910 · TX 28,472 rows, 2010–2024).
- **Findings:** All four states are currently 100% ACS fallback (quality low) until state parcel adapters land; `lotline provenance` stays OK.
- **Decisions:** none.
- **AI:** Claude Code wrote the wiring and tests and ran it on real data.
- **Open / next:** county-remainder denominators for unincorporated areas (WS-ENGINE, see #76).

### LB-046 · 2026-10-14 · Build: Rest-of-county denominators, and the Ohio village double count fixed
- **Question:** Can unincorporated county areas, where most NC permits are issued, get a denominator that covers the same ground as their permit counts, without counting any home twice?
- **What I did:**
  - `eligible.allocate_homes`: a place keeps its ACS total; a township is its ACS total minus the permit-issuing places inside it; rest of county = county total minus every permit-issuing place's in-county homes and every township's net homes. Negative remainders (sampling noise) are set to 0 and flagged.
  - `adapters/national/geoparts.py`: the Census 2020 code files show which places span counties and which aren't their own county subdivision. 2020 Census **DHC** housing units split those places by county and by township. The P.L. 94-171 file doesn't publish the township geography; the API allows no wildcards, so it's one cached request per multi-county place or relevant township, made once.
  - `lotline fetch --source eligible` now emits rest-of-county rows; the provenance document lists the new source.
- **Inputs:** ACS B25024_002 (2010–2024); Census `national_place_by_county2020.txt`, `national_cousub2020.txt`; 2020 DHC `H1_001N`.
- **Outputs:** `src/lotline/build/eligible.py`, `src/lotline/adapters/national/geoparts.py`, `src/lotline/registry.py`, `tests/core/test_eligible.py` (hand-worked Ohio-style county: jurisdictions add back up exactly to county totals), `tests/core/test_geoparts.py`; regenerated `docs/data_provenance.md`, `reports/*/V0-national.md` (125 tests passing, also with network blocked).
- **Findings:**
  - Share of each state's one-unit detached homes (ACS 2019–23) now inside a permit-issuing jurisdiction's denominator: **NC 100.0%** (was 32%), **OH 100.5%**, **MN 97.9%**, **TX 89.9%**.
  - MN and TX fall short where counties have no unincorporated BPS row (MN 15 counties, TX 200 of 254): those homes have no permit series, so leaving them out keeps numerator and denominator aligned.
  - **Ohio double count fixed:** 360 of 569 permit-issuing OH places sit inside a township's ACS count; townships now exclude them, removing **129,734** double-counted homes (2019–23). Five OH county remainders were negative (noise) and clipped, which explains the 0.5% overshoot.
- **Decisions:** Proposed: split places by 2020 housing-unit shares, fixed for all ACS years (stated in provenance limitations).
- **AI:** Claude Code designed and wrote the allocation, adapter and tests. It found the Ohio double count while designing, and found the P.L.→DHC geography gap in the first live run.
- **Open / next:** WS-ENGINE uses `eligible_parcels` with `denominator_source`/`quality`; MOE propagation for remainders (not attempted).

### LB-047 · 2026-10-14 · Build: Fix silent column loss when reading multi-source tables
- **Question:** Do processed tables built by several sources (e.g. `market_geo_year` from FHFA and FRED) read back with all their columns?
- **What I did:**
  - Confirmed a bug reported by the WS-ENGINE agent: `pandas.read_parquet(<table folder>)` keeps only the first file's schema, so FRED's `cpi_u`, `mortgage_rate` and `ppi_resid_inputs` vanished from `market_geo_year` reads.
  - Added `DataStore.read(state, table)`: reads each source file and stacks the rows with the union of columns. Switched the V0 report, the `eligible` build and the `jurisdictions` build to it. No other folder reads remain.
- **Inputs:** WS-ENGINE day-1 report (PR #80).
- **Outputs:** `src/lotline/io/store.py`, `src/lotline/validation/v0.py`, `src/lotline/build/{eligible,jurisdictions}.py`, `tests/core/test_io.py` (126 tests passing), regenerated `reports/*/V0-national.md`.
- **Findings:** Only the V0 coverage line had been affected (it under-reported `market_geo_year` columns); no model code consumed the dropped columns yet. Found before the engine's real-dollar conversion would have hit it.
- **Decisions:** Rule for all workstreams: read processed tables with `DataStore.read`, never `read_parquet(folder)`.
- **AI:** The WS-ENGINE subagent found and reported the bug; Claude Code (WS-CORE) verified it on real data and wrote the fix and test.
- **Open / next:** WS-ENGINE can replace its `panels.read_market` workaround with `DataStore.read`.

### LB-048 · 2026-10-14 · Build: County-to-metro (CBSA) crosswalk; provenance works across parallel branches
- **Question:** Where a county has no FHFA house-price index, what is the next-best index, and can every branch keep its provenance check passing while three workstreams share one data folder?
- **What I did:**
  - New adapter `adapters/national/cbsa.py`: the official OMB July 2023 county → CBSA delineation (Census "List 1", public domain). All 175 FHFA CBSA codes in MN, NC, OH and TX match it.
  - Schemas 1.5 (additive): `jurisdictions.cbsa_code` and `cbsa_type` (metro/micro), filled from each jurisdiction's county. Data dictionary regenerated.
  - Provenance: downloads by another worktree's unmerged adapter (e.g. the MN/NC agents' `metc_residential_permits`, `raleigh_permits`) are left out of the document and named as notes; processed files from unregistered sources are skipped with a note. The check still fails if a registered table depends on an undocumented download.
- **Inputs:** Census delineation `list1_2023.xlsx`; FHFA CBSA codes; WS-ENGINE decision 1 (PR #80).
- **Outputs:** `src/lotline/adapters/national/cbsa.py`, `src/lotline/schemas.py` (1.5), `src/lotline/build/jurisdictions.py`, `src/lotline/registry.py`, `src/lotline/provenance.py`, `src/lotline/cli.py`, `docs/schemas.md`, `docs/data_provenance.md`, `tests/core/test_cbsa.py`, `tests/core/test_provenance.py` (130 tests passing).
- **Findings:** Jurisdictions in a CBSA: MN 65%, NC 83%, OH 85%, TX 80%. Counties lacking a 2024 county HPI: MN 1, NC 2, OH 0, **TX 56**; the CBSA index covers 11 of TX's 56. The other 45 are rural: their best fallback is FHFA's state "non CBSA" series. Proposed engine chain: **county → CBSA → state non-CBSA → state**.
- **Decisions (Ben, 2026-10-14):** (1) build the county→metro crosswalk from official open files (done here); (3) the Handbook's $50k fee is in **2025 dollars**; (4) ADU net-new share 0.65 (0.50–0.80; E039, E051, E052), displacement 0.25 (0–0.50) and completion factor 0.90 (0.85–0.95) accepted as labelled assumptions, to become **user-tunable controls** in the app later. Open: (2) which calendar year an ACS 5-year estimate stands for (recommended: end year, carry the latest forward); sourcing the completion factor from the Census Survey of Construction.
- **AI:** Claude Code verified the FHFA code match, wrote the adapter, schema change, provenance fix and tests, and ran them on real data.
- **Open / next:** WS-ENGINE: fallback chain in `panels.py`; `DataStore.read` instead of its `read_market` workaround.

### LB-049 · 2026-10-14 · Admin: Correction to LB-026 (Carthage amicus towns unverified)
- **Question:** Is the list of seven towns recorded in LB-026 as amicus filers in *Quality Built Homes v. Town of Carthage* supported by the opinion?
- **What I did:** Corrects LB-026. That entry said "Amicus municipalities were Apex, Concord, Holly Springs, Jacksonville, Kannapolis, Surf City and Winston-Salem". The claim came from a web-search tool's summary on 2026-10-06, not from the opinion. On 2026-10-14 the WS-NC agent read the 2016 opinion (369 N.C. 15) and found no municipal amici listed. Claude Code then searched for any source tying those towns to an amicus filing and found none; the opinion pages (Justia, CourtListener) didn't serve readable text to automated fetches.
- **Inputs:** LB-026; WS-NC day-1 report (PR #83); web searches 2026-10-14.
- **Outputs:** this entry. `config/reforms/nc_carthage_towns.csv` (PR #83) already marks those seven rows low confidence.
- **Findings:** Treat the seven-town list as **unverified**. The UNC EFC rate tables (2006, 2009, Jan 2015) do show capacity fees for those towns, so they remain candidates, but not as amici.
- **Decisions:** none.
- **AI:** Claude Code recorded an unverified search summary as fact in LB-026; this entry corrects it. Lesson applied: legal and factual claims are checked against the primary document before logging.
- **Open / next:** Ben chooses the V6a treatment-list source (WS-NC decision 3).

### LB-050 · 2026-10-14 · Build: WS-NC day 1, Raleigh permits adapter, Durham freshness, Carthage town list draft
- **Question:** Is Durham's permit feed still updated, can Raleigh's permit layer be turned into canonical `permits` with honest unit counts, and can the *Carthage* town list be sourced from the UNC EFC fee tables?
- **What I did:**
  - Durham: re-queried the webgis2 MapServer (still times out from this network), then searched ArcGIS Online and found the city's hosted copy (`services2.arcgis.com/.../Inspections/FeatureServer/12`, "All Building Permits"). Checked count, newest `ISSUE_DATE` and edit date. Inspected "Active Building Permits" (`Permits/FeatureServer/13`).
  - `src/lotline/adapters/states/nc/raleigh_permits.py`: Open Raleigh Building Permits FeatureServer through the ArcGIS pager with an explicit non-personal field list; type from `censuslandusecode`; city ADU flag → `ADU`; `missing_middle` → `reform_flag_raw`; units repair rule (reported only if it fits the type code, else derived from the code, else null); demolitions; holdout filter. Tests on a synthetic fixture in `tests/states/nc/`.
  - Live pull (184,524 records, 177,473 issued permits kept) and comparison with the Census BPS Raleigh row, 2008–2025.
  - Carthage: read the 2016 opinion's counsel list (case.law) and the EFC Jan 2015 per-utility connection-fee tables (Wayback copy; extracted text locally with a throwaway pypdf, not a project dependency).
- **Inputs:** Open Raleigh Building Permits layer; Durham ArcGIS Online items; `processed/nc/bps_place_year`; 2020 Census place list (`raw/census_dec_pl`); EFC 2015 memo and tables; 369 N.C. 15; LB-026, LB-031.
- **Outputs:** `src/lotline/adapters/states/nc/raleigh_permits.py`, `tests/states/nc/test_raleigh_permits.py`, `config/states/nc.yaml` (3 sources with notes), `config/reforms/nc_carthage_towns.csv` (8 rows, draft), `docs/data_provenance.md` (regenerated). Data (not committed): `processed/nc/permits/raleigh_permits.parquet`.
- **Findings:**
  - **Durham is fresh, not stale.** The hosted "All Building Permits" layer has 93,180 records, `ISSUE_DATE` 2007-10-22 to 2026-10-09, data last edited 2026-10-14; the 2024-11-13 date on the Hub items is item metadata. "Active Building Permits" is a status-based rolling window (6,910 open permits, no dates), not needed while the full layer is fresh.
  - **Raleigh matches BPS closely through 2023** (SFD+TH permits vs BPS 1-unit buildings within ~5%; 5+ units usually within 10%, at most ~20% under), except BPS 2019 (380 vs 930 local), which looks like a BPS-side gap. **From 2024 `housingunitstotal` is empty**: 1-4 unit counts are derived from the type code, but 5+ unit permits have unknown units (226–350 known vs ~3,300 BPS units a year), so 2024+ multifamily units are missing, not zero. The catalog's "2013 anomaly" did not reproduce in new-dwelling totals.
  - **Carthage list:** the 2016 opinion names no municipal amici (only Leading Builders of America, NC Home Builders Association, NC Water Quality Association), so LB-026's seven-town "amicus" list is unsourced. All seven had capacity-type fees in the EFC Jan 2015 table; no NC 2017/18 per-utility table was found (the "2018 Tap and Impact Fee Tables" PDF is New Hampshire). The EFC table also misses plat-stage impact fees like Carthage's own.
- **Decisions:** proposed in the PR: (1) Durham uses the hosted FeatureServer, recorded fresh; (2) Raleigh 2024+ MF5 units stay null until a reviewed description parser (`units_confidence=inferred`) is approved; (3) the V6a treatment definition needs a post-ruling fee source before the town list can be trusted.
- **AI:** Claude Code (WS-NC instance) ran the queries, wrote the adapter, tests and CSV, and checked the adapter against BPS totals. Every CSV row cites its source; amicus status is marked unverified.
- **Open / next:** Durham adapter (filter to city via PIN or spatial join); parse 5+ unit counts from Raleigh descriptions; find a 2017/18 NC fee source (EFC rates dashboard data, the 2019 EFC SDF report, or town fee schedules); Carthage II (2018) counsel list for municipal amici.

### LB-051 · 2026-10-14 · Build: WS-MN day 1, Met Council permits adapter
- **Question:** Can the Met Council residential permit ledger (7-county metro) feed the canonical `permits` table, holdouts removed, and do its ADU and DTQ counts look like the published figures?
- **What I did:**
  - Found the real download: the Geospatial Commons page now redirects to an ArcGIS Hub item whose feature layer (`arcgis.metc.state.mn.us/.../Other_Structure_Public/FeatureServer/0`) Met Council recommends; the file GDB alternative would need a GDAL dependency, so it is not used.
  - Built `metc_permits` (registry source): SFD/ADU/TH/DTQ/MF5 kept whole; `RES_PERMIT_TYPE` ledger codes → `units_new`/`units_removed`, demolition and conversion flags; year-only dates; place/township GEOIDs from FIPS codes; PINs as county FIPS + local PIN; personal fields (address, owner name, notes) never requested; `holdout.apply` before validation.
  - 12 contract tests on a 20-row synthetic fixture (held-out St. Paul 2024/2025 rows vanish, year-only, DTQ, unknown units, PIN forms, pager path with a mock server).
  - Live fetch (`lotline fetch --state MN --source metc_permits`) and provenance section.
- **Inputs:** Met Council Residential Permits layer (public domain), metadata page (code definitions), `processed/mn/jurisdictions`.
- **Outputs:** `src/lotline/adapters/states/mn/metc_permits.py`, `tests/states/mn/`, `config/states/mn.yaml` (source + `train_until`), `docs/data_provenance.md`.
- **Findings:**
  - 2025 is already posted (data run 2009–2025). 114,363 rows after the holdout filter; 98.3% of rows match a jurisdictions GEOID (rest: Carver/Scott townships and a few special areas missing from the jurisdictions table).
  - ADU recording break (C32): no ADU rows 2009–2013, one in 2014, then 24–38 a year from 2016. Metro ADUs 2016–24: 279 (published ≈300; St. Paul 2024 excluded by the filter).
  - Minneapolis ADUs 2016–22 in Met Council: 106, against 232 published by the city (TCB 2023): Met Council likely undercounts Minneapolis ADUs.
- **Decisions:** (proposed) gain rows carry `units_removed=0` and loss rows `units_new=0` (ledger, other side is 0 by construction); missing UNITS → both null.
- **AI:** Claude wrote the adapter, fixture and tests; checked by the contract tests, ruff, full pytest, `compliance_check.py` (0 FAIL) and a live run with the central `HoldoutLeak` check. No St. Paul 2024–26 outcomes were printed or summarized.
- **Open / next:** jurisdictions table lacks ~24 metro county subdivisions (WS-CORE); Minneapolis ADU gap vs city count for V0; `mpls_permits` and `stpaul_permits` snapshots; manual CSV import once `~/lotline-data/manual/` exists.

### LB-052 · 2026-10-14 · Build: Jurisdictions covered only by local permit data (in_bps flag)
- **Question:** How do places that a state's own permit source covers, but the Census BPS doesn't (WS-MN: 24 Met Council county subdivisions), get into the jurisdictions table without breaking BPS-based denominators?
- **What I did:**
  - Schemas 1.6 (additive): `jurisdictions.in_bps`. BPS places are `True`; places only a local permit source reports are added with `False`, named and populated from the 2020 Census. A GEOID the Census doesn't know is skipped with a warning, never invented.
  - `jurisdictions.load` reads the state's processed `permits` table for those GEOIDs (rerun after adding a permit source).
  - `eligible.allocate_homes`: county remainders subtract only BPS-universe jurisdictions, because BPS files a local-only township's permits under its county. Local-only places still get their own denominators for local-source rates.
- **Inputs:** WS-MN day-1 report (PR #85); processed Met Council permits.
- **Outputs:** `src/lotline/schemas.py` (1.6), `src/lotline/build/jurisdictions.py`, `src/lotline/build/eligible.py`, `docs/schemas.md`, `tests/core/test_jurisdictions.py`, `tests/core/test_eligible.py` (154 tests passing).
- **Findings:** MN gains 22 local-only townships (Carver and Scott County); Met Council rows matching a jurisdiction rise from **98.3% to 99.9%**. BPS-universe denominators are unchanged (MN 97.9%, NC 100.0%, OH 100.5%, TX 89.9% of one-unit detached homes). Two Met Council codes (2703719358, 10 rows; 2713959356, 129 rows) aren't in the 2020 Census code files, likely Fort Snelling and the Shakopee Mdewakanton Sioux Community under newer codes; skipped and named.
- **Decisions:** Rule for the engine: aggregate within one universe (BPS or a local source), never across both; `in_bps` makes that possible.
- **AI:** Claude Code designed the universe rule, implemented and tested it, and ran it on real data.
- **Open / next:** map the two unknown codes if WS-MN finds their Census equivalents.

### LB-053 · 2026-10-14 · Build: Engine day 1 — parameter files, jurisdiction-year panel, V1 benchmarks, real dollars
- **Question:** Can the engine read every number from sourced config, put permits next to their denominator without ever storing a rate, and score the two benchmarks the V1 baseline must beat?
- **What I did:**
  - `config/params/`: `aggregate.yaml` (ADU net-new share 50–80%, displacement 0–50%, completion 0.85–0.95), `fees.yaml` (Handbook $50k and −50%, land capture λ 0.25–0.75, elasticity ε 0.5–3), `baseline.yaml` (5-year horizon, 3-year benchmark mean), `money.yaml` (2025 dollars). Each cites the research doc and E-ids; range-only sources use the midpoint as central value, and the notes say so.
  - `build/panels.py`: (state, geoid, year) panel from BPS (units by size class, total and reported-only; BPS rows sharing a GEOID summed), `eligible_parcels` for one explicit theme and rule version (with source, quality, tier), national CPI-U / mortgage rate / PPI and FHFA HPI by county (optional state fallback, `hpi_geo` says which). `load` re-checks the holdout filter on BPS.
  - `model/baseline.py`: last-k-year mean and OLS linear trend (floored at 0), pure functions of history up to the forecast origin; `model/money.py`: deflator `nominal × index[2025] / index[year]`.
- **Inputs:** WS-ENGINE brief; kickoff §4; schemas-v1; protocol §5.9–5.10 and §6; methods review §3b–3c, §5; fees causal diagram; validation plan V1; LB-030 (CPI-U 2025 = 322.19), LB-044–LB-046.
- **Outputs:** `config/params/{aggregate,fees,baseline,money}.yaml`, `src/lotline/build/panels.py`, `src/lotline/model/{baseline,money}.py`, `tests/model/` (28 tests, 152 total passing).
- **Findings:**
  - Reading `processed/<st>/market_geo_year/` whole with pandas keeps only the first file's columns and silently drops FRED's `cpi_u`, `mortgage_rate` and `ppi_resid_inputs`. `panels.read_market` reads file by file; the shared IO helper should too (for WS-CORE).
  - Read-only shape check on real processed tables: panels build for all four states with no duplicate keys; the denominator covers ~45% of BPS rows (2010–2024 ACS years only) and HPI 88% (TX) to 99.8% (OH).
- **Decisions:** Proposed: HPI fallback order (county only by default; state optional; CBSA needs a county→CBSA crosswalk); ACS 5-year end year used as the denominator's calendar year; dollar year of the Handbook's $50k.
- **AI:** Claude Code wrote the parameter files (sources checked against `docs/research/`), the panel, benchmarks, deflator and tests; every equation has a hand-worked example in its test docstring. Synthetic fixtures only; real tables read once, read-only, to check shapes.
- **Open / next:** sources for formalization share, trend fit window and revenue-replaced toggle; ACS covariates in the panel; the real baseline model (V1).

### LB-054 · 2026-10-14 · Build: Type-specific completion factors measured from Census data
- **Question:** What share of permitted units is actually completed, and does it differ by building type enough to matter for the ADU and missing-middle scenarios?
- **What I did:**
  - `model/completion.py`: long-run ratio of completions (years start+lag to end+lag) to permits (start to end), from monthly NSA Census New Residential Construction series via FRED; hand-worked tests.
  - `scripts/dev/completion_factors.py` downloads the series through the IO layer (manifest-logged) and prints the ratios, so the parameters can be recomputed by anyone.
  - `config/params/aggregate.yaml`: the placeholder `completion_factor` 0.90 (0.85–0.95) replaced by `completion_factor_single_family` 0.97 (0.95–1.0; also ADUs), `completion_factor_multifamily` 0.80 (0.74–0.88; missing middle) and `completion_factor_all` 0.93 (0.89–0.96; baseline), each citing its series and measured values.
- **Inputs:** FRED PERMITNSA, COMPUTNSA, PERMIT1NSA, COMPU1UNSA, PERMIT24NSA, PERMIT5NSA, COMPU24UNSA, COMPU5MUNSA (pulled 2026-10-14).
- **Outputs:** `src/lotline/model/completion.py`, `scripts/dev/completion_factors.py`, `config/params/aggregate.yaml`, `tests/model/test_completion.py`, `tests/model/test_params.py`, FRED provenance note, regenerated `docs/data_provenance.md`.
- **Findings:** Completions per permitted unit, windows 1990–2019 / 2000–2019 / 2010–2022: all units 0.96 / 0.93 / 0.91; single-family 1.04 / 1.02 / 1.03 (above 1: non-permit areas and townhouse classification); 2+ units 0.77 / 0.74 / 0.79 (a lower bound for the same reason). Using one factor would overstate missing-middle output by about 15–20%.
- **Decisions (Ben, 2026-10-14):** type-specific completion factors from Census data replace the placeholder. Also confirmed: an ACS 5-year estimate counts for its last year (2019–23 → 2023), with the newest estimate carried forward to unpublished years.
- **AI:** Claude Code (coordinating session) measured the ratios, wrote the module, script, parameters and tests on the WS-ENGINE branch, and checked the script reproduces the measured values.
- **Open / next:** the engine uses the type-specific factor per scenario (ADU → single-family, missing middle → multifamily, baseline → all).

### LB-055 · 2026-10-14 · Build: Engine panel follow-ups: HPI fallback chain, ACS carry-forward, shared reader, completion factor by type
- **Question:** Can the jurisdiction-year panel apply Ben's Oct 14 decisions so every row has a house-price index and a current denominator, with each choice visible?
- **What I did:**
  - HPI fallback chain (decision 1): county → the county's metro/micro area (`jurisdictions.cbsa_code`, #82) → FHFA's state "non CBSA" series (`cbsa:000SS`) → state; `hpi_geo` records which.
  - ACS convention (decision 2): an estimate counts for its last year; years after a jurisdiction's newest estimate carry it forward (never backward); new `denominator_year` column.
  - Panel reads through `DataStore.read` (#81); the `read_market` workaround is removed.
  - `model/completion.factor_key`: single-family, townhouse and ADU → single-family factor; 2+ unit types → multifamily; else all units; scenarios adu / missing_middle / baseline mapped accordingly.
- **Inputs:** PR #80 day-1 engine; decisions logged in LB fragments for #82 and the completion factors.
- **Outputs:** `src/lotline/build/panels.py`, `src/lotline/model/completion.py`, `tests/model/test_panels.py`, `tests/model/test_completion.py` (187 tests passing).
- **Findings:** Real data, 2015–2025: every panel row now has an HPI. TX uses the metro level for 178 rows and the non-CBSA series for 663; MN/NC/OH need the non-CBSA series for 17/25/10. 2025 rows with a denominator: 100% MN/NC/OH, 98% TX (via carry-forward). No duplicate keys.
- **Decisions:** none new (applies decisions 1 and 2 and the completion-factor decision).
- **AI:** Claude Code (coordinating session) wrote the changes and hand-worked tests on the WS-ENGINE branch and ran the panel on real data.
- **Open / next:** model/aggregate.py uses `factor_key` per scenario; Monte Carlo over the parameter ranges.

### LB-056 · 2026-10-14 · Build: shared permit-description parser (WS-CORE)
- **Question:** Can one tested, explainable parser read unit counts, building type, ADU kind, demolition
  and conversion from free-text permit descriptions, so any state adapter can fill gaps such as Raleigh's
  2024+ multifamily permits with no unit count?
- **What I did:**
  - Wrote `parse_description(text) -> PermitTextFacts` (standard-library `re` only): named, commented
    phrase rules for counts ("48 apt units", "(3) unit", "three units", "6-plex"), type words (duplex,
    triplex, fourplex, 2-4 → DTQ, 5+ → MF5, townhouse, single-family, manufactured), ADUs and their kind,
    alteration (→ 0 new units), demolition (units removed) and conversion (net units). Every value comes
    with `evidence` (rule + matched phrase).
  - Precision over recall: traps (bedrooms, stories, years, sizes, lot/building/permit numbers, "Unit 5",
    "2 HC units", "2 over 2"), project totals on one-building-of-several permits, contradictions and
    buildings named as existing or separately permitted all return None.
  - 91 synthetic test cases in `tests/core/test_permit_text.py`, each hand-checked.
  - Read-only accuracy check on Raleigh permits 2015-2023 (new construction with a plausible recorded
    count); a narrow evaluation pull (permit number, type code, units, description fields) was fetched
    through the IO layer into `LOTLINE_DATA_DIR/raw/raleigh_permits/2026-10-14/permit_text_eval/`.
    Nothing from it is in the repo.
- **Inputs:** `docs/schemas.md` (permits contract), Raleigh adapter (WS-NC), Open Raleigh building
  permits layer (descriptions). No Charlotte or St. Paul data was read.
- **Outputs:** `src/lotline/parse/__init__.py`, `src/lotline/parse/permit_text.py`,
  `tests/core/test_permit_text.py`.
- **Findings:**
  - Raleigh 2015-2023, n = 13,058: a count is returned for 61% of records with 99.9% precision. By type
    (coverage / precision): SFD 98% / 100%; duplex 88% / 98%; 3-4 units 65% / 92% (n = 20); 5+ units
    24% / 96.5% (136 of 141); ADU 88% / 100%; manufactured 90% / 100%. Building type agrees with the
    city's code in 99.9% of the 86% of records where one is returned.
  - Raleigh 2024-2025 5+ unit permits with an empty unit field: 37 of 80 (46%) get a count from the
    description. 5+ coverage is capped by the text: 61% of descriptions are cut at 100 characters and
    many name only the project and building number.
  - Main errors: a project total read as the building's count when the text doesn't say it is one
    building of several; townhouse permits are issued one per townhouse while the text gives the row
    size (so townhouse counts go to `building_units`, not `units_new`); per-unit condo permits that
    describe the whole building. Alteration permits get a positive count in 0.35%; demolitions are
    recognised in 99% and units removed match the city's code in 95%.
- **Decisions:** Proposed: (1) adapters use the parser only to fill a missing structured value, with
  `units_confidence`/`type_confidence = "inferred"`; (2) townhouse row size is not a per-permit count.
- **AI:** Claude Code wrote the parser, tests and the evaluation script (kept outside the repo), iterated
  the rules against the Raleigh error list using only general phrase patterns, and checked every test
  expectation by hand; ruff, pytest and `compliance_check.py` pass.
- **Open / next:** wire into the Raleigh adapter (WS-NC) for 2024+ 104/105 permits (needs the description
  field added to its request; it is excluded today as free text); describe the rules in the methodology
  document; try it on other jurisdictions' descriptions.

### LB-057 · 2026-10-14 · Build: WS-MN round 2, Minneapolis CCS permits adapter and V0 cross-check
- **Question:** Can the Minneapolis CCS permit layer (rolling window from Dec 2016) feed `permits` without personal data, and does it explain why Met Council shows 106 Minneapolis ADUs for 2016–22 against the city's published 232?
- **What I did:**
  - Built `mpls_permits` (registry source): explicit `out_fields` (applicant/owner names and applicant address never requested, and dropped defensively), building permits only (Res, Commercial, Wrecking), one row per permit number (about 3,700 permits repeat once per parcel), local Minneapolis dates, `completeDate` → `final_date` (final inspection) for Closed permits only, empty unit text → null, size classes from reported counts, SFD wrecks → 1 unit removed (derived).
  - ADU inference from the scope of work (no ADU flag): names an ADU, not negated/future/existing-ADU repair, existing house on the parcel, ≤1 unit reported → `ADU`, `type_confidence=inferred`, `adu_type` from the text. Audited samples of matches and misses by hand and tightened the patterns.
  - 11 contract tests on a 26-row synthetic fixture (fake names that must vanish, empty units that stay null, inferred and rejected ADUs, multi-parcel permit counted once, time-zone edge, pager path with a mock server).
  - Live: `lotline fetch` for `mpls_permits` (snapshot `raw/mpls_ccs_permits/2026-10-14/`, 157,078 raw rows → 129,832 permits) and `jurisdictions`; `lotline provenance --write`.
- **Inputs:** CCS_Permits layer and its ArcGIS item description (field definitions, CC0); `processed/mn/permits` (metc), `bps_place_year` (2743000).
- **Outputs:** `src/lotline/adapters/states/mn/mpls_permits.py`, `tests/states/mn/test_mpls_permits.py`, `tests/states/mn/fixtures/mpls_permits_synthetic.csv`, `config/states/mn.yaml`, `docs/data_provenance.md`.
- **Findings:**
  - New units 2017–25: CCS 24,598, Met Council 26,014, BPS 23,287; 1-unit 867 / 816 / 827. The three agree within a few percent most years; BPS runs below in 2022 and 2024.
  - ADUs 2017–22: CCS 135 permits (134 parcels) vs Met Council 78. CCS detached ADUs alone (64) track Met Council's year pattern; basement/attic ADUs (internal conversions) are mostly missing from Met Council. The city's 232 runs from the 2014 ordinance; CCS 2017–22 is consistent with it (2022: city 13, CCS 15).
  - The city records most ADU permits with `dwellingUnitsNew = 0`, so summing units undercounts ADUs. Empty unit fields are a Plumbing/Mechanical/Wrecking feature: only 0.4% of building permits lack them.
- **Decisions:** (proposed) ADU permits keep the city's reported `units_new` (mostly 0) per the "fill only what the source lacks" rule; Ben to decide whether ADU-typed rows should carry `units_new=1`, `units_confidence=inferred` instead.
- **AI:** Claude wrote the adapter, fixture, tests and comparison; checked by contract tests, ruff, full pytest (289 passed), `compliance_check.py` (0 FAIL), hand audit of ~50 ADU match/miss samples. No St. Paul data was touched.
- **Open / next:** shared parser does not treat "Wrecking ..." as a demolition (WS-CORE); new houses/duplexes built with an ADU (~18 permits) stay SFD/DTQ; `stpaul_permits`; V0 report.
- **Follow-up (Ben's decisions, 2026-10-14, applied by the coordinating session):** (1) an ADU permit reporting 0 or no new units gets `units_new=1`, `inferred`; (2) a new house or two-family built with an ADU gets a second `-ADU` row (1 unit, inferred, no money); if the house counted the ADU in its units, one unit moves to that row (`derived`); (3) cancelled and expired permits stay, with status in `permit_class_raw`. Minneapolis 2017–25: 194 ADU rows and 194 ADU units (187 inferred, 7 reported), including 17 new-house ADU rows; 1 house moved a unit to its ADU row.

### LB-058 · 2026-10-14 · Build: Permit-text parser reads "wreck/wrecking" as demolition
- **Question:** Does the shared parser recognise Minneapolis's demolition wording?
- **What I did:** Verified a bug reported by WS-MN (#89): "Wrecking a single family dwelling" parsed as a *new* single-family home with 1 unit, and "WRECK garage and house" wasn't recognised. Added `wreck`, `wrecks`, `wrecked`, `wrecking` to the demolition rule (rule 7), with tests.
- **Inputs:** WS-MN round-2 report.
- **Outputs:** `src/lotline/parse/permit_text.py`, `tests/core/test_permit_text.py`.
- **Findings:** "demo" and "raze" already worked; only "wreck" was missing.
- **Decisions:** none.
- **AI:** The WS-MN agent found the bug; Claude Code (WS-CORE) verified and fixed it.
- **Open / next:** none.

### LB-059 · 2026-10-14 · Validation: V1 baseline model and backtest harness
- **Question:** Can a simple, explainable baseline (recent pace, shrunk toward the county, with ranges) beat the last-3-year mean and a linear trend out of sample, with honest P10-P90 bands, in all four states?
- **What I did:**
  - `model/baseline.py`: per place and size class, the 5-year level (units per 1,000 eligible parcels) shrunk toward its county rate (state if the county has < 5 places) with Fay-Herriot weights from negative-binomial sampling variance (raised to the place's own year-to-year variance) and a moment estimate of between-place variance; P10/P50/P90 by simulation (gamma level uncertainty × resampled state cycle × negative-binomial year). Optional state momentum term (off).
  - `model/backtest.py`: V1 harness, fits ending 2016/2018/2020, forecasts to 2025 at most, scored against both benchmarks on the same place-years: MAE per 1,000 parcels (pooled and by size tercile), P10-P90 coverage (inclusive and randomized for whole-number outcomes), post-2022 bias. Placeholder reformer exclusions in `config/params/v1_excluded_places.csv`.
  - Hand-worked tests for the shrinkage weights, dispersion, cycle shocks, intervals, randomized coverage and scoring; a synthetic stationary state checks calibration (~80%) and that the model doesn't lose to the benchmarks.
- **Inputs:** processed (holdout-filtered) `bps_place_year`, `eligible_parcels` (adu theme, rule 1.0, ACS SF fallback), `market_geo_year` for MN, NC, OH, TX via `panels.load`; LB entries for the panel and benchmarks.
- **Outputs:** `src/lotline/model/baseline.py`, `src/lotline/model/backtest.py`, `config/params/baseline.yaml`, `config/params/v1_excluded_places.csv`, `tests/model/test_baseline_model.py`, `tests/model/test_backtest.py`; results table in the PR.
- **Findings:**
  - Pooled MAE beats both benchmarks for every size class (1 unit 10.18 vs 10.33 / 11.35; 5+ 2.68 vs 3.22 / 4.04), and in 41 of 48 state × window × class cells; it gains most for small places.
  - V1 fails for single-family in NC and TX: the model loses to the 3-year mean, randomized coverage is ~0.5, and it under-forecasts 2023-25 by 7-12 units per 1,000 parcels. All methods under-forecast there; summed over places, the model's mean is 70-87% of what was built. Growth the pre-period didn't show is missing from the baseline.
  - Full V1 pass in 17 of 48 cells. The "no bias" rule (|bias| ≤ 25% of MAE, proposed) fails often for 2-4 unit classes whose MAE is tiny.
- **Decisions (proposed for HANDOFF / analysis plan):** (1) score coverage for whole-number outcomes with randomized PIT coverage (inclusive coverage reads 0.9+ wherever most outcomes are 0); (2) judge bias on the model's mean, not its median; (3) sampling variance floor from a place's own history (`use_direct_variance`), adopted after the first MN run; (4) state momentum stays off (mixed: 1-unit MAE slightly better, 5+ slightly worse, 20 vs 17 cells pass, NC/TX not fixed). Note that the pre-declared spec A passes 19 cells vs 17 for the adopted spec; B was kept for its 13% lower 5+ error.
- **AI:** Claude Code (WS-ENGINE instance) wrote the model, harness, parameters and tests and ran every specification on real data: pre-declared (NB variance only), adopted (with own-history variance), state-level grouping, totals incl. imputation, momentum on, 3-year level. All are reported in the PR. Checked by the hand-worked tests and by reading place-level outliers.
- **Open / next:** a demand term for growing states (ACS household growth or HPI change, place-level damped trend), then rerun V1; a reform registry to replace the placeholder exclusions; a minimum-denominator rule for tiny townships.

### LB-060 · 2026-10-14 · Validation: V1 decisions D-002 to D-006 and a pre-declared demand specification
- **Question:** How should V1 be judged, and what's the next baseline specification, fixed before running it?
- **What I did:** Applied Ben's five decisions on PR #93: randomized coverage (D-003), bias on the mean (D-004), spec B kept with A reported (D-002), a 20-parcel scoring floor (D-005, new parameter `v1_min_eligible_parcels` and test). Wrote spec C (county household growth and house-price change, coefficients fitted on fit years only) into `docs/analysis_plan.md` as D-006 **before** any run. Reran V1 with the floor.
- **Inputs:** WS-ENGINE V1 report (PR #93).
- **Outputs:** `docs/analysis_plan.md` (D-002 to D-006), `src/lotline/model/backtest.py`, `config/params/baseline.yaml`, `tests/model/test_backtest.py`.
- **Findings:** With the floor, still 17 of 48 cells pass. The model beats both benchmarks for 2+ unit buildings (5+: 2.82 vs 3.29 and 3.94 MAE per 1,000 parcels) but is now slightly worse than the 3-year mean for single-family (10.08 vs 9.66): the demand signal is needed there.
- **Decisions:** D-002 to D-006 (Ben, 2026-10-14).
- **AI:** Claude Code (coordinating session) implemented the floor and test, reran the backtest, and drafted the plan entries Ben approved.
- **Open / next:** implement and run spec C once (D-006); Ben chooses B or C (D-007).

### LB-061 · 2026-10-14 · Build: WS-NC round 2, Durham permits adapter (city vs county) and Raleigh description fallback
- **Question:** Can Durham's hosted permit layer become canonical `permits` split between the City of Durham and unincorporated Durham County without a GIS dependency, and how many of Raleigh's unknown 2024+ multifamily counts does the shared description parser recover?
- **What I did:**
  - `src/lotline/adapters/states/nc/durham_permits.py`: hosted "All Building Permits" layer through the ArcGIS pager with an explicit non-personal field list (no comments, description, project name or project type: those hold phone numbers and e-mail addresses) plus the point geometry. Kept issued permits (not Void/Disapproved/Received); type from `BLD_Type`; `DWELLING_UNITS` kept where it fits the type, else derived or null, for new construction only; demolitions; `CO_SIGNOFF_DATE` → `final_date` (certificate of occupancy); one row per permit number; holdout filter.
  - City vs county: fetched the City of Durham corporate limits (`CoD_Boundary/FeatureServer/1`) through `fetch()` and wrote an even-odd point-in-polygon test in numpy. Permits without a point take the majority side of located permits sharing the longest 8–5 digit prefix of their normalised NC PIN, then of their parent parcel (pending plats); the rest default to the city.
  - Checked the polygon test against the server's own spatial query on 60 random points (60/60 agree) and the PIN fallback leave-one-PIN-out on located permits (99.5% agreement at 8 digits, 97% at 6).
  - `raleigh_permits.py` v1.1: adds `proposedworkdescription` (the only free-text field) and `fill_from_description`, which uses `lotline.parse.permit_text.parse_description` only to fill unknown 104/105 counts that fit the code, unknown units removed by demolitions, and the type of permits with no code, always `inferred`; `building_units` not stored; switch `USE_DESCRIPTION`.
  - Synthetic-fixture tests for both; live fetch of both sources and `jurisdictions`; regenerated provenance; `config/states/nc.yaml` marks Durham fresh (Ben's decision).
- **Inputs:** Durham hosted Inspections FeatureServer/12 and CoD_Boundary FeatureServer/1; Open Raleigh Building Permits; `processed/nc/bps_place_year`; `lotline.parse.permit_text` (#87).
- **Outputs:** `src/lotline/adapters/states/nc/durham_permits.py`, `src/lotline/adapters/states/nc/raleigh_permits.py`, `tests/states/nc/test_durham_permits.py`, `tests/states/nc/test_raleigh_permits.py`, `config/states/nc.yaml`, `docs/data_provenance.md` (regenerated). Data (not committed): `processed/nc/permits/durham_permits.parquet`, `raleigh_permits.parquet`.
- **Findings:**
  - Durham: 77,479 permits kept (70,919 city, 6,560 county); 2,132 had no point (about 1,745 placed by PIN or parent parcel, about 390 defaulted to the city). City new-construction units 2015–2025 total 38,984 vs BPS place 3719000 39,067 (ratio 1.00; years 0.74–1.32, the 5+ timing differs from BPS). SFD+TH+ADU units track BPS 1-unit within ~5% in most years but lean high (−81 to +207 a year, 9 of 11 years above), while the county side runs at 25–50% of BPS county-unincorporated 1-unit: current city limits applied to past permits count later annexations as city.
  - Raleigh: the description fills 37 of the 80 unknown 2024–25 5+ unit permits (2,194 units; 2024 21 permits/1,044 units, 2025 16/1,150). 5+ units now 1,270 (2024) and 1,500 (2025) vs BPS 3,339 and 3,317. Overall 183 rows become `inferred` (3,666 new units, 69 units removed).
- **Decisions:** proposed in the PR: (1) default for permits with no location (city vs county); (2) whether to add an annexation-date source so the city/county split uses the limits in force at issue; (3) the Raleigh parser defaults (fill-only, inferred, no `building_units`).
- **AI:** Claude Code (WS-NC instance) explored the layers, wrote the adapters and tests, ran the live pulls and checked results against BPS and the server's spatial query. It also removed 95 stale manifest entries that its own exploratory pulls had made earlier in the session (license string differed and their raw pages had been overwritten), keeping a backup.
- **Open / next:** Durham EHC flags (`PROJECT_TYPE` has "EHC Small lot", "EHC ADU" but mixes in contact details; a server-side `PROJECT_TYPE LIKE 'EHC%'` query would avoid them); Durham mixed-use apartment units (Non-Residential with units); Raleigh's remaining 43 unknown 5+ permits; V0 report.
- **Follow-up (Ben's NC decisions, 2026-10-14, applied by the coordinating session):** (1) unplaceable Durham permits (~0.5%) default to the city, now stated in provenance; (2) annexation dates deferred to an issue: city-only Durham figures lean toward the city, so V0 compares city + county with BPS until then; (3) the Raleigh parser defaults stand; (4) EHC flags are fetched server-side (`PROJECT_TYPE LIKE 'EHC%'`) and reduced at once to the code plus whitelisted components (adu, duplex, flag_lot, small_lot); the text is never stored, and a test checks no phone digits or e-mail survive. Live: 400 EHC permits (small lot 260, ADU 94; 2019–2024 peak 118 in 2022; 396 in the city). Only 6 in 2025: likely a recording change (C32), to check in V0.

### LB-062 · 2026-10-14 · Validation: V1 spec C (two demand signals) run once against spec B
- **Question:** Does the pre-declared spec C (analysis plan D-006: spec B's level × exp(β_h·g + β_p·q), with county household growth g and 3-year house-price change q, β fitted by pooled Poisson on fit years only) fix the NC/TX single-family under-forecast and pass more V1 cells than spec B?
- **What I did:**
  - `model/demand.py`: g from ACS B25003_001 (county, non-overlapping 5-year estimates, annualized), q from the FHFA index on one geography of the panel's chain (starting at the place's `hpi_geo`, walking down only when that geography lacks a year), the fit sample (expected count = spec-B level from t−5..t−1 × parcels in t), a numpy Poisson IRLS fit per state and size class, and the per-place multiplier at the origin. β_0 is estimated but not applied (implementation detail of D-006).
  - `baseline.forecast_draws` takes an optional per-place multiplier (level × m, level variance × m²); `backtest.window/run/main` take `spec` ("B" default, "C") and report the multiplier, fallback flag and betas.
  - Hand-worked tests: g and q on toy numbers (incl. the chain never mixing geographies), IRLS closed-form two-group example, IRLS recovering known betas on 40,000 synthetic Poisson draws, the multiplier on level and variance, fallback to 1, no look-ahead.
  - Ran B and C once on MN, NC, OH, TX in the same code; nothing changed after seeing results.
- **Inputs:** processed `bps_place_year`, `eligible_parcels`, `market_geo_year`, `jurisdictions` via `panels.load`; `acs_geo_year` and `market_geo_year` via `DataStore().read`; LB entries for spec B (PR #93) and D-002 to D-006.
- **Outputs:** `src/lotline/model/demand.py`, `src/lotline/model/baseline.py`, `src/lotline/model/backtest.py`, `config/params/baseline.yaml` (4 new parameters), `tests/model/test_demand.py`; results in the PR description.
- **Findings:**
  - Cells passing all three V1 criteria: B 17, C 17 of 48 (by size class B 2/5/5/5, C 2/7/5/3 for 1/2/3–4/5+ units). Pooled MAE B vs C: 1 unit 9.74 vs 9.71 (3-yr mean 9.41, trend 10.08); 5+ 2.65 vs 2.77.
  - NC/TX single-family 2023–25: under-forecast shrinks but stays (NC bias of the mean −7.5 → −6.8 per 1,000 parcels, summed mean 79% → 85% of observed; TX −10.9 → −9.5, 90% → 98%); every NC/TX single-family cell still fails.
  - Fitted betas are unstable in sign across states, windows and size classes (single-family β_h negative in MN, NC and TX 2016/2018, positive in OH); g and q are correlated. No place needed multiplier 1.
- **Decisions:** none made. Ben chooses B or C (D-007); the PR lays out both.
- **AI:** Claude Code (WS-ENGINE instance) wrote the module, tests and parameters and ran both specifications once. Checked by the hand-worked tests and by confirming spec B is unchanged when no multiplier is passed.
- **Open / next:** D-007 (B or C); single-family in NC/TX remains the main V1 failure.
- **Correction and fix (coordinating session, 2026-10-14):** CI failed on Linux (`test_multipliers_by_construction`: IRLS never converged). Causes: a coefficient-change stopping rule (1e-10) that rounding keeps from settling, and a test fixture whose price growth was household growth + 0.01 exactly (collinear with the intercept). Fixed: deviance-based convergence (R glm rule, 1e-8), least-squares steps, an explicit rank check (an unidentifiable signal is reported, not given a made-up β), and an independent fixture. The B and C figures first reported in this PR did not reproduce from its code. Rerun through `python -m lotline.model.backtest --spec B|C` (identical before and after the numerical fix): B 17/48 cells, single-family MAE 10.08, 5+ 2.82, NC/TX 2023+ single-family bias −8.00/−11.08; C 17/48, 10.01, 2.92, −7.16/−9.53. Fitted β ranges: single-family β_h −11.7 to +11.7; 2–4 units up to |66|.

### LB-063 · 2026-10-15 · Build: Baseline stays spec B; NC permits merged; NC manifest entries restored
- **Question:** Which V1 baseline do we carry forward, and can the data manifest be made whole again after the NC agent removed entries?
- **What I did:** Recorded D-007 (keep spec B; spec C stays available as `--spec C`) in `docs/analysis_plan.md` on #95, then merged #95 (spec C code, default B) and #92 (Durham permits, Raleigh description parser, Durham EHC flags) after a local trial merge confirmed the generated provenance still matched. Restored the 95 Durham download entries the NC agent had deleted from `manifest.jsonl` (which must only be appended to), reinserting them at their original positions from a backup taken before the deletion; the 3 entries logged since were kept at the end. Regenerated `docs/data_provenance.md`. Removed the merged engine, MN and NC worktrees.
- **Inputs:** #95 backtest runs (LB-062); manifest backup of 2026-10-14 18:41.
- **Outputs:** `docs/analysis_plan.md` (D-007), `docs/data_provenance.md`; `~/lotline-data/manifest.jsonl` (not in the repo).
- **Findings:** B and C each pass 17 of 48 V1 cells; C is slightly better for single-family (MAE 10.01 vs 10.08) and worse for 5+ (2.92 vs 2.82), with unstable coefficients. The restored manifest is the pre-deletion file plus the later entries (1,954 lines, all valid JSON). The 95 entries record real downloads, but their 48 file paths were downloaded again later under the same dated names, so only 1 of the 95 hashes still matches the file on disk; the later entries describe the current files. Because the provenance doc counts download entries, Durham now shows 144 files (108 MB), more than are on disk. The restored entries carry Durham's older, shorter license text, so the provenance row lists both strings.
- **Decisions:** D-007 · baseline stays spec B (Ben, 2026-10-15), recorded in `docs/analysis_plan.md`. Parser defaults confirmed (Ben, 2026-10-15): (1) Raleigh's work description is downloaded (the one free-text field; no names, addresses or comments); (2) the parser's townhouse row size (`building_units`) is not stored; (3, approved 2026-10-14) description values only fill gaps, marked inferred.
- **AI:** Claude Code (WS-CORE) wrote D-007, merged on Ben's instruction, verified `main` (364 tests, compliance 0 FAIL, provenance check passing) and checked the restored manifest line by line against the backup and the current file before replacing it, then re-hashed the restored entries' files.
- **Open / next:** a more stable demand signal for the NC/TX single-family under-forecast; a CORE "supersede" record so stale manifest entries can be marked rather than deleted, and a provenance file count by distinct path rather than by entry.

### LB-064 · 2026-10-15 · Admin: Submission form link and checklist (auto-review)
- **Question:** What exactly will we enter in the official submission form, and what must be true before Ben submits?
- **What I did:** Recorded the HackHQ submission link received from the Challenge Team on 2026-10-15 (Team Leader only) and mapped each form field (project name, description, team, repo URL, final commit SHA, demo video, slide deck PDF ≤30 slides, optional live tool URL, scenarios, states) to our answer or source with a ready/not-ready mark, plus a pre-submit checklist. The link is kept in the project doc only, not in the public repo.
- **Inputs:** Challenge Team email (2026-10-15); `HANDOFF.md` §3 manual checks; `challenge.toml`.
- **Outputs:** project doc `claude/SUBMISSION.md` (not in the repo).
- **Findings:** Deadline Dec 16, 2026, 11:59 PM ET; edits allowed until then. Only Ben submits (the submitter is treated as team lead and prize recipient). Judges evaluate the repo at the final commit SHA, so any later push means updating the SHA. Submitting early and emailing the Challenge Team gets an eligibility check; target a first full submission in early December. Still open: description, roster confirmation, Model & Assumptions and Policy Scenario Comparison docs in the repo, video, deck, benchmark state (MN recommended).
- **Decisions:** none new (target date is a plan, not a logged decision).
- **AI:** Written by a Claude session into the project; found and logged by the nightly review, which did not see the session itself.
- **Open / next:** pick the benchmark state; draft the description.

### LB-065 · 2026-10-15 · Build: Superseding stale manifest entries; provenance counts each file once
- **Question:** How do we mark download entries that no longer describe the file on disk without deleting them from the append-only manifest, and why did the provenance doc overstate file counts?
- **What I did:** Added `lotline manifest supersede` (dry run unless `--apply`; needs `--source`, a `--reason` and at least one of `--stale`, `--before`, `--path`; never supersedes the latest download of a file that is still intact on disk). Records go to a second append-only file, `manifest.superseded.jsonl`, so `manifest.jsonl` is never rewritten and older code that reads it keeps working. Provenance now counts each file once (latest entry per URL, then per path) and leaves superseded entries out. Moved `sha256_file` into `io/store.py` (still importable from `io/http`).
- **Inputs:** LB-063 (restored Durham entries); `~/lotline-data/manifest.jsonl`.
- **Outputs:** `src/lotline/io/store.py`, `src/lotline/provenance.py`, `src/lotline/cli.py`, `src/lotline/io/http.py`, `tests/core/test_manifest_supersede.py`, `docs/data_provenance.md`; `~/lotline-data/manifest.superseded.jsonl` (266 records, not in the repo).
- **Findings:** Not only Durham was overcounted: same-day ArcGIS re-pulls with a different field list rewrote the same dated page files for Raleigh, Durham and Minneapolis, and each re-pull's URL counted as a new file. Durham 144 → 50 files (108.0 → 37.7 MB), and the two other sources 159 → 80 and 225 → 132. Every entry the per-path rule drops is stale (93/93, 94/94, 79/79), and those 266 are the only stale entries in the manifest; all were superseded with a reason. Durham's older license text no longer shows.
- **Decisions:** none (proposal: a same-day re-pull with a different field list should write to a new snapshot folder rather than overwrite raw files).
- **AI:** Claude Code (WS-CORE) wrote the code and 8 tests on synthetic manifests; checked every dropped entry's hash against its file before applying; full suite and compliance check pass.
- **Open / next:** consider making the ArcGIS pager refuse to overwrite a raw file whose manifest entry came from a different URL.

### LB-066 · 2026-10-15 · Build: Raw downloads are never overwritten by a different query
- **Question:** How do we stop a same-day re-pull with a different field list from overwriting raw files that must stay exactly as downloaded (the cause of the 266 stale manifest entries superseded in #97)?
- **What I did:** Two layers. (1) `fetch()` now refuses to overwrite, or serve as cached, a raw file whose current manifest entry came from a different URL (`RawOverwriteError`, asking the caller to use another path); refreshing the same URL works as before. (2) The ArcGIS pager writes each query's pages to its own folder, `raw/<source>/<vintage>/<name>/q-<hash>/`, where the hash covers the filter, fields, geometry, page size and paging strategy; `layer.json` stays shared. Rerunning the same query reuses its cache; a different query becomes a new snapshot.
- **Inputs:** LB for `ws/core-supersede` (#97); `src/lotline/io/http.py`, `src/lotline/io/arcgis.py`.
- **Outputs:** `src/lotline/io/http.py`, `src/lotline/io/arcgis.py`, `src/lotline/io/store.py` (`latest_for_path`), `tests/core/test_io.py`, `tests/core/test_arcgis.py`.
- **Findings:** The overwrite came from `fetch()` matching its cache by URL only: a new URL found no cached copy and wrote over the existing file. The same gap could also have returned another query's file as a cached copy. No current manifest entry shares a path with another URL, so the guard doesn't trip on existing data. Snapshots already on disk keep the old layout; new pulls use query folders.
- **Decisions:** none.
- **AI:** Claude Code (WS-CORE) wrote the change and 3 new tests (plus 4 updated pager tests); 375 tests pass. Live check against Durham's city-limits layer in a scratch data folder: two field lists gave two query folders, and a rerun was served from cache (3 manifest entries, not 4).
- **Open / next:** none.

### LB-067 · 2026-10-15 · Validation: Holdout guard covers parcel rolls
- **Question:** Can a parcel roll leak held-out outcomes, and does the central guard catch it?
- **What I did:** Found that the central leak check (`assert_no_leak`, run after every `lotline fetch`) covered only `permits` and `bps_place_year`. A parcel roll of a held-out place taken after the window opens shows what was built there (land use, units, year built). Added `snapshot=True` to `held_out_mask`/`apply`: a roll dated on or after `outcome_from` is held out with no end date, and a roll with only a year is held out from that year on (strict when unsure). Registered `parcels` with the central guard (`vintage_date`, falling back to `vintage`).
- **Inputs:** `src/lotline/validation/holdout.py`; holdouts in `config/states/{mn,nc}.yaml`.
- **Outputs:** `src/lotline/validation/holdout.py`, `tests/core/test_holdout.py`.
- **Findings:** No parcels table has been built yet, so nothing on disk needed re-checking. Consequence for adapters: St. Paul parcels can come only from rolls of 2023 or earlier, and Charlotte parcels only from a roll dated before 2023-06-01; a current roll has no St. Paul or Charlotte rows.
- **Decisions:** none (proposal: parcel adapters for MN and NC call `holdout.apply(..., snapshot=True)`; round-3 briefs say so).
- **AI:** Claude Code (WS-CORE) spotted the gap while drafting the MN/NC round-3 briefs, wrote the change and 3 tests; 378 tests pass.
- **Open / next:** the same snapshot rule may be needed for `eligible_parcels` if it is ever built from a roll directly rather than from `parcels`.

### LB-068 · 2026-10-15 · Policy analysis: Texas reform CSV (WS-TX)
- **Question:** Which Texas city and state reforms change housing headroom, when did each take effect, and how do they code on the protocol §5.4 rubric?
- **What I did:**
  - Coded 14 rows in `config/reforms/tx.csv` against `schemas.Reforms`: Austin HOME phase 1, phase 2 (two coverage steps) and the 2023 parking repeal; Houston lot-size reforms (1999 urban area, 2013 citywide) and Livable Places (ADU and 3–8 unit types, 2023); San Antonio UDC ADU changes (2023); 2025 state laws SB 15, SB 840, HB 24, SB 1883, plus HB 852 (2019).
  - Opened every source URL (city pages, enrolled bill text and bill history on capitol.texas.gov, Houston's 2013 Chapter 42 implementation memo).
  - Added `tests/states/tx/test_reforms.py`: schema validation, header order, sources, GEOIDs, `supersedes` chain, hand-checked values.
- **Inputs:** `docs/research/lotline-policy-inventory.csv` (TX rows) as the starting list; sources listed per row.
- **Outputs:** `config/reforms/tx.csv`, `tests/states/tx/test_reforms.py`.
- **Findings:**
  - The 2025 ADU bill (SB 673) did not pass: it stalled on the House calendar (last action 2025-05-26). No state ADU law changes headroom.
  - SB 15 (small lots) only reaches unplatted single-family tracts of 5+ acres in large cities, so it barely touches infill; SB 840 (housing by right on commercial land) is a 2025+ confounder for large-city multifamily counts.
  - Austin's citywide parking repeal (vote 2023-11-02) lands in the same window as HOME phase 1: a confounder for the V3/V4 test.
- **Decisions:** Proposed: code treatment timing for HOME as the date applications were first accepted (2024-02-05; 2024-08-16 and 2024-11-16 for phase 2).
- **AI:** Claude found and read the sources and coded every row (single coder); the test checks the schema and values hand-read from the sources. Ben's second-coder pass is still needed.
- **Open / next:** Unsourced: HOME FAR tiers, Austin parking effective date, Houston 1998 exact date and ordinance numbers, San Antonio ADU size cap. Second coder (Ben).
- **Second coder (2026-10-18):** Ben checked 3 rows: Austin HOME phase 1 and Houston 2013 agree; San Antonio ADU adjudicated (owner occupancy confirmed; size cap 800 sq ft or 50% of the primary up to 1,600 added from the UDC text). Open: a possible later Austin change to four units.

### LB-069 · 2026-10-15 · Build: Socrata pager for city permit portals
- **Question:** Can TX and OH load Socrata-hosted permits (Austin `3syk-w9eu`, Cincinnati `uhjb-xac9`) through the same cached, logged IO layer as ArcGIS sources?
- **What I did:** Added `lotline.io.socrata.download_dataset`: SODA paging with `$limit`/`$offset` ordered by the row id `:id`, an overlap check on every page, the dataset description saved as `dataset.json`, and each query's pages in their own `q-<hash>` folder (shared `query_folder`, moved to `io/store.py`). `select` is required, so no adapter downloads every column by default (Austin's dataset holds contractor and applicant names and phone numbers). SODA error messages are surfaced. An optional `SOCRATA_APP_TOKEN` is sent but never logged.
- **Inputs:** Austin Issued Construction Permits metadata and a one-week query.
- **Outputs:** `src/lotline/io/socrata.py`, `src/lotline/io/store.py`, `src/lotline/io/arcgis.py`, `tests/core/test_socrata.py`, `.env.example`.
- **Findings:** Live check: 1,195 Austin permits issued 2024-03-04 to 03-10 in 3 pages of 500 (2.9 s); an identical rerun came from cache (4 manifest entries). `permit_class` mixes coded labels ("R- 101 Single Family Houses") with plain ones ("Residential"), which WS-TX must map. A first version could loop forever if a server repeated full pages; overlap is now checked page by page.
- **Decisions:** none.
- **AI:** Claude Code (WS-CORE) wrote the pager and 8 tests on a fake SODA server; 383 tests pass; live check in a scratch data folder.
- **Open / next:** a CKAN helper only if a source needs more than `fetch()` of a resource URL (San Antonio's CSVs don't).

### LB-070 · 2026-10-15 · Build: Columbus building permits adapter (OH)
- **Question:** Can Columbus's open permit layer give new units by year and size class that line up with the Census BPS, and can it identify ADUs?
- **What I did:** Added `columbus_permits` (ArcGIS pager, CC0 layer, server-side filter to new-structure and demolition permits, non-personal fields only). Building type from `CONST_TYPE_CODE`, the Census BPS code the city assigns; `UNITS` kept where it fits the code, else derived (SFD/TH 1, duplex 2) or null (3-4, 5+). Compared units by year and size class with `bps_place_year` for Columbus (3918000), 2010-2025.
- **Inputs:** Columbus Building_Permits FeatureServer/0 (ArcGIS item f7a785b863454d96a0fe3f5aa5368e7d); `processed/oh/bps_place_year`.
- **Outputs:** `src/lotline/adapters/states/oh/columbus_permits.py`, `tests/states/oh/test_columbus_permits.py`, `config/states/oh.yaml`, `docs/data_provenance.md`; `~/lotline-data/processed/oh/permits/columbus_permits.parquet` (29,157 permits, not in the repo).
- **Findings:** Trade and partial permits (electrical, plumbing, fire alarm, foundation-only) carry the project's Census code and unit count, so only "New Structure" permits may count as dwellings; a first pull that filtered on the code alone double-counted. With that rule, 1-unit totals match BPS within ±10% in 14 of 16 years (2012 is off by a single 433-unit townhouse typo: 726 vs 723 without it; 2015 is 13% high); 5+ units run 47-101% of BPS in the other years (unknown-unit permits and timing), and 2023 is 41% high because nine permits on one parcel each repeat a 198-unit project total. The layer has no ADU flag and no description field, so ADUs can't be identified from it.
- **Decisions:** proposed: (1) keep project-total repeats and typos as reported for now, or add a dedupe rule; (2) ADUs in Columbus need another source (zoning/ADU registry or Franklin auditor).
- **AI:** Claude Code (WS-OH) explored the layer with server-side statistics, wrote the adapter and 10 tests on a synthetic fixture, ran the fetch and the BPS comparison; full suite, ruff and compliance check pass.
- **Open / next:** `config/reforms/oh.csv`; Cincinnati permits once `io/socrata` is on main; statewide parcels.

### LB-071 · 2026-10-15 · Policy analysis: Ohio reforms CSV (Cincinnati, Columbus, Cleveland)
- **Question:** Which Ohio local reforms (2024-25) can be coded with the protocol §5.4 rubric from sources we actually opened, and does any 2024-25 Ohio state law change zoning headroom?
- **What I did:** Read the Legistar records (Cincinnati Ord. 0199-2024; Columbus Ord. 2112/2113-2024 and 2526-2025; Cleveland Ord. 347-2024), the Columbus ADU ordinance's Exhibit A (§3332.355) and fact sheet, the Cleveland FBC areas page, the APA blog on Zone In and a law-firm summary of Connected Communities; coded 8 rows into `config/reforms/oh.csv`; added a schema test.
- **Inputs:** Legistar web API (cincinnatioh, columbus, cityofcleveland); city and secondary pages listed per row in `source_url`.
- **Outputs:** `config/reforms/oh.csv`, `tests/states/oh/test_reforms.py`.
- **Findings:** Columbus ADUs are by right citywide from 2025-12-25 (computed: mayor's signature 2025-11-25 + the 30-day standard), one per single-unit lot (two in R-4), max(65% of the house, 1,000 sq ft), no parking, no owner-occupancy rule. Zone In phase 1 rezoned ~12,300 corridor parcels, effective 2024-08-29 (computed the same way). Cincinnati Connected Communities passed as an emergency on 2024-06-05; the enacted text is a scanned PDF, so its provisions are coded from a secondary summary. No Ohio state zoning mandate for 2024-25 was found, but ohio.gov sites were unreachable from this network.
- **Decisions:** proposed: second coder (Ben) spot-checks all 8 rows; confirm the computed Columbus effective dates.
- **AI:** Claude Code (WS-OH) researched and coded every row (single coder), read Exhibit A text with a temporary PDF tool, and wrote the validation test; full suite, ruff and compliance check pass.
- **Open / next:** Cincinnati distance thresholds and effective date from the enacted text; Cleveland pilot-area mapping ordinance and FBC rubric fields; Ohio HB 96 (2025) pro-housing grant program from a primary source.
- **Second coder (2026-10-18):** Ben checked 3 rows and supplied the signed Cincinnati ordinance 199-2024. Correction: its Section 6 puts the zoning changes into effect on **2024-07-01** for permit applications filed from that date (the emergency passage on 2024-06-05 only prepared for it), so all four Cincinnati rows now use 2024-07-01. Middle housing is permitted by right (subject to design standards) in three mapped designations, with no distance thresholds; the parking row now includes Middle Housing areas. Zone In adoption date set to the Council vote (2024-07-29). Columbus ADU confirmed.

### LB-072 · 2026-10-18 · Build: Registering hand-downloaded files; superseding abandoned queries
- **Question:** How do files that can only be downloaded in a browser (Travis CAD rolls behind a bot challenge; the Minneapolis and St. Paul manual exports, #9) enter the manifest, and how is a replaced query's intact raw folder kept out of provenance?
- **What I did:** Added `lotline manifest register <file> --source --url --license [--vintage]` (`DataStore.register`): links the file (or copies it across file systems) to `raw/<source>/<vintage>/`, records its sha256 with `adapter=manual_export` and the file's save time, refuses a different file under the same name and is a no-op when repeated; `DataStore.registered(source)` lists them for adapters. Added `--abandoned` to `lotline manifest supersede`, which also marks intact files but only with `--path`, for the pages of a query that was replaced (Columbus's first pull, `q-f0979caf`).
- **Inputs:** WS-TX and WS-OH round-1 reports (2026-10-15).
- **Outputs:** `src/lotline/io/store.py`, `src/lotline/cli.py`, `tests/core/test_manifest_register.py`.
- **Findings:** none beyond the design.
- **Decisions:** Ben, 2026-10-18, on the WS-OH questions: keep Columbus permits' repeated project totals and unit typos as reported for now; look for a Columbus ADU source; spot-check a sample of reform rows; leave the apartment code 401 (4-19 units → MF5) mapping as it is.
- **AI:** Claude Code (WS-CORE) wrote the change and 4 tests; 379 tests pass.
- **Open / next:** after OH #104 merges, supersede `q-f0979caf` with `--abandoned` and regenerate provenance.

### LB-073 · 2026-10-18 · Build: Pager geometry modes and retries on ArcGIS error pages
- **Question:** Can the ArcGIS pager fetch polygon boundaries (for placing parcels in cities and townships) and parcel centroids without polygons, and survive servers that fail deep pages intermittently (WS-OH request)?
- **What I did:** `download_layer(geometry=...)` now takes `False`, `True`/`"point"` (unchanged queries, so existing caches still hit), `"centroid"` (label points only, polygon layers whose server advertises `supportsReturningGeometryCentroid`) and `"polygon"` (a `rings` column). ArcGIS error bodies are retried with exponential backoff (`retries=3`) before raising; error pages are never kept. The object-ID field is always requested (added only when `out_fields` lacks it).
- **Inputs:** WS-OH round-1 report; TIGERweb Places/County Subdivisions MapServer; Ohio Statewide Parcels FeatureServer.
- **Outputs:** `src/lotline/io/arcgis.py`, `tests/core/test_arcgis.py`.
- **Findings:** Live: TIGERweb ACS 2025 Incorporated Places returned Columbus (256 rings, 18,250 vertices) and Toledo as polygons in 2.6 s. TIGERweb's MapServer silently ignores `returnCentroid` (it doesn't advertise the capability), so centroid mode now refuses such servers instead of returning empty coordinates. On the Ohio parcels layer, centroid mode returned 13,218 Vinton County parcels, 99.8% with a point (78 s). Requesting `out_fields` without the object-ID field used to crash the overlap check; no existing adapter did that.
- **Decisions:** none.
- **AI:** Claude Code (WS-CORE) wrote the change and 7 tests (382 pass); live checks in scratch data folders.
- **Open / next:** the place/township assignment helper that uses polygon mode.

### LB-074 · 2026-10-18 · Build: points to places or townships (TIGERweb ACS 2025)
- **Question:** How do we put a parcel or permit point that carries only a county field (Ohio's ~6.3M statewide parcels) into the government that permits it, fast enough for a whole state and without a GIS dependency?
- **What I did:**
  - New national source `tiger_boundaries` (`census_tigerweb_acs2025`): TIGERweb ACS 2025 layers 18 (incorporated places) and 15 (county subdivisions), queried by state through the ArcGIS pager in polygon mode, 50 polygons per page, fixed vintage folder `acs2025`. Documented-only in the registry.
  - New `lotline/geo.py` (numpy only): even-odd point-in-polygon over all rings with a vectorized scanline (points sorted by y, `searchsorted` per edge, ragged (edge, point) expansion in chunks, parity by `bincount`); `assign` (points sorted by x, each polygon scans only its strip); `place_or_township` (place, else county subdivision where `township_permits`, else None so the caller uses the county).
  - ArcGIS pager: the politeness pause is skipped for pages served from cache (a cached Ohio load took 29 s of pure sleeping; now 0.3-0.4 s).
- **Inputs:** TIGERweb Places_CouSub_ConCity_SubMCD MapServer (public domain); `config/states/*.yaml` `township_permits`.
- **Outputs:** `src/lotline/adapters/national/tiger_boundaries.py`, `src/lotline/geo.py`, `src/lotline/registry.py`, `src/lotline/io/arcgis.py`, `tests/core/test_geo.py`, `tests/core/test_arcgis.py`, `docs/data_provenance.md`.
- **Findings:**
  - Ohio: 925 incorporated places (318,236 vertices; Columbus 256 rings, 18,250 vertices) and 1,607 county subdivisions (656,821 vertices). First download 31 s + 60 s; cached loads under 0.5 s.
  - Known points: downtown Columbus → 3918000, Upper Arlington → 3979002 ("Upper Arlington city"), a rural Franklin County point → 3904963254 (Pleasant township), a Holmes County point → 3907570156 (Salt Creek township).
  - Throughput: 100,000 random points in Franklin County's bbox: Columbus alone 0.04 s (~2.4M points/s), all Ohio places 0.11 s; 6.3M clustered synthetic points statewide through `place_or_township`: 7.1 s, ~1.1 GB peak memory. A full Ohio parcel run takes seconds, not hours.
- **Decisions:** Proposed: boundaries are the ACS 2025 (Jan 2025) vintage for every year; CDPs excluded; boundary points follow the half-open even-odd rule (no tolerance).
- **AI:** Claude Code (WS-CORE) wrote the adapter, geometry module and tests. Checked against a pure-Python reference ray cast on 2,000 random points with a concave star, a hole and a separate ring (forcing tiny chunks), synthetic hole/enclave/multipolygon/boundary cases, a fake TIGERweb server, and the live Ohio known points above.
- **Open / next:** WS-OH can call `lotline.geo.place_or_township` on parcel centroids; MN/NC/TX parcel layers can reuse it. Annexation timing near edges is not modeled.

### LB-075 · 2026-10-14 · Admin: One copy of every doc: the repo (replaces the project ↔ repo sync rule)
- **Question:** Since Cowork works from the same folder as the repo (`~/Engineering/Lotline`), is the two-copy sync rule (LB-025) still needed?
- **What I did:**
  - Confirmed `~/Engineering/Lotline` and the repo are the same folder (case-insensitive APFS, same inode), and that the six project-mapped files changed since Oct 6 were already current there.
  - Replaced CLAUDE.md's "Project ↔ repo sync" section with "One copy: this repo": each doc lives once at its repo path; no mirror folders; any online claude.ai Project copy is a read-only reference.
  - New rule for sessions working directly in the main checkout (Cowork, nightly review): commit via a PR before the session ends, and log as fragments in `logbook.d/`. Today the main checkout held uncommitted work during branch changes, and direct `LOGBOOK.md` edits collided with fragment folds three times.
  - Matching cleanups: the BUILD_PLAN §7.3 Cowork line; `merge_logbook.py` no longer writes a second `claude/LOGBOOK.md`.
- **Inputs:** LB-025 (sync rule), Ben's confirmation that Cowork works from this folder.
- **Outputs:** `CLAUDE.md`, `docs/build/BUILD_PLAN.md`, `scripts/dev/merge_logbook.py`.
- **Findings:** none beyond the above.
- **Decisions:** Proposed for HANDOFF: the repo is the single source for every shared doc; main-checkout sessions use PRs and logbook fragments.
- **AI:** Claude Code drafted the change for Ben's review.
- **Open / next:** Ben confirms the main-checkout rule suits Cowork and the nightly review.

### LB-076 · 2026-10-15 · Data feasibility: Ohio statewide parcels (Franklin, Hamilton)
- **Question:** Can the Ohio Statewide Parcels public view give a tier-2 parcel denominator (DTE land use + lot size), and what blocks a statewide run?
- **What I did:** Added `oh_parcels` (per-county server-side filter, non-personal fields, retry on the server's intermittent 400s) with two crosswalks: `config/crosswalks/oh_dte_luc.csv` (327 DTE classes → `land_use_std`; 5x1-5x5 are the 5x0 use on unplatted acreage, per the Defiance County code list) and `config/crosswalks/oh_county_fips.csv` (88 counties, checked against the jurisdictions table). Downloaded Franklin and Hamilton and profiled them with `build()`.
- **Inputs:** OhioStatewidePacels_full_view FeatureServer/0; Defiance County auditor land-use code list; `processed/oh/acs_geo_year` (B25024) for coverage.
- **Outputs:** `src/lotline/adapters/states/oh/oh_parcels.py`, the two crosswalks, `tests/states/oh/test_oh_parcels.py`, `config/states/oh.yaml`, `docs/data_provenance.md`. Raw pages in `~/lotline-data/raw/oh_parcels/` (not in the repo); no processed table written.
- **Findings:** 6,313,610 parcels in 88 counties. Franklin 448,726 and Hamilton 352,528 parcels after cleaning (exports of 2023-09-26 and 2023-08-02). Single-family parcels are 96% of ACS one-unit-detached homes in both counties (297,269 vs 309,840; 213,250 vs 222,028). UNKNOWN land use 7.1% / 4.5%, mostly county custom codes 553 and 508. Franklin's LandArea is empty or 0 for 97.5% of parcels, so its lots use polygon area; in Hamilton the two agree (median ratio 1.00). The layer has no city or township field.
- **Decisions:** proposed: `load()` stays off until parcels can be placed in places/townships by point-in-polygon (WS-CORE helper + centroid-only pager option); 401 (apartments 4-19) maps to MULTIFAMILY_5P.
- **AI:** Claude Code (WS-OH) explored the layer, wrote the adapter, crosswalks and 9 synthetic-fixture tests, ran the downloads and profile; full suite, ruff, compliance and provenance pass.
- **Open / next:** WS-CORE helper for jurisdictions; full-state paging (~3,160 pages); county crosswalks for custom codes.

### LB-077 · 2026-10-18 · Build: Austin permits adapter (WS-TX)
- **Question:** Can Austin's Issued Construction Permits feed `permits` with BPS-comparable building types, ADUs and the HOME two-/three-unit signal?
- **What I did:**
  - Added `austin_permits` (Socrata `3syk-w9eu` via `lotline.io.socrata.download_dataset`): building permits with a Census code 101-106, 436 or 645-649 in `permit_class`, plus plain-class "New" permits; explicit non-personal field list.
  - Type from the Census code (R-102 Secondary Apartment = ADU, per the city's ADU dataset `687g-qcqy`); `housing_units` kept where plausible, else derived from the code; the description parser fills gaps only (inferred); HOME "TWO/THREE UNIT RES" phrase → `reform_flag_raw`.
  - Jurisdiction: AUSTIN FULL PURPOSE and AUSTIN LTD → 4805000; ETJ, other cities and blank left out (2,862 of 159,334 rows).
  - Compared with BPS (Austin 4805000) 2010-2025 and with `687g-qcqy`.
- **Inputs:** `3syk-w9eu` and `687g-qcqy` (2026-10-18 snapshots); `bps_place_year` (TX).
- **Outputs:** `src/lotline/adapters/states/tx/austin_permits.py`, `tests/states/tx/test_austin_permits.py`, `config/states/tx.yaml`, `docs/data_provenance.md`.
- **Findings:**
  - 151,655 permits. 1-5+ unit totals are 0.80-1.30x BPS; single-family runs 5-20% below BPS every year; 5+ exceeds BPS in 2019-2023 (1.41x in 2022), where multi-building permits repeat a project's total.
  - R-102 (ADU) permits: 3,166 kept, matching `687g-qcqy` (3,244, all R-102 rows) after status/jurisdiction filters. They collapse after HOME (90 in 2024, 9 in 2025): second and third homes are now R-101/R-103 permits marked "TWO/THREE UNIT RES" (2024: 37 permits; 2025: 149 permits, 163 units). ADU series break in 2024.
  - Duplex (R-103) units jump in 2025 (527 vs 178 in 2024).
- **Decisions:** Proposed: count AUSTIN LTD with Austin; keep 5+ units as reported (no project-total dedupe) until a rule is agreed.
- **AI:** Claude explored the dataset with aggregate SoQL queries, wrote the adapter and tests (synthetic fixture), and ran the BPS and ADU-dataset comparisons; numbers in the PR come from that run.
- **Open / next:** Explain the single-family gap; a project-total rule for 5+; TCAD adapter for hand-downloaded files.

### LB-078 · 2026-10-18 · Build: TCAD parcels adapter for hand-downloaded rolls (WS-TX)
- **Question:** Can Travis CAD's certified roll feed `parcels` for Austin once Ben downloads the files in a browser (the site's bot check blocks scripted downloads)?
- **What I did:**
  - Added `tcad_parcels`: reads every zip registered with `lotline manifest register --source tcad` (`DataStore.registered`), parses the fixed-width PROP, PROP_ENT, STATE_CD, LAND_DET and IMP_DET files by position per TCAD's Legacy 8.0.33 layout, never slicing owner, mailing, mortgage or deed fields.
  - City placement by taxing-unit name (`config/crosswalks/tx_tcad_entities.csv`: CITY OF AUSTIN → 4805000); land use via the state category (`config/crosswalks/tx_ptad_land_use.csv`, Comptroller categories A–S).
  - With no file registered, `load()` stops with the exact register command and the download page.
  - Tests on a synthetic fixed-width zip (21 cases).
- **Inputs:** TCAD export layout (xlsx in `Website_Legacy8.0.33-AppraisalExportLayout_06182026.zip`); Comptroller 2025 Property Value Study page for category names.
- **Outputs:** `src/lotline/adapters/states/tx/tcad_parcels.py`, `tests/states/tx/test_tcad_parcels.py`, `config/crosswalks/tx_ptad_land_use.csv`, `config/crosswalks/tx_tcad_entities.csv`.
- **Findings:** The export has no units or building area; land use only at the state-category level until TCAD's subcodes are read from STATE_CD.TXT. Category B (2+ units) has no matching `land_use_std` value.
- **Decisions:** Proposed: category A → SF_DETACHED, B → OTHER until subcodes are crosswalked.
- **AI:** Claude read the layout spreadsheet, wrote the adapter, crosswalks and tests; nothing was run on real TCAD data (none registered yet).
- **Open / next:** Ben registers the 2026 certified zip (and EARS 2022–2025 if wanted); then verify the entity name, implied decimals and coverage on the real file.

### LB-079 · 2026-10-18 · Build: Ohio parcels placed in cities and townships (Franklin, Hamilton)
- **Question:** Can the statewide parcels be assigned to permit-issuing jurisdictions, and how do single-family parcel counts compare with ACS by place?
- **What I did:** Rebased #106 on main; switched to the pager's `geometry="centroid"` and retries; assigned `jurisdiction_geoid` with `lotline.geo.place_or_township` and `resolve_jurisdictions` (only GEOIDs in the OH jurisdictions table; else the parcel's township; else the county remainder row); `holdout.apply(..., snapshot=True)`; load() on. Replaced county-wide offset paging (30+ s/page and server 400s past offset ~400,000) with per-county OBJECTID-range queries (100,000 ids); superseded the abandoned queries.
- **Inputs:** OhioStatewidePacels_full_view; TIGERweb ACS 2025 places/county subdivisions (#110); `processed/oh/jurisdictions`, `acs_geo_year`.
- **Outputs:** `src/lotline/adapters/states/oh/oh_parcels.py`, `tests/states/oh/test_oh_parcels.py`, `docs/data_provenance.md`; `processed/oh/parcels/oh_parcels.parquet` (801,254 parcels; not in the repo).
- **Findings:** 618,410 parcels (77.2%) fall in a permit-issuing place; 182,844 go to the county remainder row: 174,159 in townships (Franklin and Hamilton townships are not BPS issuers; the county permits them), 8,679 in 9 villages outside the BPS universe (Indian Hill, Amberley, ...), 6 without a polygon match. Single-family parcels vs ACS one-unit detached homes: Cincinnati 0.92, Columbus 0.90 (Franklin part only; the city spills into Delaware and Fairfield), Upper Arlington 1.02, Gahanna 0.99, Grove City 0.97. Fetch for both counties: 35 min, 527 page requests.
- **Decisions:** proposed: county remainder rows are the right home for township parcels where the county permits them.
- **AI:** Claude Code (WS-OH) rewrote the adapter, added tests (29 in tests/states/oh), ran the fetch and comparisons; full suite, ruff, compliance and provenance pass.
- **Open / next:** full-state run (proposal in PR #106); ACS for multi-county places' county parts.

### LB-080 · 2026-10-18 · Build: Cincinnati building permits adapter (OH)
- **Question:** Can Cincinnati's open permit data give new units by year and size class that match the Census BPS, and what do 2-4 unit permits look like around Connected Communities (2024-07-01)?
- **What I did:** Added `cincy_permits` via `lotline.io.socrata` (main BLDS dataset `uhjb-xac9`, server-side filter to new-construction building and wrecking permits; combo dataset `thvx-5mem` only for rows whose work description names an ADU or townhouse, parsed with `parse_description` and never stored). Type from use group + units (no Census code). Compared with `bps_place_year` for 3915000, 2010-2025.
- **Inputs:** data.cincinnati-oh.gov datasets uhjb-xac9 and thvx-5mem; `processed/oh/bps_place_year`.
- **Outputs:** `src/lotline/adapters/states/oh/cincy_permits.py`, `tests/states/oh/test_cincy_permits.py`, `config/states/oh.yaml`, `docs/data_provenance.md`; `processed/oh/permits/cincy_permits.parquet` (8,190 permits; not in the repo).
- **Findings:** 1-unit and 2-unit permits track BPS closely (e.g. 2025: 161 vs 168, 4 vs 4); 2024-25 totals are within 3%. 5+ units run up to 1.6x BPS in some years (2012, 2015, 2018, 2019, 2022) because several permits on one project report the same project total (kept as reported, Ben's decision for Columbus). Descriptively, 2-4 unit permits were 9 (23 units) in the two years before 2024-07-01 and 10 (24 units) in the two years after: no visible change (not a causal estimate). 26 ADU permits found from combo descriptions.
- **Decisions:** none new (repeated project totals kept as reported, as for Columbus).
- **AI:** Claude Code (WS-OH) explored both datasets with SoQL aggregates, wrote the adapter and 8 synthetic-fixture tests, ran the fetch and comparison; full suite, ruff, compliance and provenance pass.
- **Open / next:** a project-total dedupe rule for both cities if V0 needs it.

### LB-081 · 2026-10-19 · Build: Repeated project totals counted once (D-008)
- **Question:** City permit files repeat a multi-building project's total unit count on every building's permit; how do we count it once, transparently, and what does that do to Columbus, Cincinnati and Austin against BPS?
- **What I did:** Added `config/params/permits.yaml` (`repeated_total_min_units` 50, range 20-100; `repeated_total_min_permits` 3, range 2-5) and `src/lotline/build/permits.py`: `flag_repeated_totals` (same jurisdiction, parcel, year and unit count ≥ 50 on ≥ 3 new-construction permits → keep the lowest `permit_id`, flag the rest; demolitions and no-parcel rows never grouped) and `count_units` (units by jurisdiction × year × BPS size class, `dedupe=True` primary, `False` as-reported sensitivity). Logged D-008 in `docs/analysis_plan.md`. Ran it read-only on the processed Columbus, Cincinnati and Austin tables against `bps_place_year` 5+ units, 2018-2025, plus a 3×3 threshold grid.
- **Inputs:** `processed/oh/permits/{columbus,cincy}_permits`, `processed/tx/permits/austin_permits`, `processed/{oh,tx}/bps_place_year` (no MN or NC tables read).
- **Outputs:** `config/params/permits.yaml`, `src/lotline/build/permits.py`, `tests/core/test_build_permits.py`, `docs/analysis_plan.md` (D-008).
- **Findings:** Columbus 2023 5+ units go from 1.41 to 1.02 of BPS (8 × 198 removed); Austin 2022 from 1.42 to 1.25 (incl. 8 × 280). 2018-25 removed: Columbus 13 permits / 1,963 units, Austin 31 / 4,167, Cincinnati none: its 1.6x years (2018, 2019, 2022) have no parcel with 3+ identical large counts, so its excess has another cause. Flagged groups mostly carry the identical valuation on every permit (a sign of a repeated total); Austin 2018 parcel 484530418070701 (3 × 64, valuations differ) may be real identical buildings.
- **Decisions:** D-008 (Ben, 2026-10-19): repeated project totals counted once, sensitivity both ways. Also recorded, Ben 2026-10-19: **TX** — Austin limited-purpose permits count as Austin (ETJ and other cities excluded); HOME treatment for V3/V4 = "TWO/THREE UNIT RES" flag plus duplex permits, not R-102; TCAD land use A → SF_DETACHED, B → OTHER, C1/O → VACANT_RESIDENTIAL, E → OTHER until district subcodes are crosswalked; TCAD starts with the 2026 certified export; San Antonio permits skipped for now. **OH** — township and non-BPS-village parcels go to the county remainder row; full-state parcels run approved; Cincinnati 1-unit = SFD inferred; Columbus ADUs via a public-records request to BZS (no adapter); Franklin auditor terms read as not prohibiting download (no auditor adapter now).
- **AI:** Claude Code (WS-CORE) wrote the rule, params, D-008 text and 6 hand-worked synthetic tests (9 × 198 → 198 once; 3 × 12, 2 × 280, no parcel, split years and demolitions untouched; thresholds from params); ran the real-data comparison read-only. Full suite, ruff, compliance and provenance checked.
- **Open / next:** explain Cincinnati 5+ excess (pairs such as 2 × 127 on one parcel in 2022, CNEW and RNEW permits on one project, BPS timing); wire `count_units` into V0/V3 permit comparisons once those consume city permits.

### LB-082 · 2026-10-19 · Build: Travis CAD 2026 roll loaded; TCAD land-use codes
- **Question:** Does the Travis CAD adapter work on the real certified roll, and are its land-use categories right?
- **What I did:** Ben downloaded the "2026 Certified Appraisal Export (July)" in a browser (traviscad.org is behind a bot challenge); WS-CORE registered it with `lotline manifest register --source tcad` (hard link into `raw/tcad/2026-07-18/`) and ran `lotline fetch --state TX --source tcad_parcels`. Read TCAD's code table (`STATE_CD.TXT`) and added `config/crosswalks/tx_tcad_state_codes.csv`, looked up before the state category: A4/A5 condos → CONDO_UNIT, A2 → MOBILE_HOME, B1 → MULTIFAMILY_5P, B2 → DUPLEX, B3/B4 → TRI_QUAD, B5 (multifamily with homestead) → OTHER. Added the source to `config/states/tx.yaml`.
- **Inputs:** TCAD 2026 certified export (Legacy 8.0.33 fixed width, 557 MB zipped, about 18 GB unzipped; PROP_ENT 9.8 GB, PROP 4.9 GB).
- **Outputs:** `config/crosswalks/tx_tcad_state_codes.csv`, `src/lotline/adapters/states/tx/tcad_parcels.py`, `tests/states/tx/test_tcad_parcels.py`, `config/states/tx.yaml`, `docs/data_provenance.md` (TCAD section only).
- **Findings:** 239,626 City of Austin parcels (Travis County part), unique parcel IDs, every one with lot size and appraisal values; 5.8% without year built; single-family lot median 7,431 sq ft (10-90%: 3,128-13,825). "CITY OF AUSTIN" appears in PROP_ENT as expected. The category-level rule had counted 35,946 condo units (A4/A5) as detached houses; with TCAD codes: 163,890 SF detached, 35,946 condo units, 8,921 duplexes, 1,143 triplex/fourplex, 1,976 multifamily (5+), 14,132 vacant residential. SF detached = 0.78 of ACS 2020-24 one-unit detached homes for Austin (209,772), as expected since part of Austin lies in Williamson and Hays counties. The run takes 42 s and 0.8 GB of memory.
- **Decisions:** none new (applies Ben's 2026-10-19 decision to start with the 2026 certified export).
- **AI:** Claude Code (WS-CORE) registered and ran the export, read STATE_CD.TXT, wrote the crosswalk and tests (507 pass). The Ohio parcels row of the provenance doc is left as on main because the statewide Ohio run is still writing files; WS-OH regenerates it.
- **Open / next:** Austin parcels in Williamson and Hays counties (WCAD, Hays CAD) if the Austin denominator must be complete; older rolls only via the EARS submissions (different layout).

### LB-083 · 2026-10-19 · Validation: Judging panel run on main @ e31b4ed (auto-review)
- **Question:** How would the entry score today against the Rules §8 rubric, and what are the biggest levers before Dec 16?
- **What I did:** (inferred from the reports) Ran the `/judge` panel on a clean clone of `main` at e31b4ed (build stage): a gatekeeper plus five criterion judges, combined into a weighted scorecard with "today" and "ceiling" scores.
- **Inputs:** clean clone of `main` @ e31b4ed; Official Rules §7a/§8; WS briefs and BUILD_PLAN.
- **Outputs:** `reports/judging/2026-10-19-0518-e31b4ed/` (`SCORECARD.md`, `RUN.md`, `judge-gatekeeper.md`, `judge-transparency.md`, `judge-replicability.md`, `judge-usability.md`, `judge-methodology.md`, `judge-policy-insight.md`).
- **Findings:**
  - Not scored as of today (incomplete under §7a: no tool, deck or video; D4 and D6 stubs; D8 said "None so far" while the code calls external APIs). Weighted total 44.5/100 today, 72.2 at ceiling; a top-5 entry likely sits around 75–85.
  - Strengths: 507 tests pass from a clean clone (91% coverage), hand-worked equation tests, generated provenance. Weakest: Usability (1.4 today, ceiling 5.8 under the current WS-APP plan) and Transparency's empty deliverable docs.
  - Recommended now: draft D4 and a D6 skeleton, rewrite the WS-APP brief around user tasks, close cheap gate items (D8, held-out St. Paul figures, eligibility E1/E6) and four engine fixes (MM denominator, fee elasticity range, RNG coupling, `prereg-v1` tag).
- **Decisions:** none recorded by the run itself; several same-day fragments (gate fixes, D-010, D-011, D-013, D-014, Model & Assumptions draft) act on its findings.
- **AI:** Claude ran the panel; `judge-gatekeeper.md` and `judge-methodology.md` were reconstructed by the main session from the judges' replies after a disk-full error (scores complete, some probe output summarized). Logged by the nightly review; no session entry found for the run itself.
- **Open / next:** Usability plan rewrite (WS-APP); re-run the panel after the fixes land.

### LB-084 · 2026-10-19 · Build: ArcGIS pager rejects non-JSON block pages; analysis plan housekeeping (auto-review)
- **Question:** Stop an HTML "Request Rejected" page from being cached as data, and keep the decisions log in order.
- **What I did:**
  - `lotline.io.arcgis._json`: a reply that is not JSON now deletes the cached file and raises `ArcGISError` ("not JSON (an error or block page?)"), the same treatment as ArcGIS error bodies (issue #132, PR #134); test added.
  - `docs/analysis_plan.md`: decision entries put back in numeric order and D-013's "Decided by" line, lost in a merge, restored (PR #136).
- **Inputs:** issue #132.
- **Outputs:** `src/lotline/io/arcgis.py`, `tests/core/test_arcgis.py`, `docs/analysis_plan.md` (commits 17abe84, 403eff7; merged to `main`).
- **Findings:** none beyond the above.
- **Decisions:** none.
- **AI:** Claude Code made both changes (co-authored commits); no session logbook fragment found, so logged by the nightly review.
- **Open / next:** none.

### LB-085 · 2026-10-19 · Build: Ohio parcels set up for the full 88-county run (auto-review)
- **Question:** Run the approved statewide Ohio parcels fetch (LB-079, LB-081 decisions) in a way that survives a day-long run.
- **What I did:** `oh_parcels` now downloads all 88 counties in `oh_county_fips.csv` by default (a list still limits the run), with OBJECTID ranges per county; new `snapshot_vintage()` reads `OH_PARCELS_VINTAGE` (YYYY-MM-DD) so a run resumed on a later date reuses the cached pages of the same snapshot. Provenance cleaning text updated to match.
- **Inputs:** LB-079 adapter; Ben's 2026-10-19 approval of the full-state run.
- **Outputs:** `src/lotline/adapters/states/oh/oh_parcels.py` on branch `ws/oh-3-statewide` (commit be97ad9; not merged, no PR or fragment yet).
- **Findings:** Not stated in the commit; LB-082 notes the statewide run was still writing files on Oct 19.
- **Decisions:** none new.
- **AI:** Claude Code (WS-OH) made the change; results of the statewide run are not recorded yet.
- **Open / next:** finish the run, regenerate the Ohio provenance row, open the PR with a logbook fragment.

### LB-086 · 2026-10-19 · Build: Met Council regional parcels and Ramsey County parcels adapters, work in progress (WS-MN) (auto-review)
- **Question:** Can the Twin Cities parcel denominator come from the Met Council regional parcel points (2021–2025 rolls plus the current roll), with Ramsey County's own layer adding lot frontage, while keeping St. Paul held out?
- **What I did:** (from WIP commits; intent read from the docstrings)
  - `metc_parcels`: 7-county parcel points, one row per parcel per roll; `vintage` = service-name year, `vintage_date` = county `EXP_DATE` (Ben, 2026-10-19); jurisdiction by `place_or_township`, checked against `CTU_NAME`, else the county remainder row; `USECLASS1` → `land_use_std` by ordered rules, overridden by `DWELL_TYPE` where recorded and refined by unit counts; owner/taxpayer/situs fields never requested.
  - Holdout: St. Paul rows only from rolls exported up to 2023 (`holdout.apply(..., snapshot=True)` on both the point's jurisdiction and `CTU_NAME`).
  - `ramsey_parcels`: Ramsey current roll outside St. Paul (excluded at the server query and again by the holdout filter), adding `ParcelFrontage` → `lot_width_ft` and the detailed land-use description.
  - Crosswalks `mn_land_use.csv`, `mn_land_use_dwelling.csv`, `mn_land_use_ramsey.csv`; `config/states/mn.yaml` source entry; synthetic-fixture tests.
- **Inputs:** Met Council `Parcel_Points_2021`…`2025` and `Parcel_Points_Aggregate`; Ramsey `CAD_AttributedParcelPoint_ViewOnly`; Minn. Stat. 273.13 property classes.
- **Outputs:** branches `ws/mn-3-metc-parcels` (ffd2be0, 4d5de80) and `ws/mn-3-ramsey-parcels` (adds d26821b): `src/lotline/adapters/states/mn/metc_parcels.py`, `src/lotline/adapters/states/mn/ramsey_parcels.py`, the three crosswalks, `tests/states/mn/test_metc_parcels.py`, `tests/states/mn/test_ramsey_parcels.py`, fixtures. Not merged; no fragment yet.
- **Findings:** Rolls 2002–2020 are token-locked (checked 2026-10-19; requested from Met Council, #11). The "2023" roll was exported 2023-10-01 to 2024-01-08 depending on county, and the "2025" roll is a mid-2025 export. Hennepin leaves `NUM_UNITS`/`DWELL_TYPE` blank. No real-data results recorded yet.
- **Decisions:** Recorded in code: vintage naming and dating rule (Ben, 2026-10-19).
- **AI:** Claude Code (WS-MN) wrote the WIP adapters and tests; whether tests pass on the branch was not checked by this review.
- **Open / next:** finish and run the adapters, open PRs with logbook fragments; the `mn.yaml` diff on the branch replaces the `stpaul_permits` source entry, which needs reconciling with `main` at merge.

### LB-087 · 2026-10-20 · Admin: Handoff briefs 08 (Minnesota data complete) and 09 (combine scenarios, statewide aggregation) (auto-review)
- **Question:** What should the next two parallel threads do: finish Minnesota's inputs for a statewide end-to-end run, and turn per-place scenario results into combined, statewide numbers?
- **What I did:** (from the briefs; added after the 01–07 briefs, whose fragment is `logbook.d/2026-10-20-docs-handoffs.md`)
  - Thread 8 (WS-MN): every input the baseline and the three scenarios need for all 1,053 MN jurisdictions (763 places, 218 townships, 72 county remainders), ending with a readiness report and a baseline + ADU integration run; states what is on `main` (metro-only parcels, 98 ADU rule rows, 2 missing-middle rows, no fees) and the lanes of threads 1–3 to stay out of.
  - Thread 9 (WS-ENGINE-AGG): D-026 entry before code; a common scenario output contract (place × year × draw) with `adu.run()` retrofitted and stub MM/fee scenarios; `model/combine.py` (one project per parcel, the more profitable of ADU vs 2–4 units; fees applied inside the pro forma); aggregation to county and state with ranges, gross-to-net, and a local demand cap (judging finding MS-04).
- **Inputs:** `docs/build/handoffs/README.md`, WS-MN brief, D-014 to D-025, LB-083 judging reports.
- **Outputs:** `docs/build/handoffs/08-minnesota-data-complete.md`, `docs/build/handoffs/09-combine-and-aggregate.md`, `docs/build/handoffs/README.md` (PRs #185, #190, merged to `main`).
- **Findings:** none (briefs only).
- **Decisions:** none recorded. Note: the brief reserves "D-026" for thread 9, but D-026 was used the same day on other branches (ADU imputation estimator; baseline calibration fixes), so the number needs reconciling at merge.
- **AI:** Claude Code wrote both briefs (co-authored commits); no fragment found, so logged by the nightly review.
- **Open / next:** Ben starts threads 8 and 9.

### LB-088 · 2026-10-20 · Validation: D-024 missing-middle estimator built; first real run aborted; rerun fixes (WS-ENGINE-MM, branch) (auto-review)
- **Question:** Estimate the D-024 pre-registered missing-middle effect (extra 2–4 unit homes after a missing-middle rule) on the pooled four-state panel.
- **What I did:** (from commits on `ws/engine-mm-estimate`; the branch's fragment covers only the panel and D-024 approval)
  - Wrote the estimator: PPML with place and state × year fixed effects, Poisson-gamma random-effects fallback, randomization inference, checks, transport and imputation of added homes; run script `--full`, `--dry-run`, `--coverage`; D-024 run parameters added to the parameter table.
  - First real run (17:06) aborted: PPML diverged, the pre-specified fallback ran, then randomization inference crashed on a diverging refit. Log kept.
  - Then switched the fallback to D-025's estimator (D-024 names it) via a relabelled panel (20:13), and at 20:35 made mechanical fixes stated as independent of results (divergence and overflow raise `EstimationError`, damped Newton steps, RI counts failed reassignments) with the fallback back on the 17:06 Poisson-gamma spec and PPML, RE and D-025's NB all reported as robustness. Whether Ben approved that fallback change is not recorded.
- **Inputs:** D-024 (approved by Ben 2026-10-20), D-025 `pooled_adu`; panel of 560 places, 8,763 place-years.
- **Outputs:** `src/lotline/model/estimate_mm.py`, `scripts/dev/estimate_mm.py`, `tests/model/test_estimate_mm_fit.py`, `config/params/mm.yaml`, `docs/model_and_assumptions.md`, `reports/mm-d024/aborted-2026-10-20-log.txt` (commits eecb39c, 4df1203, 5e676ab, e43aaa2, 42fd9f8; not merged, no PR yet).
- **Findings:** Not a result (run aborted before inference, nothing written). The aborted log printed fallback main estimates: ATT 0.77 on the log scale (90% 0.07–1.54); added 2–4 unit homes dominated by Houston (2,422) with Austin negative (−131), which the checks were meant to examine. 16 pipeline-flagged comparison places were dropped by check 7b. Two NB tests are skipped until `pooled_adu`'s mode search is safeguarded.
- **Decisions:** none recorded; the fallback choice (Poisson-gamma RE vs D-025's NB) may need a dated D-024 note.
- **AI:** Claude Code (WS-ENGINE-MM) wrote the code and ran it; logged by the nightly review from commits and the log, without rerunning tests.
- **Open / next:** rerun once with the fixes; update the branch fragment and open a PR.

### LB-089 · 2026-10-21 · Admin: Handoff brief 10 (North Carolina end-to-end data collection) (auto-review)
- **Question:** What should a parallel WS-NC thread do to get North Carolina's inputs good enough for the baseline, the three scenarios and thread 9's combining and aggregation, following the Minnesota pattern (thread 8)?
- **What I did:** (from the brief)
  - Snapshot of `main` on 2026-10-21: 322 NC jurisdictions; parcels for the 10 largest counties plus the Wake Dec 2023 roll; permits for Raleigh and Durham only (Mecklenburg coded but blocked); 31 ADU rule rows, 5 missing-middle rows, 11 fee rows; Charlotte V5 holdout, whose prediction must be frozen by Nov 17.
  - Step 1: verify the snapshot and write `docs/build/nc-data-plan.md` (one subtask per gap, with what it feeds, source, cost, priority and owner; at least 8 named gaps) and get Ben's approval before heavy work. Step 2: small PRs, with no broad web-search sweeps (fill-in lookup tables for Ben instead). Step 3: `docs/build/nc-readiness.md` and a statewide integration run.
  - Stay out of `model/*`, the demand index, and Charlotte or Mecklenburg outcomes from 2023-06-01.
- **Inputs:** `docs/build/handoffs/README.md`, brief 08, WS-NC brief, D-012, D-014 to D-025.
- **Outputs:** `docs/build/handoffs/10-north-carolina-data-complete.md`, `docs/build/handoffs/README.md` (commit fb4810f, PR #197, merged to `main`).
- **Findings:** none (brief only).
- **Decisions:** none.
- **AI:** Claude Code wrote the brief (co-authored commit); no fragment found, so logged by the nightly review. The thread's own work the same day (data plan, decisions 1–4 and 6 approved by Ben, issue #208; OneMap, Greensboro, Mecklenburg, Wake, Durham, rules/fees and Charlotte V5 PRs) has fragments on its `ws/nc-*` branches and is not repeated here.
- **Open / next:** merge the thread 10 PRs; readiness report.

### LB-090 · 2026-10-23 · Admin: Handoff briefs 11 (Ohio) and 12 (Texas) end-to-end data collection (auto-review)
- **Question:** What should parallel WS-OH and WS-TX threads do to get Ohio and Texas data good enough for the engines statewide and, above all, to add places to the multi-state ADU and missing-middle estimation panels?
- **What I did:** (from the briefs)
  - Both follow the North Carolina pattern (brief 10, `nc-data-plan.md`, PRs #199–#214): verify a snapshot of `main`, write a subtask plan (`docs/build/oh-data-plan.md`, `tx-data-plan.md`) for Ben's approval, then small PRs, then a readiness report (`oh-readiness.md`, `tx-readiness.md`) with no model runs. New rule for data threads: don't run engine, scenario or dev-run scripts unless Ben asks. Target: week of 2026-10-26.
  - Ohio snapshot: 952 jurisdictions, no tier 1 (statewide roll lacks year built); 6.09M parcels from one 2023 roll (needs a second roll year for eligible history, D-035); permits for Columbus and Cincinnati only (ADU flags 0 and 26); 20 ADU rule rows, 1 missing-middle row, no fees.
  - Texas snapshot: 1,006 jurisdictions, only Austin tier 1; parcels from the Travis 2026 roll only; Austin permits only (3,166 ADU, 8,790 2–4 unit); 23 ADU rule rows, 2 missing-middle rows, 2 fee rows; no sale-price disclosure. Top priority in both: permit sources with ADU and units-per-building fields, watching D-008 and annexation dates.
- **Inputs:** `docs/build/handoffs/README.md`, brief 10, WS-OH and WS-TX briefs, D-008, D-014 to D-035.
- **Outputs:** `docs/build/handoffs/11-ohio-data-complete.md`, `docs/build/handoffs/12-texas-data-complete.md`, `docs/build/handoffs/README.md` (commit f27f277, PR #216, merged to `main`).
- **Findings:** none (briefs only).
- **Decisions:** none.
- **AI:** Claude Code wrote both briefs (co-authored commit); no fragment found, so logged by the nightly review. The threads' own work the same day (OH and TX data plans with Ben's 2026-10-23 approval; Fort Worth, San Antonio and Dallas permit adapters; Texas rules for places 21–40; Franklin County Auditor ADU flags) and NC rules pass 2 have fragments on their branches and are not repeated here.
- **Open / next:** Ben reviews the thread PRs; readiness reports.

### LB-091 · 2026-10-23 · Deliverables: "NC Model Run, Oct 22" dashboard artifact (auto-review)
- **Question:** Present the first North Carolina development run (fragment `logbook.d/2026-10-22-ws-nc-dev-run-2026-10-22.md` on `ws/nc-dev-run-2026-10-22`) as a page Ben can open and share. Intent inferred from the artifact; not stated elsewhere.
- **What I did:** Built a dashboard artifact from fixed copies of the run's tables (written 2026-10-23 14:40Z): ADU scenario statewide, by place, sensitivity and diagnostics; baseline by place and by housing class; the V1 backtest; and the Raleigh fee scenario.
- **Inputs:** `reports/nc/dev-run-2026-10-22.md` (PR #213, branch, DEVELOPMENT RUN).
- **Outputs:** https://claude.ai/artifact/JvYXyFA3YuDQwRMG4UvRMw (private).
- **Findings:** none new; numbers are the dev run's (e.g. 2,065 added ADU permits at P50 over five years, mostly extrapolation).
- **Decisions:** none.
- **AI:** Claude built the page; datasets are marked as copied from the report. This review did not check the figures against the report.
- **Open / next:** label it as a development run if shared; refresh after the next NC run.

### LB-092 · 2026-10-27 · Admin: Ohio data plan, Ben's manual list for 2026-10-27 and his Montgomery County answer (WS-OH, branch) (auto-review)
- **Question:** What does Ben need to do by hand (decisions, reviews, browser lookups, emails) to unblock thread 11's Ohio data, ranked by payoff?
- **What I did:** (from commits on `ws/oh-5-data-plan`; the branch's fragment covers only the plan and its 2026-10-23 approval)
  - Added §8 to the Ohio data plan: 15 items. Decisions on PR #232 (Cuyahoga exempt code 6411 → INSTITUTIONAL; one roll per jurisdiction for multi-county cities), the D-017 10% unknown-land-use cutoff (Hamilton at 10.4%), Dayton/Montgomery options (CAMA extract, a tax-class proxy, or stay on ACS), and whether Columbus joins the D-025 ADU panel; PR reviews #217, #224, #226, #232; four Dependabot alerts; ADU and missing-middle lookup tables (47 places each; Euclid flagged as a likely second Ohio missing-middle event); Columbus ADU counts request; Warren County parcel search; OGRIP email for a 2022 statewide roll; `uv` 0.13.5 note; fold fragments after merging.
  - Recorded Ben's 2026-10-27 answer on Montgomery County: no reuse restrictions but no explicit licence ("no reuse terms stated"), and a CAMA download with parcel land-use codes exists, so option (a) is open (download in a browser, register with `lotline manifest register`).
- **Inputs:** S5 probe results (commit 6ccc676), PR #232, Montgomery Auditor GIS Downloads page (checked by Ben).
- **Outputs:** `docs/build/oh-data-plan.md` §8 (commits f751287, b5b950c, 7bbc975, 7cb5cee on `ws/oh-5-data-plan`; PR #217, not merged).
- **Findings:** Montgomery's weekly geodatabase has no parcel land-use code, so pyogrio was not added; Columbus auditor descriptions find about 1 in 4 of the city's ADUs (14 vs 57, 2019 to Sep 2025).
- **Decisions:** none recorded in `HANDOFF.md`; items 1–3 and 5 await Ben.
- **AI:** Claude Code (WS-OH) wrote the list; Ben supplied the Montgomery finding. No fragment found for these commits, so logged by the nightly review. The day's other OH and TX work (Franklin yearly rolls and history check, OH readiness draft, OH rules tracker, StratMap file-geodatabase reader and completeness check, TX readiness after StratMap, Texas loose ends merged as PR #233, StratMap merged as PR #238) has fragments on its branches and is not repeated here.
- **Open / next:** Ben answers items 1–5 and downloads the Montgomery CAMA extract; merge #217.

### LB-093 · 2026-10-28 · Admin: Ben merges four Ohio thread PRs (#217, #224, #232, #239) to `main` (auto-review)
- **Question:** Bring thread 11's reviewed Ohio work onto `main`. Intent inferred from the merges; Ben left no note.
- **What I did:** (from merge commits, 19:43–19:59 ET)
  - Merged #217 (Ohio data plan, incl. §8 manual list; docs only), #224 (ADU flags from the Franklin County Auditor permit file, Columbus and suburbs), #232 (Summit, Lucas and Cuyahoga county land use; one roll per jurisdiction for multi-county cities) and #239 (yearly eligible-lot rolls for Franklin County places, 2016–2025). Two branches were updated from `main` first to clear conflicts.
- **Inputs:** PRs #217, #224, #232, #239 on `ws/oh-5-data-plan`, `ws/oh-6-franklin-permits`, `ws/oh-8-summit-land-use`, `ws/oh-11-franklin-yearly`.
- **Outputs:** `main` at c503301 (merges 616f600, 8a40ccf, 90b9bea, c503301).
- **Findings:** none new; the PRs' work has its own fragments (`logbook.d/2026-10-26-ws-oh-8-summit-land-use.md`, `2026-10-27-ws-oh-11-franklin-yearly.md`, and the branches' others) now on `main` awaiting the fold.
- **Decisions:** Merging #232 adopts its mapping of Cuyahoga exempt code 6411 to INSTITUTIONAL and the one-roll-per-jurisdiction rule (items in Ohio plan §8, LB-092); no dated row in `HANDOFF.md` records this.
- **AI:** Claude Code wrote the merged PRs (logged in their fragments); the merges are Ben's. Logged by the nightly review from git history, without rerunning tests.
- **Open / next:** fold the `logbook.d/` fragments; remaining Ohio §8 items (D-017 cutoff for Hamilton, Montgomery CAMA download, Columbus in the D-025 panel). Not merged yet: `ws/oh-7-rules` (Euclid missing-middle row) and `ws/tx-research-tracker`, both with fragments.

### LB-094 · 2026-10-30 · Admin: Ben merges five Texas and Ohio thread PRs (#241–#245) to `main` (auto-review)
- **Question:** Bring the reviewed Texas rules/fees work and the Columbus ADU recall work onto `main`. Intent inferred from the merges; Ben left no note.
- **What I did:** (from merge commits, 17:51–20:49 ET)
  - Merged #241 (`ws/tx-research-tracker`: rule and fee rows from Ben's second research workbook, 35 proposed corrections listed), #242 (`ws/tx-corrections`: Ben's decisions on those 35 corrections applied), #244 (`ws/tx-ben-lookups`: rule and fee rows from Ben's own lookups, incl. Austin, SAWS, Houston, Fort Worth and Dallas fee answers), #243 (`ws/oh-12-columbus-adu-recall`: Columbus Council variance approvals and recall rules for auditor ADU descriptions) and #245 (`ws/tx-wrapup`: county land-use codes, jurisdiction fix, second-coder review sheet, Ben's second lookup batch, readiness refresh).
- **Inputs:** PRs #241–#245 and their branches.
- **Outputs:** `origin/main` at 59f3daa (merges a74d681, 6b1301e, bc30a7f, c8906bd, 59f3daa). The local checkout's `main` is at c8906bd (before #245).
- **Findings:** none new; each PR's work has its own fragment (`logbook.d/2026-10-30-ws-tx-research-workbook-2.md`, `-ws-tx-corrections.md`, `-ws-tx-ben-lookups.md`, `-ws-oh-12-columbus-adu-recall.md`, `-ws-tx-wrapup.md`), now on `main` awaiting the fold. Per #245's commit, Texas is pooled into the ADU estimate (Ben, 2026-10-30); readiness now 478 jurisdictions from parcels, tiers 125/176/705.
- **Decisions:** Texas joining the pooled ADU estimate (Ben, 2026-10-30) has no dated row in `HANDOFF.md`.
- **AI:** Claude Code wrote the merged PRs (logged in their fragments); the merges are Ben's. Logged by the nightly review from git history, without rerunning tests.
- **Open / next:** fold the `logbook.d/` fragments; pull `main` locally. Not merged yet, both with fragments: `ws/oh-7-rules` (Franklin suburbs, Lancaster, Cleveland Heights, Findlay, Dayton rows, 2026-10-30) and `ws/oh-13-montgomery-cama` (Montgomery CAMA, Dayton off ACS, Warren County land use).

### LB-095 · 2026-11-01 · Admin: Ben merges ten Texas, Ohio, North Carolina and core PRs to `main` (auto-review)
- **Question:** Bring the closing work of the Texas, Ohio and North Carolina data threads, the D-035 interpolation and the transfer-purpose decision onto `main` before the engine week. Intent inferred from the merges; Ben left no note.
- **What I did:** (from merge commits, 10:40–20:15 ET)
  - Merged #249 (`ws/tx-carrollton`: Carrollton ADU rule, Dallas utility fees), #250 (`ws/tx-handoff`: Texas thread 12 closed), #246 (`ws/oh-13-montgomery-cama`: Montgomery CAMA, Dayton tier 1, ADU-panel coverage rule), #226 (`ws/oh-7-rules`: Ohio rule rows incl. Ben's 2026-11-01 lookups, Grove City pre-window row, second-coder agreement on 21 "no ADUs" rows), #234 (`ws/oh-9-readiness`: Ohio readiness report rewritten), #252 (`ws/core-interpolate-roll-years`: D-035 addendum, `parcels_interpolated`, schemas 1.9), #253 (`ws/oh-handoff`: Ohio thread handoff), #215 (`ws/nc-rules-pass2`), #257 (`ws/handoff-transfer-purpose`: HANDOFF purpose row and V8 unseen-state test) and #254 (`ws/nc-second-coder`: NC second-coder review and Ben's decisions).
- **Inputs:** PRs #215, #226, #234, #246, #249, #250, #252, #253, #254, #257 and their branches.
- **Outputs:** `main` at 7fc54e5 (merges 8972692, 29016b5, c17eead, 6a70f9d, d095d62, 63a273a, 8b95d30, f9d9624, 4cbe440, 7fc54e5); local checkout matches `origin/main`.
- **Findings:** none new; each PR's work has its own fragment in `logbook.d/` (e.g. `2026-11-01-ws-tx-carrollton.md`, `-ws-tx-handoff.md`, `-ws-core-interpolate-roll-years.md`, `-ws-oh-handoff.md`, `-ws-nc-second-coder.md`, `2026-10-28-cowork-transfer-purpose.md`), now on `main` awaiting the fold. The Texas and Ohio data threads are closed with handoffs for the engine week.
- **Decisions:** the merges bring onto `main` the HANDOFF rows dated 2026-10-28 (general-purpose transfer) and 2026-11-01 (`[predates]`, LB-097), and the D-035 addendum in `docs/analysis_plan.md` (Ben, 2026-11-01).
- **AI:** Claude Code wrote the merged PRs (logged in their fragments); the merges are Ben's. Logged by the nightly review from git history, without rerunning tests.
- **Open / next:** fold the `logbook.d/` fragments. Not merged yet, all with fragments: `ws/nc-13-readiness`, `ws/mn-13-data-plan`, `ws/mn-13-v5-stpaul`, `ws/mn-13-mm-rules`; `ws/handoff-13` (handoff brief 13) has a fragment but no merge found.

### LB-096 · 2026-11-01 · Policy analysis: Ohio research brief for the remaining ordinance lookups (auto-review)
- **Question:** What exactly should a research agent find to finish dating Ohio's ADU and missing-middle rules, so each finding can become a dated row in `config/reforms/oh.csv`?
- **What I did:** (from the brief)
  - Set answer rules: effective date beats adoption date (charter rule or Ohio R.C. 731.29's 30 days; emergency ordinances on passage); "first allowed" is the earliest enacted ordinance, not an amendment; a dated "no ADUs" finding needs a code edition and section; official publishers and ordinance records first, news only as leads; unresolved stays unresolved.
  - Fixed a one-row-per-place return table and listed the open lookups with what is known and where to start (e.g. Westerville §1175.06, amended by Ord. 2023-15 so ADUs predate it; Reynoldsburg §1105.05, amended 2020 and 2021).
- **Inputs:** `config/reforms/oh.csv`, Ohio data plan §8 (LB-092), the Ohio rules work on `ws/oh-7-rules`.
- **Outputs:** `docs/research/ordinances/oh-lookups-brief-2026-11-01.md` (commit ba7243c).
- **Findings:** none (brief only). Results of Ben's lookups the same day were coded on `ws/oh-7-rules` (commits 36c3fd7, 4ea2b2c; covered by that branch's fragment).
- **Decisions:** none.
- **AI:** Claude Code wrote the brief (co-authored commit); no fragment found, so logged by the nightly review. Which branch it sits on was not checked.
- **Open / next:** the lookups still unresolved after Ben's pass.

### LB-097 · 2026-11-01 · Study design: `[predates]` rule recorded in HANDOFF; Minnesota data plan approved and aligned (auto-review)
- **Question:** How should reform rows whose date is only a code rewrite be treated by the engines, and does the Minnesota plan follow the rule?
- **What I did:** (from commits e33c4da, 31d57f4, c694bcb, fb52bdd)
  - Added a 2026-11-01 row to the `HANDOFF.md` decisions log: a rule row dated only by a rewrite or recodification carries `[predates]` in `coding_notes`, and D-024/D-025 panels, rule age and event studies must not treat its date as a reform event; applies to every state until WS-CORE adds a `date_basis` field. Then corrected the count in the rationale (10 of 31 `[earliest-known]` NC rows dated 2010+ were rewrites; 8 tagged, 2 redated).
  - Added the rule to the Minnesota data plan (M4 coding, M5 event counts, in-window `[earliest-known]` rows first on the MN second-coder sheet) and marked the plan approved by Ben on 2026-11-01 (§5 decisions 1–2, the plan and the MnGeo download; 3–4 as recommended).
- **Inputs:** NC second-coder review and decisions (fragment `logbook.d/2026-11-01-ws-nc-second-coder.md`), `docs/build/mn-data-plan.md` (fragment `logbook.d/2026-11-01-ws-mn-13-data-plan.md`).
- **Outputs:** `HANDOFF.md` (on `main` via #254), `docs/build/mn-data-plan.md` on `ws/mn-13-data-plan` (not merged).
- **Findings:** none new beyond the NC review.
- **Decisions:** HANDOFF 2026-11-01 `[predates]` rule; MN data plan approved (Ben, 2026-11-01; no dated HANDOFF row).
- **AI:** Claude Code made the edits (co-authored commits); the NC fragment called the tag "proposed", so the decision and the MN approval are logged here by the nightly review.
- **Open / next:** WS-CORE `date_basis` field; MN M1 and M4 are under way on their branches (with fragments).

### LB-098 · 2026-11-02 · Admin: Ben merges seven Minnesota, North Carolina and handoff PRs (#255, #256, #259–#263) to `main` (auto-review)
- **Question:** Close the Minnesota (thread 13) and North Carolina data work and start the engine thread before the four-state runs. Intent inferred from the merges; Ben left no note.
- **What I did:** (from merge commits, 19:04–19:26 ET)
  - Merged #255 (`ws/nc-13-readiness`: NC readiness with an engine kickoff section), #256 (`ws/mn-13-data-plan`), #259 (`ws/mn-13-v5-stpaul`), #260 (`ws/mn-13-mm-rules`), #261 (`ws/mn-13-mngeo`: Greater Minnesota parcels from MnGeo's opt-in compilation, statewide eligible rebuilt), #262 (`ws/mn-13-readiness`: MN readiness report, second-coder return and Ben's acceptance of all 62 recommendations, about 30 MN ADU dates confirmed or re-dated from ordinance lookups during the day) and #263 (`ws/handoff-14-engine`: handoff brief 14, engine refresh on all four states). `ws/mn-13-readiness` was updated from `main` first.
- **Inputs:** PRs #255, #256, #259–#263 and their branches.
- **Outputs:** `origin/main` at fa3994a (merges 1f7ecf6, 8c32102, f5a4a3b, cc6f341, e1589fc, 4e01c59, fa3994a); `docs/build/handoffs/14-engine-four-state-refresh.md`. The local checkout's `main` is still at 7fc54e5.
- **Findings:** none new; each PR's work has its own fragment (`logbook.d/2026-11-01-ws-nc-13-readiness.md`, `-ws-mn-13-data-plan.md`, `-ws-mn-13-v5-stpaul.md`, `2026-11-02-ws-mn-13-mm-rules.md`, `-ws-mn-13-mngeo.md`, `-ws-mn-13-readiness.md`, `-ws-handoff-14-engine.md`), now on `main` awaiting the fold. With these merges all four state data threads are closed.
- **Decisions:** the MN fragment records Ben's 2026-11-02 decision that `DATE UNCONFIRMED` rows count as events, with runs with and without them (commit 24e7c00), and his decision to keep seasonal cabins out of eligibility (54e9727); neither has a dated row in `HANDOFF.md`.
- **AI:** Claude Code wrote the merged PRs (logged in their fragments); the merges are Ben's. Logged by the nightly review from git history, without rerunning tests.
- **Open / next:** fold the `logbook.d/` fragments; pull `main` locally; add HANDOFF rows for the two MN decisions if Ben wants them there. Not merged yet, with fragments: `ws/engine-14-rule-tags` (#264, rule date tags in both panel builders, placeholder-date fix) and `ws/engine-14-counts` (four-state panel counts and the D-024/D-025 2026-11-02 amendment entries).

### LB-099 · 2026-11-02 · Validation: D-025 pooled ADU model on four states does not converge; no estimate (auto-review)
- **Question:** Does the pre-registered D-025 pooled ADU model, now with Texas pooled in (80 places: MN 76, TX 4; 3,192 ADU permits), produce an estimate on the four-state data?
- **What I did:** (from commit bd93178 and its log)
  - Ran `scripts/dev/estimate_pooled_adu.py --full` once at 19:56 ET on commit 0ca15cc, as the amendment entry written before the run required. BFGS hit its 500-iteration limit (19,445 likelihood evaluations, 27 s), the convergence guard raised `EstimationError`, and no later stage ran (no bootstrap, checks, sensitivity, transport or CSV). Not re-run.
  - Diagnosed with convergence information only (no coefficient read): 19 columns, none dropped, no separated rows, no coefficient near ±20, neither variance parameter at its bound, so slow convergence rather than an identification failure; likely cause is scale (Austin's ~2,500 ADU permits beside Minnesota places with a few each).
  - Appended the result to the D-025 entry in `docs/analysis_plan.md`.
- **Inputs:** panel and amendment entries from `ws/engine-14-counts` (fragment `logbook.d/2026-11-02-ws-engine-14-counts.md`), handoff 14.
- **Outputs:** `docs/analysis_plan.md` (D-025, 2026-11-02 run note), `reports/adu-d025-4state/run-2026-11-02-log.txt` (commit bd93178 on local branch `ws/engine-14-results`, not pushed, no PR).
- **Findings:** no four-state D-025 estimate; the October Minnesota-only D-025 estimate stays the one on record.
- **Decisions:** none yet. Needed from Ben (new dated entry): e.g. apply the October refit rule to the main model (higher iteration limit, or start from the Minnesota-only fit) or pool Texas differently.
- **AI:** Claude Code (WS-ENGINE, co-authored commit) ran the script and wrote the note; the run log is the script's own output. No fragment found for this commit, so logged by the nightly review; figures copied from the commit, not re-checked.
- **Open / next:** Ben's decision on the refit; push `ws/engine-14-results`; the D-024 four-state run.

### LB-100 · 2026-11-03 · Admin: Ben merges thirteen engine-week PRs (#264–#266, #270–#278) to `main` (auto-review)
- **Question:** Bring the day's engine-thread work (four-state runs, the D-037 mechanism route and the D-038 to D-041 calibration runs, the results dashboard) and a dependency bump onto `main`. Intent inferred from the merges; Ben left no note.
- **What I did:** (from merge commits, 13:14 and 17:51–18:08 ET)
  - Merged #276 (`ws/engine-14-austin-adu`: Austin and Houston checks, pre-reform missing-middle rows tagged `[predates]`, Ben 2026-11-03) at 13:14, then #264 (`ws/engine-14-rule-tags`), #265 (`ws/engine-14-counts`), #266 (`ws/engine-14-results`: D-025 non-convergence, D-024 four-state run with no credible estimate, V5 freeze proposal), #270 (`ws/engine-14-dashboard`), #271 (`ws/engine-14-route1`: D-037, scenario effects from the mechanism route, calibrated on our own four states), #274 (`ws/engine-14-adu-refit`: D-039 four-state ADU anchor 1.11/1,000, 0.74–1.74), #275 (`ws/engine-14-statewide`: D-040 statewide backtest, 1 of 4 state totals useful; ADU anchor diagnosis), #277 (`ws/engine-14-adu-counts`: D-041 consistent counts), #278 (`ws/engine-14-dashboard-calib`), #272 (`ws/engine-14-mm-anchor`: D-038 missing-middle anchor, D-042 refit, Ben's decision to keep the D-038 values) and #273 (`ws/deps-security-bump`: Pillow 13.0.0, certifi 2026.10.23).
- **Inputs:** PRs #264–#266, #270–#278 and their branches.
- **Outputs:** `origin/main` at bb968ec; `docs/analysis_plan.md` (D-037 to D-042 entries); `reports/mm-d042/` and the other run folders named in the fragments. The local checkout's `main` is still at 7fc54e5.
- **Findings:** none new; each PR's work has its own fragment (`logbook.d/2026-11-03-ws-engine-14-results.md`, `-route1.md`, `-mm-anchor.md`, `-adu-refit.md`, `-statewide.md`, `-diagnosis.md`, `-adu-counts.md`, `-austin-adu.md`, `-dashboard.md`, `-dashboard-calibration.md`, `-ws-deps-security-bump.md`), now on `main` awaiting the fold.
- **Decisions:** the fragments record D-037 (Ben, 2026-11-03), the Austin/Houston pre-reform rows (Ben, 2026-11-03) and keeping the D-038 missing-middle values over the D-042 refit (Ben, 2026-11-03, commit 145c7f0); D-038, D-039 and D-041 readings are marked for Ben to confirm. None has a dated row in `HANDOFF.md`.
- **AI:** Claude Code wrote the merged PRs (logged in their fragments); the merges are Ben's. Logged by the nightly review from git history, without rerunning tests or re-checking figures.
- **Open / next:** fold the `logbook.d/` fragments; pull `main` locally; add HANDOFF rows for D-037 and the kept D-038 values if Ben wants them there. Not merged yet, with fragments: `ws/engine-14-unseen-state` (D-043, a range for θ in an unseen state; method approved by Ben, run once into `reports/adu-state-effect/`) and the uncommitted office-hours notes in the main checkout (`logbook.d/2026-11-03-cowork-office-hours.md`, `docs/research/office-hours-2026-11-03-tomasso-notes.md`). Three Dependabot branches (pandera, pytest, ruff) are open.

### LB-101 · 2026-11-04 · Admin: Ben merges eight Oregon, holdout and dashboard PRs (#280–#282, #284, #286–#289) to `main` (auto-review)
- **Question:** Bring the Oregon setup (fifth state, run as the V9 transfer test), the statewide-holdout fixes and the data dashboard onto `main`. Intent inferred from the merges; Ben left no note.
- **What I did:** (from merge commits, 14:40–18:34 ET)
  - Merged #280 (`ws/data-dashboard`: coverage, parcels, reforms and growth by state) and #281 (`ws/or-transfer-setup`: statewide holdout by state FIPS, `config/states/or.yaml`, V9 in the validation plan, WS-OR brief) at 14:40, then #282 (`ws/or-package`: Oregon adapter package kept as `or`), #287 (`ws/core-v9-holdout-gaps`: BPS region from config, ACS stock filter, state totals; Ben's note that the Oregon freeze is conditional on observed market inputs), #288 (`ws/core-v9-null-geoid`: statewide holdout also hides rows with no GEOID, a V9 leak found by WS-OR), #286 (`ws/or-fees`: Portland, Bend, Salem SDC rows; Eugene water only), #289 (`ws/or-config`) and #284 (`ws/or-state-law`: SB 1051, HB 2001, SB 458, 2023 c.223, HB 2138 rows with a second-coder pass).
- **Inputs:** PRs #280–#282, #284, #286–#289 and their branches.
- **Outputs:** `origin/main` at cb60a5c (local `main` pulled to the same commit).
- **Findings:** none new; each PR's work has its own fragment (`logbook.d/2026-11-04-or-assessment.md`, `-ws-data-dashboard.md`, `-ws-or-package.md`, `-core-v9-holdout-gaps.md`, `-ws-or-fees.md`, `-ws-or-config.md`, `-ws-or-state-law.md`), now on `main` awaiting the fold.
- **Decisions:** the fragments record Ben's 2026-11-04 decisions (V9 freeze conditional on observed market inputs; Portland fee baseline, Eugene kept on the Handbook prior, accepted non-BPS gap). None has a dated row in `HANDOFF.md`.
- **AI:** Claude Code wrote the merged PRs (logged in their fragments); the merges are Ben's. Logged by the nightly review from git history, without rerunning tests.
- **Open / next:** fold the `logbook.d/` fragments. Pushed but not merged, with fragments: `ws/or-local-rules` (Portland, Bend and Metro rule rows, checked row by row in the evening by Ben's validation agent), `ws/or-readiness` (Oregon readiness report for the V9 freeze, 22 local rows, 28 county SB 1051 rows), `ws/engine-14-unseen-state` (D-043, then D-044 adopted: τ drawn from its profile, `adu_state_effect.yaml`). Office-hours notes (`logbook.d/2026-11-03-cowork-office-hours.md`, `docs/research/office-hours-2026-11-03-tomasso-notes.md`) are still uncommitted in the main checkout.

### LB-102 · 2026-11-04 · Study design: D-048, the D-041 ADU model without the ramp, pre-registered (auto-review)
- **Question:** D-047 chose no ramp in every fold and the D-045 audit found counts flat where the ramp expected 3–5× growth. Does D-041 do better with the ramp removed and nothing else changed?
- **What I did:** (from commits 04f9fde, 3c5228d, 20:50–20:51 ET)
  - Wrote D-048 in `docs/analysis_plan.md` before any fit (approved by Ben, 2026-11-04): ramp = 1 from the effective date; D-041 counts, fit places, test set, rule-share grid and gamma place effects unchanged. Reports: full fit beside D-041's log-likelihood (−383.718), leave-one-state-out (K1 vs 0.791, P90/P10 vs 28.0), test set.
  - Fixed the adoption rule in advance: adopt only if no state is missed, K1 < 0.791 and the test set is not missed; else keep D-041. On adoption, the scenario ramp, θ, α and `adu_anchor.yaml` are refitted in separate PRs, and five-year totals will rise.
  - Added a correction to D-047: its chart and PR comment called D-041's Raleigh–Durham test set useful; it was inside only (observed 410 vs P50 159).
  - Added the no-ramp run to `scripts/dev/calibrate_shape.py` with a test in `tests/model/test_calibrate_shape.py`.
- **Inputs:** D-041, D-045–D-047 (fragment `logbook.d/2026-11-04-ws-engine-15-fit-audit.md`).
- **Outputs:** `docs/analysis_plan.md` (D-048 and the D-047 correction), `scripts/dev/calibrate_shape.py`, `tests/model/test_calibrate_shape.py` on local branch `ws/engine-15-fit-audit` (two commits ahead of `origin`, no PR).
- **Findings:** none yet; the run had not been made at scan time.
- **Decisions:** D-048 method approved by Ben (2026-11-04); no HANDOFF row.
- **AI:** Claude Code wrote the entry, script and test (co-authored commits); the fragment ends at proposing D-048, so this step is logged by the nightly review. Not re-run.
- **Open / next:** run D-048 once and apply the fixed adoption rule; push the branch.

### LB-103 · 2026-11-05 · Admin: Ben merges fifteen ADU-fit, V9 and Oregon PRs (#279, #285, #290–#302) to `main` (auto-review)
- **Question:** Bring the ADU fit audit and the D-048 adoption, the V9 Oregon transfer test (runner, freeze, scoring, release) and the remaining Oregon data work onto `main`. Intent inferred from the merges and the fragments' quotes of Ben ("Adopt D-048", "unblind and score", "start it"); Ben left no merge note.
- **What I did:** (from first-parent merge commits on `origin/main`, Nov 4 21:04 to Nov 5 17:16 ET)
  - Nov 4 evening: #290 (`ws/or-local-rules`), #291 (`ws/or-readiness`).
  - Overnight: #292 (`ws/v9-or-freeze-runner`, D-046 runner, later renumbered), #294 (`ws/v9-adu-history`: own-history ADU variant, Portland pre-2018 counts), #293 (`ws/or-statelaw-validation`: 2023 duplex tier and county ADU rows), #296 (`ws/renumber-v9-decisions`: V9's D-046 → D-051 and D-049 → D-052, clashing with #285's numbers), then #279 (`ws/engine-14-unseen-state`, D-043/D-044), #285 (`ws/engine-15-fit-audit`: D-045 to D-049, including D-048's not-adopted result and the D-049 held-out log score) and #295 (`ws/engine-16-adopt-d048`: D-048 adopted, θ 0.000659 and α 2.214 refitted, `adu_anchor.yaml` regenerated, D-050 state effect re-estimated, `adu_state_effect.yaml` regenerated).
  - Morning: #297 (`ws/v9-state-effect`: V9 draws τ as the scenario does), #298 (`ws/v9-or-freeze`: `results/frozen/V9-OR-TRANSFER.json`), #299 (`ws/v9-or-score`: missing-middle scores), #300 (`ws/or-permit-adapters`: Portland and Bend), #301 (`ws/v9-or-score-adu`: ADU scores). Afternoon: #302 (`ws/or-release`: `Holdout.released_on`, V9-OR-TRANSFER released 2026-11-05).
- **Inputs:** the PRs above and their branches.
- **Outputs:** `origin/main` at 583b94c. The local checkout's `main` is at de54d9c (#301), one merge behind.
- **Findings:** from the fragments, not re-checked: the V9 missing-middle headline (1,753 built, P10 1,738) is inside its range by 15 buildings but the model over-predicts HB 2001's response; every ADU target missed (Portland 1,930 against 3–1,418; Bend 414 against 0–206), so V9 fails its pass rule. Each PR's work has its own fragment (`logbook.d/2026-11-04-ws-or-local-rules.md`, `-ws-or-readiness.md`, `-v9-or-freeze-runner.md`, `-ws-engine-15-fit-audit.md`, `2026-11-05-v9-adu-own-history.md`, `-ws-or-statelaw-validation.md`, `-ws-engine-16-adopt-d048.md`, `-v9-state-effect.md`, `-v9-or-freeze.md`, `-v9-or-score-mm.md`, `-ws-or-permit-adapters.md`, `-v9-or-score-adu.md`, `-or-release.md`), now on `main` awaiting the fold.
- **Decisions:** the fragments record Ben's 2026-11-05 decisions: adopt D-048; unblind and score V9; release the V9 holdout with a dated field rather than delete it; the `released_on` shared-contract change. None has a dated row in `HANDOFF.md` (unchanged since the last scan).
- **AI:** Claude Code wrote the merged PRs (logged in their fragments); the merges are Ben's. Logged by the nightly review from git history, without rerunning tests or re-checking figures.
- **Open / next:** fold the `logbook.d/` fragments; pull `main` locally; add HANDOFF rows for D-048's adoption and the V9 release if Ben wants them there. Pushed but not merged, with a fragment: `ws/or-pool` (Oregon's full data rebuilt, `v9.FIT_STATES` pins V9 to the four fit states, D-053 drafted; see LB-104). Office-hours notes from Nov 3 are still uncommitted in the main checkout.

### LB-104 · 2026-11-05 · Validation: D-053 run, Oregon added to the ADU calibration; not adopted, a coding question first (auto-review)
- **Question:** What happens to the ADU fit when Portland and Bend (2016–2025, 20 place-years) join the four-state D-048 fit, as drafted in D-053?
- **What I did:** (from the "D-053 Oregon Refit" artifact, dated run 2026-11-05; the run itself is not in any commit or fragment the review could see)
  - Refit θ with all five states and leaving each state out; reran leave-one-state-out with the state spread drawn; re-estimated τ (D-050 method) with Oregon in; compared Portland's and Bend's yearly permits against both fits.
  - Published the results as a dashboard with a decision panel.
- **Inputs:** D-048, D-050, the Oregon data rebuilt on `ws/or-pool` (fragment `logbook.d/2026-11-05-or-pool.md`).
- **Outputs:** [D-053 Oregon Refit](https://claude.ai/artifact/LimqtUsaCT4MiPmTCjtoTg); per the artifact, `reports/adu-d053-fit/` and `reports/adu-tau-draws-d053/` on branch `ws/or-pool`, draft PR #303. The branch's latest visible commit (ebb02b4) only drafts D-053, so the run outputs may be uncommitted or gitignored.
- **Findings:**
  - Adding Oregon halves θ (0.308 per 1,000, 0.213–0.463, against D-048's 0.659); the fit without Oregon reproduces D-048 exactly.
  - Leave-one-state-out with the state spread: every state inside its range, Oregon only just (3,363 built, P90 3,925); without the spread Oregon is missed. τ̂ rises from 0 to 0.57, widening a new state's range from about ×0.5–×2 to ×0.33–×3.
  - The partial-rule share jumps from the judgment value 0.3 to an estimated 1.0, which the artifact traces to blank fields in Portland's 2016–2020 rule row (parking, size cap, owner occupancy) rather than behaviour; it proposes filling them in `config/reforms/or.csv` and rerunning.
- **Decisions:** none. The artifact marks D-053 "not yet adopted" and the partial-rule share as needing Ben's decision before any config is written. Whether Ben approved the run itself (the fragment said D-053 waited for approval) was not found.
- **AI:** Claude ran the fit and built the artifact (session not identified); no fragment found, so logged by the nightly review from the artifact. Figures copied from the artifact, not re-checked.
- **Open / next:** Ben's call on Portland's rule coding and the partial-rule share; commit the D-053 run outputs and a fragment on `ws/or-pool`; then decide on adopting D-053.

### LB-105 · 2026-11-06 · Admin: Ben merges twenty-two Oregon, engine, missing-middle and app PRs (#303, #305–#309, #311–#326) to `main` (auto-review)
- **Question:** Bring the D-053 Oregon ADU refit, the missing-middle backtests and refit, the parcel-proxy and housing-need work, and the first build of the app onto `main`. Intent inferred from the merges and the fragments; Ben left no merge note.
- **What I did:** (from first-parent merge commits on `origin/main`, 06:52–16:19 ET)
  - Morning: #303 (`ws/or-pool`: D-053 run and adopted, five-state ADU fit, θ 0.308 per 1,000), #308 (`ws/dashboard-fallback-fill`: Census-fallback counties shown as estimated), #306 (`ws/mm-d054`: missing-middle statewide backtest, leave one state out), #312 (`ws/mm-d055`: D-054's refit adopted in `mm_hazard.yaml` after a V9 Oregon re-score).
  - Midday: #305 (`ws/or-rlis-parcels`: Metro tax lots from RLIS joined to regional zoning), #307 (`ws/engine-d053-proxy-test`, renumbered D-056: ACS one-unit detached homes as the parcel denominator for states without parcels, passed), #309 (`ws/engine-housing-need`, D-057: `housing_need.yaml`, share of need), #311 (`ws/engine-results-schema`: results bundle schema 1.10, `lotline results --all`).
  - Afternoon: #320 (identity: Mondrian compact mark, favicon, missing middle green and fee reduction vermilion), #313, #314, #315, #318, #319 (WS-APP: one static page built from results bundles, three sections, data tier, trust section, one page per section), #316 (`ws/mm-d056`, renumbered D-058: baseline rule for unstable pre-reform pace, run, config unchanged), #321, #322, #324, #325, #326 (app: data dashboard folded into the data tab, slider rule marked provisional, fonts committed and inlined, data-tab summary, page background), #323 (`ws/mm-d059`: backtest without Lubbock; Ben kept D-055's values) and #317 (`ws/engine-adu-fit-range`: D-060 method, see LB-106).
- **Inputs:** the PRs above and their branches; the HANDOFF rows added in eef000c (app shape, Ben 2026-11-06).
- **Outputs:** `origin/main` at 72a8cb4. The local checkout's `main` is at 29665b8 (Nov 6 07:31 ET), behind. Results pages for the runs: [D-054](https://claude.ai/artifact/M24pZ4HRhhxvGxmTHrQNqv), [D-055](https://claude.ai/artifact/N5tC4z7ZEwKVEWzFwaqknX), [D-058](https://claude.ai/artifact/XvRsYZGDB1vv1GE8Kzc5Kg), [D-059](https://claude.ai/artifact/A1xAvPmBvyp1MP4dCDGHQ6), [D-053](https://claude.ai/artifact/LimqtUsaCT4MiPmTCjtoTg) (updated); [Lotline Visual Identity Brief](https://claude.ai/artifact/21FhKZdVH2axzz3nQFThtA); the [Lotline](https://claude.ai/artifact/XW95915mHhn65atvgS5Vye) artifact was also updated on Nov 6 (not opened by the review).
- **Findings:** from the fragments, not re-checked: D-055's refit scores V9 Oregon's 2018–2025 missing-middle total far better than D-038 (CRPS 84.8 against 690.6; median 1,673 against 1,753 built), but misses 2018–2022 and place coverage falls (0.43 against 0.57), and Oregon was not blind. D-059 without Lubbock gives θ within 5% of the adopted value, NC and TX useful, and an effect under 2 SE. Each PR's work has its own fragment (`logbook.d/2026-11-05-or-pool.md` and the 2026-11-06 fragments: `cowork-app-shape`, `identity`, `ws-app-*` (10), `ws-dashboard-fallback-fill`, `ws-engine-adu-fit-range`, `ws-engine-d053-proxy-test`, `ws-engine-housing-need`, `ws-engine-results-bundle`, `ws-mm-d054`, `ws-mm-d055`, `ws-mm-d058`, `ws-mm-d059`, `ws-or-rlis-parcels`), now on `main` awaiting the fold.
- **Decisions:** the fragments record Ben's 2026-11-06 decisions: the app's shape (two HANDOFF rows in eef000c, the only HANDOFF change since the last scan); D-053 adopted; D-054 method; D-055 adopted; D-058 approved; D-059 run, keeping D-055's values; D-060 method approved; overlap flag on the eligible-weighted median distance; the provisional slider rule and app background. Other decisions are listed in fragments as "proposed for HANDOFF".
- **AI:** Claude Code wrote the merged PRs (logged in their fragments); the merges are Ben's. Logged by the nightly review from git history, without rerunning tests or re-checking figures.
- **Open / next:** fold the `logbook.d/` fragments; pull `main` locally. The main checkout also holds uncommitted identity edits (mark SVGs, tokens, style guide, a favicon SVG, an updated identity fragment) and an untracked `Claude outputs/` folder with three mark-option PNGs from Nov 6 morning; they look like the pre-PR copy of #320's work, so check before discarding. Local branch `ws/forecast-window` (no commits of its own yet) exists; its purpose is not recorded.

### LB-106 · 2026-11-06 · Engine: D-060 run, the fit-set ADU calibration range adopted (branch, not merged) (auto-review)
- **Question:** Should the ADU calibration range (rent, value and rate bands) come from the five fit states rather than the current West Coast reference, as pre-registered in D-060 (approved by Ben as "D-058" before renumbering)?
- **What I did:** (from commit 03ce934, 16:27 ET, on `ws/engine-adu-fit-range-run`; the branch's fragment still ends at the method step)
  - Ran leave one state out over the five states with widening, for three arms: no widening, C (current range) and F (fit set).
  - Applied the pre-registered gates: both passed, so `config/params/hazard.yaml` now holds the fit set's range (generated by `scripts/dev/adu_reference.py --fit-set --write`); V9 stays pinned to the old range through `hazard.PRE_D060_CALIBRATION`.
- **Inputs:** D-053 fit, D-060 method (`docs/analysis_plan.md`), the five states' place data.
- **Outputs:** `reports/adu-d060-range/` (`summary.csv`, `ranges.csv`, `places.csv`, `statewide.csv`, `run-2026-11-06-log.txt`); `config/params/hazard.yaml`, `config/params/aggregate.yaml`; code and tests in `src/lotline/model/calibrate_adu.py`, `hazard.py`, `validation/v9.py`, `scripts/dev/calibrate_adu.py`, `tests/model/` and `tests/core/test_v9.py`. Pushed to `origin/ws/engine-adu-fit-range-run`; no PR found by the review.
- **Findings:** no state missed under either range; place P10–P90 coverage 73.6% (fit set) against 74.1% (West Coast). The fit-set rent band is $1,237–$1,855 against $1,573–$2,034, and the value band $218,000–$597,000 against $519,000–$836,000. The overlap-flag thresholds were not retuned, and all five fit states now read high.
- **Decisions:** adoption follows the pre-registered rule in D-060; no HANDOFF row.
- **AI:** Claude Code ran the test and wrote the code (co-authored commit); no fragment for the run, so logged by the nightly review from the commit and report files. Figures copied from `summary.csv` and `ranges.csv`, not re-checked.
- **Open / next:** add the run to the branch's fragment; open and merge a PR; decide whether to retune the overlap-flag thresholds now that every fit state reads high.

### LB-107 · 2026-11-07 · Engine: D-061 five-year forecast window moved to 2027–2031 (proposed, branch) (auto-review)
- **Question:** The entry is read in 2027; should the five-year projection still run 2026–2030 from the 2025 data origin, given that the Handbook and Rules fix a five-year horizon but no start year?
- **What I did:** (from commits 06a0cd1 and 25b0df4 on `ws/forecast-window` and its fragment `logbook.d/2026-11-06-ws-forecast-window.md`)
  - Drafted D-061 (first numbered D-059, renumbered because `main` already uses D-059 and D-060): new parameter `forecast_lead_years` = 1, so origin 2025 gives 2027–2031; the baseline simulates the lead year and drops it; ADU and fee scenarios start their reform clock in 2027 (ADU runs the lead year under current rules only).
  - Kept the registered V1 backtest with no gap (`v1_lead_years` = 0) so V1 and frozen predictions reproduce; added hand-worked tests, including one checking lead-1 draws equal years 2–6 of a lead-0 six-year run; regenerated the results fixture; merged `origin/main` into the branch.
- **Inputs:** Handbook and Rules (via a fetch agent); `baseline.py`, scenario and results code.
- **Outputs:** `docs/analysis_plan.md` (D-061), `config/params/baseline.yaml`, `aggregate.yaml`, `market.yaml`, `src/lotline/model/{baseline,backtest,results}.py`, `scenarios/{adu,fees}.py`, `scripts/dev/{adu,fee}_dev_run.py`, `tests/model/test_forecast_window.py` and updated tests, `tests/fixtures/results/zz/bundle.json`. Pushed to `origin/ws/forecast-window` (3 commits ahead of `main`; D-062 refers to this as PR #328, not checked).
- **Findings:** no runs on real data. Four open items listed in D-061: which rules count as "current" in the lead year, the housing-need denominator's years, the bundle metadata, and results already published.
- **Decisions:** D-061 proposed; HANDOFF row proposed in the PR description, not added.
- **AI:** Claude Code wrote the code, tests and fragment and ran the full suite and `compliance_check.py` (per the fragment). Logged by the nightly review from the commits; not re-run.
- **Open / next:** Ben's approval of D-061 and the four open items; merge; regenerate published results on the new window.

### LB-108 · 2026-11-07 · Engine: Ben keeps the overlap-flag thresholds after D-060 (auto-review)
- **Question:** With D-060's fit-set range, all five fit states' overlap flags read high (LB-106); should the 0.5 / 1.0 thresholds be retuned?
- **What I did:** (from commits a12932d and 50d45d1 on `ws/engine-adu-fit-range-run`) recorded Ben's answer in D-060, the `aggregate.yaml` notes and the branch fragment.
- **Inputs:** LB-106; D-060.
- **Outputs:** `docs/analysis_plan.md`, `config/params/aggregate.yaml`, `logbook.d/2026-11-06-ws-engine-adu-fit-range-run.md` (now covers the run and the decision). Branch 4 commits ahead of `main`, not merged.
- **Findings:** the fragment also notes D-053's published table no longer reproduces on today's `main` (D-053's own command, rerun, matches the no-widening arm).
- **Decisions:** thresholds kept (Ben, 2026-11-07, "Keep thresholds"); no HANDOFF row.
- **AI:** Claude Code made the edits; logged by the nightly review from the commits.
- **Open / next:** merge the branch; decide whether to regenerate D-053's table.

### LB-109 · 2026-11-07 · WS-APP: state map on the results page, coloured by data tier (branch) (auto-review)
- **Question:** How does a visitor see which states Lotline has run, how much local data each rests on, and what to do about one it hasn't run?
- **What I did:** (from commit 926d206 on `ws/app-map` and fragment `logbook.d/2026-11-07-ws-app-map.md`)
  - Added a tile grid of the 50 states and DC at the top of Results: states with a results bundle are shaded by data tier on the identity's tier ramp and switch the page on click; grey states link to a new README section, "Bring your own state". `?state=` in the URL now switches state.
  - Chose a tile grid over drawn boundaries: no new library or geometry download, works offline.
- **Inputs:** WS-APP brief; identity tokens; `challenge.toml`.
- **Outputs:** `src/lotline/app/us_tiles.yaml`, `build.py` (`tile_map()`, `TIER_TOKENS`), `template.html`; `README.md` ("Bring your own state"); `tests/app/test_build.py`. Pushed to `origin/ws/app-map`, one commit ahead of `main`.
- **Findings:** none beyond the build.
- **Decisions:** none recorded.
- **AI:** Claude Code (WS-APP instance) wrote it; checked by `tests/app`, `compliance_check.py` and a browser pass with four synthetic bundles at desktop and phone width, light and dark (per the fragment). Not re-checked by the review.
- **Open / next:** PR and merge.

### LB-110 · 2026-11-07 · Missing middle: Lubbock second coder; D-062 five-year-rate range and D-063 scenario module proposed (auto-review)
- **Question:** After D-059, what was Lubbock's missing-middle rule really; how should the scenario carry the θ–ramp trade-off; and what should `model/scenarios/mm.py` compute?
- **What I did:** (from commit 7114974 on `ws/mm-followups` and fragment `logbook.d/2026-11-07-ws-mm-followups.md`)
  - Second-coded `TX-4845000-missing_middle-2023` from web sources (a fresh-context Claude subagent; the first coder was also Claude, so not a human second coder).
  - Drafted D-062: put the scenario's range on the five-year rate r5 = θ × mean ramp share, because θ's 90% interval (0.0325–1.006 per 1,000) is profiled over every half-way point while V9 and the scenario hold the ramp at 0.5.
  - Drafted D-063, the Handbook missing-middle scenario: added buildings ~ Poisson(h_t × u × E × (1 − current dose) × F(PCR)/F(1)), with four choices for Ben (5–6 unit buildings, teardowns, three stories/FAR, holdouts).
- **Inputs:** `config/reforms/tx.csv`, Lubbock Ch. 39 and staff reports, `mm_hazard.yaml`, `hazard.ramp`.
- **Outputs:** `docs/research/ordinances/tx-second-coder-lubbock-2026-11-07.csv` and `.md`; `docs/research/ordinances/README.md`; `docs/analysis_plan.md` (D-062, D-063). Pushed to `origin/ws/mm-followups`, one commit ahead of `main`.
- **Findings:** the second coder partly agrees: the 2023 cells hold, but old R-2 already allowed duplexes (maps to MDR) and the SF-2 gain is limited by the block-face rule; `tx.csv` not edited. Top θ draws at a fast ramp give about 0.85 per 1,000 a year, against 0.04–0.10 at either fitted peak.
- **Decisions:** D-062 and D-063 proposed, not run; no code. No HANDOFF row.
- **AI:** Claude Code and a subagent; m(half) values computed by hand from `hazard.ramp`; no model run, no data read, no holdout touched (per the fragment). Logged by the nightly review.
- **Open / next:** Ben's call on D-062, D-063's four choices and whether to edit Lubbock's row; then code and run `calibrate_mm_d062.py`.

### LB-111 · 2026-11-08 · Engine: D-062 run, the missing-middle five-year rate; config range stands (branch) (auto-review)
- **Question:** Does θ's wide 90% interval (LB-110) still hold once the range is put on the five-year rate r5 = θ × mean ramp share, as D-062 proposed?
- **What I did:** (from commits 84986bc and dc9358f on `ws/mm-followups` and fragment `logbook.d/2026-11-07-ws-mm-followups.md`)
  - Added `calibrate_mm.ramp_mean` and `five_year_profile` with hand-worked tests, and `scripts/dev/calibrate_mm_d062.py`.
  - Profiled r5 over ramp speeds on fit-set place-years only; asserted the main fit reproduces D-055's θ.
- **Inputs:** D-055 fit, D-062 (`docs/analysis_plan.md`), `hazard.ramp`.
- **Outputs:** `src/lotline/model/calibrate_mm.py`, `tests/model/test_calibrate_mm.py`, `scripts/dev/calibrate_mm_d062.py`; `reports/mm-d062/` (`summary.json`, `by_half.csv`, `profile_curve.csv`, `d062-results.html`, `run-2026-11-08-log.txt`); results in D-062; page [D-062 Five-Year Rate](https://claude.ai/artifact/UJooP3X5oNfwCZ2vFvmJW7).
- **Findings:** r5 = 0.104 per 1,000 a year (0.027–0.85), 0.08–0.11 at every ramp speed. θ's top end comes from place spread at the fast ramp, not the slow peak, so D-062's premise was wrong and the configured range already matches; no config change.
- **Decisions:** none; no HANDOFF row. Run on Ben's go-ahead ("Run D-062", per the fragment).
- **AI:** Claude Code wrote the code and ran it (co-authored commits); logged by the nightly review from the commits and fragment, figures not re-checked.
- **Open / next:** merge `ws/mm-followups` (9 commits ahead of `main`). Note the number clash in LB-116: a second "D-062" exists on another branch.

### LB-112 · 2026-11-08 · Missing middle: D-063 approved, scenario module coded and run on five states (branch) (auto-review)
- **Question:** Under the Handbook missing-middle scenario (2–6 units, three stories, on single-family parcels), how many net homes does each of the five states add over five years?
- **What I did:** (from commits 71b5871, 7c9a717, 7701a1d, 40ba649 and 066c12e on `ws/mm-followups` and its fragment)
  - Ben approved D-063 with each of the four choices taken as proposed ("Approve D-063"). Wrote `scenarios/mm.py` with 12 hand-worked tests and four keys in `config/params/mm.yaml`; recorded two deviations in D-063 (teardowns as one house per replaced lot, Binomial on a house share; house share from each place's latest roll).
  - Ran all five states (4,000 draws) with `scripts/dev/mm_scenario_run.py`; checked the page against `summary.csv` and `inputs.json`.
  - Ben then narrowed homes per building ("Yes, narrow it"): `mm_units_per_project` high 4.0 → 2.75 (the largest state ratio on 100+ buildings, Ohio; Minnesota's 4.0 rested on 10 buildings). Reran into the same folder; page version 2.
- **Inputs:** D-055 fit, D-063, five states' place data and rules.
- **Outputs:** `src/lotline/model/scenarios/mm.py`, `tests/model/test_scenario_mm.py`, `config/params/mm.yaml`, `config/params/mm_hazard.yaml`, `docs/model_and_assumptions.md`, `docs/analysis_plan.md` (D-063); `scripts/dev/mm_scenario_run.py`; `reports/mm-scenario-2026-11-08/` (`summary.csv`, `places.csv`, `inputs.json`, `params.json`, `draws_*.npz`, `run-log.txt`, `scenario-results.html`); page [Missing-Middle Scenario Run](https://claude.ai/artifact/T7fwy1ke9B62Jm1Ea9FVNS).
- **Findings:** net added homes over five years, P50 (P10–P90), after narrowing: TX 4,747 (1,152–20,518), NC 1,193 (299–5,263), OH 1,071 (266–4,271), MN 704 (180–2,928), OR 94 (20–435); first run was about 25% higher (TX 5,968). Teardowns take back about a third of gross homes; holding homes per building at 2.08 gives about 14% less. V9's frozen record uses only the central 2.08, so it is unaffected.
- **Decisions:** D-063 approved and the homes-per-building range narrowed (Ben, 2026-11-08), both recorded in D-063; no HANDOFF row.
- **AI:** Claude Code wrote the module, tests and run script and ran them (co-authored commits). Logged by the nightly review from the commits and fragment; figures copied from D-063, not re-checked. The runs predate the merge of D-061's 2027–2031 window into this branch (2152565, 15:35 ET); whether that changes the scenario was not checked by the review.
- **Open / next:** the results-bundle `mm` part (`model/results.py`, WS-APP contract); confirm the runs on the D-061 window; merge `ws/mm-followups`.

### LB-113 · 2026-11-08 · Engine: D-061 adopted; 2027–2031 window merged to main (auto-review)
- **Question:** After review, does the 2027–2031 forecast window (LB-107) stand?
- **What I did:** (from PR #328, merged 05:16 ET, and PR #331, commit 20ee424, with fragment `logbook.d/2026-11-08-ws-adopt-d061.md`) Ben adopted D-061 as written; the entry was marked adopted, the `forecast_lead_years` source updated, the parameter table regenerated and a HANDOFF row added. `main` was then merged into `ws/mm-followups` (2152565).
- **Inputs:** LB-107; D-061.
- **Outputs:** `docs/analysis_plan.md`, `config/params/baseline.yaml`, `docs/model_and_assumptions.md`, `HANDOFF.md`; the D-061 code from LB-107 now on `main`.
- **Findings:** no code or numbers changed by the adoption itself.
- **Decisions:** HANDOFF row 2026-11-08: the five-year window is 2027–2031 (D-061).
- **AI:** Claude Code made the edits and ran `compliance_check.py` (per the fragment); logged by the nightly review.
- **Open / next:** D-061's remaining open items: housing-need years, bundle metadata (#333 per LB-116's fragment), relabelling earlier results. "Which rules count as current" is taken up in LB-116.

### LB-114 · 2026-11-08 · WS-APP: state map merged; one file per state, loaded when picked (auto-review)
- **Question:** Can the page carry all 51 states if each gets a precomputed run, and what does the map say once few states are grey?
- **What I did:** (from commits 17869bd, 6c29d40, 79ac5d8, 79706f9; PRs #329 and #332 merged; fragments `logbook.d/2026-11-07-ws-app-map.md` and `2026-11-08-ws-app-lazy-states.md`)
  - Map follow-up (Ben): the "bring your own data" call to action also sits on the tier-3 legend entry; the grey entry shows only while a grey state remains.
  - The page now embeds only each state's meta; `build_app` writes each full bundle to `states/<st>.js` and the page loads it on first pick (scripts, not JSON, so it still opens from disk).
  - Cleared CodeQL `js/xss-through-dom` alerts: embedded values go through `esc()`, and the script path is built from the checked two-letter code.
- **Inputs:** LB-109; WS-APP brief.
- **Outputs:** `src/lotline/app/build.py`, `template.html`, `scripts/build_app.py`, `README.md`, `tests/app/test_build.py`; both fragments.
- **Findings:** a full bundle is about 2 MB at 1,000 draws, so embedding 51 states would make the page about 100 MB. #329 was merged with a failing non-required CodeQL check unnoticed; merges now check every check.
- **Decisions:** load-on-demand agreed by Ben (per the fragment); no HANDOFF row.
- **AI:** Claude Code (WS-APP instance); `tests/app` (36 passed), `compliance_check.py` and a browser pass over http with synthetic bundles (per the fragment). Opening from `file://` was not tested by the browser tool. Logged by the nightly review.
- **Open / next:** real results bundles.

### LB-115 · 2026-11-08 · WS-APP: publish the app to GitHub Pages from a results release (branch) (auto-review)
- **Question:** How does the app reach a public URL when results come from downloaded data that can't be committed and CI can't rebuild?
- **What I did:** (from commit 7f4c660 on `ws/app-pages-deploy` and fragment `logbook.d/2026-11-08-ws-app-pages-deploy.md`) wrote `scripts/publish_app.py`, which checks and stages every results bundle and, with `--go`, uploads them as a GitHub release at the current commit and starts a new manual Pages workflow that builds the page at that tag and deploys it.
- **Inputs:** WS-APP brief; the no-committed-data rule.
- **Outputs:** `scripts/publish_app.py`, `.github/workflows/pages.yml`, `src/lotline/app/build.py` (`stage_release()`, `release_inputs()`), `scripts/build_app.py --from-release`, `README.md` ("The app"), `tests/app/test_build.py`. Pushed to `origin/ws/app-pages-deploy`, one commit ahead of `main`.
- **Findings:** release assets aren't commits, and each release pins the exact results and code behind a published version. Nothing deployed yet.
- **Decisions:** HANDOFF row proposed in the fragment (published app built in CI from a GitHub release of results bundles), not added.
- **AI:** Claude Code (WS-APP instance); `tests/app` (40 passed), `compliance_check.py`, and dry runs of `build_app.py --from-release` and `publish_app.py` without `--go` on the fixture (per the fragment). The workflow has not run. Logged by the nightly review.
- **Open / next:** Ben enables Pages (Settings → Pages → Source "GitHub Actions"); first real bundles and deploy; set `challenge.toml` `tool_url`; check the page in a private window; merge.

### LB-116 · 2026-11-08 · Engine: "current rules" are those in force by 31 Dec of the window's first year (branch; numbered D-062) (auto-review)
- **Question:** With the 2027–2031 window, which coded rules count as current in the baseline rather than as reform (D-061 open item 1)?
- **What I did:** (from commit 150fde4 on `ws/d062-current-rules` and fragment `logbook.d/2026-11-08-ws-d062-current-rules.md`) Ben chose rules in force by the window's start (2027-12-31). Wrote the entry before code or run, then added `current_rules_window_years` = 1 (low 0 = 2026-12-31), `baseline.rules_as_of` and its use in `adu.places_from_store`; listed the 28 ADU rows that enter the baseline (NC 21, 19 of them S.L. 2026-59; TX 5; MN 2) and classified the 26 affected places from the rules config.
- **Inputs:** D-061; rules configs.
- **Outputs:** `docs/analysis_plan.md`, `config/params/baseline.yaml`, `src/lotline/model/baseline.py`, `src/lotline/model/scenarios/adu.py`, `docs/model_and_assumptions.md`, `tests/model/test_current_rules_date.py`, `tests/model/test_scenario_adu.py`. Pushed to `origin/ws/d062-current-rules`, one commit ahead of `main`.
- **Findings:** expected effect is small, since D-053 already counts partial rules in full; most movement is in one TX place. No model run. **Number clash:** this entry is D-062 on its branch, while `ws/mm-followups` already uses D-062 for the five-year rate (LB-110, LB-111); neither is on `main`, so one needs renumbering before merge.
- **Decisions:** Ben's choice of date (2026-11-08); HANDOFF row proposed in the PR description, not added.
- **AI:** Claude Code drafted the entry, code and tests; related tests (532), ruff and `compliance_check.py` (0 FAIL) pass (per the fragment). Logged by the nightly review.
- **Open / next:** resolve the D-062 number; merge; run the ADU scenario with the new baseline date.

### LB-117 · 2026-11-09 · Engine: the results bundle carries missing middle and the baseline; D-064 renumbered and applied to missing middle; window label fixed (auto-review)
- **Question:** Can the app show the missing-middle scenario and the no-change baseline from the same bundle, on the 2027–2031 window, with one "current rules" date across both reforms?
- **What I did:** (from PRs #335, #336, #338, #342 and fragments `2026-11-08-ws-d064-current-rules.md`, `2026-11-09-ws-mm-bundle.md`, `2026-11-09-app-window-label.md`, `2026-11-09-ws-baseline-export.md`)
  - Renumbered the current-rules decision D-062 → D-064 (resolves the clash in LB-116) and, at Ben's request, applied its date to `scenarios/mm.py` (38 rows enter: OR 34, MN 1, NC 2, TX 1).
  - `model/results.py` now runs the missing-middle scenario into the bundle (`ENGINE_SCENARIOS` = adu, missing_middle) and adds a `results_baseline` table (schemas 1.11), shown as a "With no policy change" card on the Results tab.
  - Fixed the page labelling the window 2026–2030: it now reads the window from the bundle (`AGG.windowLabel`).
- **Inputs:** LB-111 – LB-116; D-061, D-063, D-064.
- **Outputs:** `src/lotline/model/results.py`, `scenarios/mm.py`, `schemas.py` (1.11), `docs/schemas.md`, `src/lotline/app/aggregate.js`, `template.html`; tests `test_results.py`, `test_results_baseline.py`, `tests/app/test_window_label.py`; D-063/D-064 in `docs/analysis_plan.md`.
- **Findings:** a real NC bundle showed missing middle 177–3,000 net homes beside ADUs 47–361 (before the reruns in LB-119). A duplicate five-state run on PR #342 was reverted (2ab6021); its page is probably the artifact [Five-State Bundle Run](https://claude.ai/artifact/4ArC6Uxh1TJKFpCfPLQvz2) (not named in any fragment).
- **Decisions:** none new; HANDOFF rows proposed in PRs, not added.
- **AI:** Claude Code; tests, ruff, `compliance_check.py` and in-app browser checks (per the fragments). Logged by the nightly review.
- **Open / next:** see LB-119 for the reruns.

### LB-118 · 2026-11-09 · Engine: housing need over the 2027–2031 window; Texas from the Center's annual totals (auto-review)
- **Question:** How should the "% of housing need" denominator match the D-061 window (D-061 open item 2)?
- **What I did:** (from PRs #337, #339 and fragments `2026-11-09-ws-housing-need-window.md`, `2026-11-09-ws-tx-annual-projections.md`) Ben chose mid-2026 → mid-2031, interpolating between published years. `scripts/dev/housing_need.py` reads each demographer's years around the window; Ben then downloaded Texas's annual totals, registered as a manual source, which replaced the interpolation for Texas.
- **Inputs:** MN, NC, OH, OR and TX state population projections; D-057.
- **Outputs:** `scripts/dev/housing_need.py`, `config/params/housing_need.yaml`, `docs/model_and_assumptions.md`, `docs/analysis_plan.md` (D-061 item 2 settled), `tests/test_housing_need_window.py`.
- **Findings:** households added over the window: MN 45,989; NC 205,251; OH −33,316; OR 42,291; TX 681,001 (583,510–837,656). The earlier Texas low/high 2030 transcription (D-057) was off by 1,456–9,210 people.
- **Decisions:** Ben's choice of window years (2026-11-08); no HANDOFF row.
- **AI:** Claude Code found and parsed the sources, hand-checked NC and TX; the Texas zip form was left for Ben. Logged by the nightly review.
- **Open / next:** none stated.

### LB-119 · 2026-11-09 · Engine: first results on the 2027–2031 window; D-067 borrowed rule mix; D-068 Oregon no-state-rule prior and actual permits (auto-review)
- **Question:** What do the five states' ADU and missing-middle results look like after D-061, D-064 and the need change, and why does Oregon's ADU scenario add exactly 0?
- **What I did:** (from PRs #341, #344 and fragments `2026-11-09-ws-results-2027-window.md`, `2026-11-09-ws-or-adu-prior.md`)
  - On Ben's "Yes, rerun", ran `lotline results --all` with two comparison runs (old setup; new window with end-2025 rules) and diagnosed the drivers by place.
  - Ben chose the end-2025 rule mix for places that borrow their rules: D-067 pre-registered (bf563eb), coded, rerun as run D.
  - Ben chose a "no state rule" prior for places outside a state ADU law: D-068 pre-registered (f4ea9fa), coded, rerun as run E with the baseline; added actual 2021–2025 permits (`scripts/dev/observed_permits.py`).
- **Inputs:** LB-117, LB-118; D-022, D-061, D-064.
- **Outputs:** D-064 results bullet, D-067, D-068 in `docs/analysis_plan.md`; `adu.rule_inputs` (`prior_as_of`), `pool_dose`, `adu.no_state_rule_priors`, `StateConfig.adu_state_law_rows_complete`; `reports/results-2026-11-09/` (`results-2027-window.html`, `summary.csv`, `data.json`, `run-e.json`, `observed.json`); page [Results for 2027–2031](https://claude.ai/artifact/WF92C89mxGCqRajaa8CXNs) (version 3).
- **Findings:** the window alone only relabels; D-064 cut NC ADUs 37% and MN/NC missing middle 11%/6%, 70–88% of it through borrowed rules. Run D: NC ADUs 105, TX 1,356, MN missing middle 460, NC 773. Run E: Oregon ADUs 0 → 5 (2–12); every reform median is under 1% of its state's baseline. Austin's ADU permits drop from 243 (2023) to 9 (2025), probably HOME-era ADUs filed as 2–3 unit permits.
- **Decisions:** D-067 and D-068 (Ben, 2026-11-09); no HANDOFF rows.
- **AI:** Claude Code ran the bundles, wrote scratch diagnosis scripts, the code and hand-worked tests; page numbers taken from the bundles (per the fragments). Logged by the nightly review.
- **Open / next:** the Austin undercount (WS-TX adapter rule).

### LB-120 · 2026-11-09 · Fees: fee plan and Phase 0 decisions (D-065); fee levels by building type in 2025 dollars (D-066, #247) (auto-review)
- **Question:** After the 2026-11-03 office hours, what should the fee model still build, and what does each place really charge per unit by building type?
- **What I did:** (from PR #340 with #343 and fragments `2026-11-09-ws-fees-phase0.md`, `2026-11-09-ws-fees-phase1.md`)
  - Drafted a four-phase fee plan; Ben's Phase 0 choices became D-065 (D-032, D-033 adopted; D-034 replaced by a component-wise fill; three labelled scenarios `handbook`, `local_half`, `local_25k`; Handbook dollars read as 2025).
  - Wrote `model/fee_levels.py` (newest schedule per component plus still-in-force rows, CPI-U to 2025, low/high ranges, state-then-pooled median fill) and the three scenarios in `scenarios/fees.py`; schema columns (1.13 at merge); `docs/research/fee-levels-vs-handbook.md`.
  - Ben chose Eugene option (a) and confirmed D-066's details; Eugene's house priced at $17,508 ($25,365 high).
- **Inputs:** office-hours notes 2026-11-03; `config/fees/*.csv`; D-010, D-032 – D-034.
- **Outputs:** D-065, D-066 in `docs/analysis_plan.md`; `src/lotline/model/fee_levels.py`, `scenarios/fees.py`, `schemas.py`, `config/fees/*.csv`, `scripts/dev/fee_ranges_2026_11_09.py`, `fee_levels_table.py`, `eugene_fees_2026_11_09.py`, `docs/research/fee-levels-vs-handbook.md`; fee tests.
- **Findings:** house fee medians in 2025 dollars: MN $9,148, NC $9,632, TX $9,461, OR $33,553; no coded place reaches the Handbook's $50,000. 23 of 39 places had no permit fee and took a mostly Minnesota pooled median (addressed in LB-121).
- **Decisions:** D-065, D-066 (Ben, 2026-11-09); proposed for HANDOFF in the PR.
- **AI:** Claude Code; hand-worked tests (one wrong P25 caught and fixed), fee CSV values checked unchanged apart from new columns. No model run. Logged by the nightly review.
- **Open / next:** Phase 2 (LB-122).

### LB-121 · 2026-11-09 · Fees: fee lookups: duplex/fourplex water and sewer (D-069), building permits, and the largest uncoded places in four states (auto-review)
- **Question:** What do places really charge a duplex and fourplex for water/sewer, what do the places that borrowed the pooled permit median charge, and what do the largest uncoded places charge?
- **What I did:** (from PRs #345, #346, #349 and the `ws/fees-coverage-{mn,nc,oh,tx}` merges; fragments `2026-11-09-ws-fees-plex-utility.md`, `-fees-permits.md`, `-fees-coverage-{mn,nc,oh,tx}.md`)
  - Claude (Cowork) with research subagents read official schedules and coded rows through dated idempotent scripts: 38 duplex/fourplex water/sewer rows (10 places), 201 permit rows (20 of 24 places), and coverage rows for MN (62), NC (54), OH (110, new `config/fees/oh.csv`) and TX (34).
  - Recorded D-069: where metering is the builder's choice, one meter per unit is central and the master meter is the range.
- **Inputs:** Ben's local copies in `~/lotline-data/manual/nc_fees/`; city, county and utility schedules named in each row's `source`.
- **Outputs:** `config/fees/{mn,nc,oh,or,tx}.csv`; `scripts/dev/plex_utility_fees_2026_11_09.py`, `permit_fees_2026_11_09.py`, `coverage_fees_{mn,nc,oh,tx}_2026_11_09.py` (+ rows JSON); `docs/research/fee-levels-vs-handbook.md`; D-069.
- **Findings:** a master-metered fourplex pays well under the house fee per unit; NC and TX permit fees ($840–$3,760 a house) sit well below the $4,355 pooled fill. Ohio's coded house fees run $2,958–$15,826 (median $7,194) with no impact fees found. Several sources were blocked (Akron, Eagan, Buncombe, municode), so those places stay filled or partial.
- **Decisions:** D-069 (one meter per unit central). Proposed, not settled: NC places with no schedule take the NC median; whether a place with only SAC still gets a local connection fill.
- **AI:** quotes in the permit and plex rows were re-checked word for word where a local copy existed (53 permit rows) or by a second agent; coverage rows have blank quotes because sources were read only through a web-fetch summariser. Needs a human second coder. Logged by the nightly review.
- **Open / next:** a person opens the blocked sources (Johnston County first) and fills `verified_by`.

### LB-122 · 2026-11-09 · Fees: Phase 2, dose by building size, fee-rise sensitivity and pencil-out table (D-073) (branch) (auto-review)
- **Question:** How should a fee cut reach duplexes and fourplexes, and how do a house, duplex and fourplex pencil out at today's fees and after a cut?
- **What I did:** (from commits ba05152 and 2bba76f on `ws/fees-phase2`; fragment `2026-11-09-ws-fees-phase2.md`) Ben chose a per-type elasticity dose, no effect on 5+ unit buildings, stacking deferred and a +50% fee-rise sensitivity (D-073). Wrote `model/pencil_out.py`, a `local_rise` mode and per-size dose in `scenarios/fees.py`; on "Yes, run it", ran `fee_dev_run.py` for MN, NC, OH and TX.
- **Inputs:** LB-120, LB-121; office hours 2026-11-03 (A4, A5).
- **Outputs:** `src/lotline/model/pencil_out.py`, `scenarios/fees.py`, `config/params/fees.yaml`, `scripts/dev/fee_pencil_out_table.py`, `docs/research/fee-pencil-out.md`, `reports/fees-phase2-run/`; D-073; page [Fee Cut Results, Phase 2](https://claude.ai/artifact/LN5G4rajXAxVi3uhEXtwDs).
- **Findings:** the $50k benchmark cut adds +0.8% to +1.4% of baseline; real fees halved add +0.1% to +0.2%; the rise mirrors the cut.
- **Decisions:** D-073 (Ben, 2026-11-09).
- **AI:** Claude Code; hand-worked tests (37), full suite 1,712 passed; page statements checked against `totals.csv` (per the fragment). Logged by the nightly review.
- **Open / next:** better new-home values for NC, OH, TX; stacking; merge `ws/fees-phase2`.

### LB-123 · 2026-11-09 · WS-APP: the app goes live on GitHub Pages; plain gross/net wording, each state's permit record, data and model pages reordered (auto-review)
- **Question:** Can a judge open the app without running anything, and can a reader follow what the counts mean and how the method works?
- **What I did:** (from PRs #334, #347, #348 and fragments `2026-11-09-ws-app-release.md`, `2026-11-09-ws-app-net-new-wording.md`)
  - On "merge and push the release", rebuilt the five bundles (run E), published release `app-2026-11-09` and deployed Pages; set `challenge.toml` `tool_url` (D1). A second release `app-2026-11-09b` followed #348.
  - Ben's wording: "All new homes" / "Net new housing"; a "What gets built now, and what the reform would add" chart with actual permits 2019–2025 and the reform's yearly range (schemas 1.12, `results_observed`).
  - Reordered the data page (needs and years first, dashboard, sources last; tier card dropped) and the model page (goal → data → model and range → other states, with causal diagram, all 56 confounders and the tests table including failures).
- **Inputs:** LB-115, LB-119; `docs/analysis_plan.md`, `config/params/`.
- **Outputs:** live app https://cappellacci.github.io/lotline/; releases `app-2026-11-09`, `app-2026-11-09b`; `src/lotline/app/template.html`, `knobs.yaml`, `model/results.py`, `schemas.py` (1.12); app tests.
- **Findings:** Claude flagged `docs/model_and_assumptions.md` as stale in places; the app now follows `docs/analysis_plan.md`.
- **Decisions:** wording and page order by Ben; no HANDOFF row.
- **AI:** Claude Code; live page checked in the in-app browser, a subagent's fact brief re-checked against config (one misread placebo row corrected). Logged by the nightly review.
- **Open / next:** Ben checks the page in a private window (D3).

### LB-124 · 2026-11-09 · Research: office hours with Greg Miller; three new workstream briefs (auto-review)
- **Question:** What did Greg's review of the NC/TX ADU results say, and what should be done about it?
- **What I did:** (from the uncommitted fragment `logbook.d/2026-11-09-cowork-office-hours-greg.md` and new untracked files) Claude (Cowork) critiqued the walkthrough from the pasted transcript and listed action items; Ben set priorities (output simplicity and NC model quality first). Three workstream briefs were written from the action items.
- **Inputs:** meeting transcript (pasted by Ben); `HANDOFF.md`.
- **Outputs:** `docs/research/office-hours-2026-11-09-greg-miller-notes.md`; `docs/build/workstreams/WS-NC-GUTCHECK.md`, `WS-RESULTS-SIMPLE.md`, `WS-SCALE.md` (one settings file per state, graceful degradation, WI onboarding as proof). All uncommitted on `main`.
- **Findings:** NC's with-reform median (about 50) sat below history (about 100 a year) unexplained; no baseline shown; the results page should be a simple "two worlds" view.
- **Decisions:** none; a HANDOFF row for the "two worlds" page is to be proposed.
- **AI:** Claude (Cowork); no code run. Who wrote the three briefs is not stated in them. Logged by the nightly review.
- **Open / next:** commit the notes and briefs; WS-SCALE not started.

### LB-125 · 2026-11-09 · Engine: why NC's ADU forecast read below its history; trailing observed floor (D-070) (auto-review)
- **Question:** Is NC's low-looking ADU result a units mismatch, a calibration bug, or both (WS-NC-GUTCHECK)?
- **What I did:** (from PR #352 and fragment `2026-11-09-ws-nc-gutcheck.md`) audited units, compared the no-reform forecast with 2019–25, replaced the fixed 2019–2022 floor window with a trailing `adu_observed_years` = 4 (D-070), and added a `historical_floor` scorecard guardrail.
- **Inputs:** LB-124; holdout-filtered store; NC, TX, MN, OH ADU runs at 1,000 draws.
- **Outputs:** `reports/diagnostics/nc/` (README, before/after plots); `scripts/dev/gutcheck_diagnostics.py`; `src/lotline/model/gutcheck.py`; `config/params/adu.yaml`, `aggregate.yaml`, `config/historical_floor_reasons.yaml`; `tests/model/test_nc_gutcheck.py`; D-070.
- **Findings:** "about 50" matched no exported figure; like for like the no-reform forecast was 78 a year against 126 observed, because the floor stopped before NC's ADU take-off; after the fix 135 without the reform, 137 with. The added effect stays small because 81% of NC lots already allow ADUs. BPS and city permits agree (0.94–1.10).
- **Decisions:** D-070 proposed in the PR (merged with #352).
- **AI:** Claude Code; diagnostics reproduce the bundle's 40/105/301; no holdout bypassed (per the fragment). Logged by the nightly review.
- **Open / next:** two-worlds outcomes in the bundle (WS-CORE contract change); Austin HOME rule (WS-TX); official bundles not yet rebuilt.

### LB-126 · 2026-11-09 · Deliverables: results page as a simple data story, one tab per policy (branch; QC deploy) (auto-review)
- **Question:** Can a non-technical reader answer "how many more homes, compared with what, how sure" from the first screen (WS-RESULTS-SIMPLE)?
- **What I did:** (from commits 2e8011f and 81837c3 on `ws/results-simple`, tag `app-2026-11-09-results-qc`; fragment `2026-11-09-ws-results-simple.md`) wrote Section 1 copy with every number a bundle slot; rebuilt Section 1 with one tab per policy (Ben: no combined view), a two-worlds bar chart, funnel sentences and limits; wrote a 60-second usability check; deployed a QC build to Pages.
- **Inputs:** LB-124; release `app-2026-11-09` bundles.
- **Outputs:** `src/lotline/app/copy/results.md`, `copy/scenarios.yaml`, `template.html`, `build.py` (`policy_copy`), `tests/app/test_results_simple.py`, `docs/build/usability-check.md`.
- **Findings:** the reform is a thin slice of all building (NC ADUs about 260 on about 348,000); an honest with-reform range, the backtest line and three sliders need contract changes (Q1, Q3, Q4).
- **Decisions:** one tab per policy (Ben, 2026-11-09); proposed for HANDOFF.
- **AI:** Claude; app tests (55), a mutation check on hard-coded numbers, browser check of NC. Logged by the nightly review.
- **Open / next:** Ben QCs the Pages build and answers Q1–Q5; merge.

### LB-127 · 2026-11-09 · Validation: V5 Charlotte frozen blind and scored: pass (D-071); Mecklenburg permits follow the release (auto-review)
- **Question:** Before seeing outcomes, what does Lotline predict Mecklenburg County built in 2–4 unit buildings in 2023–2025 after Charlotte's UDO, and was it right?
- **What I did:** (from PRs #353, #355 and branch `ws/meck-release` e64d741; fragments `2026-11-09-ws-v5-clt-freeze.md`, `-v5-clt-score.md`, `2026-11-10-ws-meck-release.md`)
  - Pre-registered D-071 (6f26963) before code; wrote `validation/v5.py` and froze the forecast.
  - On Ben's go-ahead, released `V5-NC-CHARLOTTE`, regenerated the frozen draws (identical) and scored against BPS 37119.
  - Fixed `meck_permits.py` to filter on `holdout.still_blind`, since Charlotte permits still stopped at 2023-06-01 after the release (branch).
- **Inputs:** pre-UDO roll (2023-05-31), `mm_hazard.yaml`, `config/reforms/nc.csv`, BPS.
- **Outputs:** `results/frozen/V5-NC-CHARLOTTE.json`; `reports/v5-charlotte/README.md`, `score.json`; `config/states/nc.yaml`; `scripts/dev/v5_clt_predict.py`, `v5_clt_score.py`; D-071.
- **Findings:** pass: 119 buildings observed against P10–P90 89–172 (median 104); homes 256 inside 213–402; CRPS 10.1 vs 14.5 for no reform. One county, one case. After the adapter fix, Mecklenburg permits rise to 482,249 rows; 2025 looks about half-covered (legacy layer).
- **Decisions:** D-071; proposed for HANDOFF: V5 frozen and scored 2026-11-09 (pass).
- **AI:** Claude Code; hand-worked tests, regeneration guard, months-reported check. Logged by the nightly review.
- **Open / next:** merge `ws/meck-release`; check 2025 coverage of the legacy layer.

### LB-128 · 2026-11-09 · Engine: ADUs in two steps by zone, D-072 proposed with data checks (branch) (auto-review)
- **Question:** How should the ADU model first estimate the state's ADUs today from places we can count, then forecast them, inferring only from collected evidence?
- **What I did:** (from commits 128fafa – 117a017 on `ws/adu-three-zones`; fragment `2026-11-09-ws-adu-three-zones.md`) wrote D-072 before any code: zones (100k+ places, other places, unincorporated) × metro/micro/none, step 1 cell levels from sampled places with a place bootstrap, step 2 forecast, pre-registered leave-one-out tests. Ran data checks and added a coverage rule (at least 0.8 of BPS).
- **Inputs:** holdout-filtered store; `jurisdictions`; V5 release (LB-127).
- **Outputs:** D-072 in `docs/analysis_plan.md` (branch).
- **Findings:** NC sample model 66 vs observed 126 ADUs a year; statewide scale-ups disagree (330–770). Bexar unincorporated fails coverage (0.30); Durham County enters by a combined-office test (Ben; 1.20x BPS); Mecklenburg passes (1.08x): Charlotte 2.04 ADUs per 10,000 lots a year. The metro unincorporated cell has 44 places, 32 ADUs.
- **Decisions:** Ben chose the two-step design and the combined-office test; D-072 still proposed.
- **AI:** Claude Code; rates from ad hoc scripts, not committed. Logged by the nightly review.
- **Open / next:** Ben reviews D-072; then code, tests and the pre-registered checks.

### LB-129 · 2026-11-10 · Study design: ADU counts pre-registered for NC (D-074), then one protocol for all five states (D-075) (auto-review)
- **Question:** If the goal is an accurate statewide ADU number, how do new ADU counts enter the model and how is accuracy judged, fixed before any count is read; and how is the method kept from being tuned to NC alone?
- **What I did:** (from commits efdb4ee8, 9b21b241, e77ecc34; PR #358; fragment `2026-11-10-nc-adu-count-prereg.md`)
  - Worked through Ben's proposal for a stratified in-state ADU rate; quick descriptive counts showed NC's ADU-flagged places hold about 9% of eligible lots.
  - Wrote D-074 (first numbered D-072, renumbered): the flag undercount k measured in Raleigh by matching roll to permits, parser recall for parser sources, the entry rule for new places and Charlotte, three accuracy tests with pass bars.
  - After Ben asked that NC be the test bed for a five-state method, wrote D-075: the same counting steps in every state, k kept per source (never one global constant), one joint refit once all states are on `main`, the same tests everywhere, and a data-tier test for a new state. Started the NC, MN, OH, TX and OR data sessions.
- **Inputs:** processed NC `permits`, `eligible_parcels`; D-048, D-070, D-071, D-072.
- **Outputs:** D-074 and D-075 in `docs/analysis_plan.md`.
- **Findings:** NC's rate rested on 11 places; ad hoc sums of `eligible_parcels` double-count local-only towns in ACS-fallback county remainders (handled in the model by `adu.non_overlapping`).
- **Decisions:** D-074, D-075 (method only; Ben's direction for D-075).
- **AI:** Claude Code; counts checked against `docs/build/nc-readiness.md`; no model run. Logged by the nightly review.
- **Open / next:** the state counting sessions (LB-130 – LB-132); the undercount table and model form (LB-133, LB-135).

### LB-130 · 2026-11-10 · Data (NC): Raleigh's flag undercount from the Wake rolls; Charlotte and unincorporated Mecklenburg ADU counts (auto-review)
- **Question:** How many second homes were really added to Wake single-family lots 2019–2023, how much do Raleigh's ADU flags undercount them, and how many ADU permits did Charlotte issue now that V5 is released?
- **What I did:** (from PRs #360, #361; fragments `2026-11-10-nc-wake-roll-adu.md`, `2026-11-10-ws-charlotte-adu-counts.md`)
  - Committed the Wake roll detection rule before any count (56330e7), implemented it as tested functions, and matched Raleigh's roll finds to ADU-flagged permits by PIN.
  - Counted Charlotte and unincorporated Mecklenburg ADU permits, checked the parser's precision and recall, reviewed the rule rows and wrote the Accela download steps.
- **Inputs:** Wake rolls Nov 2019 and Dec 2023 (registered); `raleigh_permits`, Mecklenburg permits through `holdout.apply`.
- **Outputs:** `reports/nc/wake-roll-adu-diff.md`/`.json`, `src/lotline/adapters/states/nc/wake_roll_diff.py`, `tests/states/nc/test_wake_roll_diff.py`, `scripts/dev/nc_wake_roll_adu_diff.py`; `reports/nc/charlotte-adu-counts.md`.
- **Findings:** Wake: 88 of 256,532 single-family lots gained a second home (0.08 per 1,000 a year). Raleigh k = 1.07 (90% 1.02–1.21) with duplex rebuilds removed (1.20 as written; 1.4 as the upper sensitivity). Charlotte: 310 flagged ADU permits 2010–2025 (0.20 per 1,000 lots a year 2021–24), recall about 0.96; the 37119 remainder row would double-count lots for permit-level rates (about 21,800 real single-family lots, not 275,566).
- **Decisions:** for D-074, the duplex-removed k = 1.07; proposed: Charlotte flags from 2016 treated as a field flag.
- **AI:** Claude Code; hand-worked tests, 26 known ADUs traced through both rolls before the rule was written. Logged by the nightly review.
- **Open / next:** permit-level remainder (LB-134); Accela download for 2025.

### LB-131 · 2026-11-10 · Data (NC): five more cities scouted for ADU permits (Asheville, Cary, Chapel Hill, Wilmington adapters; Winston-Salem closed) and accepted rule rows (auto-review)
- **Question:** Can record-level ADU permits from more NC cities widen the ADU base beyond about 9% of eligible lots, and what are their local rule histories?
- **What I did:** (from PRs #359, #362–#366; fragments `2026-11-10-nc-{asheville,cary,chapel-hill,wilmington,winston-salem}-permits.md`, `2026-11-10-nc-adu-rule-rows.md`)
  - Built and fetched adapters for Asheville (Accela view, PDDL), Cary (hand-registered export; reads "UDU"), Chapel Hill (legacy LAMA geodatabase, with a standard-library `filegdb.py` reader checked against GDAL) and Wilmington (New Hanover County); each with a 30 + 30 hand check and a BPS cross-check.
  - Winston-Salem: no usable source; Ben decided no records requests for Winston-Salem or Chapel Hill 2021–26.
  - Transcribed the rule rows Ben accepted from the scout reports into `config/reforms/nc.csv` (92 → 101 rows; 4 rows amended).
- **Outputs:** `src/lotline/adapters/states/nc/{asheville,cary,chapel_hill,wilmington}_permits.py`, `filegdb.py`, their tests; `config/crosswalks/nc_cary_permit_types.csv`; `config/states/nc.yaml`; `docs/data_provenance.md`; `reports/nc/{asheville,cary,chapel-hill,wilmington,winston-salem}-adu-scout.md`; `config/reforms/nc.csv`.
- **Findings:** Asheville 361 ADU permits 2014–2026 (1–2.7 per 1,000 lots a year; description recall 63%, so pre-2022 is a floor); Cary 43 since 2019; Chapel Hill 30 in 2015–2021; Wilmington 291 since 2014, rising from 0.2 to 1.5–2.2 per 1,000 after its 2021 code (an in-window event). Coverage of NC eligible lots rises to about 9.9% with Wilmington and unincorporated New Hanover.
- **Decisions:** rule rows accepted by Ben (2026-11-10); no records requests (Ben).
- **AI:** Claude Code; every match and sample non-match read by hand; tests, schema checks, `compliance_check.py`. Logged by the nightly review.
- **Open / next:** Wilmington 2021 `supersedes` check; unincorporated Mecklenburg ETJ row; parser misses (LB-134).

### LB-132 · 2026-11-10 · Data (MN, OH, TX, OR): the D-075 counting steps in the other four states (auto-review)
- **Question:** Can Minnesota, Ohio, Texas and Oregon run NC's ADU counting steps (coverage, a measured flag undercount k, new open permit sources) so all five states are comparable?
- **What I did:** (from PRs #367–#372; fragments `2026-11-10-{mn,oh,tx,or}-adu-counts.md`) in each state: a coverage audit over non-overlapping units; a k detection rule committed before counting (Minneapolis rolls, Franklin roll, TCAD 2026 improvements for Austin, RLIS for Portland); subagent source scouting; new adapters with 30 + 30 hand checks: Rochester MN (accepted by Ben with no stated licence), Cleveland (ODbL confirmed by Ben), College Station, Salem (MWVCOG) and Medford. Undercount helpers moved to `lotline.validation.undercount`; Austin's post-HOME ADU counting rule written.
- **Outputs:** `reports/{mn,tx,or}/adu-coverage-and-undercount.md`, `reports/oh/` ADU report, JSON aggregates; `mpls_roll_diff.py`, `franklin_roll_diff.py`, `austin_adu_roll.py`, `rochester_permits.py`, `cle_permits.py`, `cstx_permits.py`, OR Salem/Medford adapters, tests; `src/lotline/validation/undercount.py`.
- **Findings:** Coverage of eligible lots by flagged permits: MN 47% (all metro), OH 15–18%, TX 14%, OR 17–23%. Measured field-flag k: Austin 1.13 (1.09–1.18), Portland 1.06 (1.05–1.07), matching Raleigh's 1.07; Minneapolis 1.04 (parser-typed); Franklin roll cannot measure k (carriage houses carded as garages). Austin after HOME is a range (104–217 in 2024). Met Council suburbs treated as a floor (Ben).
- **Decisions:** Ben accepted Austin k as a measured field-flag source; Met Council suburbs a floor; Rochester terms and Cleveland ODbL (all 2026-11-10).
- **AI:** Claude Code; rules committed before counts, deviations labelled in each report; hand checks read by Claude; no engine or fit run. Logged by the nightly review.
- **Open / next:** wire Austin's HOME rule; Denton download; College Station rule rows.

### LB-133 · 2026-11-10 · Study design / WS-CORE: the ADU undercount table by source, decided (D-078) and wired (branch) (auto-review)
- **Question:** With k measured per source, how are unmeasured, parser, low-recall, Columbus and floor sources handled, how is k drawn, and how does it enter the model?
- **What I did:** (from PR #373, commit 17e6d006 on `ws/adu-undercount-table`; fragments `2026-11-10-ws-adu-k-table-picks.md`, `2026-11-10-ws-adu-undercount-table.md`)
  - Proposed one answer for each of six open choices; Ben accepted all six ("Yes, use your picks"), recorded as D-078. Field-flag prior centre exp(mean ln k) = 1.086.
  - On the branch: made `adu_flag_undercount` a 28-source validated table, wrote `lotline.model.undercount` (split-lognormal draws, shared z for field rows), applied k to counted ADU permits only (panels, calibration, D-070 floor, per-draw in `run`), rendered the table into `docs/model_and_assumptions.md`.
- **Outputs:** D-078 in `docs/analysis_plan.md`; on the branch `config/params/adu.yaml`, `src/lotline/model/undercount.py`, changes in `scenarios/adu.py`, `calibrate_adu.py`, `estimate_adu.py`, `results.py`, `tests/model/test_undercount.py`.
- **Decisions:** D-078 (Ben, 2026-11-10).
- **AI:** Claude Code; each k cited to its report; no fit or run. Logged by the nightly review.
- **Open / next:** merge `ws/adu-undercount-table`; the joint refit.

### LB-134 · 2026-11-10 · WS-CORE / Engine: permit-level county remainders and the shared parser's ADU misreads (auto-review)
- **Question:** What denominator should a county remainder take when its ADU rate comes from record-level permits, and can the shared permit parser read the ADU phrasings the state sessions found it missing?
- **What I did:** (from PRs #375, #376 and commit 3e7fb2a6 on `ws/adu-permit-remainder`; fragments `2026-11-10-ws-eligible-permit-remainder.md`, `-ws-permit-text-adu-misreads.md`, `-ws-adu-permit-remainder.md`)
  - Added `remainder="permits"` and `eligible.permit_level` (ACS-fallback remainders lose their local-only places); default stays `"bps"`.
  - Taught `permit_text.py` (Ben approved editing it) "additional dwelling unit", Cary's UDU, ADUs made by addition or conversion, and ADU removals (new `adu_removed` field); 40 synthetic test rows.
  - On the branch, wired permit-level lots into the ADU fit panels only where ADU counts come from permit files, with a test that it never stacks with the D-070 floor.
- **Outputs:** `src/lotline/build/eligible.py`, `src/lotline/parse/permit_text.py`, `tests/core/test_eligible.py`, `tests/core/test_permit_text.py`; on the branch `estimate_adu.py`, `calibrate_adu.py`, `tests/model/test_adu_permit_remainder.py`.
- **Findings:** unincorporated Mecklenburg ADU lots fall from 275,566 to 20,086 (2024); the same pattern in 21 more NC counties and 2 MN counties. Parser phrase check: recall 0.18 → 0.82, precision 0.40 → 0.95 (a phrase check, not a re-run of hand-check samples).
- **Decisions:** proposed in the PRs: permit-based rates use permit-level remainders; parser sources re-measure k_parser on their next rebuild.
- **AI:** Claude Code (overnight for the branch, Ben asleep); hand-worked tests, full pytest, `compliance_check.py`; no data fitted. Logged by the nightly review.
- **Open / next:** merge `ws/adu-permit-remainder`; remaining parser misses.

### LB-135 · 2026-11-10 · Method: D-079 proposed, the model form for the five-state ADU joint refit (branch) (auto-review)
- **Question:** Should the D-075 joint refit use D-048 or D-047's approach 3 with rule-change terms, and how is the choice made before any fit?
- **What I did:** (from commit 27e8f6f2 on `ws/adu-d079-model-form`; fragment `2026-11-10-ws-adu-d079-model-form.md`) wrote D-079 defining Form A (D-048) and Form B (approach 3 plus a dose term identified only from in-window rule changes, estimated only with 8+ events in 3+ states), the shared data, scoring by the data-tier test, tests A–C and the D-049 log score, and a decision rule. Proposed pick: Form A, Form B the pre-registered challenger.
- **Outputs:** D-079 in `docs/analysis_plan.md` (branch).
- **Decisions:** none; D-079 awaits Ben's review.
- **AI:** Claude Code, overnight; numbers checked against D-047–D-053 as written; no fit or data read. Logged by the nightly review.
- **Open / next:** Ben reviews D-079; rebuild, joint refit, tests.

### LB-136 · 2026-11-10 · Fees: results page v2–v9, statewide run with a centred elasticity (D-076), fee knobs (D-077), merged; app hand-off (auto-review)
- **Question:** After office hours and Ben's review, how should the fee results read, what does a statewide run say, and can a user change the size of the cut and which home types it covers?
- **What I did:** (from commits 345571df – bdb37a41 on `ws/fees-phase2`, merged as PR #356; commit a54dc874 on `ws/fees-app-handoff`; addenda in `2026-11-09-ws-fees-phase2.md`, fragment `2026-11-10-ws-fees-app-handoff.md`)
  - Rebuilt the page as one "two worlds" story; found the headline mean implied ε ≈ 0.7 because the triangular draw was lopsided, so Ben chose to lead with the central estimate.
  - D-076: elasticity drawn lognormal (median 0.3, p95 1.75); fee run over every baseline place in MN, NC, OH, TX (2,937 places).
  - D-077: `fees.change_grid`, a fee-change slider (cuts left, rises right) and targeted-bill toggles; a fee-revenue "Test" box; a "what gets built today" waffle; plain wording for the 0.3 response (pages v5–v9).
  - Wrote hand-off 15 for WS-APP to rebuild the fee section from `reports/fees-knobs/grid.json`.
- **Outputs:** `src/lotline/model/scenarios/fees.py`, `tests/model/test_fee_scenario.py`, `scripts/dev/fee_knobs_export.py`, `reports/fees-statewide-run/`, `reports/fees-knobs/`; D-076, D-077; page [Fee Cut Results, Phase 2](https://claude.ai/artifact/LN5G4rajXAxVi3uhEXtwDs) (v9); `docs/build/handoffs/15-fee-section-for-app.md` (branch).
- **Findings:** halving real fees adds about 1,480 homes statewide (0.09%); the $50k benchmark cut about 13,200 (0.8%); a half cut forgoes about $3.14 billion of fee revenue. Duplexes are 2.3% of new homes in the four states (corrects a chat answer of 0.5%).
- **Decisions:** D-076, D-077 and the page design calls (Ben, 2026-11-10).
- **AI:** Claude Code; fee tests, P50s against central paths, page numbers against `summary.json`, browser checks at desktop and phone widths. Logged by the nightly review.
- **Open / next:** fees into `lotline results` so the app reads the grid from the bundle; Ben's open choices (slider range, headline, revenue box).

### LB-137 · 2026-11-11 · Data / WS-CORE: five-state ADU rebuild, an offline rebuild mode, and D-080 (auto-review)
- **Question:** After the parser fix (#376), permit-level remainders (#375, #378) and the state count PRs, how do each source's ADU counts and county denominators move, and how can tables be rebuilt without re-downloading everything?
- **What I did:** (from PRs #380–#383; fragments `2026-11-11-ws-adu-rebuild-2026-11-11.md`, `-ws-offline-rebuild.md`, `-ws-permit-text-negated-second-unit.md`, `-ws-d080-rebuild-decisions.md`)
  - Rebuilt MN, NC, OH, TX and OR one source at a time with the holdout filter on, compared before and after by `permit_id`, and re-ran the old parser on today's raw to separate parser effects from new 2026 permits.
  - The rebuild re-downloaded about 4,700 files (~3.5 GB), so WS-CORE added `lotline fetch --offline` (newest complete cached snapshot per query, never mixed, no network) and a read-only `lotline manifest prune-candidates`.
  - Fixed a Dallas shed read as an ADU ("can not be used as second dwelling unit") in the shared parser's negation guard.
  - Ben decided D-080: unincorporated Mecklenburg (37119) takes its lot count from the parcel roll, and permits that legalize an existing ADU are not new production.
- **Outputs:** `reports/adu-rebuild-2026-11-11.md`; `src/lotline/io/offline.py`, changes in `io/arcgis.py`, `io/socrata.py`, `io/http.py`, `cli.py`, `tests/core/test_offline.py`; `src/lotline/parse/permit_text.py` and tests; D-080 in `docs/analysis_plan.md`. All merged.
- **Findings:** the parser fix adds 58 ADUs and drops 7; only Dallas moves by more than 25% (1 → 2, a false positive). The 37119 denominator falls from 275,566 (ACS fallback) to 21,812 (roll). 2,020 older snapshot folders (9.63 GB) are repeated by newer ones; nothing deleted.
- **Decisions:** D-080 (Ben, 2026-11-11, "Yes, go ahead").
- **AI:** Claude Code; scratch comparison scripts, offline no-network tests that fail when the guard is bypassed, full pytest, `compliance_check.py`. Logged by the nightly review.
- **Open / next:** adapters that call the network directly (Rochester, Charlotte UDO translation) fail offline; Ohio parcels refresh.

### LB-138 · 2026-11-11 · Validation / Method: first parser hand checks (NC, TX, OH) and parser k as precision ÷ recall (D-081) (auto-review)
- **Question:** After the parser fix, what are recall and k for each ADU parser source, and how should k handle false positives?
- **What I did:** (from PRs #384–#386, #387; fragments `2026-11-11-ws-nc-parser-handcheck.md`, `-ws-tx-parser-handcheck.md`, `-ws-oh-parser-handcheck.md`, `-ws-d081-parser-k-precision.md`)
  - In each state, committed the judging rule, pools and estimator before reading any sample, then judged seeded flagged and near-miss draws blind to their flag (Mecklenburg, Asheville before/after 2022, Greensboro, Fort Worth, Dallas, Cincinnati, Cleveland).
  - Precision came out at 0.52–0.77 in several sources, so Claude proposed six decisions; Ben accepted them as D-081: parser k = precision ÷ recall, in-law suites with no kitchen are not ADUs, a Cincinnati adapter fix, a second shared-parser round, an offline rebuild and fresh checks for sources that move.
- **Outputs:** `reports/nc/parser-handcheck-2026-11-11.md`, `reports/tx/parser-handcheck-2026-11-11.md`, `reports/oh/parser-handcheck-2026-11-11.md`; D-081 in `docs/analysis_plan.md`. Merged.
- **Findings:** Fort Worth k = 2.49 (recall 0.40); Dallas recall not estimable (1 of 6 found); Cincinnati precision 15/29 (11 development carriage houses, a negated shed); Cleveland k 1.07 holds; Asheville before 2022 1.71; Greensboro 1.12, first measured.
- **Decisions:** D-081 (Ben, 2026-11-11, "Yes, use your picks").
- **AI:** Claude Code judged every permit; one reader, no second coder; no engine or fit run. Logged by the nightly review.

### LB-139 · 2026-11-11 · WS-CORE / WS-OH: Cincinnati adapter fixes, the second shared-parser round, and an offline rebuild (auto-review)
- **Question:** Can the misses and false positives the hand checks found be fixed with generic rules, and which sources' counts then move enough to need fresh checks?
- **What I did:** (from PRs #388, #389, #391; fragments `2026-11-11-ws-cincy-adu-false-positives.md`, `-ws-parser-round2.md`, `-ws-adu-rebuild-2026-11-11b.md`)
  - Cincinnati adapter v1.1: drops ADU flags in development buildings and on "not a dwelling unit", and reads a separately permitted house as context; no hard-coded ids.
  - Second parser round (D-081 item 6): new ADU names ("GARAGE APT", "2ND DWELLING UNIT", detached "living quarters"), the no-kitchen rule with a sensitivity switch, legalizations as 0 new units (D-080), Asheville house-context and Ohio negation phrasings; Asheville and Mecklenburg adapter tweaks; a phrase-check script.
  - Rebuilt all five states with `--offline` and split each count change into adapter and parser effects.
- **Outputs:** `src/lotline/adapters/states/oh/cincy_permits.py`, `src/lotline/parse/permit_text.py`, their tests, `scripts/dev/parser_phrase_check.py`; `reports/adu-rebuild-2026-11-11b.md`. Merged.
- **Findings:** movers: Cincinnati 29 → 18, Dallas 2 → 5, Mecklenburg 441 → 426, Greensboro 44 → 41; Fort Worth and Asheville reclassify many permits for a net change near zero. The kitchen rule removes 107 permits. New problems: Meck code 437 apartment upfits, "upgrade" vetoing real ADUs; offline gaps (Rochester, mixed Ohio parcel vintages).
- **AI:** Claude Code; synthetic tests per case, in-memory rebuilds reproducing the tables, cause columns summed to totals; no fit run. Logged by the nightly review.

### LB-140 · 2026-11-11 · Validation: second-round parser hand checks and the undercount table takes their k values (auto-review)
- **Question:** After the second parser round, what is k = precision ÷ recall for the sources that moved, and what goes into the D-078 table for the joint refit?
- **What I did:** (from PRs #393, #394, #396, #400; fragments `2026-11-11-ws-nc-parser-handcheck-b.md`, `-ws-tx-handcheck-2026-11-11b.md`, `-ws-cincy-parser-handcheck-b.md`, `-ws-adu-k-table-handchecks.md`)
  - Fresh pre-committed hand checks with new seeds: NC (802 permits judged), Fort Worth and Dallas (130, incl. a census of all 51 kitchen-rule drops), Cincinnati (all 18 flags plus 70 near-misses).
  - Ben allowed parser rows to have k < 1 (field rows stay ≥ 1; #402) and approved merging the checks and writing the table PR ("Yes, do both").
  - Wrote the values into `adu_flag_undercount` and loosened the loader for parser k < 1 (a contract change).
- **Outputs:** `reports/nc/parser-handcheck-2026-11-11b.md`, `reports/tx/parser-handcheck-2026-11-11b.md`, `reports/oh/parser-handcheck-2026-11-11b.md`; `config/params/adu.yaml`, `src/lotline/config/__init__.py`, `src/lotline/model/undercount.py`, `tests/model/test_undercount.py`. Merged (#400).
- **Findings:** k: Mecklenburg 0.98, Asheville before 2022 1.47, Asheville 2022 on 1.00, Greensboro 1.39, Fort Worth 1.14 for 2015–2026 (down from 2.49), Cincinnati 0.78 (0.61–1.31), Cleveland range widened to 1.00–1.31. Dallas: 5 of 5 flags real but too few for a k, so it stays out of the fit. 43 of Fort Worth's 51 kitchen-rule drops are in-law suites (its usual ADU form); the no-kitchen count is a named sensitivity.
- **Decisions:** parser k may be below 1 (Ben, 2026-11-11); table values accepted (Ben, 2026-11-11).
- **AI:** Claude Code judged every permit (one reader); flag counts matched the rebuild; 552 ADU-related tests pass. Logged by the nightly review.

### LB-141 · 2026-11-11 · Build: ADU joint refit pre-run code for D-079 (branch, no fit run) (auto-review)
- **Question:** Does the code feed the five-state ADU refit exactly what D-074 to D-081 decided, and can it run D-079's Form A vs Form B comparison once, unattended?
- **What I did:** (from commit 777f36bd on `ws/adu-joint-refit-prep`; fragment `2026-11-11-ws-adu-joint-refit-prep.md`) took Dallas out of the fit; fixed `place_years` rounding k-scaled counts down; built `lotline.model.joint_refit` (Form B dose, events, tiers, scores, tests A–C, decision rule) and a one-shot run script inside `offline_build`; added test B's roll counts.
- **Outputs:** on the branch `src/lotline/model/joint_refit.py`, `scripts/dev/adu_joint_refit.py`, `tests/model/test_joint_refit.py` (31 tests), `config/validation/adu_roll_counts.csv`, `reports/adu-joint-refit-2026-11/{fit_set,events}.csv`, a "Built" note under D-079.
- **Findings:** 64 places, 395 place-years; only 5 in-window rule-change events in 2 states, so g is held at 0 and Form B becomes approach 3. Ohio's one fit place is tier 2, so Ohio cannot be scored and the 4-of-5 claim rule needs all four other states.
- **Decisions:** none; the building choices await Ben's confirmation before the run.
- **AI:** Claude Code; hand-worked tests, full suite, `compliance_check.py`. Logged by the nightly review.
- **Open / next:** Ben confirms D-079 choices; the run.

### LB-142 · 2026-11-11 · Study design: missing-middle methodology review and D-082 proposed (branch) (auto-review)
- **Question:** Can the adopted missing-middle method (D-054 (b) / D-055) give an accurate statewide number, and what would an ADU-style rebuild take?
- **What I did:** (from PRs #390, #392 and commits on `ws/mm-review`; fragments `2026-11-11-ws-mm-review-brief.md`, `-ws-mm-review.md`)
  - At Ben's request, wrote a WS-MM-REVIEW brief (merged), then ran the review: read the MM D-entries, causal diagram, params, code and reports; inventoried permit and roll sources by column names only (no outcomes, no St. Paul or Ramsey file opened); answered nine questions with options and a proposed sequence.
  - Ben approved the sequence ("Let's follow your order"); D-082 (proposed) pre-registers one counting protocol, Oregon in the fit and accuracy tests, later amended (§1b) with the rule-check results and Ben's confirmation that every always-allowed place feeds the level component.
- **Outputs:** `docs/build/workstreams/WS-MM-REVIEW.md`; on the branch `docs/research/mm-methodology-review-2026-11.md`, D-082 in `docs/analysis_plan.md`; page [Missing Middle Method Review](https://claude.ai/artifact/Ah44XwT3nYkvQJzf4bAMGm).
- **Findings:** the fit's signal rests on six NC towns with `[earliest-known]` dates; without NC θ falls from 0.12 to 0.013 per 1,000. Oregon (up to 65 places with a cap rise) is the largest untapped source. About 11 permit sources carry unit counts and parcel ids; the ADU/MM overlap is not coded.
- **Decisions:** review sequence approved (Ben, 2026-11-11); D-082 status Proposed.
- **AI:** Claude Code; no counts or fits. Logged by the nightly review.

### LB-143 · 2026-11-11 · Rules: missing-middle second-coder checks in five states, rule rows accepted (branch) (auto-review)
- **Question:** Are the missing-middle events the fit depends on real cap rises, and what did each code allow just before?
- **What I did:** (from PRs #395, #397, #398, #401 and commit 62cfa41e on `ws/mm-rule-rows`; fragments `2026-11-11-mm-rules-nc.md`, `-ws-mm-rules-tx.md`, `-ws-mm-rules-mn-oh.md`, `-ws-mm-rules-or.md`, `-ws-mm-rule-rows.md`)
  - NC: read predecessor codes for Wilson, Wake Forest, Morrisville, Sanford, Burlington, Garner and Durham's EHC dates. TX: League City, Lewisville, Houston, Lubbock. MN/OH: signed ordinances for St. Louis Park, Richfield, Euclid (local OCR). OR: second-coded 7 single-coder rows and listed first cap-rise events for 111 places from the rows alone.
  - Research sub-agents did first passes; Claude checked the decisive pages; no outcomes read, no records requests or emails.
  - Ben accepted all proposed rows ("Let's accept all of these"); 23 rows edited and 3 added across the five CSVs, each stamped with the second coder and its report.
- **Outputs:** `reports/{nc,tx,mn,or}/mm-rule-checks-2026-11.md`, `reports/or/mm-first-events-2026-11.csv`; on the branch `config/reforms/{nc,tx,mn,oh,or}.csv` and two tests.
- **Findings:** Garner 2022 and Wilson 2013 (SR6 only) are real events; Wake Forest, Morrisville, Sanford, Burlington and League City are `[predates]`; Durham city effective 2019-10-01; Lewisville 2022 confirmed; Houston 2023 is a standards route (cap 8 → 4), not a cap rise; Lubbock stays out; St. Louis Park and Euclid confirmed. Oregon SB 458 rows left alone (no verified signing date).
- **Decisions:** all proposed rows accepted, League City as `[predates]` (Ben, 2026-11-11).
- **AI:** Claude Code (Opus 5.5) and Claude (Sonnet 5.5, MN/OH); same-model-family second coding, partly from mirrors, flagged in the reports; 2,058 tests pass, `compliance_check.py` 0 FAIL. Logged by the nightly review.

### LB-144 · 2026-11-11 · Build: D-082 code: missing-middle counting, model and the permit-to-theme classifier (branches, nothing counted) (auto-review)
- **Question:** Can D-082's counting rules, model and ADU/MM split be committed in code with hand-worked tests before Ben approves the protocol and before any count is seen?
- **What I did:** (from commits f8e7dd2a, e01e7661, 6e565f1a on `claude/mm-counts-code-*`, `claude/mm-model-code-*`, `claude/permit-theme-classifier-*`; fragments of the same names)
  - `mm_counts.py`: building collapse, coverage screen with k_src, strong-source tests, uplift ratios, a generic 2–4 roll-diff rule; every table goes through a blind step that drops St. Paul and Ramsey County; the run script stops without Ben's go-ahead (`--dry` run once).
  - Model: event-setting-row tag rule, standards dose class S, level component L, challengers C1/C3/C4 and §5's choosing rule in `calibrate_mm.py` and `rule_tags.py`; Houston tagged `[standards]`.
  - `permit_theme.py`: each permit gets exactly one of ADU, new 2–4 building, conversion or other, so ADU and MM counts never share a permit; issue #404 for the wiring.
- **Outputs:** on the branches `src/lotline/model/mm_counts.py`, `src/lotline/model/calibrate_mm.py`, `src/lotline/model/rule_tags.py`, `src/lotline/build/permit_theme.py`, tests (22 + 5 + 25), `scripts/dev/mm_counts_d082.py`, `scripts/dev/calibrate_mm_d082.py`, `config/params/mm.yaml`, `config/reforms/tx.csv`; issue #404.
- **Findings (structure only):** no processed permit table carries a street address, so the collapse falls back to parcel × year; no roll has `sf_only_zoned`, so two uplift ratios need a zoning join; Franklin's parcels lack `units`; `estimate_mm.local_counts` does not filter demolitions. `fit_level` recovered a simulated θ_L in 6 of 6 seeds.
- **Decisions:** none; D-082 is still Proposed.
- **AI:** Claude Code; synthetic tests only, no counts printed, no fit, no `--unblind`. Logged by the nightly review.
- **Open / next:** Ben approves D-082; merge the branches; counting runs.

### LB-145 · 2026-11-12 · Calibration: the five-state ADU joint refit (D-079), run once; Form A kept, no data tier passes (auto-review)
- **Question:** Under D-079's pre-registered rule, which ADU model form wins the five-state refit, and how well does each predict a state it has not seen at data tiers 0–2 (D-075), with tests A–C (D-074)?
- **What I did:** (from commit a8ea6b18 on `ws/adu-joint-refit-results`; fragment `2026-11-12-ws-adu-joint-refit-results.md`)
  - Ran `scripts/dev/adu_joint_refit.py` once on `main` at `1c7ad001` (#409 merged), offline, seed 20261111, 20,000 draws; an earlier start was stopped before any fit at Ben's request to review the year windows, and its output discarded unread. Ben then confirmed the windows and the other "Built" choices (D-079 note).
  - Wrote the README, a results page and the fragment; nothing tuned after a score was read.
- **Outputs:** `reports/adu-joint-refit-2026-11/` (README, results.html, run-log, summary.json, fits, tiers, logscores, tests A–C, event check); page [ADU Joint Refit 2026-11](https://claude.ai/artifact/WUDTnwJ4hXMNXwy5nrUUcr); D-079 "Built" note in `docs/analysis_plan.md`.
- **Findings:** Form A is kept; neither form passes the claim rule at any tier, so the tool shows tier-2 ranges. Form A's median is off by more than ×2 in every scored state (MN over ~2.7×; NC, OR, TX under 2.7–15×). Form A passes 1 of tests A–C (test A, Texas), Form B 0; test B fails in NC and OH; test C fails in all five states (43 of 73 places). Refit θ 0.756 per 1,000 (0.554–1.112); leaving out Minnesota doubles θ. Sensitivities don't change the decision.
- **Decisions:** none here; config values and the failed tests put to Ben.
- **AI:** Claude Code ran the script; every number read from the run's files; one misread README sentence caught before commit. Logged by the nightly review.
- **Open / next:** Ben's calls on config and failed tests; τ profile not saved; Austin HOME-rule inferred counts.

### LB-146 · 2026-11-12 · Model: why ADU test C failed; the observed floor moves to 3 years (auto-review)
- **Question:** The refit failed test C (the no-reform floor) in all five states. Is the model wrong, or the test?
- **What I did:** (from PR #412, commits 9fbe5aec, e2e9fb5c; fragment `2026-11-12-ws-adu-floor-3yr.md`) read the test and the engine floor; tabulated each counted place's 2022–25 ADUs (counts only, no model). The engine floor averaged 2022–25 while the test averaged 2023–25; matching the windows removes 41 of 43 failures. Re-scored test C offline with the refit's Form A values.
- **Outputs:** `config/params/adu.yaml` (`adu_observed_years` 4 → 3); decision entry in `docs/analysis_plan.md`; regenerated table in `docs/model_and_assumptions.md`; `TEST_C_TOLERANCE` (0.01) in `src/lotline/model/joint_refit.py` with a hand-worked test. Merged (#412).
- **Findings:** with a 1% tolerance test C passes in all five states; 42 places are still slightly below 1 (pool shrinkage and k draws). The floor, not the model's rate, sets the baseline in nearly every counted place.
- **Decisions:** Ben, 2026-11-12 ("Yes, use 3 years"; "Yes, count as pass" for a shortfall under 1%). Recorded on `main` as **D-082**, a deviation from D-070 written after test C was read. Note: the missing-middle protocol on `ws/mm-review` also carries D-082 (marked provisional there), so one will need renumbering on merge.
- **AI:** Claude Code; `params_table.py --check`, ruff, model tests. Logged by the nightly review.
- **Open / next:** Austin's inferred HOME counts, which affect its floor.

### LB-147 · 2026-11-12 · Study design: WS-ADU-RULES brief for coding ADU rule details in the fit places (auto-review)
- **Question:** The refit missed active cities and suburbs, and coded rule details (by right, owner occupancy, parking) are often blank. What research would let a model version fit a separate effect for each detail?
- **What I did:** (from commit 4125eaee on `ws/adu-rule-coding-brief`; fragment `2026-11-12-ws-adu-rules-brief.md`) at Ben's request ("Let's write a markdown for an agent to research the uncoded cities"), built a worklist from `config/reforms/*.csv` and the D-079 fit set, checked each place's in-force rows for blank rubric fields, and kept outcome numbers out of the brief so coding stays blind to which places the model misses.
- **Outputs:** `docs/build/workstreams/WS-ADU-RULES.md`; `docs/research/ordinances/adu-fit-rules-todo-2026-11-12.csv` (64 fit-set places plus St. Paul, rules only; priorities 46 / 18 / 1). On the branch.
- **Decisions:** none.
- **AI:** Claude Code. Logged by the nightly review.
- **Open / next:** run the workstream; Ben accepts rows; a rule-detail model needs its own pre-registration.

### LB-148 · 2026-11-12 · Analysis: missing-middle D-082 approved; run 1, permit coverage screen and k_src (auto-review)
- **Question:** Which missing-middle permit sources see about as many new 2–4 unit buildings as Census BPS before each place's reform, and so count as "strong" under D-082 §2?
- **What I did:** (from commits 312d3141, c691e157, 96c0757f, d6ef60dd on `ws/mm-run1-coverage`; fragment `2026-11-12-ws-mm-run1-coverage.md`)
  - Ben approved D-082 ("Approve D-082") and run 1 ("Yes, start run 1"), which also accepted PR #408's 13 counting choices. Branch stacks #408 on #407 (model code, #403 rule rows).
  - Added `mm_counts.area_coverage` (one k per source over each place's pre-event years) with a hand-worked test and the `--coverage` mode; ran once on cached tables through `mm_counts.blind`; added an address-split sensitivity (reported only).
- **Outputs:** `reports/mm-d082/run1-coverage/{README.md,coverage.csv,coverage_by_year.csv}`, `src/lotline/model/mm_counts.py`, `tests/model/test_mm_counts.py`, `scripts/dev/mm_counts_d082.py`.
- **Findings:** strong as pre-registered: Raleigh (k 0.81), Austin (0.92), Bend (1.01); Medford enters with 2 pre-years; Minneapolis too high (1.41); Cincinnati, Portland, College Station, Durham, Columbus too low; Mecklenburg not screened (no BPS rows). Splitting merged buildings moves Durham, Columbus and College Station into the band; the address fix (#406) is recommended. Out-of-range buildings are mostly `units_new = 0` alterations.
- **Decisions:** D-082 approved; run 1 go-ahead and #408 choices accepted (Ben, 2026-11-12).
- **AI:** Claude Code; 23 tests pass; the 30-building hand check per source not yet done. Logged by the nightly review.

### LB-149 · 2026-11-12 · Analysis: D-082 runs 2 and 3, uplift ratios and 2–4 unit roll diffs (auto-review)
- **Question:** Run 2: how much 5–6 unit, townhouse, conversion and teardown activity comes with new 2–4 unit buildings in the strong sources? Run 3: how many house or vacant lots gained a 2–4 unit building between two rolls (test B's observed side)?
- **What I did:** (from commits ea813f8d, 23237fd4 on `ws/mm-run2-3`, stacking #410 and the permit-theme classifier #405; fragment `2026-11-12-ws-mm-run2-3.md`) on Ben's overnight go-ahead ("Can we get close to having a finalized model over night?"), added theme recode, 2-unit ADU share, conversion diagnostic, split passthrough, card and parcel roll diffs, Franklin and Wake keys, and `--ratios` / `--rolls` modes; ran both on cached data through `mm_counts.blind`.
- **Outputs:** `reports/mm-d082/run2-ratios/`, `reports/mm-d082/run3-rolls/`, code and tests. PR #414.
- **Findings:** s_td 0.20 (0.11–0.43) on split-strong sources, likely a lower bound; rCV 0.023 (only Bend records conversions); r56 and rTH not measurable (no `sf_only_zoned`); ADU share of 2-unit permits ≈ 0. Roll gains: Minneapolis 0.36% of house lots, Columbus 0.061%, Franklin 0.042%, Met Council 0.055%, Raleigh 0.021%, Wake 0.013%.
- **AI:** Claude Code; first-pass bugs (0-row parcel joins, single-vintage Franklin map, sparse Minneapolis units, Bend's conversion flag) fixed before the final run; 59 tests, `compliance_check.py` 0 FAIL. Logged by the nightly review.

### LB-150 · 2026-11-12 · Calibration: D-082 runs 4–6, missing-middle joint refit and §7 tests; no model passes, choice left to Ben (auto-review)
- **Question:** What uptake rate θ do model M and challengers C1, C3, C4 give on the D-082 event rows, does any pass §7's tests, and which does §5's rule pick?
- **What I did:** (from commits 02d161c2 on `ws/mm-run5`, eec656a3, e09903d2 on `ws/mm-review`; fragment `2026-11-12-ws-mm-run4-5.md`) added `src/lotline/model/mm_tests.py` (tests A and C, leave-one-state-out, placebo, randomized PIT, place coverage; 8 hand-worked tests), `scripts/dev/mm_tests_d082.py` and eight sourced thresholds in `config/params/mm.yaml`; ran `calibrate_mm_d082.py` (2 h 39 min) then scoring, cached data, holdouts dropped. Run 6 built a results page from the report files; the results were recorded under D-082. Two run-5 commits mistakenly put on `ws/mm-run1-coverage` were reverted there.
- **Outputs:** `reports/mm-d082/run4-refit/`, `reports/mm-d082/run5-tests/`, `reports/mm-d082/run6-results/d082-results.html`, `scripts/dev/mm_results_page_d082.py`; page [Missing-middle model check](https://claude.ai/artifact/DVyYJNJjwPRXu3a28Ue5Dp); D-082 results note in `docs/analysis_plan.md`. PR #415.
- **Findings:** M's θ 0.63 per 1,000 eligible parcels a year (0.36–1.32); without Oregon 0.034 (Oregon is 86 of 93 fit places). M, C1, C3, C4 each pass 0 of tests A–C, all fail leave-one-state-out (Oregon), place coverage ≈ 0.44; M fails the placebo. §5 mechanically picks C4 (beats M by 2.9 paired SE, same θ). Main cause: the no-reform baseline is treated as known; only 37% of 43 no-reform places land in their P10–P90.
- **Decisions:** none; no config value written; model choice is Ben's.
- **AI:** Claude Code; scoring script smoke-tested on fake fits; tables spot-read (e.g. Reynoldsburg baseline 159 vs 5 traced to its pre-period); pytest, params check, `compliance_check.py`. Logged by the nightly review.
- **Open / next:** Ben chooses the model and whether to widen the baseline's uncertainty; config PR only with his approval.

### LB-151 · 2026-11-13 · Rules: WS-ADU-RULES, ADU rule details coded for the 65 fit places, 2016–2025 (branch) (auto-review)
- **Question:** For each place on the WS-ADU-RULES worklist (LB-147), what were the ADU rules each year 2016–2025 (by right, owner occupancy, parking, detached, ADUs per lot, size, lot minimum), and when did they change?
- **What I did:** (from commit f87a51d6 on `ws/adu-rule-coding`; fragment `2026-11-12-ws-adu-rules.md`; PR #417)
  - First-coder agents per group of places read code, adopted ordinances and Wayback copies, one record per rule version with short verbatim quotes; a fresh second coder re-opened every cited source; a browser agent re-checked values on script-blocking official pages.
  - Scripts assembled the filled worklist, proposed `reforms` rows and a README section. Coding stayed blind to outcomes.
- **Outputs:** `docs/research/ordinances/adu-fit-rules-todo-2026-11-12.csv` (filled), `docs/research/ordinances/adu-fit-rules-proposed-2026-11.csv`, `docs/research/ordinances/README.md` ("WS-ADU-RULES"); PDFs under `~/lotline-data/manual/adu-rules-2026-11/` (outside the repo).
- **Findings:** most places changed their ADU rules at least once in the window; many existing rows have blank or slightly wrong fields (conflicts listed, none applied).
- **Decisions:** six coding conventions (provisional); Ben ruled seven judgment calls on 2026-11-13 (Raleigh, Bloomington, Cincinnati, Bend, Orono, New Brighton, Durham).
- **AI:** Claude Opus 5.5 ran the workstream; checked by the second-coder pass and the browser check. Three process incidents are recorded in the README (Medford refused fetch retried with curl, copy deleted; one Scott County retry; a St. Paul staff report downloaded and flagged). Logged by the nightly review.
- **Open / next:** taken into config in LB-155.

### LB-152 · 2026-11-13 · Method / Analysis: D-083, a screen of ADU place effects against unused place factors (branch) (auto-review)
- **Question:** Which pre-2016 place factors that the ADU model doesn't use explain the large place effects (α 1.92) and state misses of the D-079 refit?
- **What I did:** (from commits 174fe7ac, be7a4603, f6134cdf, e6c440a0 on `ws/adu-covariate-screen`; fragments `2026-11-13-ws-adu-covariate-screen.md`, `…-run.md`)
  - After a methodology review in chat, Ben asked for the screen ("Draft the screen"); wrote D-083 (seven factors, an availability rule, one-factor-at-a-time Poisson-gamma refits, a three-part bar), then ran it once Ben accepted ("Accept D-083"), offline, holdouts filtered, St. Paul out.
  - Ben asked for a leave-one-place-out check ("Run the check"), pre-registered as a dated addition to D-083 before running.
- **Outputs:** `docs/analysis_plan.md` (D-083); `src/lotline/model/adu_screen.py` (10 tests); `config/params/adu_screen.yaml` (test bars); `scripts/dev/adu_covariate_screen.py`, `adu_screen_page.py`; `reports/adu-covariate-screen/`; page [ADU place-factor screen](https://claude.ai/artifact/DkPM2akXdQNgPsP9qiW5vQ).
- **Findings:** two candidates pass all three bars, both narrowly: owner-occupied share (β −0.71 per SD, Holm p 0.083, α −16%) and pre-1960 housing share (β +0.59, Holm p 0.095, α −11%). Both keep sign and p < 0.10 in all 57 drop-one fits. New-house rate, lot size, detached share, place size and home value not measurable; HOA and homestead share not screened.
- **AI:** Claude Code; vectorized likelihood equals `calibrate_adu` at β = 0; planted-effect recovery tests. Logged by the nightly review.

### LB-153 · 2026-11-13 · ADU model: version C, a separate effect per rule detail; exploratory, dropped (branch) (auto-review)
- **Question:** Does fitting separate effects for each ADU rule detail (not by right, parking, other restrictions, size) on #417's rows fix the joint refit's misses?
- **What I did:** (from commits c1315a72, 4cb07ee1, ba9c17c3, 20ccee47, c4f917fc on `ws/adu-version-c`; fragment `2026-11-13-ws-adu-version-c.md`) wrote the test plan before fitting; applied #417's proposed rows on the branch only; wrapped `adu_joint_refit` for the fit and scoring; added two exact speedups checked equal to the originals.
- **Outputs:** `reports/adu-version-c-2026-11/` (PLAN, README, results.html, run/); `scripts/dev/adu_version_c.py`, `scripts/dev/apply_adu_rules_proposed_2026_11.py`; page [ADU Version C Test](https://claude.ai/artifact/DMZGGyL8qPeiewq7GmuwPb).
- **Findings:** no. Version C fits the past slightly better (AIC 11) but predicts held-out places no better, passes no tier, and its effects hinge on North Carolina. Form A on the new rows alone passes test C in all five states.
- **Decisions:** Ben dropped version C as a predictor (2026-11-13); code kept on the branch.
- **AI:** Claude Code. Disclosed: a timing smoke test showed C's estimates before the main run; nothing changed after it. Logged by the nightly review.

### LB-154 · 2026-11-13 · ADU model: D-084, owner-occupied share as a place term (Form A′), built and run (branch) (auto-review)
- **Question:** Does Form A × exp(β_o z), with z the ACS 2011–15 owner-occupied share, beat Form A on D-079's tests?
- **What I did:** (from commits cb13a61f, 7760ee5e, 24de4e46 on `ws/adu-owner-share`; fragments `2026-11-13-ws-adu-owner-share.md`, `…-run.md`) Ben asked for the draft ("Draft owner share"); wrote D-084 (centre/scale from D-083's 57 places, D-079 tests, decision rule extended to apply when neither form passes). Ben accepted ("Accept D-084"); code and Built note committed before any fit (`7760ee5e`), run once offline (a first start stopped before scoring for a missing API key, rerun).
- **Outputs:** `src/lotline/model/adu_owner.py`, `config/params/adu_owner.yaml`, `tests/model/test_adu_owner.py` (10), `scripts/dev/adu_owner_refit.py`, `adu_owner_page.py`, `reports/adu-owner-share/`; D-084 in `docs/analysis_plan.md`; page [ADU owner-share refit](https://claude.ai/artifact/Ck1Jt7ZERV19TgXGWkxEeG).
- **Findings:** the rule picks A′ narrowly (held-out log score +5.0 vs a 2-SE bar of 4.1); neither form passes any tier. β_o −0.55 (−0.88 to −0.22), α −19%; every state moves the right way but TX and OR stay ~×2.5 under. Six MN townships explain why β_o is smaller than the screen's.
- **Decisions:** nothing written to config; adoption is Ben's call.
- **AI:** Claude Code; new fitter reproduces `calibrate_adu.fit3` and D-079's Form A to four figures. Logged by the nightly review.

### LB-155 · 2026-11-13 · Rules / ADU model: #417's rule rows into config, source check, and the D-083 screen rerun on them (branches) (auto-review)
- **Question:** Put the WS-ADU-RULES rows into `config/reforms`, check every value they overturn, and do D-083's place factors still pass on them?
- **What I did:** (from commits 70285914, 2ed9917e, 6e727553, ef37063f on `ws/adu-rules-config` (PR #419), and 90e70cdf, deb58649, c3b26de0 on `ws/adu-screen-new-rows`; fragments `2026-11-13-ws-adu-rules-config.md`, `…-screen-new-rows.md`)
  - Ben accepted #417's rows ("Yes, do both"); applied them by script (153 rows for 65 places replace 112 old local rows; state-law rows untouched; pinned tests updated).
  - Ben asked for a source check ("Yes, check each"): a subagent re-read the sources for 43 overturned values and 35 moved dates. Four research values reversed Ben's 2026-11-02 calls; Ben ruled "Take research" (Richfield, Inver Grove Heights, Chanhassen, Roseville).
  - Reran D-083 unchanged except the rows and Form A's multipliers, first on the new rows, then ("Rerun screen") on the final source-checked rows; plan written before the run.
- **Outputs:** `config/reforms/{mn,nc,oh,or,tx}.csv`, `scripts/dev/apply_adu_rules_proposed_2026_11.py`, `docs/research/ordinances/adu-rules-source-check-*.csv`; `reports/adu-covariate-screen-new-rows/`, `reports/adu-covariate-screen-final-rows/`; pages [ADU screen on new rules](https://claude.ai/artifact/RVRKQx3D1pr4VCFCUzgQrh), [ADU screen, final rows](https://claude.ai/artifact/Cs6N6fQCwca2NogTGv3tku).
- **Findings:** source check: values 40 research, 1 config, 1 other, 1 unresolved; dates 9 research, 1 config, 1 unresolved, 24 restructured. Final-rows screen: both factors pass, housing age strongly (Holm p 0.0004, α −30%), owner share narrowly (Holm p 0.081, α −21%; 0.110 with m_x held at 0.7); both robust to dropping any place.
- **Decisions:** Ben accepted #417's rows and the four "Take research" rulings (2026-11-13); HANDOFF decision proposed in the PR description.
- **AI:** Claude Code; result checked equal to the config the version C run read; tests and `compliance_check.py`. Logged by the nightly review.
- **Open / next:** a method entry adding owner share and housing age to Form A, scored on the data tiers.

### LB-156 · 2026-11-13 · ADU model: D-085, a calendar-year trend and a 2016–20 → 2021–25 forecast test; no trend kept (branch) (auto-review)
- **Question:** Does ADU uptake drift by calendar year, and can the model forecast later years for places it has seen (the scenario's job)?
- **What I did:** (from commits 73789939, 6dcb2d47, f7689e84, 2d3c044f on `ws/adu-time-trend`; fragments `2026-11-13-ws-adu-time-trend.md`, `…-run.md`) Ben asked to try it ("Cool let's try both of those"); wrote D-085 with no assumed sign, after correcting an earlier chat reading of the D-045 year pattern. Ben accepted ("Accept both"); code and Built note committed before any fit (`f7689e84`), run once offline.
- **Outputs:** `src/lotline/model/adu_trend.py`, `config/params/adu_trend.yaml`, `tests/model/test_adu_trend.py` (11), `scripts/dev/adu_trend_refit.py`, `adu_trend_page.py`, `reports/adu-time-trend/`; D-085 in `docs/analysis_plan.md`; page [ADU time-trend test](https://claude.ai/artifact/7XoGFvJ5UyHnyBvAV8Ypxb).
- **Findings:** the rule keeps no trend (test D gains 4.2 and 0.7 vs bars 16.3 and 15.3). In-sample γ −0.128 a year, mostly Oregon (−0.044 without). No form forecasts 2021–25 reliably; carrying forward each place's early rate does as well. Minneapolis's 2021 reform is forecast as a ~10× step that never came.
- **AI:** Claude Code; γ = 0 reproduces D-084's fitter; planted γ recovered. Logged by the nightly review.

### LB-157 · 2026-11-13 · Rules: D-086, ADU rule histories for the fit places to find rule-change events (branches, first coder, no fit) (auto-review)
- **Question:** D-079's rule-change term needs 8 events in 3 states and has 5 in 2. Can coding each fit place's rule history, blind to counts, supply more?
- **What I did:** (from commits 01a259a3, 00e99668, 84d49a7a, 44a31b69, 2c1b6b67, 4352c972, cc6ce762 and merges into `ws/adu-events-all`; fragment `2026-11-13-ws-adu-rule-events.md`) counted inputs only (26 fit places with permit years before their first coded row); wrote D-086 (first adoptions can't identify the term, so code histories with a second coder on any event-making row). Ben accepted ("Accept both"). First coders then coded MN (two batches), NC and TX/OR/OH.
- **Outputs:** D-086 in `docs/analysis_plan.md`; new and edited rows in `config/reforms/*.csv` on the branches; `reports/adu-rule-history/{mn-1,mn-2,nc,tx-or-oh}.md`.
- **Findings:** mostly adoptions (no ADUs → rule), which are not events. MN: no new events; Inver Grove Heights 2018 is probably not a grade change, and New Brighton 2024 is too late to qualify. NC: filled fields remove three earlier D-079 events. Bend's pre-2016 conditional-use lots give a candidate event. Three MN first rules were unlinked from their no-ADU rows (a blank `adus_per_lot` inherited 0).
- **AI:** Claude Code agents as first coders, blind to counts. Logged by the nightly review.
- **Open / next:** second coder on event-making rows; then the event count against D-079's bar.

### LB-158 · 2026-11-14 · ADU model: D-087, housing age as a second place term, rescored on the checked rows; Form A stays (branch) (auto-review)
- **Question:** Does housing age, or owner share, earn a place in Form A once the model is refit on the source-checked rule rows from #419?
- **What I did:** (from commits dc2010c0, 84ba6b4f, 52d4ef2a, 46544ca8, 2e690e91 on `ws/adu-age-term`, built on `ws/adu-owner-share` #418; fragment `2026-11-14-ws-adu-age-term.md`) Ben asked for the draft ("Draft it"); wrote D-087 before any fit: Form A″ = A′ × exp(β_a z_age), age standardized on D-083's 57 places, and a two-step decision under D-084's rule (A′ vs A, then A″ vs the base in use). Built a two-term fitter (vector β in `joint_refit.GlobalsA`) with hand-worked tests reproducing D-084, ran a `--smoke` check, then the full run (1 h 40 min, offline, St. Paul held out).
- **Outputs:** `src/lotline/model/adu_terms.py`, `tests/model/test_adu_terms.py`, `config/params/adu_age.yaml`, `scripts/dev/adu_age_refit.py`, `adu_age_page.py`, `reports/adu-age-term/`; D-087 in `docs/analysis_plan.md`; page [ADU housing-age refit](https://claude.ai/artifact/34Yor5h8wn51dDAT3PoXaf). PR #426.
- **Findings:** Form A stays in both steps. A′ and A″ each beat A's held-out log score by more than 2 SE but pass 1 of tests A–B against A's 2 (the gap is College Station). Age adds nothing held-out on top of owner share; within states, age carries the signal and owner share does not.
- **Decisions:** Ben accepted the rule's outcome (2026-11-14, "Accept, keep A"): Form A stays; #418 (A′) and A″ not adopted.
- **AI:** Claude Code; decision lines and log-score gains recomputed by hand from `logscores_tier1.csv`; the College Station check was run after the result and labeled so. Logged by the nightly review.

### LB-159 · 2026-11-14 · ADU model: D-088, place types shared across states (core city, suburb, town); Ben chooses Form A + place types (branch) (auto-review)
- **Question:** With no ADU form passing any data tier and a place's own past rate forecasting better than the model, can the data be segmented another way so the model carries over across all five states? Where does the place-effect spread sit?
- **What I did:** (from commits 1608fbd4, d3a302a8, 9f840b55, e50e5276, f58d7900 on `ws/adu-segments`; fragments `2026-11-14-ws-adu-segments.md`, `…-run.md`) Ben asked whether the data could be characterized or segmented another way, and stopped D-086 at the first coding (a second coder would not change the 6-events-in-2-states count). Wrote D-088 before any type, count or fit: Part 1, a breakdown of place effects by state, type and counting source; Part 2, Form P with national place types scored on D-075's tiers, tests A–B and D-085's test D. A first idea (ADUs per new home) was dropped because D-083's X4 had come out flat. Ben accepted ("Accept D-088"); inputs counted before any fit; fits run offline; a tally bug in the final step fixed and that step rerun from saved tables.
- **Outputs:** `src/lotline/model/adu_types.py`, `tests/model/test_adu_types.py`, `scripts/dev/adu_types_refit.py`, `adu_types_page.py`, type terms in `joint_refit.GlobalsA`, `reports/adu-place-types/`; D-088 in `docs/analysis_plan.md`; page [ADU place types](https://claude.ai/artifact/F8JER4WdEHK6GUn581E4J3). PR #427.
- **Findings:** the fit set's types line up with its states (16 core cities in 5 states; 48 suburbs in MN and NC). Under Form A, state, type and source each explain about a quarter of the spread (29% together); ~70% is between look-alike places. A core-city term (×3.3) replaces Form A by the rule (tier-1 log score +7.2 vs 2 SE 6.1; useful states 0/0/0 → 2/3/3) but does not improve A′ (owner share and core city correlate −0.68). No tier passes the claim rule; carry-forward still wins test D.
- **Decisions:** Ben chose Form A + place types (2026-11-14), settling D-084.
- **AI:** Claude Code; 11 new hand-worked tests; Form A and A′ reproduce D-084 to the digit; planted type terms recovered; `compliance_check.py` 0 FAIL. Logged by the nightly review.

### LB-160 · 2026-11-14 · ADU model: D-089, state place profiles, share outside the fit's evidence, and a town prior (branch) (auto-review)
- **Question:** Ben asked whether each state's mix of places ("proportion of suburb, city, population, price etc") could give a coefficient or modifier. How much of each state's ADU forecast rests on places like the fitted ones?
- **What I did:** (from commits cf65246d, e410bcb8, 0d4fd3e3 on `ws/adu-state-profiles`; fragments `2026-11-14-ws-adu-state-profiles.md`, `…-run.md`) recommended against a state-level coefficient (the model already sums place by place, so it would double count, and four scorable states can't support one); wrote D-089 before tabulating: state profiles by type, share of lots outside the evidence with a 25% labeling rule, a town prior N(0, 0.729²) from D-088's core-city gap, and one sensitivity run. Ben accepted ("Accept D-089"); built and ran; two run errors (county-remainder owner-share lookup, state-code case) fixed before any total was read.
- **Outputs:** `src/lotline/model/adu_profiles.py`, `tests/model/test_adu_profiles.py`, `scripts/dev/adu_state_profiles.py`, `adu_profiles_page.py`, `reports/adu-state-profiles/`; D-089 in `docs/analysis_plan.md`; page [ADU state profiles](https://claude.ai/artifact/GoxSAAjVEv2szddSuRSJEb).
- **Findings:** all five states are labeled: 63–93% of lots are outside the evidence, mostly on price and size; towns are 9–30% of lots but yield 1–5% of expected ADUs, so the town prior barely moves ranges. Share of expected ADUs from places outside the evidence runs from 25% (NC) to 96% (TX). The fitted suburbs are all pricey Twin Cities and Triangle ones; lower-priced suburbs would be the most useful new data.
- **AI:** Claude Code; 6 hand-worked tests (totals match `pool_paths` draw by draw); a rerun reproduced every total. Logged by the nightly review.

### LB-161 · 2026-11-14 · ADU model: D-090 and D-091, can own history forecast 2021–2025, and does a drift term make the ranges honest? (branches) (auto-review)
- **Question:** D-090: fit on 2016–2019, can a state's own ADU history forecast 2021–2025 (MN, NC, TX, OR)? D-091: after D-090's ranges came out far too narrow, does a per-place period drift, with its spread learned leaving one state out, fix them?
- **What I did:** (from commits 952f54d3, 62669bd5, d03ec95e on `ws/adu-time-split` (#429), and a69c7b7a, d8429d88, aa95f539, 31b18595 on `ws/adu-drift`; fragments `2026-11-14-ws-adu-time-split.md`, `…-adu-drift.md`)
  - Ben asked ("Draft it D-90"); before writing, tallied observed vs expected totals by state and year (no common trend, so no pooled trend term). D-090: forecasters F0 persistence, F1 Form A with state θs and own history, F2 F1 + housing age; claim if F1 useful in 3 of 4 states and beats persistence by 2 SE. Ben accepted with the 3-of-4 bar; places and rule changes committed (62669bd5) before any fit.
  - D-091: measured how far large places moved from persistence (log-ratio SD 1.07) on the windows to be scored, disclosed, hence the leave-one-state-out σ (Ben's choice). Rule 3 added: 65–95% of places inside their P10–P90. Ben accepted on two conditions (rollback possible; report shows clear evidence on predictive power). A hand-worked test showed 40 Gauss–Hermite nodes under-estimate σ for large places, so the integral switched to a trapezoid rule (disclosed).
- **Outputs:** `src/lotline/model/adu_forecast.py` (incl. drift functions), `tests/model/test_adu_forecast.py`, `scripts/dev/adu_time_split.py`, `adu_time_split_page.py`, `adu_drift.py`, `adu_drift_page.py`, `reports/adu-time-split/`, `reports/adu-drift/`; D-090, D-091 in `docs/analysis_plan.md`; pages [ADU own-history forecast](https://claude.ai/artifact/Bfz5915ng524v1tJu1mW1o), [ADU forecast drift](https://claude.ai/artifact/G4sRpudCfVVXt8PyWV2asM).
- **Findings:** D-090: no. F1 useful in 1 of 4 states and no better than persistence (−5.5 vs 2 SE 204); F2 worse; persistence's medians within ×2 in every state but ranges about ±9%, far too narrow. The mechanism priced NC's rule changes well (Wilmington, Charlotte) and over-priced Minneapolis and Bend. D-091: coverage 58% → 81%, persistence + drift useful in 3 of 4 states; log-score gain +429 vs 2 SE 551 (mostly Portland), so better predictive power is not shown at the pre-set bar; per-place CRPS improves 13%, F1's state totals get worse. A README row for the summed log score was corrected afterwards (gains unchanged).
- **Decisions:** D-090 and D-091 accepted as methods by Ben (2026-11-14); both results and the tool outcome D-091 triggers await Ben.
- **AI:** Claude Code; 57 and 23 tests pass, ruff clean; rollback check gap 3.6 × 10⁻¹⁵; page claims checked against CSVs (two sentences corrected before publishing). Logged by the nightly review.

### LB-162 · 2026-11-14 · ADU model: Form A + place types into config and the scenario engine, and the anchor's draw terms recomputed (branches) (auto-review)
- **Question:** With Ben's choice of Form A + place types (D-088) and D-089's town prior, what changes when the scenario engine runs that model?
- **What I did:** (from commits d36bd9fe, 3b5a2625 on `ws/adu-types-config`, eaa0a15a on `ws/adu-types-engine`, 2b3b134b on `ws/adu-types-slopes`; fragments `2026-11-14-ws-adu-types-config.md`, `…-types-engine.md`, `…-types-slopes.md`)
  - Config ("Open the config PR"): wrote the typing rules, the A + P fit and the town prior sd; reran the central fit once offline to read intervals the D-088 run didn't save; corrected a note on the core term's SE (0.411).
  - Engine ("Wire it here"): moved typing code into `adu_types.py`, added type multipliers and a `place_type` column to `scenarios/adu.py`, updated θ, α, m_o, m_x in config; ran the engine before and after the switch, plus an m_x = 1.0 run to split the change.
  - Slopes ("Recompute slopes"): recomputed the anchor's θ and α draw slopes for the D-088 fit and reran the statewide check (rerun from the start after a laptop restart cut off the first attempt).
- **Outputs:** `config/params/adu_place_types.yaml`, `adu.yaml`, `adu_anchor.yaml`, `hazard.yaml`; `src/lotline/model/adu_types.py`, `src/lotline/model/scenarios/adu.py`; tests in `tests/model/test_adu_types.py`, `test_scenario_adu.py`; `scripts/dev/adu_types_engine_check.py`, `adu_types_engine_page.py`, `adu_types_slopes.py`, `adu_types_slopes_page.py`; `reports/adu-types-engine/`, `reports/adu-types-slopes/`; notes under D-089 and parameter table in `docs/model_and_assumptions.md`; pages [ADU engine with place types](https://claude.ai/artifact/Wn5ktV2Hvo26TQdTEseNci), [ADU anchor slopes](https://claude.ai/artifact/FiiNrCDR2gxt3q8FBjtRnZ).
- **Findings:** additional homes at P50 rise: MN 286 → 634, NC 139 → 575, OH 236 → 422, TX 1,902 → 4,809; Oregon 26 → 29; ranges widen. Types and the new anchor drive most of the rise in OH and TX; partial rules at m_x 0.4 drive most of it in MN and NC. Recomputed slopes: θ close to D-053's, α about half, core term negligible; statewide totals move at most 3.4% at P50 and 5.7% at P90. θ's width still comes from the profile interval.
- **Decisions:** Ben approved writing the values to config and wiring the engine (2026-11-14); not yet merged to `main`.
- **AI:** Claude Code; the central refit reproduces D-088 exactly; moved typing code reproduces all 3,633 saved jurisdiction types; hand-worked hazard tests; full suite and `compliance_check.py`; three page claims corrected before publishing. Logged by the nightly review.

### LB-163 · 2026-11-14 · Docs: handoff 16, what was tried for the five-state ADU fit and what worked (branch) (auto-review)
- **Question:** Ben asked for a short handoff for his ADU thread: what was tried and what worked, in case it helps find a better way.
- **What I did:** (from commit 032977fc on `ws/adu-handoff`; fragment `2026-11-14-ws-adu-handoff.md`) summarized D-079 to D-090 and the engine switch from the analysis-plan entries and PR bodies.
- **Outputs:** `docs/build/handoffs/16-adu-model-what-we-tried.md`; a row in `docs/build/handoffs/README.md`.
- **Findings:** a coarse national place type is the only change that passed held-out scoring; extra place covariates and time terms didn't; a place's own recent rate beats every model form where counts exist. Four ideas: own history plus drift where counts exist, a drift term, counts for cheap suburbs from open portals, and a look at counting source.
- **AI:** Claude Code; each number checked against its D-entry or PR; two first-draft claims corrected (α's range across fit sets; the engine-switch split by state). Logged by the nightly review.

### LB-164 · 2026-11-15 · Admin: missing middle renumbered D-082 → D-092, the ADU PR stack rebased into one line, CI fixed, and the stacks merged to `main` (auto-review)
- **Question:** Two methods shared the number D-082 and the ADU and missing-middle PR stacks had red CI; how do we untangle them so they can merge?
- **What I did:** (from commits 2f048deb … 50e01eb9, a6e58de5, the 06:55–07:50 rebased ADU commits, 680051f8/bc52a7d4/9d2add60/adb0dfa8, 55d533a3, and merges e1106f1b … 73731257, 4646aca9; fragment `2026-11-15-ws-mm-review-renumber.md`)
  - Renumbered missing middle's method D-082 → D-092 (ADU's D-082 had merged first) with one deterministic script on each of eight stacked MM branches: new commits, no rebase; Ben's quoted "Approve D-082" kept verbatim; paths `*_d082*` → `*_d092*`. Later the ADU engine wiring was renumbered D-092 → D-093, and the ADU first-years draft D-098 → D-099, as numbers collided again.
  - Rebased the ADU stack into one line (#418 → #420 → #427 → #428 → #431 → #432 → #434 → #426 → #429 → #430 → #435); lint-only commits fixed the `ruff check .` failure from `adu_trend_page.py`; four MM PRs (#395, #397, #398, #401) merged with `main` to pick up the Cincinnati test fix; the parameter table regenerated.
  - In the evening the ADU PRs (#420, #426–#432, #434, #435, #437, #440) and the missing-middle stack (#436) were merged to `main`.
- **Outputs:** renumbering commits on `ws/mm-review`, `ws/mm-rule-rows`, `ws/mm-run1-coverage`, `ws/mm-run2-3`, `ws/mm-run5` and three `claude/mm-*` branches; PR titles updated; `main` now carries both stacks.
- **Findings:** the collision came from one session drifting from missing middle into ADU work while a second ADU session ran; since 2026-11-15 each model has one owning session. Published result pages still say D-082.
- **Decisions:** one owning session per model (ADU: "ADU statewide prediction methodology"; missing middle: the MM session).
- **AI:** Claude (Opus 5.5); dry run read line by line, grep on every branch afterwards (only Ben's quotes say D-082), ruff, `compliance_check.py` and the full suite on every branch. Logged by the nightly review.

### LB-165 · 2026-11-15 · Study design / Calibration: missing middle's baseline gets its own uncertainty (D-092 deviations a–b, runs 7–11) (auto-review)
- **Question:** Runs 4–5 found no missing-middle model passes §7, mainly because the no-reform baseline was treated as known. How can the baseline carry honest uncertainty without slowing each fit?
- **What I did:** (from commits c7ae1a67, 3d313801, b48bdfa3, 5890ce71, b7b0a15b, b8e93229, 24f4c295, 7fdb31bf on `ws/mm-baseline-spread`; fragment `2026-11-15-ws-mm-baseline-spread.md`)
  - Deviation pre-registered under D-092 (Ben: "Yes, start step 1"); a place multiplier w ~ Gamma(1, κ) that integrates out in closed form. Run 7 estimated κ on 483 uncoded places: κ̂ = 7.65, unusable (median multiplier 0.02) because 2–4 unit buildings come in projects.
  - Deviation (b): four baseline constructions × two noise forms pre-registered (5890ce71) before any scoring; run 8 picked C0-year (3-year baseline, per-year negative binomial, φ 9.13), coverage 0.79.
  - Runs 9–11 ("Yes, code and refit"): φ = 13.63 on both origins; refit (44 min) gives M's θ 1.68 per 1,000 (0.12–21.9); §7: test B, leave-one-state-out and coverage (0.84) pass; test C misses only MN's three-place total; placebo still fails; §5's rule picks C4.
- **Outputs:** `src/lotline/model/calibrate_mm.py`; `scripts/dev/mm_kappa_d092.py`, `mm_baseline_choice_d092.py`, `calibrate_mm_d092.py`, `mm_tests_d092.py` and page scripts; `tests/model/test_mm_baseline_spread.py` (33 tests); `reports/mm-d092/run7-kappa/` … `run11-tests-phi/`; pages [Missing-middle baseline spread](https://claude.ai/artifact/7PUN5YyVXbsDUSsg3e6SWD), [baseline choice](https://claude.ai/artifact/BUNjwor6A2oD2WpUyEZLg8), [lumpy-year refit](https://claude.ai/artifact/Nc9Y2HZMAgmZbdb4sHPEEf).
- **Findings:** per-year noise beats a place multiplier by ~1,500 log points; the ranges are now honest but too wide to show the reform effect (M beats no-effect by 5.0, SE 3.4).
- **Decisions:** each run was approved by Ben in turn; Ben also decided place types are a planned step whatever the result.
- **AI:** Claude (Opus 5.5); closed form checked against quadrature, κ and φ recovered from simulation, κ = 0 / φ = 0 draws bit-identical to the old code, full suite (2,178). Also diagnosed CI failures Ben asked about. Logged by the nightly review.

### LB-166 · 2026-11-15 · Calibration / Deliverables: missing middle runs 12–13, what it counts, C4 to config, an accuracy report and the methodology write-up (auto-review)
- **Question:** Do place types or counting projects narrow the missing-middle ranges, which model goes to config, and how accurate is it?
- **What I did:** (from commits 23a09b4a, 4174e4c8, 5b763a95, 84514e78, 8dc40a28, a453f0e5, f0c9e92d, ec4268b2; fragments `2026-11-15-ws-mm-baseline-spread.md`, `2026-11-15-ws-mm-docs-c4.md`)
  - Deviation (c), place types (shared `src/lotline/model/place_types.py`), pre-registered; run 12: φ by type +24.8 (paired SE 32.9), not adopted; one φ kept.
  - Disclosed what is counted (Ben: "Keep 2–4, disclose gaps"): BPS 2-unit and 3–4 unit buildings only, so the result is a floor for the Handbook's 2–6 homes and townhouses.
  - Deviation (d), buildings per project, pre-registered; run 13: pooled inflation 12.8 by lot, 5.3 by day, so the project model goes back to Ben; Ben chose "Record it, choose config"; clustering recorded as the reason the ranges are wide.
  - C4 (θ 1.04 per 1,000, φ 13.63) written to config, with lumpy years in the scenario; accuracy report built from results on file; `docs/model_and_assumptions.md` gains a missing-middle model section.
- **Outputs:** `config/params/mm_hazard.yaml`, `src/lotline/model/scenarios/mm.py`, `src/lotline/model/project_size.py`, `reports/mm-d092/run12-types/`, `run13-projects/`, `config-c4/`, `accuracy/`; `docs/model_and_assumptions.md`; pages [Missing-middle place types](https://claude.ai/artifact/G5ceVA6aHXtUBP9UUMJEDf), [project size](https://claude.ai/artifact/BvoadqpTCF3itcSBYUYdgq), [config C4](https://claude.ai/artifact/1BzpK5S9isRk9eptDaBKDR), [accuracy](https://claude.ai/artifact/72uydyJJNJduLuErr9uQXw).
- **Findings:** statewide five-year median net homes rise about 2.5× under C4 (MN 696 → 1,758; TX 4,747 → 12,066). 78% of 136 places fall inside P10–P90; Oregon held out 703 built against a median of 915. The reform effect itself is not clearly detected. Minneapolis's adapter types ~950 permits as 3–4 unit with 0 new homes (worth a look).
- **Decisions:** Ben chose C4 for config (2026-11-15); proposed for HANDOFF in the PR.
- **AI:** Claude (Opus 5.5); grouping code with 7 hand-worked tests, every page number read from result files, CI set. Logged by the nightly review.

### LB-167 · 2026-11-15 · Validation: V5 St. Paul with C4, method (D-098), freeze and scoring script (auto-review)
- **Question:** Can St. Paul's blind test be frozen with the C4 model and scored in one step once Ben unblinds?
- **What I did:** (from commits 9ee70aa6, 092882c1 on `ws/mm-baseline-spread` and d61a87b4 on `ws/v5-stpaul-score`; fragments `2026-11-15-ws-mm-baseline-spread.md`, `2026-11-15-ws-v5-stpaul-score.md`)
  - Ben: "Let's try St. Paul". Wrote D-098 before any prediction (BPS 2–4 unit buildings, pass rule on 2024–2025, inputs read only before 2024); prediction code with a dry run.
  - Ben: "Freeze now on #436". Froze `results/frozen/V5-MN-STPAUL.json` (4,000 draws, seed 20261108): 2024–2025 P10 9, P50 15, P90 28 buildings.
  - Wrote `scripts/dev/v5_stp_score.py`: refuses unless the holdout is released, regenerates and checks the frozen draws, scores 2024–2025 and later years.
- **Outputs:** `src/lotline/validation/v5_stpaul.py`, `scripts/dev/v5_stp_predict.py`, `v5_stp_score.py`, `tests/core/test_v5_stpaul.py`, `results/frozen/V5-MN-STPAUL.json`, D-098 in `docs/analysis_plan.md`.
- **Decisions:** D-098 recorded; the freeze is ahead of the 17 Nov deadline. Scoring waits for Ben's "unblind".
- **AI:** Claude (Opus 5.5); 8 hand-worked tests; the freeze matches the dry run exactly; no outcome read. Logged by the nightly review.

### LB-168 · 2026-11-15 · ADU model: D-093, the engine takes a place's own counts with drift, and a scorecard of every ADU test (auto-review)
- **Question:** What happens to statewide ADU results when places with counts take their no-reform rate from those counts with drift (D-091's outcome), and how do all the ADU model versions compare?
- **What I did:** (from commits 4e73ec85, bb93d21a, 96640dfd, a40c09cf on `ws/adu-engine-drift` (#435); fragment `2026-11-15-ws-adu-engine-drift.md`) wired own-rate draws into `scenarios/adu.py`, with the bill's effect as the model's ratio; recorded Ben's adoption of D-091 (5c62865b). Separately, a page gathered every held-out ADU score since D-079 by version, state and tier, plus project status (no new run).
- **Outputs:** `src/lotline/model/scenarios/adu.py`, `config/params/adu.yaml`, `tests/model/test_adu_own_rate.py`, `scripts/dev/adu_engine_drift_check.py`, `_page.py`, `reports/adu-engine-drift/`, D-093 in `docs/analysis_plan.md`; pages [ADU engine with own counts](https://claude.ai/artifact/RbG2SiXAtPKiJY1xMoyTQV), [ADU prediction scorecard](https://claude.ai/artifact/9FPeepkWbJF6RReNtcPU9b) (the scorecard is not in the repo).
- **Findings:** additional homes move under 10% at P50 in every state; the no-reform baseline falls in MN, NC, OH and TX. Scorecard: A + place types is useful in 3 of 4 held-out states at tiers 1–2, short of D-075's 4-of-5 bar; a place's own rate with drift is best within a state.
- **AI:** Claude Code; hand-worked tests, switch-off identity, model suite. Scorecard intent read from the page itself. Logged by the nightly review.

### LB-169 · 2026-11-15 · ADU model: A + place types on the checked rows, range coverage, and D-094 (a spread per place type, not adopted) (auto-review)
- **Question:** Does A + place types still hold on the source-checked rule rows, are its ranges the right width, and should core cities and suburbs have their own place-luck spread?
- **What I did:** (from commits 7e3e21dc, a061f7c1, 40da50ea, 9792a6a1; fragments `2026-11-15-ws-adu-types-checked-rows.md`, `…-range-coverage.md`, `…-type-spread-draft.md`, `…-type-spread.md`)
  - Reran D-088's unchanged script on the checked rows (#437).
  - Range coverage check (Ben asked): leave-a-state-out refits and predictive draws, with each source of width switched off.
  - Drafted D-094 ("Draft D-094"), Ben accepted and asked for the run; built `fit3_types(spread=True)` and scored it held out.
- **Outputs:** `reports/adu-place-types-checked/`, `reports/adu-range-coverage/`, `reports/adu-type-spread/`; `src/lotline/model/adu_types.py`, `adu_screen.py`, `joint_refit.py`, `adu_trend.py`; D-094 in `docs/analysis_plan.md`; pages [ADU Place Types, Checked Rows](https://claude.ai/artifact/78HMSfvqJRfySqQrNpf6cd), [ADU Range Coverage](https://claude.ai/artifact/DM6piJbfqSHe6RBZMQVrRh), [ADU Spread by Type](https://claude.ai/artifact/1QRuqXpv5b1rrYFDPBszR9).
- **Findings:** on checked rows A + P is useful in all 4 scorable states at tiers 1 and 2, the first form to pass D-075's claim rule (D-088's rule still keeps Form A on one place). Ranges about right overall (69% in the middle 80%); core cities too wide, suburbs too narrow. D-094: no held-out gain (−0.1, 2 SE 2.9), A + P kept, nothing to config.
- **AI:** Claude Code; fits reproduce D-087/D-088; λ = 0 reproduces A + P exactly; a width-split bug found and the run repeated. Logged by the nightly review.

### LB-170 · 2026-11-15 · ADU model / Rules: D-095 reform-ratio check, the coverage audit, 33 rule rows corrected, D-096 refit and config moved to it (auto-review)
- **Question:** Does the engine's reform ratio match real in-window rule changes, and are the rule rows coded consistently enough to trust it?
- **What I did:** (from commits 1973d3a9, 96053858, c9f24d50, 6b6075a4, 82e6e1b3, 66b22d8b, f3cc59eb, 8626efeb, f6801252; PR #440; fragments `2026-11-15-ws-adu-reform-ratio.md`, `…-coverage-audit.md`, `2026-11-15-adu-coverage-fix.md`, `…-fixed-rows-refit.md`, `…-config-d096.md`)
  - D-095 ("Test reform effect"): method committed before any score; 10 events in 3 states: "not shown either way" (+4.2, 2 SE 7.9).
  - Coverage audit ("Yes, check coverage") found three coding patterns; a rules session then corrected 33 rows and annotated 26 (`docs/research/adu-coverage-fix-2026-11.md`).
  - D-096 ("Yes, fix then refit"): A + P refitted on the fixed rows; then config moved to it ("Yes, update config").
- **Outputs:** `src/lotline/model/adu_reform_check.py` and tests; `scripts/dev/adu_reform_ratio.py`, `adu_coverage_audit.py`, `adu_refit_fixed_rows.py` and page scripts; `config/reforms/{mn,nc,or,tx}.csv`; `config/params/adu*.yaml`, `hazard.yaml`; `reports/adu-reform-ratio/`, `adu-coverage-audit/`, `adu-types-fixed-rows/`, `adu-config-fixed-rows/`; D-095, D-096 in `docs/analysis_plan.md`; pages [ADU Reform Ratio Check](https://claude.ai/artifact/JggHUyaPLYuJxwMFBvMk6j), [ADU Refit on Fixed Rules](https://claude.ai/artifact/XNZB6mCqWFQzzModq2oeLQ), [ADU Config Update](https://claude.ai/artifact/N2MHdgvxHh3KL3rM2nLP7i).
- **Findings:** D-096: m_x 0.4 → 0.7, θ 0.448 → 0.240 per 1,000, α 1.55 → 1.44, core +1.67; held-out state ranges narrow (NC ×24 → ×18). The Handbook bill's five-state additional ADUs fall from 6,819 to 3,948 at P50, driven by m_x (its leave-one-state-out range 0.4–1.0, flagged for Ben).
- **Decisions:** Ben approved the D-096 config update (2026-11-15).
- **AI:** Claude Code / Opus 5.5 with research subagents for district lists; coverage recomputed before and after every changed row; two wrapper bugs fixed before results were read; 72 ADU tests pass. Logged by the nightly review.

### LB-171 · 2026-11-15 · ADU model: D-097, m_x drawn from a refitted grid, and the ADU gut-check page (auto-review)
- **Question:** Carry m_x's uncertainty into the ADU ranges, then show Ben how well the model predicts within a state and what it gives for 2027–31 ("My goal here is to gut check the results").
- **What I did:** (from commits ff47ed9d, 2b62084a, 06ad7be2, baae2a7a; fragment `2026-11-15-ws-adu-d097-gut-check.md`) drafted D-097 (accepted), built grid draws (off by default), ran the fits and five engine variants, built the gut-check page and checked it in the browser.
- **Outputs:** `config/params/adu_partial_share_grid.csv`, `adu_partial_share_draws` in `adu.yaml`, `scenarios.adu.apply_partial_share_grid`; `scripts/dev/adu_mx_grid.py`, `adu_mx_engine.py`, `adu_gut_check_*.py`; `reports/adu-mx-grid/`, `adu-mx-engine/`, `adu-gut-check/`; page [ADU Gut Check](https://claude.ai/artifact/GTSTVZFmMr7gdwJsV52KXq).
- **Findings:** drawing m_x keeps medians and widens ranges somewhat; within-state forward forecasts land inside their ranges. Flags large predicted gains in core cities with no ADUs allowed today (Dallas, Fort Worth, Cleveland) and a no-reform mean above recent counts.
- **AI:** Claude Code; the grid's 0.7 row equals D-096's fit; mode 3 at 0.7 reproduces the fixed run exactly; held-out mixture score not computed (disclosed). Logged by the nightly review.

### LB-172 · 2026-11-15 · Data feasibility: ADU count sources in Texas, Oregon and Ohio (auto-review)
- **Question:** Are there public record-level permit files that would let more TX, OR and OH places, especially core cities, enter the ADU fit (D-074, D-078)?
- **What I did:** (from commits f035290f, 2cf0fd0f, 0ee36075; fragment `2026-11-15-adu-data-hunt.md`) three research subagents, one per state; TX/OH count queries and ≤200-row samples (nothing saved); Oregon metadata only (V9 holdout).
- **Outputs:** `docs/research/adu-count-sources-tx-or-oh-2026-11.md`.
- **Findings:** no new core city clears the bar cleanly; Houston is a lower bound only. Deschutes and Jackson counties (OR) look usable from metadata; Keizer is the cheapest new place after unblinding. `fw_permits` already uses Fort Worth's ArcGIS layer.
- **Decisions:** none; candidates proposed for Ben.
- **AI:** Claude Code (Opus 5.5) via subagents; the lead session re-ran the Fort Worth count, downgrading a subagent verdict. Logged by the nightly review.

### LB-173 · 2026-11-15 · Rules: ADU rules for the 20 largest uncoded places in Minnesota and Ohio; Blaine's moratorium recoded (auto-review)
- **Question:** What are the ADU rules (2016 to today) in the uncoded places carrying the most predicted added ADUs, and why did Blaine read as uncoded?
- **What I did:** (from commit d289eed8 on `adu-uncoded-rules`; fragment `2026-11-16-adu-uncoded-rules.md`) ranked the gut check's unknown-rule places, researched 40 places with subagents plus an independent second pass; recoded Blaine's `suspended` moratorium as an in-force no-ADU row; family-only units coded as no ADU.
- **Outputs:** `config/reforms/oh.csv` (+20 rows), `config/reforms/mn.csv` (+24 rows, Blaine edited), `docs/research/adu-uncoded-rules-2026-11.md`, `reports/adu-coverage-audit/` rerun, place whitelist in `tests/states/{oh,mn}/test_reforms.py`.
- **Findings:** the coded places hold 23.5% of Ohio's and 30.8% of Minnesota's uncoded added ADUs; 27 of 40 have an explicit no-ADU rule for some or all of the period. 18 Ohio county remainders are township-zoned and can't be one rule.
- **Decisions:** proposed for HANDOFF: moratoria coded as in-force no-ADU rows; family-only / no-rental units coded as no ADU.
- **AI:** Claude subagents researched, a second pass re-opened every source; rows appended by script; `pytest -k reform` 99 passed, `compliance_check.py` 0 FAIL. Logged by the nightly review.
- **Open / next:** ADU refit on the new rows.

### LB-174 · 2026-11-15 · ADU model: D-099 drafted, uptake in the first years after a place first allows ADUs (code behind ν = 1, not run) (auto-review)
- **Question:** The gut check gives places that first allow ADUs (Dallas, Fort Worth, Cleveland) the full fitted core-city rate; do such places build less in their first years?
- **What I did:** (from commits 0ad5a32b, a281b65c, 6ecbcb60; fragment `2026-11-16-ws-adu-new-rule-draft.md`) listed ~27 first ADU-allowing rows in fit places from the rule rows only (no counts read); drafted the entry; wrote helpers and an engine term behind ν = 1 with hand-worked tests; wrote the profile and held-out script without running it. Renumbered D-098 → D-099 after missing middle took D-098.
- **Outputs:** D-099 in `docs/analysis_plan.md` (not accepted); `src/lotline/model/adu_new_rule.py`, `tests/model/test_adu_new_rule.py`, `adu_new_rule_share` in `config/params/adu.yaml`, ν term in `scenarios.adu.pool_paths`, `scripts/dev/adu_new_rule.py`.
- **AI:** Claude Code; ν = 1 leaves every existing test unchanged; ruff passes. Logged by the nightly review.
- **Open / next:** Ben's acceptance, then the run.


### LB-175 · 2026-11-16 · ADU model: D-099 accepted and run (first-years share 0.75, no held-out gain, ν stays 1); gut check corrected to medians (auto-review)
- **Question:** Do places that first allow ADUs build less in their first years (D-099, LB-174), and does that explain the gut check's large Dallas and Fort Worth predictions?
- **What I did:** (from commits 7fc974c2, 07b95e6e, e96b9813, 68e954ef on `ws/adu-new-rule-uptake`; fragment `2026-11-16-ws-adu-d099-result.md`)
  - Ben: "I accept D-099"; acceptance committed before any fit.
  - Ran the accepted script: profile, leave-one-place-out held-out check and three sensitivities (K = 3, explicit no-ADU before, without Raleigh); built the results page.
  - Same-day correction: the gut check had compared Dallas's mean over draws with other cities' actual rates; the gut-check page now compares medians with ranges, matched by state, and D-099's Dallas reading was corrected.
- **Outputs:** `reports/adu-new-rule/`, `scripts/dev/adu_new_rule_page.py`, D-099 result in `docs/analysis_plan.md`; `reports/adu-gut-check/` and `scripts/dev/adu_gut_check_{page,places}.py`; pages [ADU First-Years Uptake](https://claude.ai/artifact/GZoQ3mG5iVvKhRzwQGVLEb), [ADU Gut Check](https://claude.ai/artifact/GTSTVZFmMr7gdwJsV52KXq) (updated).
- **Findings:** ν̂ 0.75 (0.70–0.85) in the fit but no held-out gain (−0.11, 2 SE 1.86), so ν stays 1 and config is unchanged. Dallas's median is 0.35 a year per 1,000 lots (P10–P90 0.01–5.1), below Austin's and Portland's built rates; the earlier "gap" was mostly mean vs median.
- **Decisions:** D-099 accepted by Ben (2026-11-16); ν = 1 kept. Whether Dallas's special-exception rule should be coded as restricted is open for Ben.
- **AI:** Claude (Opus 5.5); ν = 1 profile row reproduces the D-096 fit; placeholder years cut as logged. Logged by the nightly review.

### LB-176 · 2026-11-16 · Validation: V5 St. Paul unblinded and scored, a miss (D-098) (auto-review)
- **Question:** Does the frozen C4 missing-middle forecast for St. Paul (LB-167) hold up once the holdout is released?
- **What I did:** (from commits 416a3444 on `ws/v5-stpaul-score` (#442) and efb55955 on `ws/mm-docs-c4`; fragments `2026-11-15-ws-v5-stpaul-score.md`, `2026-11-15-ws-mm-docs-c4.md`) Ben: "Yes, unblind". Released the holdout in `config/states/mn.yaml` (`released_on: 2026-11-16`), ran `v5_stp_score.py` (which regenerated the frozen draws exactly first), added post-hoc ramp rows (reported only), built the page, added St. Paul to the accuracy report and to the V5 row and model section in `docs/model_and_assumptions.md`; adapter tests that used V5 as a filter example now use a blind registry.
- **Outputs:** `reports/v5-stpaul/` (README, `score.json`, `posthoc_ramp.json`, `results.html`), `scripts/dev/v5_stp_page.py`, D-098 "Scored" bullet in `docs/analysis_plan.md`, `docs/model_and_assumptions.md`; pages [St. Paul blind test](https://claude.ai/artifact/19Eyqzf78EtfjJtRqivixd), [Missing-middle accuracy](https://claude.ai/artifact/72uydyJJNJduLuErr9uQXw) (updated).
- **Findings:** **miss**: 55 new 2–4 unit buildings in 2024–2025 against P10–P90 9–28 (98th percentile); it still beats no reform on CRPS (32.8 vs 40.0). Post-hoc: C4's level with a half-way point near 1 year gives a median of 55, so C4's level fits and its 4-year ramp is too slow.
- **Decisions:** Ben unblinded (2026-11-16). Config unchanged; any ramp change is a new entry (became D-100, LB-177).
- **AI:** Claude (Opus 5.5); frozen draws regenerated before scoring; a chart-label mix-up caught before publishing. Logged by the nightly review.

### LB-177 · 2026-11-16 · Calibration: D-100, one ramp or one per adoption route, proposed, coded and run; C4 stays (auto-review)
- **Question:** After St. Paul's miss, should the missing-middle ramp change, and is it one ramp or one for local reforms and one for state mandates (Oregon HB 2001)?
- **What I did:** (from commits 980630dc, 3c16df8f, 30a635e7, cbbe2fde on `ws/mm-ramp-entry`; fragment `2026-11-16-ws-mm-ramp-entry.md`)
  - Ben: "Draft a ramp entry". Read run 10's fits and wrote D-100: R0 (C4), R1 (one ramp, St. Paul added), R2 (a ramp per adoption route), chosen by D-092 §5's 2-SE rule.
  - Ben: "Approve, run the refit". Merged the St. Paul release in; wrote `mm_routes` (HB 2001 route rule, age shift, `fit_routes`), `build_panel(include=)` that refuses a blind holdout, the Metro crosswalk and the run, summary and page scripts; dry run 57 state-required and 37 local places; ran run 1.
- **Outputs:** D-100 in `docs/analysis_plan.md`; `src/lotline/model/mm_routes.py`, `estimate_mm.py`, `tests/model/test_mm_routes.py`, `test_estimate_mm.py`; `config/crosswalks/or_hb2001_metro.csv`; `scripts/dev/mm_ramp_d100.py`, `mm_ramp_d100_summary.py`, `mm_ramp_page.py`; `reports/mm-d100/run1/`; page [Missing-middle ramp test](https://claude.ai/artifact/GNK6HcwX39PvgsdWwkisJ5).
- **Findings:** in the fit, local adopters reach half speed at 0.5 years and HB 2001 places at 4.0, in every fold; held out, R1 vs C4 −2.68 (SE 1.70) and R2 vs R1 −0.15 (SE 1.01): nothing beats by 2 SE, so **C4 stays** and nothing goes to config.
- **Decisions:** D-100 approved for the run by Ben (2026-11-16); outcome C4 kept.
- **AI:** Claude (Opus 5.5); 7 hand-worked tests; a JSON key bug at the last step, summary rebuilt from the saved fits without refitting. Incident: rebuilding MN BPS with St. Paul's released rows tripped the ADU session's holdout-leak check; rebuilt blind from clean `main`; MN BPS needs one more offline rebuild after #442 merges. Logged by the nightly review.

### LB-178 · 2026-11-16 · ADU model / Repo: ADU stack (#418) and uncoded rules (#444) merged to main; final ADU config refit with m_x draws on (auto-review)
- **Question:** Bring the ADU model stack onto `main` and set the ADU config to its final state for the app's results bundles.
- **What I did:** (from commits 0cf22321, 4811bf7c (#418), 0f394f33 (#444), 8f2b5a86 on `ws/adu-final-config`; fragment `2026-11-16-ws-adu-final-config.md`)
  - Merged main into `ws/adu-owner-share` (missing-middle rows from main, ADU rows from the stack, both sets of decision entries kept), then #418 to `main`: the ADU stack from D-084 onward (place types, rule rows, coverage fix, D-096 config).
  - Merged #444 (LB-173's MN/OH rule rows) on Ben's word; refit A + place types on main's rows; regenerated the m_x grid and anchor slopes; turned on D-097's m_x draws; updated pinned tests and the parameter table.
- **Outputs:** `config/params/hazard.yaml`, `adu.yaml` (`adu_partial_share_draws: 1`), `adu_place_types.yaml`, `adu_anchor.yaml`, `adu_partial_share_grid.csv`; `scripts/dev/adu_config_fit.py`; `tests/model/test_scenario_adu.py`; `reports/adu-final-config/`; config note in `docs/analysis_plan.md`; `docs/model_and_assumptions.md`.
- **Findings:** θ 0.000224 per lot, α 1.505, m_x 0.7, core +1.740, on 70 places and 498 place-years (D-096 had θ 0.000240, α 1.439, core +1.670).
- **Decisions:** Ben (2026-11-16): merge #444, turn on the m_x draws, report medians, keep Dallas as no ADUs; config update approved.
- **AI:** Claude (Opus 5.5); slope script's central fit and the grid's 0.7 row equal the config fit; 70 ADU tests pass. The final-config branch is not yet merged. Logged by the nightly review.

### LB-179 · 2026-11-17 · Admin / Validation: missing-middle and ADU work merged to `main` (#441, #442, #443, #445, #446, #447, #449, #451, #453); MN BPS rebuilt; results rerun (auto-review)
- **Question:** With St. Paul scored and D-100 run, what has to land on `main` so the app reflects the missing-middle and final ADU work, and is any holdout still blind?
- **What I did:** (from first-parent merges on `origin/main` 02:32–06:54 ET; fragment `2026-11-17-ws-mm-day.md`; page "Results for 2027–2031")
  - Merged on Ben's word: #446 (final ADU config, LB-178), #442 (V5 St. Paul scored and released), #441 (D-099), #449 (app model tab), #445 (D-100), #447 (fast ramp), #443 (missing-middle docs for C4), #451 (Minneapolis permit typing), #453 (run 13 rerun). #442 and #445 were brought up to date first; both conflicts were two appended decision blocks, both kept.
  - Closed stale stacked PRs #403, #405, #407, #408, #410, #414 (their work reached main through #436); branches kept.
  - Rebuilt MN's processed BPS table offline from clean main after #442 (St. Paul 2024: 33, 2025: 22 two-to-four unit buildings); warned the ADU session that branches cut before #442 will stop on the holdout-leak check.
  - Reran every state's results bundle (`lotline results --all`, 1,000 draws) at a267a3d0 and later 0a6f97b9 (not committed); a results page compares them with the 9 Nov run E.
  - Filed #448 (results-bundle sensitivity table so the app can show the fast ramp; WS-CORE).
- **Outputs:** merges above; issue #448; page [Results for 2027–2031](https://claude.ai/artifact/WF92C89mxGCqRajaa8CXNs).
- **Findings:** no holdout is left blind on main (Oregon V9 released 2026-11-05, Charlotte 2026-11-09, St. Paul 2026-11-16). Five-year net homes at P50: missing middle MN 1,130, NC 2,047, OH 1,747, TX 7,972, OR 167; ADUs MN 206, NC 131, OH 183, TX 2,109, OR 5. Missing middle more than doubled since run E (C4) and Texas ADUs rose by about half (Dallas and Fort Worth take the core-city rate). St. Paul's release moves Minnesota's ADU midpoint by one home.
- **Decisions:** none new in HANDOFF; Ben: merge the PRs, regenerate the app with C4, open #448.
- **AI:** Claude Code (missing-middle session); ruff, `params_table.py --check`, `compliance_check.py` (0 FAIL) on each branch and main; full suite before #442 (2,363 passed) and on D-100 + fast ramp (2,372); CI on every PR; NC bundle reproduces a fresh C4 run exactly. Results page author session not identified from the page. Logged by the nightly review.
- **Open / next:** #448 waits on WS-CORE and Ben.

### LB-180 · 2026-11-17 · Calibration: fast-ramp sensitivity for missing middle (D-100) (auto-review)
- **Question:** D-100 found local adopters reach half pace in about half a year (4 years for Oregon's state-required places); what does the missing-middle scenario give at that pace, as a sensitivity beside C4 (Ben's request)?
- **What I did:** (from commit 3f5bae8a, PR #447; fragment `2026-11-17-ws-mm-fast-ramp.md`) wrote a pre-registration bullet in D-100 before the run; added `mm_ramp_half_years_fast` (0.5, high 1.0) to config and a `ramp="fast"` option to `scenarios/mm.py`; ran half-way 0.5 and 1.0 next to C4; built the page.
- **Outputs:** `config/params/mm_hazard.yaml`, `src/lotline/model/scenarios/mm.py`, `tests/model/test_scenario_mm.py`, `scripts/dev/mm_fast_ramp_run.py`, `mm_fast_ramp_page.py`, `reports/mm-d100/fast-ramp/`; page [Missing-middle fast ramp](https://claude.ai/artifact/CjkLoS18nmRupLFcyskYR6).
- **Findings:** five-year totals 3.30× C4 at half-way 1.0 and 3.61× at 0.5 in every state, as predicted by hand (Texas median 12,066 → 43,589 net homes). Config main values unchanged.
- **Decisions:** Ben asked for the sensitivity; C4 stays the main result.
- **AI:** Claude (missing-middle session); the main variant reproduces C4's published numbers to the home; two hand-worked tests; page checked in the browser. Logged by the nightly review.
- **Open / next:** showing it in the app needs #448.

### LB-181 · 2026-11-17 · Data / Calibration: Minneapolis repair permits no longer typed as new 2–4 unit buildings (#450, #451); run 13 rerun (auto-review)
- **Question:** Why did Minneapolis's permit table hold 991 `U3_4` and 5,048 `DTQ` permits when almost none added homes, and does fixing it change run 13's clustering finding (D-092)?
- **What I did:** (from commits cd24a238 (#451), f1d360cb (#453); fragments `2026-11-17-ws-mn-mpls-occupancy-type.md`, `2026-11-17-ws-mm-run13-mpls-fix.md`)
  - The adapter typed every permit by the building's occupancy; `TFD`/`3to4` now give `DTQ`/`U3_4` only to new construction and wrecking; other work is `OTHER`. Offline rebuild of the 2026-11-11 snapshot; Rochester and Met Council checked (not affected).
  - Ben: "rerun run 13's Minneapolis row" and "publish the run 13 results page"; reran from main after #451.
- **Outputs:** `src/lotline/adapters/states/mn/mpls_permits.py` (v1.1), `tests/states/mn/test_mpls_permits.py` (10 cases), `docs/data_provenance.md`; `reports/mm-d092/run13-projects-mpls-fix/`, `scripts/dev/mm_projects_page.py`, D-092 "Run 13 corrected" bullet, `docs/model_and_assumptions.md`, `mm_year_spread_phi` note; page [Missing-middle project size](https://claude.ai/artifact/BvoadqpTCF3itcSBYUYdgq) (updated).
- **Findings:** `U3_4` 991 → 126, `DTQ` 5,048 → 145; Minneapolis 2017–2025 2–4 unit buildings 175 against BPS 165. Run 13: Minneapolis 1,042 → 179 buildings by lot; pooled inflation 12.8 → 14.3 by lot, 5.3 → 5.6 by day; verdict unchanged. C4 (fit on BPS) unaffected.
- **AI:** Claude Code (WS-MN and missing-middle sessions); full pytest, ruff, `compliance_check.py`; only Minneapolis differs from the original run 13. Logged by the nightly review.
- **Open / next:** `SFD`, `TH` and `MF5` still follow occupancy for repair work (MF5: 6,203 of 6,240 rows add no unit); readers counting MF5 rows should filter `units_new` > 0.

### LB-182 · 2026-11-17 · Validation: missing-middle gut check against 2019–2025 permits (#475) (auto-review)
- **Question:** Do the app's missing-middle numbers pass a gut check against observed 2–4 unit permits in the five states?
- **What I did:** (from commit dc97a9cd, PR #475; fragment `2026-11-17-ws-mm-gut-check.md`) rebuilt every bundle from main ef37f59a (not committed), compared baseline and scenario with the bundles' BPS 2–4 unit history, decomposed the funnel from the draws; asked by Ben through the ADU session; report only.
- **Outputs:** `reports/mm-gut-check/`, `scripts/dev/mm_gut_check_data.py`, `mm_gut_check_page.py`; page [Missing-middle gut check](https://claude.ai/artifact/VPPb52Mxzc4yTd1Ue6yLzb).
- **Findings:** every state passes `historical_floor` (with reform 1.10–2.14× the 2023–2025 pace); no-reform midpoints 78–96% of recent pace; added permits at the median about equal recent five-year 2–4 unit output in MN and NC; uptake (θ) drives level and range. The Method card asked about permits while the headline counts net homes (fixed in #474, LB-184).
- **Decisions:** Ben approved the Method card wording.
- **AI:** Claude Code (missing-middle session); summary reproduces the bundle's scorecard; funnel products match `aggregate.homes_from_draws`. Logged by the nightly review.

### LB-183 · 2026-11-17 · Build: both fee scenarios and ADU detail in the results bundle (#457, #473; schemas 1.14, 1.15) (auto-review)
- **Question:** How do fee results and the ADU evidence card's inputs (ADUs by place type, statewide no-reform ADUs by year) reach the app through the results bundle?
- **What I did:** (from commits 7edddef1 (#457), aed98e4d (#473); fragments `2026-11-17-ws-app-fees.md`, `2026-11-17-ws-adu-bundle-detail.md`)
  - Ben chose both fee scenarios side by side as D-065 labelled them: the Handbook benchmark (`fees`) and real local fees halved (`fees_local_half`); the statewide fee place builder moved out of a dev script into `model/fee_inputs.py`.
  - Asked by the app session (Ben: "Yes, ask it"): `results_adu_place_types` and `results_adu_baseline` in the bundle; older bundles read as empty. No backcast of past statewide ADUs (the engine forecasts from the origin), so the app keeps showing counted permits.
- **Outputs:** `src/lotline/model/results.py`, `fee_inputs.py`, `fees.simulate`, schemas 1.14 and 1.15, app labels, analysis-plan results note 2026-11-17, tests.
- **Findings:** NC real-fees-halved permits 475 (122–1,940) against D-076's 486; Texas ADUs a year (no reform / added, medians): core 577 / 535, suburb 171 / 462, town 3 / 7; no-reform statewide about 790 a year (355–2,080).
- **Decisions:** Ben: both fee scenarios shown; D-077 knobs in a later PR.
- **AI:** Claude Code; hand-worked tests, full suite, compliance 0 FAIL. Logged by the nightly review.

### LB-184 · 2026-11-17 · Deliverables: app Model tab with three model cards, every-state chart, Oregon fee line and Method wording (#449, #462, #474, #477) (auto-review)
- **Question:** How should the app's "The model" tab explain ADUs, missing middle and fees together, and show model effectiveness across states?
- **What I did:** (from commits c79e637c, b16367f4 (#449), 6cedfba3 (#462), 5ce3a0d3 (#474), 0b66cd28 (#477); fragments `2026-11-17-ws-app-model-tab.md`, `…-app-fee-card-oregon.md`, `…-app-method-net-label.md`, `…-app-allstates-chart.md`, `…-app-home-overview.md`)
  - Ben: keep the shared steps; step 3 gets a switcher with one card per model answering the same five questions; the missing-middle session reviewed its card (St. Paul's miss, slow ramp, placebo failing, earlier-value labels).
  - Oregon fee line corrected: 4 coded cities, pooled median elsewhere; 58 coded places (was 50).
  - Method card now says "gain" in net new homes, not permits (from LB-182).
  - Ben: no combined scenarios ("I don't think we need to combine"); the every-state range chart per reform moved into the Model tab. A home-screen redesign on `ws/app-home-overview` (#460) was superseded by #466 (LB-185); only its chart was kept.
- **Outputs:** `src/lotline/app/template.html`, `src/lotline/app/build.py` (`headline`), `src/lotline/model/results.py` (`SINGLE_SCENARIOS`), `tests/app/test_build.py`.
- **Findings:** Oregon's 4 coded cities pay $17,500–$42,800 a home; other places take the pooled median (~$7,100), likely an understatement.
- **Decisions:** Ben (2026-11-17): model-tab structure; no combined scenarios (supersedes WS-APP's "per scenario and combined" and WS-ENGINE's `combine.py`).
- **AI:** Claude Code (ADU session); app tests, ruff, compliance; switcher checked in the browser pane; a "not in the model" claim about mortgage rates corrected from `hazard.yaml` before commit. Logged by the nightly review.
- **Open / next:** whether Oregon's uncoded places should draw from its 4 coded cities (D-065's 5-place minimum).

### LB-185 · 2026-11-17 · Deliverables: app home card, "Add a state" page, Results headline and evidence cards for all three reforms (#466, #476; tag `app-2026-11-17d`) (auto-review)
- **Question:** What should someone see first when they open Lotline, what number should a state's Results page lead with, and how does each reform show its evidence?
- **What I did:** (from ~20 commits on `ws/app-add-state` (#466) and `ws/app-evidence-cards` (#476); fragments `2026-11-17-ws-app-add-state.md` (11 entries), `2026-11-17-ws-app-evidence-cards.md`) built from Ben's notebook sketches, in steps:
  - opening card (`#home`) with the state map and two buttons; an "Add a state" toolbar button and placeholder page;
  - Results headline "[State] can add [X] homes over the next 5 years": first the largest reform midpoint, then (Ben's switch) the three reforms summed run by run, P10–P90 as the likely range; the note rewritten in Ben's words;
  - the reforms on one log-axis range chart; a segmented selector over evidence cards; old headline, no-change and funnel cards removed;
  - ADU card (yearly stack with no-reform whiskers, place types, five steps), missing-middle and fee cards with "How we get these numbers" (the fee card names its elasticity studies); Model page deep dives for ADUs and missing middle (Oregon held out 703 vs 915; St. Paul 55 vs 15);
  - share of housing need for all three together, then each, with linked sources; header tagline made transparent.
- **Outputs:** `src/lotline/app/template.html`, `tests/app/test_build.py`; release tag `app-2026-11-17d`.
- **Findings:** North Carolina's headline is 6,190 homes (2,000–21,300), 3.0% of 205,300 needed; ADUs alone are 0.06%. Oregon 748 (298–2,040). Page numbers recomputed from the bundle's runs match the engine exactly.
- **Decisions:** Ben (2026-11-17): headline = three reforms summed per draw (each estimated alone, so a lot two reforms open is counted twice); share of need shows all three, then each.
- **AI:** Claude Code (UI/UX workflow session); `tests/app` (up to 52 passed), ruff, `compliance_check.py`, CodeQL fixes; checked in the browser pane on all five states' real bundles. Logged by the nightly review.
- **Open / next:** Ben's real add-a-state steps; the Up for Growth and Freddie Mac shortage figures not rechecked against their spreadsheets; fee slider waits on the fee grid in the bundle.

### LB-186 · 2026-11-17 · Deliverables: publishing the app can no longer drop the data dashboard (branch) (auto-review)
- **Question:** Why did the published app lose its embedded data dashboard?
- **What I did:** (from `ws/app-publish-summary`, commit 5b0a2857; fragment `2026-11-17-ws-app-publish-summary.md`) traced releases `app-2026-11-17` and `-17b` to `publish_app.py` running from a worktree with no `reports/data_dashboard/summary.json`; `--go` now refuses without it, a check-only run warns, `--no-data-summary` opts out. Ben republished as `app-2026-11-17c`.
- **Outputs:** `scripts/publish_app.py`, two tests in `tests/app/test_build.py`.
- **AI:** Claude Code; 47 app tests, ruff, compliance; full suite left to CI. Branch not yet merged. Logged by the nightly review.

### LB-187 · 2026-11-17 · Research: office hours with Amy Tomasso (second session), the WS-NEED-AMI brief and an AMI method note (auto-review)
- **Question:** What did Amy's review of the NC results in the app say, and what should change?
- **What I did:** (from fragment `2026-11-17-cowork-office-hours-amy.md`, uncommitted; project doc `research/office-hours-2026-11-17-tomasso-notes.md`) Claude (Cowork) read the Granola notes and transcript, checked each point against the app on `origin/main` (78778f58), wrote feedback and action items, a build brief, and a web-researched method for showing which incomes the homes serve (HUD income limits, tax-credit rent convention).
- **Outputs:** `docs/research/office-hours-2026-11-17-tomasso-notes.md` (mirrored to the project), `docs/build/workstreams/WS-NEED-AMI.md`, `docs/research/lotline-ami-method.md` (all uncommitted).
- **Findings:** the share of need doesn't read as a table; the page doesn't say which reform does the most; with the Handbook fee benchmark as default, fees look as large as missing middle; the benchmark-vs-real-fee gap needs its arithmetic shown; the mentor wants supply tied to affordability.
- **Decisions:** proposed for HANDOFF (Ben, 2026-11-17): real local fees are the headline default; need, gap and AMI share one Results card; the new-state run waits on the ingestion rework.
- **AI:** Claude (Cowork); no code run. Logged by the nightly review.
- **Open / next:** Ben's two open decisions in the brief (what the gap is measured against; HUD limits vs ACS income); commit the files.

### LB-188 · 2026-11-17 · Deliverables: housing need as a bar, real local fees by default, and what builders pay in fees today (branches) (auto-review)
- **Question:** Following the office hours (LB-187, items B1–B2), can one card show how much of the need the reforms cover and which covers most, and how far real fees sit below the $50,000 benchmark by kind of home?
- **What I did:** (from `ws/app-need-ami` (f71cfccf) and `ws/app-fee-sample` (b22a64e2); fragments `2026-11-17-ws-app-need-ami.md`, `2026-11-17-ws-app-fee-sample.md`)
  - Need card (part A): one bar per kind of need, each reform's midpoint filled in, the three-together likely range, the remaining gap, and a generated sentence ranking the reforms; fee view now defaults to real local fees halved, falling back to the benchmark.
  - Fee card: `dashboard/fees.py` lays out the fee scenario's own inputs per coded place (fee per home for house, duplex, fourplex, ADU; component split; fee per lot; share of building cost) into the data dashboard summary; the app shows the typical/lowest/highest house fee against the "Challenge benchmark" (Ben's wording), a dot strip and tables.
- **Outputs:** `src/lotline/app/template.html`, `tests/app/test_need_card.py`, `need_card_harness.js`; `src/lotline/dashboard/fees.py`, `summarize.py`, `src/lotline/model/fee_levels.py` (`component_fees`), `src/lotline/app/build.py`, tests.
- **Findings:** state median house fees MN $9,168, NC $6,683, OH $7,194, OR $34,454, TX $6,516; a typical fourplex pays about 4× a house's fee on one lot, 2.5–2.9% of building cost against 1.5–2.0% (8.7% vs 5.8% in Oregon). The headline's default number is now lower than the live site's.
- **Decisions:** Ben: real local fees halved as the default; "Challenge benchmark" wording.
- **AI:** Claude Code (ADU session / app session); tests check every number against hand computation from draws and fixtures; state medians checked against the generated fee-levels doc; browser pane on all states. Both branches not yet merged. Logged by the nightly review.
- **Open / next:** part B (who the homes serve) waits on Ben's two decisions; regenerate the data dashboard summary before publishing.

### LB-189 · 2026-11-17 · Build / Rules: rule agent swarms for missing middle, ADUs and fees, with dry runs (MM #469 merged; ADU, fees on branches) (auto-review)
- **Question:** Can October–November's ad-hoc local rule research become reusable agent swarms that take one state and return schema-valid `reforms` / `fees` rows, every value cited, with unreadable sources handed to a person as structured lookups?
- **What I did:** (from three sessions started by the parent session: `claude/rule-agent-mm-4aa182` (#469), `claude/rule-agent-adu-8b4a95` (#471), `claude/rule-agent-fees-910965` (#470); fragments `2026-11-17-rule-agent-mm.md`, `…-rule-agent-adu.md`, `…-claude-rule-agent-fees-910965.md`) each mined the logbook and decisions into a lessons register, designed a swarm (scout, blind coders, reconciler/verifier, hand-off), built tested Python helpers and a `/rules-*` command, and dry-ran on coded places: MN (4 places, MM), NC (5, ADU), MN (5, fees).
- **Outputs:** `docs/build/rule-agents/{mm,adu,fees}/` (LESSONS, DESIGN, dry-run notes, SHARED_CANDIDATES), `.claude/agents/rules-*.md`, `.claude/commands/rules-{mm,adu,fees}.md`, `src/lotline/rule_agents/{mm,adu,fees}/`, tests (38 + 61 + 33); `pypdf` dependency. Dry-run outputs stay in `LOTLINE_DATA_DIR`.
- **Findings:** MM: all 4 places match on the engine's reading; ~370k tokens a place. ADU: 34 of 62 field comparisons match, 1 differs, 18 left as lookups; both coders missed two later amendments (scout now sweeps amendments); ~200k tokens a place. Fees: reproduced every readable amount; 12 of 19 coded MN places lack the state permit surcharge (~$177 a house) and Coon Rapids' fourplex permit is ~$580 a unit high; 3 of 5 cities block readers in robots.txt. Only 29 of 928 coded fee rows were ever second-coded.
- **Decisions:** Ben (2026-11-17, proposed for HANDOFF in the PRs): pypdf added; a 2→3 rise in two-family districts counts as MM coverage; Raleigh's 2019 cottage overlay is "no ADUs" (config change to the ADU owner); second coder only where the first pass is weak plus a ~10% audit; MM schema additions approved for WS-CORE; fee evidence columns sent as issue #472; proposed rows stay out of `config/`.
- **AI:** Claude Code (Opus) with Sonnet subagents; hand-worked tests, schema checks, blind second coding, comparison with coded rows, `compliance_check.py`. Logged by the nightly review.
- **Open / next:** register agent types and re-measure cost; work the human tasks (13 MM, 12 ADU, 16 fees); Brooklyn Park R-2 and the Coon Rapids permit.

### LB-190 · 2026-11-17 · Build / Rules: shared core for the rule agents (document store, token budget) and the user path (branch) (auto-review)
- **Question:** What should the three swarms share, how should they store and cite primary documents, and how can a user outside the team run them?
- **What I did:** (from `ws/rule-agents-core` (41e0176c, d0640c42, 35a5d1a1, cad3b4b6, revert fb4de4ea); fragment `2026-11-17-ws-rule-agents-core.md`)
  - Built `rule_agents/common/` from the MM code (Ben: MM is the master copy): content-addressed document store, page-cited passages, spending ledger, shared hand-off, evidence confidence; MM agents pointed at the store with a per-place budget and selective second coding (`mm select-b`).
  - Ben reframed the agents as an **app service** a user switches on to add a state: a guardrails commit routing rows to owner sessions was reverted and replaced by `PRINCIPLES.md`; records-request-only sources become optional priority-3 lookups.
  - User path: `docs/adding_local_rules_with_agents.md`, `python -m lotline.rule_agents doctor ST`, `import PROPOSAL reforms|fees ST` (preview, then `--yes`; never deletes).
  - Registered the three committed Sunfish Lake PDFs in the store and removed them from git.
- **Outputs:** `docs/build/rule-agents/PRINCIPLES.md`, `CORE.md`; `src/lotline/rule_agents/{__main__,common/*}.py`; `tests/rule_agents/common/test_rule_core.py` (22 tests); `docs/research/rule_docs_catalog.csv`; `.gitignore`.
- **Findings:** on the 329-page Sunfish Lake code, ADU passages are ~3k characters against 655k; a first passage scorer missed the 1,200 sq ft cap and was fixed. Preview import of the fees proposal for MN: 48 new surcharge rows, 2 Coon Rapids changes; nothing written.
- **Decisions:** proposed for HANDOFF: one document store under `LOTLINE_DATA_DIR/rule_docs` with a data-free catalogue; second coder only for events, below-high confidence and a 10% audit; per-place budget 120k tokens / 12 fetches / 8 searches.
- **AI:** Claude Code (parent session); 62 rule-agent tests, ruff, compliance; `docs find` / `excerpts` / `docs quote` run on the real store. Not yet merged. Logged by the nightly review.

### LB-191 · 2026-11-17 · Deliverables / Build: adding-a-state guide and WS-SCALE: a new state runs with no code edits, one place-input table, shared resolver, aliases, crosswalks and onboarding steps (#452, #456, #459, #461, #463, #465, #467, #468; later tasks on branches) (auto-review)
- **Question:** Ben: "create a step by step instruction guide for adding a new state", then consolidate the pipeline so "one consolidated dataset feed[s] all 3 models", folded into WS-SCALE.
- **What I did:** (from merges on `main` 19:32–20:48 ET and branches `ws/scale-{audit,state-schema,crosswalks,rules,onboarding,missing-inputs}`; fragments `2026-11-17-docs-new-state-guide.md`, `2026-11-17-ws-scale-*.md` (12))
  - Wrote `docs/adding_a_state.md` (four data levels, 14 steps, per-model input tables) and committed the WS-SCALE brief (written 2026-11-09) with an audit and tasks 0–13. Audit: ADU, MM and fees each build their own place frame; MM skips D-056's tier-3 scaling; parcel stats use the latest roll; jurisdiction tagging done seven ways.
  - Task 0 (Ben: "borrow only"): an unlisted state borrows rule priors and feeds none back; a missing permit table reads as empty.
  - Tasks 2–4, 7, 8: state-file schema tests; one resolver `geo.resolve`; per-state aliases files; jurisdictions built from Census plus each state file's `local_jurisdictions` (no adapter output); `place_inputs` table with place tags and a `DataStore` read cache, registered as a fetch step (schemas 1.16); crosswalks in two formats with one reader; named adapter rules in state files.
  - Tasks 11, 13: onboarding steps as data (`config/onboarding/steps.yaml`, `lotline onboard`).
- **Outputs:** `docs/adding_a_state.md`, `docs/build/workstreams/WS-SCALE.md`, `docs/build/ws-scale-audit.md`, `README.md`; `src/lotline/geo.py`, `build/place_inputs.py`, `build/jurisdictions.py`, `adapters/crosswalks.py`, `onboarding.py`, `io/store.py`, `config/__init__.py`, `cli.py`, `schemas.py`; `config/crosswalks/*`, `config/states/*.yaml`, `config/onboarding/steps.yaml`; tests.
- **Findings:** every refactor checked for zero difference (resolver, aliases 6/6, 18 crosswalk loaders, jurisdictions tables identical, `place_inputs` columns equal the models' own); a synthetic tier-3 state builds a full `national_only` bundle; `lotline onboard --state OR` marks 9 of 14 steps done; 2 Met Council GEOIDs (139 permits) are never counted; two Oregon Metro lists disagree (23 vs 24).
- **Decisions:** Ben (2026-11-17): "borrow only" for new states; jurisdictions straight-line build with today's 220 extra governments written once; place tags in `place_inputs`; fixed lists only in aliases. Proposed HANDOFF rows in the fragments.
- **AI:** Claude Code (WS-SCALE session) with read-only subagents; new tests fail on old code; full pytest, ruff, compliance. The guide's steps were not run on a new state (V8). Logged by the nightly review.

### LB-192 · 2026-11-17 · Build / Analysis: WS-SCALE task 5 rules (D-101, D-102, D-103) and what local data is worth (tasks 9–10) (branches) (auto-review)
- **Question:** Can the place-input rules the audit found inconsistent be set once for every model, and how far do results move when parcels, rules or permits fall back to national data?
- **What I did:** (from commits 086850fb, 24938d09, 94f6eac8, 8661b404 on `ws/scale-fix-county`, `-fix-remainder-pop`, `-fix-place-rules`, `-missing-inputs`; fragments `2026-11-17-ws-scale-fix-*.md`, `…-missing-inputs.md`)
  - D-101: a place in two counties takes the county with most of its 2020 homes (Ben said population; housing units used, deviation stated).
  - D-102: county remainders get their 2020 population (county minus places and townships).
  - D-103: in `place_inputs`, one place set for both scenarios, missing rent/value filled with the state median (flagged), no parcel roll later than origin + 1 (schemas 1.17).
  - Missing-input matrix: NC run four ways offline (as is, no parcels, no coded rules, no permits); borrowed-parameters section after reading the Rules and Handbook.
- **Outputs:** `src/lotline/adapters/national/geoparts.py`, `src/lotline/build/{jurisdictions,panels,place_inputs}.py`, `src/lotline/schemas.py`, `docs/schemas.md`, D-101–D-103 in `docs/analysis_plan.md`; `scripts/dev/missing_input_matrix.py`, `docs/adding_a_state.md` §2, §8.
- **Findings:** D-101 moves 18 places, scenario medians ≤0.06%; D-102 moves Oregon missing middle −40%, NC ADU −8%, OH ADU −4% (remainders now borrow city-band priors); D-103 adds places to ADU (MN 56, OH 22, TX 11, NC 4), results unchanged until the owners switch over. NC without coded rules: ADU median +251%, range ×4.9; without parcels the middle-housing range narrows (×0.79), against the brief's expectation. The Rules and Handbook never ask for causal identification.
- **Decisions:** D-101, D-102, D-103 approved by Ben (2026-11-17). Open for Ben: should remainders borrow from cities' bands; population download; rebuild stored jurisdictions tables.
- **AI:** Claude Code (WS-SCALE session); hand-worked tests, offline before/after bundles for five states, nothing written to the data directory. Not yet merged. Logged by the nightly review.


### LB-193 · 2026-11-18 · Validation: judging panel run on main @ 59c272f (auto-review)
- **Question:** How would the entry score today against the Rules §8 rubric, and what should change before Dec 16?
- **What I did:** (from fragment `logbook.d/2026-11-17-cowork-judging-panel.md`, uncommitted) Claude (Cowork) ran `/judge all --ref main` on a fresh clone of `main` at 59c272f in the cloud workspace (local `main` was 602 commits behind with uncommitted edits): gatekeeper and five criterion judges in parallel, then the head judge, which ran on 2026-11-18 after a usage limit stopped the run overnight. The usability judge was told to evaluate the static page, not Streamlit.
- **Inputs:** `.claude/judging/RUBRIC.md`, `.claude/agents/judge-*.md`; `HANDOFF.md` §2–3; previous run LB-083.
- **Outputs:** `reports/judging/2026-11-17-1939-59c272f/` (`SCORECARD.md`, `RUN.md`, six judge reports; gitignored).
- **Findings:** weighted total 64.9/100 today (44.5 on Oct 19), 79.8 at ceiling. Not scored today: the Policy Scenario Comparison is 38 words, no deck, video or SBOM, `state = ""`, and the Model & Assumptions Overview is ~44 pages against 25. Engineering is the strength (2,454 tests, 90% coverage, 12 of 13 mutants killed); losses are a stale README, an Overview that contradicts the config (ADU anchor 0.66 vs 0.224 per 1,000) and a headline summing separately run reforms. Method points: MM ramp held at 4 years; the Handbook fee cut skips 5+ unit buildings; MM counts 2–4 units against the Handbook's 2–6; three commits dated 2026-10-08 in the gap week.
- **Decisions:** none. Proposed for Ben: choose the benchmark state; record the combined-scenarios decision in HANDOFF (done in code by LB-194); get the organizers' written answer on the gap-week commits.
- **AI:** Claude (Cowork) ran seven subagents and checked the weighted arithmetic and main claims against the clone; the Rules, Handbook, live tool and GitHub settings were not reachable. Logged by the nightly review.
- **Open / next:** update `judge-usability.md` for the static page; re-run after the Scenario Comparison and Overview rewrite.

### LB-194 · 2026-11-18 · Deliverables: each reform run on its own, the ranges in plain words (#491, #486 merged; tags `app-2026-11-18`, `app-2026-11-18b`) (auto-review)
- **Question:** Ben: "we're not doing any combined runs. make sure the engine and code don't contain that concept"; and what does "P10 to P90" mean to a policymaker?
- **What I did:** (from commits 68affda4, 7c3c7d18, 933132c3 on `ws/app-range-words`, merged as #491; fragment `2026-11-18-ws-app-range-words.md`)
  - Removed combined scenarios: schemas 1.17 drops `adu+missing_middle`, `adu+fees`, `missing_middle+fees` and `combined`; the engine lists only single reforms as pending; the app drops their labels and the `scenario-combined` colour and ignores them in older bundles; WS-APP, WS-ENGINE briefs and handoff 09 marked superseded; `docs/model_and_assumptions.md`, two judge prompts and a dated deviation in `docs/analysis_plan.md` updated.
  - Added a "How to read the bars" paragraph under the results bars (middle result, middle 80%, longer bar = less certain, log scale); the all-states caption uses the same words.
  - Also merged on 2026-11-18: #486 (fee sample card, LB-188; tag `app-2026-11-18`). On `ws/app-need-ami` (still a branch), the need-card test harness finds script blocks by string scanning (CodeQL `js/bad-tag-filter`), a1b37da5.
- **Outputs:** `src/lotline/schemas.py`, `docs/schemas.md`, `src/lotline/model/results.py`, `src/lotline/app/{build.py,template.html}`, `docs/build/identity/tokens.*`, `STYLE_GUIDE.md`; tests `test_no_combined_scenarios`, `test_results_ranges_are_explained_in_plain_words`.
- **Decisions:** Ben (2026-11-18): no combined scenarios anywhere; each reform is run alone. Not yet seen in `HANDOFF.md` on this computer.
- **AI:** Claude Code; full suite and compliance check; wording checked in the browser pane on North Carolina. Logged by the nightly review.

### LB-195 · 2026-11-18 · Build / Rules: rule agents merged on the shared core, Wayback captures dated, and a first run on an unseen state (Burlington VT) (#470, #471, #480, #492, #493 merged; fixes on a branch) (auto-review)
- **Question:** Can the three swarms share one fetch, store and evidence layer, date archived ordinances by the copy actually read, and work on a state the app has never seen?
- **What I did:** (from merges on `main` 2026-11-18 and `ws/rule-agents-poc-fixes` (4f52b04c); fragment addenda to `2026-11-17-rule-agent-adu.md` and `…-fees-910965.md`; fragments `2026-11-18-ws-rule-fetch-final-url.md`, `2026-11-19-ws-rule-agents-poc-fixes.md`)
  - Merged the shared core (#480, LB-190), then moved the ADU (#471) and fees (#470) swarms onto it: store-first `common.fetch.get`, shared evidence, hand-off and budget ledger, `doctor` as step 0 and `import` at the end; their own fetch/PDF/robots copies deleted.
  - #492: the shared fetch records the URL that answered and the Wayback capture served (`final_url`, `wayback_ts`, also in `DocRecord`), a feature lost in the move; #493: the ADU scout dates Wayback copies by that capture.
  - Proof of concept: MM agents on Burlington, VT in a throwaway data folder proposed no rows (scout used 88.5k tokens against 60k, every city link 404, two crashes). Fixes: per-run limits saved in `RUN/limits.json`, default 250k tokens a place; `ledger summary` fixed; one places reader so all three accept a places CSV for a state with no jurisdictions table; 404s suggest the Wayback copy and dead links expire after a day; one hand-off task per page; `compare`, `reconcile`, `select-b` fixes; prompts fit the budget.
- **Outputs:** `src/lotline/rule_agents/common/{fetch,docstore,budget,places,handoff}.py`, `__main__.py`, `rule_agents/{adu,fees,mm}/`, `docs/build/rule-agents/CORE.md`, `adu/`, `fees/` docs, `docs/adding_local_rules_with_agents.md`; tests.
- **Findings:** the 120k token budget was too low because the Agent tool's count includes everything an agent reads; a year-only Wayback link served a 2022 copy for a 2023 request in the test.
- **AI:** Claude Code (Opus 5.5, ADU, fees and core sessions); rule-agent and full test suites, ruff, compliance 0 FAIL; both PoC crashes reproduced before fixing. The PoC fixes are not yet merged and the Burlington rerun has not happened. Logged by the nightly review.

### LB-196 · 2026-11-19 · Build: missing middle and ADUs read their place inputs from `place_inputs` with no change in results (branches) (auto-review)
- **Question:** Can both models take their per-place inputs from the shared WS-SCALE `place_inputs` table (LB-191) instead of building them themselves, without changing any input or result?
- **What I did:** (from `ws/mm-place-inputs` (387953c9, 2026-11-17 21:12 ET) and `ws/adu-place-inputs` (2cea62b8); fragments `2026-11-17-ws-mm-place-inputs.md`, `2026-11-19-ws-adu-place-inputs.md`)
  - MM: `mm.places_from_store` reads eligible lots net of the D-020 overlap, house share, size band and ACS rent at `year == origin`, building the year when it is missing; doses, price-to-cost and feasible share stay in the scenario. A first version dropped Scott County's MN remainder (0 lots after overlap); the comparison caught it.
  - ADU: `adu.places_from_store` reads eligible lots, ACS rent and value, the observed floor (central k), the D-088 place type and data tier; coded rules, county mix and the undercount split stay in the model.
- **Outputs:** `src/lotline/model/scenarios/{mm,adu}.py`; `tests/model/test_mm_place_inputs.py`, `test_adu_place_inputs.py`, `test_adu_permit_remainder.py`.
- **Findings:** old and new frames identical in every shared column for all five states (MM at origins 2021, 2023, 2025; ADU at 2025); ADU results bundles identical apart from `run_at`.
- **AI:** Claude Code (missing-middle and ADU sessions); column-by-column comparisons on real cached tables, full suite, ruff, compliance. Neither branch merged. Logged by the nightly review.
- **Open / next:** adopt D-103 once #489 merges; D-056 tier-3 scaling for MM; which pool county remainders borrow from (#488).

### LB-197 · 2026-11-19 · Validation: V8 Wisconsin blind registered and D-104 written before any Wisconsin fetch (branch) (auto-review)
- **Question:** Can a state the model was never developed on be onboarded from a state file and national data alone, with a prediction frozen before any outcome is seen?
- **What I did:** (from `ws/v8-wi` (ea268ef7); fragment `2026-11-19-ws-scale-v8-wi.md`) committed `config/states/wi.yaml` with the statewide holdout `V8-WI-TRANSFER` (state 55, outcomes from 2020) and D-104 before the first Wisconsin fetch: origin 2019 forecasting 2021–2025, the standard results bundle, frozen to `results/frozen/V8-WI-TRANSFER.json` on main before any outcome is opened; data level 0 (no reforms file, rule priors borrowed; ACS lots scaled by D-056; no permit floor); the D-044 unseen-state multiplier.
- **Outputs:** `config/states/wi.yaml`, `docs/analysis_plan.md` D-104.
- **Decisions:** Ben (2026-11-18, in the multi-state setup guide session): keep the blind; download Wisconsin's national data.
- **AI:** Claude Code wrote the file and D-104. Not yet merged. Logged by the nightly review.
- **Open / next:** fetch, run, freeze, then score.

### LB-198 · 2026-11-19 · Deliverables: who the new homes serve, Ben's choices and a hand-off for the AMI strip (WS-NEED-AMI part B; uncommitted) (auto-review)
- **Question:** Following LB-187, what should the income strip under the need chart show, and how should a build session take it on?
- **What I did:** (from `docs/research/lotline-ami-method.md`, the addendum to `logbook.d/2026-11-17-cowork-office-hours-amy.md` and `docs/build/handoffs/16-need-ami-part-b.md`, all uncommitted and updated 2026-11-19) recorded Ben's decisions and wrote a hand-off: per home type (ADU, a duplex-to-fourplex unit, a new house for contrast), the assumed rent or price and the break-even rent or price against area median income; a list of existing inputs; build order in small PRs; a `contract-change` issue for the new bundle table and HUD adapter; confirm the FY 2026 HUD Section 8 income limits file by hand.
- **Outputs:** the three files above. A Claude Code worktree `.claude/worktrees/need-ami-b` was created on 2026-11-19 from `main` at 294f786a; no commits yet at scan time.
- **Decisions:** Ben (2026-11-19): show both market and break-even rent; include the single-family contrast row (monthly owning cost at 30% of income, 3-bedroom household); HUD file and 1.5 persons per bedroom stand as recommended.
- **AI:** Claude (Cowork) wrote the hand-off and decisions; the HUD file could not be reached, so its layout is unconfirmed. Logged by the nightly review.
- **Open / next:** the part B build; the hand-off is numbered 16, which LB-163's branch hand-off also used, so it may need renumbering at commit; part A (`ws/app-need-ami`) still not on `main`.

### LB-199 · 2026-11-19 · Deliverables: the AMI strip built and merged, the need card as a shortfall, and Ben's line-by-line review of the Results, Data and Model tabs (#481, #497 merged; tag `app-2026-11-19`) (auto-review)
- **Question:** Following LB-198, can the page show who the new homes serve, and does each tab read clearly to a policymaker?
- **What I did:** (from merges #481 (part A, LB-188) and #497 on `main` 2026-11-19 and fragments `2026-11-17-ws-app-need-ami.md`, `2026-11-19-ws-need-ami-b.md`)
  - AMI strip (part B): HUD FY 2026 income limits adapter (`adapters/national/hud_il.py`, file registered by hand because huduser.gov serves a bot challenge to scripts), `config/params/affordability.yaml`, `model/affordability.py` (rent to income, AMI share, break-even rent or price for three fee cases, owning cost) and bundle table `results_affordability` (schemas 1.18, #496); the strip sits under the need chart with assumed and break-even markers that follow the fee switch.
  - Need card reworked to the shortfall view (`model/shortfall.py`, `results_shortfall`, `stock_loss_rate`): need = shortage + household growth + homes lost, less the no-change forecast; a dated deviation in `docs/analysis_plan.md`.
  - About 40 small commits from Ben's review (each marked "Ben, 2026-11-19"): Results page details folded behind "Graph details" links, "How accurate is our model" at the end of each model card, empty pencil-out card removed, fee strip as a beeswarm, assumptions panel folded, no slider for factors the engine holds fixed; Data tab headings, stat tiles, a per-state source list with search; Model tab rewritten (why-led opening, causal factors 3a–3c with a 56-factor bar, building the models with a runs explainer, applying the model nationwide); a CodeQL `js/xss-through-dom` fix.
- **Outputs:** `src/lotline/adapters/national/hud_il.py`, `src/lotline/model/{affordability,shortfall}.py`, `config/params/affordability.yaml`, `src/lotline/schemas.py`, `src/lotline/app/template.html`, `docs/model_and_assumptions.md` (five D4 limits), tests `test_hud_il.py`, `test_affordability.py`, `test_ami_strip.py`; results rerun for all five states and provenance regenerated.
- **Findings:** ADUs and plex units rent near the median, so break-even is what separates them; shortfall gaps about 98k MN, 88k OR, 234k TX, none at the midpoint in NC and OH.
- **Decisions:** Ben (2026-11-19): HUD file by hand; break-even excludes land and profit; hollow marker at today's fees; merge part A. Not yet seen in `HANDOFF.md`; the shortfall view still needs a D-entry.
- **AI:** Claude Code; hand-worked tests for each equation, full suite, ruff, compliance 0 FAIL. Down payment, tax, insurance and stock-loss values are marked "approx." and need checking against sources. Logged by the nightly review.

### LB-200 · 2026-11-19 · Build / Rules: rule agents fixed on two Vermont towns, a token share per role, and the ADU lookup list keeps its fields (#494, #498, #499 merged) (auto-review)
- **Question:** After the Burlington proof of concept (LB-195), what still breaks on real towns before the agents go into the setup guide?
- **What I did:** (from merges on `main` and fragments `2026-11-19-ws-rule-agents-poc-fixes-2.md`, `2026-11-19-ws-rule-adu-handoff-tool.md`) merged the first fixes (#494); ran MM, ADU and fee swarms on Burlington and South Burlington, VT in a throwaway data folder, then fixed: documents typed by their first bytes (CivicPlus PDFs with no `.pdf`), login pages and bot challenges recorded as blockers and never stored, exact Wayback tips, fees empty-run and one-task-per-page fixes, ADU ledger lines and `coded_at`, one token recorder, and `ROLE_SHARES` so the second coder and reviewer keep their budget (#498; asked for by Ben). #499: `adu tasks` no longer drops fields for a blocker about an uncoded period; the hand-off agent runs on haiku and only polishes wording.
- **Outputs:** `src/lotline/rule_agents/common/{docstore,fetch,handoff,budget}.py`, `rule_agents/{adu,fees,mm}/`, `.claude/agents/rules-adu-*.md`; regression tests.
- **Findings:** South Burlington's ADU run proposed one schema-valid row with page-cited quotes; the tool alone now rebuilds the three tasks the hand-off agent had spent 48k tokens on.
- **AI:** Claude Code (Opus 5.5); both failures reproduced before fixing; rule-agent tests, ruff, compliance 0 FAIL. Logged by the nightly review.

### LB-201 · 2026-11-19 · Validation: V8 Wisconsin frozen, scored (fails the pass rule, ×1.49), released, and its low start diagnosed (D-104 – D-106; #500, #501, #502 merged; diagnosis on a branch) (auto-review)
- **Question:** Does a prediction from national data alone, frozen before any outcome is seen, cover Wisconsin's 2021–2025 permits?
- **What I did:** (from merges #500–#502, branch `ws/v8-wi-diagnosis` (cd6f46e0) and fragments `2026-11-19-ws-scale-v8-wi*.md`) fetched Wisconsin's national data (leak check passes, V0 passes 2010–2019); ran `lotline results --state WI --origin 2019` with no code change and froze it; scored it with `scripts/dev/v8_score.py` from a fresh clone (D-105); released Wisconsin from the blind and kept a hashed copy at `~/lotline-data-v8-blind`; then traced why the baseline starts ~12% below 2019 (D-106, diagnosis only).
- **Outputs:** `results/frozen/V8-WI-TRANSFER.json`, `reports/wi/V8-score.{json,md}`, `reports/wi/V8-baseline-diagnosis.md`, `scripts/dev/v8_{score,baseline_diagnosis}.py`, `config/states/wi.yaml` (`released_on`), `docs/analysis_plan.md` D-105, D-106 (branch); artifact [Wisconsin V8 test](https://claude.ai/artifact/2a32ySrSWiozdgGZkLD4D2).
- **Findings:** observed 112,166 homes vs P50 75,347 (P10–P90 53,126–103,715): single-family inside (×1.14), 2 units ×1.98, 5+ units ×2.43, overlap low. The baseline's shrinkage step removes ~11% of state totals in every state; the low start explains under a third of the miss, most of the rest is apartment growth after 2019.
- **Decisions:** Ben (2026-11-19): unblind and score; release Wisconsin, anything after is post-test; diagnose only. Open for Ben: benchmark the shrunk levels (a WIP switch is on `ws/baseline-benchmark`, also labelled D-107, which clashes with the ADU D-107 in LB-203).
- **AI:** Claude Code; rebuilt baseline checked equal to the frozen file, observed counts cross-checked with 2010–2019, step totals reconciled to the frozen 2021 mean. Logged by the nightly review.

### LB-202 · 2026-11-19 – 2026-11-20 · Build: WS-SCALE merged to `main`: code audit, state-file tests, D-101/D-103 place rules, crosswalks, adapter rules, onboarding steps and the missing-input matrix (#478, #479, #484, #485, #489, #495) (auto-review)
- **Question:** Can the scaling work logged on branches in LB-191 and LB-192 reach `main`?
- **What I did:** (from first-parent merges on `origin/main`) merged #479 (task 1 audit), #478 (state-file schema tests), #489 (D-103 place set, price fill, roll rule; D-101 one county per place carried in), #484 (onboarding steps as data, with the crosswalk and adapter-rule branches carried in), #485 (tasks 9–10 missing-input matrix) and #495 (ADU reads `place_inputs`, LB-196). Still on branches: `ws/scale-fix-remainder-pop` (D-102, plus option (b): county remainders borrow from coded remainders behind a config switch, 3f3755b9) and `ws/mm-place-inputs`.
- **Outputs:** as listed in LB-191, LB-192 and LB-196; `docs/analysis_plan.md` D-101, D-103 on `main`.
- **Findings:** no new results; content as already logged.
- **Decisions:** none new. Open for Ben: D-102 option (b).
- **AI:** Claude Code sessions. Logged by the nightly review; the local `main` checkout is behind `origin/main` (e35fb193 vs 1ab471c3).

### LB-203 · 2026-11-19 – 2026-11-20 · ADU model: why NC's no-reform forecast sits above its permit history (#505 merged), and D-107, the drift recentred to average 1 (branches) (auto-review)
- **Question:** Why is NC's no-reform ADU midpoint (~650 a year) more than twice the ~290 a year counted in 2023–2025, and what should change?
- **What I did:** (from fragment `2026-11-19-cowork-nc-adu-baseline-gap.md` (#505), branches `ws/adu-nc-baseline-split` (6d38a1fe) and `ws/adu-drift-mean` (64d0569e)) Claude (Cowork) traced the chart to its inputs and read the bundle and permit store; the ADU owner session measured the split with an engine run. Then: own rates only where the source recorded the place in every window year; D-107 switch `adu_drift_mean_one` so a place's drift averages 1 (`exp(σz − σ²/2)`, every own-count draw ×0.591, σ unchanged); the no-reform result split into counted vs estimated places (schemas 1.20) in the bundle and app.
- **Outputs:** `config/params/adu.yaml`, `src/lotline/model/{scenarios/adu.py,results.py}`, `src/lotline/schemas.py`, `src/lotline/app/template.html`, `tests/model/test_adu_own_rate.py`, `test_nc_gutcheck.py`.
- **Findings:** the per-place drift is the main cause: the 23 counted places reach P50 453 while their own medians sum to 306; with σ = 0 they give 303 and the state 441. The history bars cover places with about 46% of NC's people. Cowork's first read (coverage first) was wrong and is corrected in the fragment.
- **Decisions:** Ben (2026-11-20), quoted in the config: recentring the drift "isn't a bad idea"; D-107 is proposed, a judgment and not a refit. Not merged.
- **AI:** Claude (Cowork) read only, no engine run; the ADU session ran the engine and wrote the switch and tests. Logged by the nightly review.
- **Open / next:** whether D-107 is adopted; number clash with the baseline-benchmark WIP (LB-201).

### LB-204 · 2026-11-20 · Deliverables: the data tab shows only states with results (branch) (auto-review)
- **Question:** Why did the published data dashboard list Wisconsin, which has no results on the page?
- **What I did:** (from `ws/dash-built-states` (58025f84); fragment `2026-11-20-ws-dash-built-states.md`) the app build cuts the data dashboard summary to states with a results bundle (`build.built_states_only`); the fragment says the page was republished as `app-2026-11-20` (tag not seen in this checkout).
- **Outputs:** `src/lotline/app/build.py`, `tests/app/test_build.py`.
- **Decisions:** Ben (2026-11-20): the dashboard shows only fully built states.
- **AI:** Claude Code; app tests pass, preview lists five states. Not yet merged. Logged by the nightly review.

### LB-205 · 2026-11-20 · ADU model: the coverage rule merged (#508), and the drift recentred to average 1 redone on top of it (branch `ws/adu-drift-mean-one`) (auto-review)
- **Question:** Following LB-203, once the own-rate coverage rule is on `main`, does a mean-1 drift bring each state's no-reform ADU forecast back to its permit pace, and what does it do outside NC?
- **What I did:** (from merge #508 on `main` (fa1242ad), commit 0b43c929 on `ws/adu-drift-mean-one` (pushed, not merged) and fragments `2026-11-20-ws-adu-nc-baseline-split.md`, `2026-11-20-ws-adu-drift-mean-one.md`)
  - #508 merged the coverage rule (own rates only where the permit source recorded the place every window year) with its dated deviation in `docs/analysis_plan.md`.
  - A new session rebuilt the drift switch `adu_drift_mean_one` (default 1; drift exp(σz − σ²/2), each draw ×0.5914, σ unchanged; 0 restores D-091) on top of the coverage rule, after the earlier `ws/adu-drift-mean` session (LB-203) handed it back; ran both settings for every state one at a time and wrote a dated deviation (proposed D-entry, amends D-091) with a before/after table.
- **Outputs:** `config/params/adu.yaml`, `src/lotline/model/scenarios/adu.py` (`own_rate_draws(mean_one=...)`), `tests/model/test_adu_own_rate.py`, `docs/analysis_plan.md`, `docs/model_and_assumptions.md`.
- **Findings:** no-reform statewide P50 (ADUs a year, 2027–31), median-1 → mean-1: NC 646 → 453, OR 697 → 513, TX 768 → 620, MN 140 → 95, OH 55 → 42, WI unchanged. NC's counted places now 261 vs a pace of 298. Where one city dominates the state midpoint falls toward ×0.59 of pace (OR 264 vs 347, TX 147 vs 205), still inside P10–P90. Reform adds fall TX −10%, MN −9%, others under 1%. D-091's fit with a free log-mean found +0.5, so mean 1 is the cautious end. The #508 fragment notes 3.7–7.2 GB peak memory per state; two parallel `place_inputs` rebuilds likely caused the 2026-11-19/20 freezes on the 16 GB machine.
- **Decisions:** Ben (2026-11-20), quoted in the config: "recentering the drift towards the average isn't a bad idea"; "Take the drift fix back here and proceed". D-entry still proposed.
- **AI:** Claude Code; hand-worked test (drift mean 1), engine runs both settings per state. Logged by the nightly review.
- **Open / next:** merge or drop `ws/adu-drift-mean-one` vs the older `ws/adu-drift-mean` branch; refit σ under mean 1; the D-107 number is still shared with the baseline benchmark (LB-206).

### LB-206 · 2026-11-20 · Build / Validation: V8 diagnosis and crosswalks merged (#503, #482); D-102 branch rebased with a before/after script; baseline benchmark switch committed (branches) (auto-review)
- **Question:** Following LB-201 and LB-202, which open branches reached `main`, and what was added to the ones still waiting?
- **What I did:** (from first-parent merges on `origin/main` and branch commits)
  - #503 merged the V8 Wisconsin diagnosis (D-106; `reports/wi/V8-baseline-diagnosis.md`, `scripts/dev/v8_baseline_diagnosis.py`), on the branch in LB-201.
  - #482 merged WS-SCALE task 7, crosswalks in two formats with one reader (already carried into `main` via #484, LB-202).
  - `ws/scale-fix-remainder-pop` rebased (D-102 and option (b), LB-202) and given `scripts/dev/d102_bundles.py`: before/after bundles from three jurisdictions variants (D-101, D-102 as built, option (b) emulated as remainders in band 0) fed offline to the unchanged models. Its docstring notes Oregon ADU (26 coded remainders) needs the ADU owner's `model.borrowing.bands` code for true (b). Local only; the remote branch is behind.
  - `ws/baseline-benchmark` committed (7edb16e1): `benchmark_shrinkage` switch, off by default, keeps each shrinkage group's total after Fay-Herriot (ratio benchmarking, Rao and Molina 2015); hand-worked tests; no result change while off. Labelled D-107.
- **Outputs:** `scripts/dev/d102_bundles.py`; `config/params/baseline.yaml`, `src/lotline/model/baseline.py`, `tests/model/test_baseline_benchmark.py`, `docs/model_and_assumptions.md` (branches); merged files as above.
- **Findings:** no before/after numbers from the D-102 script or the benchmark switch were found in the repo.
- **Decisions:** none new seen. Open for Ben: D-102 option (b); whether to turn on the benchmark.
- **AI:** Claude Code sessions. Logged by the nightly review; local `main` is still behind `origin/main` (e35fb193 vs e112373a).
- **Open / next:** renumber one of the two D-107s; run the D-102 script and the benchmark before/after.

### LB-207 · 2026-11-20 – 2026-11-22 · ADU model: mean-1 drift merged to `main` (#509) and the app retagged `app-2026-11-22` (auto-review)
- **Question:** Following LB-205, did the mean-1 drift switch reach `main` and the published app?
- **What I did:** (from first-parent merge #509 on `origin/main` (6967048f, 2026-11-20 15:24 -0500, fetched after the last scan) and tag `app-2026-11-22` on that merge) merged `ws/adu-drift-mean-one`: `adu_drift_mean_one` in `config/params/adu.yaml`, `own_rate_draws(mean_one=...)`, tests, and a dated deviation "ADU: per-place drift has mean 1, not median 1 (amends D-091)" in `docs/analysis_plan.md`. The tag name suggests the app was republished from this commit on 2026-11-22; no other note on the republish was found.
- **Outputs:** as listed in LB-205, now on `main`; `logbook.d/2026-11-20-ws-adu-drift-mean-one.md`; tag `app-2026-11-22`.
- **Findings:** no new numbers; LB-205's before/after table now describes `main`.
- **Decisions:** the mean-1 drift is merged (Ben's go-ahead quoted in LB-205). The older `ws/adu-drift-mean` branch (LB-203) is still unmerged.
- **AI:** Claude Code sessions. Logged by the nightly review; the local `main` checkout is 109 commits behind `origin/main`.
- **Open / next:** drop `ws/adu-drift-mean`; refit σ under mean 1; the shared D-107 label with the baseline benchmark (LB-206).

### LB-208 · 2026-11-22 · Deliverables: "Test a fee bill" on the app's Fee reduction tab (D-077 slider and targeted bills; branch `ws/app-fee-testing`) (auto-review)
- **Question:** The Fee reduction tab showed two fixed cases. Can a user set the size of the fee change and aim it at one kind of home (D-077), with the same model runs and ranges?
- **What I did:** (from commits d209a227, 8625a56f, 23544f56 on `ws/app-fee-testing` (pushed, not merged), fragment `logbook.d/2026-11-22-ws-app-fee-testing.md` and the app note in `docs/analysis_plan.md`)
  - Measured that homes added are exactly linear in the fee change in every draw (NC, 100 draws, sd of the ratio 0), so the bundle carries only the half cut by size; a build-time check (`check_fee_line`) enforces it.
  - Added `results_fee_types` (schemas 1.20) and `fee_policy_draws` / `feePolicyDraws` with JS–Python parity tests; the default reproduces the engine draws exactly.
  - Added the "Test a fee bill" box: a slider from Abolish to +50% of each city's own fees (default: half cut) and buttons for every home, houses only, duplexes only, duplexes to fourplexes; headline, fee card and need card follow; the $50,000 → $25,000 Challenge benchmark stays fixed; fee revenue not shown.
- **Outputs:** `src/lotline/schemas.py`, `src/lotline/model/{results,aggregate}.py`, `src/lotline/app/{aggregate.js,template.html}`, `tests/model/test_results.py`, `tests/app/test_aggregate_parity.py`, `docs/analysis_plan.md` (app note 2026-11-22).
- **Findings:** the fee effect is linear in the size of the cut, so any bill size is a rescale of the half cut; a state whose bundle predates the table hides the box.
- **Decisions:** Ben (2026-11-22): "Yes, build it", as the fee testing area.
- **AI:** Claude Code; hand-worked and parity tests, NC bundle built, page driven in a browser (abolish doubles the half cut, +50% loses it, duplexes-only, Reset). Logged by the nightly review; work done in worktree `.claude/worktrees/adu-types-checked`.
- **Open / next:** merge to `main` and republish the app.

### LB-209 · 2026-11-23 · Deliverables: the fee box renamed "Try a different fee change" and moved; ADU chart splits the no-change bars by counted vs estimated (#511, which also carried `ws/app-fee-testing` to `main`) (auto-review)
- **Question:** Following LB-203 and LB-208, can the ADU chart show judges which part of the no-change forecast comes from places' own permit counts and which is a model estimate, and does the fee box read clearly?
- **What I did:** (from commits 4c3c719b, d4848e0a, 8789c226, 8add6bed on `ws/app-fee-testing`, 3d66a69d on `ws/adu-chart-split`, merge #511 on `origin/main` (ee232677); fragment `logbook.d/2026-11-23-ws-adu-chart-split.md` and the app note of 2026-11-23 in `docs/analysis_plan.md`)
  - Fee box renamed from "Test a fee bill" to "Try a different fee change" (Ben: "bill" reads as legislation or an invoice) and placed below "What the fee change would add"; tests for the fee card drawn whole or split around the box.
  - `results_adu_baseline` gains basis and mean (schemas 1.21) via `adu_baseline_years`; the ADU chart's no-change bars split by own counts vs model estimate, with a no-change range whisker and relabelled history.
  - Fixed the #510 schema-version test that failed in CI because `tests/core` had not been run locally.
- **Outputs:** `src/lotline/schemas.py`, `src/lotline/model/results.py`, `src/lotline/app/template.html`, `tests/model/test_results.py`, `tests/app/test_build.py`, `docs/analysis_plan.md`.
- **Findings:** in NC the own-count group's mean (298 a year) equals its 2023–25 permit pace, the plain-language answer to "why is the forecast above history".
- **Decisions:** Ben (2026-11-19, 2026-11-23): try the chart split where the data allow; rename and move the fee box.
- **AI:** Claude Code; hand-worked test (means add up, old shape kept without own counts), 769 app, core and results tests, NC bundle checked in a browser. Logged by the nightly review.
- **Open / next:** republish the app (no tag after `app-2026-11-22` seen).

### LB-210 · 2026-11-23 · Baseline: keep each shrinkage group's total (`benchmark_levels`), tested and turned on (#512) (auto-review)
- **Question:** D-106 found the Fay-Herriot step lowers state totals (Wisconsin −11%). Does benchmarking the shrunk levels fix the low start without hurting place-level accuracy?
- **What I did:** (from commits d8390858, 2687685e, b9e73595, 0bca578d on `ws/baseline-benchmark`, merge #512 (79ea27e8); fragment `logbook.d/2026-11-23-ws-baseline-benchmark.md`; dated deviation of 2026-11-23 in `docs/analysis_plan.md`) added `baseline.benchmark_levels` (ratio benchmark: within each shrinkage group the shrunk levels are scaled so the group's homes equal those at its places' own rates; weights, cycle, momentum and draws unchanged); ran the V1 back-test off and on for MN, NC, OH, OR, TX; rebuilt Wisconsin's V8 baseline from the blind tables after the fact; measured today's effect per state; then turned the switch on and regenerated the parameter table and results fixture. This replaces the earlier `benchmark_shrinkage` attempt on the same branch (LB-206).
- **Outputs:** `config/params/baseline.yaml` (`benchmark_levels` on), `src/lotline/model/baseline.py`, `tests/model/test_baseline_model.py`, `docs/analysis_plan.md`, `docs/model_and_assumptions.md`.
- **Findings:** V1 state totals, observed ÷ P50 off → on: 1 unit 1.11 → 1.07, 2 units 1.76 → 1.42, 3–4 units 1.85 → 1.58, 5+ 1.47 → 1.32; inside P10–P90 rises (2 units 40% → 87%). Place-level V1 about neutral (passes 20 → 21 of 60). Wisconsin 2021–25 after the fact: 83,220 (58,989–115,565) vs 112,166 observed, ×1.35, inside the range (frozen: ×1.49, outside); V8 stays a fail. Today's 2027–31 baseline P50: MN +9.0%, NC +7.5%, OH +5.1%, OR +8.0%, TX +6.0%; fee results rise by about the same share; ADU and missing-middle additions unaffected. A first measurement script patched only one module and showed zero change; caught and rerun.
- **Decisions:** Ben (2026-11-23): "start the Wisconsin baseline fix", then "Yes, turn it on". D-entry still proposed (labelled as D-106's proposal).
- **AI:** Claude Code; hand-worked tests (ratio, totals kept, weights unchanged); off setting reproduces the frozen 75,347 exactly. Logged by the nightly review.
- **Open / next:** settle the D-number (the shared D-107 label, LB-206); republish results.

### LB-211 · 2026-11-23 – 2026-11-24 · Validation: V6b, the fee pro forma threshold test, passes (#513) (auto-review)
- **Question:** Validation plan V6b (issue #49): how many lots cross feasibility with the $25,000 benchmark cut and with real local fees halved, and is the five-year response inside the published 0–12% (houses) and 0–18% (2–4 units)?
- **What I did:** (from commit c62a117b on `ws/v6b-fee-threshold`, merge #513 (2683961c); fragment `logbook.d/2026-11-23-ws-v6b-fee-threshold.md`; results note of 2026-11-23 in `docs/analysis_plan.md`) wrote a script on the engine's own functions (`fees.feasibility_change`, `fees.simulate`), no new model arithmetic, and ran the five development states one at a time (under 1 GB each).
- **Outputs:** `scripts/dev/v6b_fee_threshold.py`, `reports/v6b/V6b-fee-threshold.md`, `reports/v6b/<ST>.json`, `docs/analysis_plan.md`.
- **Findings:** pass: 20 of 20 state-cut-size midpoints inside the range (94–100% of draws). Benchmark cut: houses +1.0% to +1.4%, 2–4 units +1.4% to +3.0%; real fees halved: +0.1% to +0.4%. Lots crossing: MN +336 (benchmark) vs +183 (real), OR +369 vs +74; NC, OH, TX have no parcel inputs for this route. Real fees for a new house have medians of $3,900–$9,100 against the Handbook's $50,000, so halving them moves building about 4–10 times less than the benchmark cut. The rule is weak on its own since the range starts at 0.
- **Decisions:** Ben (2026-11-23): "lets do the Fee threshold check (V6b, #49)". V6a stays open.
- **AI:** Claude Code. Logged by the nightly review.

### LB-212 · 2026-11-24 · Deliverables: fee slider exact in MN and OR (stored slider stops, #514), each size's baseline counted once (branch); missing-middle place inputs merged (#490) (auto-review)
- **Question:** The fee-slider build check from LB-208 stopped the MN and OR bundles, because houses there take the lot-feasibility route and are not linear in the fee change. Can the slider still be exact?
- **What I did:** (from commit 891930f2 and merge #514 (46ff171d); commit 2489fccc on `ws/fee-box-baseline` (pushed, not merged); merge #490 (2833e22b); fragment `logbook.d/2026-11-24-ws-fee-grid-nonlinear.md`)
  - `results.fee_types_with_stops` and `FEE_STOPS`: a size that is not linear stores the engine's value at every slider stop; `results_fee_types` schema 1.22; `feePolicyDraws` / `fee_policy_draws` use a stored stop where one exists and scale the half cut otherwise.
  - `ws/fee-box-baseline`: the fee box counted each size's baseline more than once when stops were stored (MN, OR); fixed in `template.html` with a test.
  - #490 merged `ws/mm-place-inputs` (missing middle reads `place_inputs`; branch logged in an earlier entry).
- **Outputs:** `src/lotline/model/results.py`, `src/lotline/schemas.py`, `src/lotline/app/{aggregate.js,template.html}`, `tests/model/test_results.py`, `tests/app/{test_aggregate_parity.py,test_build.py}`; `src/lotline/model/scenarios/mm.py`, `tests/model/test_mm_place_inputs.py` (#490).
- **Findings:** MN houses abolished: 583 vs 2 × 293 at the half cut; a 50% rise: −320. MN bundle grows to 5.5 MB. The check worked as intended, stopping a wrong slider before publication.
- **Decisions:** none new seen.
- **AI:** Claude Code; tests with a hand-made non-linear grid, parity with a stored curve, 806 core, app, results and fee tests; MN bundle built. Logged by the nightly review.
- **Open / next:** merge `ws/fee-box-baseline`; republish the app with the new baseline and fee slider.

### LB-213 · 2026-11-24 · Build: county remainders borrow rules from coded remainders (D-102 option (b), #516); fee box counts each baseline once (#515) (auto-review)
- **Question:** With D-102's 2020 populations, county remainders borrowed ADU rule priors and missing-middle doses from cities their size. Should they borrow from coded county remainders instead?
- **What I did:** (from commits 52cb82f5, c45141e1 on `ws/remainders-option-b`, merge #516 (f3961ec3, tag `app-2026-11-24c`); fragment `logbook.d/2026-11-24-ws-remainders-option-b.md`; merge #515 (19270690, tag `app-2026-11-24b`) of `ws/fee-box-baseline`)
  - Carried #488's rule-6 commits (D-102: remainders get their 2020 population) onto `main`; added `adu.remainder_priors` / `apply_priors` and `mm.dose_pools` / `remainder_pool_key`, with hand-worked tests; dated deviation of 2026-11-24 in `docs/analysis_plan.md`.
  - Rebuilt jurisdictions and `place_inputs` offline for six states (with a backup) and measured each state one at a time.
  - Merged the fee-box baseline fix left open in LB-212.
- **Outputs:** `src/lotline/model/scenarios/{adu,mm}.py`, `tests/model/test_scenario_adu.py`, `tests/model/test_scenario_mm.py`, `docs/analysis_plan.md`; `src/lotline/app/template.html` (#515).
- **Findings:** Oregon missing middle +5% instead of −42%, Oregon ADU −8%, NC ADU −3%, the rest within 1%. Without a fallback Oregon stayed at −42%, because only Oregon's ADU rules have 5 or more coded remainders.
- **Decisions:** Ben (2026-11-24): option (b), falling back to the smallest band where too few remainders are coded.
- **AI:** Claude Code. Logged by the nightly review.

### LB-214 · 2026-11-24 · Build: Wisconsin on the app as a data-ingestion test; ADU price-gap guard; handoff 17 (#517) (auto-review)
- **Question:** How can Wisconsin appear on the live app without being presented as part of the model's core evidence?
- **What I did:** (from commit d26fcf75 on `ws/wi-ingestion-label`, merge #517 (0d7d4e09, tag `app-2026-11-24d`); fragment `logbook.d/2026-11-24-ws-wi-ingestion-label.md`)
  - Added a state role `ingestion_test` (schemas 1.23), shown in the picker as "Data-ingestion test (not core)", with a Results note: national data only; its frozen V8 forecast came in about a third below the 2021–25 permits; the miss led to `benchmark_levels` (LB-210).
  - Replaced the ADU no-price filter in `results.build_bundle` with an error, since `place_inputs` already fills missing prices (the filter dropped nothing).
  - Wrote `docs/build/handoffs/17-code-review-and-cleanup.md` for the next thread.
- **Outputs:** `src/lotline/schemas.py`, `src/lotline/app/{build.py,template.html}`, `src/lotline/cli.py`, `src/lotline/model/results.py`, `docs/schemas.md`, `tests/app/test_build.py`, handoff 17.
- **Findings:** no model result changes; nothing rescored.
- **Decisions:** Ben (2026-11-24): Wisconsin is shown under its own role, not as a development or transfer state.
- **AI:** Claude Code; full test suite, ruff, compliance check, published page checked. Logged by the nightly review.

### LB-215 · 2026-11-24 · Validation: code review, thread 17 part A: every report and decision the analysis plan cites put on `main` (#518) (auto-review)
- **Question:** `docs/analysis_plan.md` cited reports and a decision (D-086) that existed only on unmerged branches. Does everything a judge would follow exist on `main`?
- **What I did:** (from commits 76f04248, 92572ebf on `ws/code-review`, merge #518 (d2d3c8f1); fragment `logbook.d/2026-11-24-ws-code-review.md`) compared every open PR's files with `origin/main` by content and listed every `reports/` path cited in `docs/` that did not exist; brought the missing reports and their fragments onto `main`.
- **Outputs:** `reports/review/2026-11-code-review.md` (review log: Part B cleanup lists, findings A1–A4); D-086 entry from #421 and #411's confirmation lines in D-079 in `docs/analysis_plan.md`; `reports/adu-joint-refit-2026-11/`, `reports/{mn,nc,tx,or}/mm-rule-checks-2026-11.md`, `reports/or/mm-first-events-2026-11.csv`, `reports/adu-rule-history/`, `reports/adu-covariate-screen-final-rows/`; `--m-owner` / `--m-other` flags in `scripts/dev/adu_covariate_screen.py`.
- **Findings:** remaining misses are gitignored build outputs, placeholders, a URL fragment and D-060's range report. A1: D-060's calibration range (approved 2026-11-06) never reached `main` (taken up in LB-216).
- **Decisions:** none new.
- **AI:** Claude Code; no config, parameter or engine code changed; ruff and `compliance_check.py`. Logged by the nightly review.

### LB-216 · 2026-11-24 · Build: D-060's ADU calibration range ported to `main`, with before/after (#519) (auto-review)
- **Question:** Review finding A1: `main` still measured ADU widening from Portland, Seattle and Los Angeles. What changes when D-060's range from the anchor's fit set is used?
- **What I did:** (from commits e0481cf9, be0ded3f on `ws/d060-port`, merge #519 (97e2436b); fragment `logbook.d/2026-11-24-ws-d060-port.md`) ported #327's generator and pins, applied D-060's rule to today's fit set (70 places, 513 place-years), and ran `lotline results` for the five core states before and after, changing only the config.
- **Outputs:** `config/params/hazard.yaml` (`adu_calibration_*`: rent $1,204–1,826, value $218k–590k, rate 2.96–6.81), `scripts/dev/adu_reference.py --fit-set`, `calibrate_adu.{weighted_percentile,fit_set_range}`, `hazard.PRE_D060_CALIBRATION`, V9 pin in `validation/v9.py`, new tests; D-060 "Run and ported" in `docs/analysis_plan.md`, `docs/model_and_assumptions.md`; page [D-060 Calibration Range Port](https://claude.ai/artifact/MZVVDXUA8jhcDV6D9sneLZ).
- **Findings:** ADU added permits at P50 rise 26–30% in MN, NC and TX, 101% in OH, 4% in OR; means move under 4%; P90 ÷ P10 roughly halves; every overlap flag now "high". Missing middle, fees, baseline and shortfall unchanged. The review's earlier note that own counts would cancel most of the change was wrong and is corrected in the review log.
- **Decisions:** Ben (2026-11-24): "Port it, show before/after".
- **AI:** Claude Code; 116 hazard, calibration, V9 and ADU tests; bundles compared (non-ADU outputs identical); `params_table.py --check`; compliance check. Logged by the nightly review.

### LB-217 · 2026-11-24 · Admin: open pull requests cleared and the app republished (thread 17 part B, #520); HANDOFF status table drafted (branch) (auto-review)
- **Question:** Which open pull requests still belong on `main`, and does the public app show the results after the D-060 port?
- **What I did:** (from merges #439, #464, #507, #267, #268, #269 and #520 (972ca985), tags `app-2026-11-24e` and `app-2026-11-24f`; fragment `logbook.d/2026-11-24-ws-review-cleanup.md`; commit 839d5cee on `ws/handoff-status-draft` (pushed, not merged))
  - Merged twelve PRs after CI passed (among them the earlier `ws/adu-data-hunt`, `ws/app-publish-summary` and `ws/dash-built-states` work and three Dependabot bumps: pytest 9.2.0, pandera 0.36.0, ruff 0.17.6) and closed seven with a reason each; #507's test conflict resolved by keeping both tests.
  - Built six state bundles from a clean checkout of `main`, one at a time, and published with `scripts/publish_app.py --go`.
  - Drafted a replacement for HANDOFF §1 "Where we are" as section B4 of the review log, for thread 6 to fold in; rows not backed by the repo are marked "(Ben to confirm)".
- **Outputs:** `reports/review/2026-11-code-review.md` (B1 outcome; B4 draft on the branch); release on https://cappellacci.github.io/lotline/.
- **Findings:** no open pull requests remain; bundles match the D-060 before/after run exactly; live page shows six states, MN ADU P50 601. The B4 draft lists what is still to do for submission: slides PDF and demo video, SBOM, three empty Policy Scenario Comparison sections, the 25-page check on the Model & Assumptions doc, and `stage = "submission"`.
- **Decisions:** Ben (2026-11-24): "Close the PRs then republish the app"; "close out the other 6 PRs, get this to be as close to deliverable as possible".
- **AI:** Claude Code; 74 app tests; live page checked. Logged by the nightly review.
- **Open / next:** merge the B4 draft into HANDOFF (thread 6); Part A area-by-area review.

### LB-218 · 2026-11-24 · Scope: Minnesota is the official benchmark state (#521, closes #40) (auto-review)
- **Question:** The benchmark state had been open since 2026-10-04, and compliance check S5 warned that `challenge.toml` named none.
- **What I did:** (from commit 26ffa2b8 on `ws/benchmark-mn`, merge #521 (3c4dab1e); fragment `logbook.d/2026-11-24-ws-benchmark-mn.md`) set the state, updated the docs, and rebuilt and republished Minnesota's app bundle with `--role benchmark`.
- **Outputs:** `challenge.toml` (`state = "MN"`), `docs/model_and_assumptions.md` ("Which states"), MN app bundle.
- **Findings:** reasons put to Ben: tier 1 data (Met Council permit-level ADU counts 2009–2024), the highest reassessment score (MN 37, TX 34, NC 32, OH 30 of 45), and real reforms to test against (Minneapolis, St. Paul). NC, OH, TX, OR and Wisconsin carry the thin-data story.
- **Decisions:** Ben (2026-11-24): Minnesota ("Yes let's settle it"). HANDOFF decision proposed for thread 6 to fold in.
- **AI:** Claude Code; compliance check S5 now passes; live page labels Minnesota as the benchmark. Logged by the nightly review.

### LB-219 · 2026-11-24 · Validation: which assumptions drive each reform's range (issue #54; branch `ws/range-drivers`) (auto-review)
- **Question:** The Handbook asks which assumptions matter most, and the "Critical assumptions" section of the Policy Scenario Comparison was empty. Can a cheap first-order analysis answer it without full Sobol?
- **What I did:** (from commit f20f8af6 on `ws/range-drivers` (pushed; a later remote commit 66f5734a not yet fetched, and the B4 draft cites #522); fragment `logbook.d/2026-11-24-ws-range-drivers.md`) regenerated each run's parameter draws from the scenarios' seeds and estimated first-order shares from the existing runs, after a first try on the bundle's per-run product proved uninformative (θ there is back-solved).
- **Outputs:** `src/lotline/model/sensitivity.py`, `tests/model/test_sensitivity.py`, `scripts/dev/range_drivers.py`, `reports/range-drivers/` (`drivers.csv`, `README.md`, `results.html`), "Critical assumptions" in `docs/policy_scenario_comparison.md`; page [What Drives the Range](https://claude.ai/artifact/AWq8ivW6dLV82AaLhpSERk).
- **Findings:** missing middle: the fitted uptake rate explains 96% of a ×40 range in every state; fees: the fee-to-permits elasticity explains 42–93%; ADUs: the uptake rate and partial-rule share together explain most of a ×4.5–7 range; Wisconsin's ADU range comes mostly from its unseen-state adjustment.
- **Decisions:** Ben (2026-11-24): "Let's do the cheap review".
- **AI:** Claude Code; hand-worked and analytic tests of the estimator; draw regeneration checked exactly against the bundles; no model code, config or results changed. Logged by the nightly review.
- **Open / next:** merge to `main`.

### LB-220 · 2026-11-24 · Deliverables: slide deck draft 1 (D2) and a Model & Assumptions Overview draft as a doc (D4) (auto-review)
- **Question:** Can the D2 deck (PDF, at most 30 slides) be drafted around the app's own charts, and the Model & Assumptions Overview be drafted as an editable doc?
- **What I did:** (from the untracked fragment `logbook.d/2026-11-24-deck-draft-1.md` and the two artifacts, both updated 2026-11-24)
  - Deck: re-read Rules §7a item 2; captured 19 Minnesota charts and cards from the built app (bundles at 46ff171) at 2x; built 27 slides from the Slides type with the Lotline design system: approach, findings by reform, tests, travel to other states, implications, limits, reproducibility.
  - Doc: a draft dated 2026-11-24 with seven sections (purpose and scope, core assumptions, data sources, methodology 4.1–4.12, limitations, sensitivity, intended use) and ten figures. Which session wrote it, and how it relates to `docs/model_and_assumptions.md`, is not recorded.
- **Outputs:** [Lotline: slide deck (draft 1)](https://claude.ai/artifact/6nu9bCYFfpHeuxEoQUQDrf); [Lotline: Model & Assumptions Overview](https://claude.ai/artifact/PTy5MPeqZ5q8jov9DKAmaK); `logbook.d/2026-11-24-deck-draft-1.md` (not committed).
- **Findings:** the app's cards read well on slides at an 820–980 px viewport; every state's "What builders pay in fees today" panel says no fee schedules are coded in this build, possibly a display bug.
- **Decisions:** none. The fragment's proposal of Minnesota as benchmark was settled the same day (LB-218).
- **AI:** Claude (Cowork session) wrote the slides from the rendered app and bundles, rendering each slide to check for overflow. Logged by the nightly review.
- **Open / next:** check the fee panel; re-capture after the final results run; cut toward about 22 slides; export the deck to PDF; check the doc fits 25 pages.

### LB-221 · 2026-11-25 · Build: code review part A, engine fixes: ADU rule priors, missing-middle dose pools, fees on elasticity everywhere, baseline coverage, fee draws by place (#522, #524–#527, #531) (auto-review)
- **Question:** Do the ADU, missing-middle, fee and baseline engines do what D-022 and D-102 (b) say for new states, places with gaps and county remainders, and why does the baseline leave some places out?
- **What I did:** (from commits 9943f712, 0b0f7c2d, fb73d8ba, 563f32df, 8a9ff48c, a9123748 and merges #524, #525, #526, #527, #531; fragments `logbook.d/2026-11-25-ws-{adu-review-fixes,mm-review-fixes,fees-elasticity,baseline-coverage,fee-draws-geoid}.md`; also merge #522 of `ws/range-drivers`, closing LB-219's open item)
  - ADU priors: reviewed `adu.py` and fixed three findings (A5–A7); a fourth (amended rules losing zone limits) was checked against the reform rows and found wrong.
  - Missing middle: fixed two real and three small findings in the dose pools (A12–A16).
  - Fees: measured the lot-feasibility channel against the elasticity route per place (4–40 times larger) and put the choice to Ben; added `fee_feasibility_channel` (now 0) instead of deleting the channel.
  - Baseline: found which places it dropped (new to BPS, or no eligible-parcel count) and added two routes behind config switches (`level_min_years`, `count_only_places`).
  - Fees (A19): local-fee draws now use one random stream per place, seeded by run seed and geoid, like the ADU and missing-middle draws.
  - Ran `lotline results` for all six states, one at a time, after each change.
- **Outputs:** `src/lotline/model/scenarios/{adu,mm,fees}.py`, `src/lotline/model/baseline.py`, `config/params/{fees,baseline}.yaml`, tests in `tests/model/`, `src/lotline/app/template.html` (fee card), `docs/model_and_assumptions.md`, deviation entries of 2026-11-25 in `docs/analysis_plan.md`, review log rows A5–A21 in `reports/review/2026-11-code-review.md`.
- **Findings:** ADU fixes: Wisconsin P50 −11%, MN, NC, OH within 2%, TX and OR unchanged. Missing-middle fixes: Wisconsin P50 −52%, NC within 1%, others unchanged. Elasticity everywhere: MN benchmark fee P50 862 → 618, OR 642 → 314. Baseline: origin-year homes covered 99.6% or more in every state; Ohio baseline P50 +4.5%; V1 backtest not rerun. Fee draws by place: real-local-fee P50 within 2 homes everywhere, other results identical.
- **Decisions:** Ben (2026-11-25): "Fix them here please" (ADU), "Fix them here" (MM), "Elasticity everywhere", "Model them too" (baseline), "Yes, do A19". HANDOFF decisions for the fee channel and baseline routes proposed in their PRs, not yet in HANDOFF.
- **AI:** Claude Code; hand-worked tests for each fix; six-state before/after runs. Logged by the nightly review.

### LB-222 · 2026-11-25 · Build: code review part A, adapters and tidy-ups; issue triage; results record their provenance (#528–#530, #532, #533) (auto-review)
- **Question:** Do the data adapters and app build do what their docstrings say, can the small review findings be cleared without moving any result, which open issues still need work, and can a results bundle say whether it came from committed code and after which blind tests?
- **What I did:** (from commits d7b6245d, 51844d07, def7c728, 398c676c, 6dce1c9f, 55d5b5b9 and merges #528, #529, #530, #532, #533; fragments `logbook.d/2026-11-25-ws-{adapter-fixes,review-tidy,dfw-permits,mm-fast-note,meta-provenance}.md`)
  - Reviewed `src/lotline/app/` directly and the adapters with two read-only subagents; re-read each reported bug before fixing four (A4 Austin, A22 Portland, A23 Raleigh, A24 Minneapolis/St. Paul dates read as UTC); A25 (Austin demolition window) checked and left.
  - Tidy-ups A10, A26–A30: hard-coded thresholds moved to config with sources (values unchanged), four empty packages removed (`adapters/comparables/`), units-confidence labels aligned, CSTX dedupe made order-independent, app build checks every template slot.
  - Dallas permit ids kept as text (a guard; built table identical, 134,124 rows); Fort Worth kept on filing year because only 7,924 of 297,818 permits carry an issue date.
  - Issue triage: #247, #406, #138, #448 closed with notes; a one-sentence note on missing middle's fast-ramp case (3.6×, from D-100) added to the app instead of a result.
  - Schemas 1.24: `results_meta.tree_clean`, `post_test`, `post_test_note` (closes #506, A21).
- **Outputs:** adapters under `src/lotline/adapters/states/{tx,or,nc,mn}/` with tests; `config/params/adu.yaml`, `config/states/{tx,oh}.yaml`; `src/lotline/schemas.py`, `src/lotline/model/results.py`, `docs/schemas.md`; `src/lotline/app/{build.py,template.html}`; review log rows A4, A10, A21–A30 and an issue triage table in `reports/review/2026-11-code-review.md`.
- **Findings:** adapter fixes on cached 2026-11-11 raw files with the network blocked: Portland 9 homes move from ADU to house (total unchanged), one St. Paul permit with no new homes changes year, Austin, Raleigh and Minneapolis unchanged. No other result changed. Wisconsin's rebuilt bundle shows `post_test` V8-WI-TRANSFER.
- **Decisions:** Ben (2026-11-25): "Yes, fix them" (bugs), "keep going" (tidy-ups), "Yes, do A29", close the three issues "as recommended", "Yes, add the note", "yup do A21 and 506 next".
- **AI:** Claude Code with read-only review subagents; full suite and compliance check before each PR. Logged by the nightly review.

### LB-223 · 2026-11-25 · Validation: nightly deep inspection (judging panel 69.4/100) and the robustness fixes it led to (#534–#537, #540, #541, #545) (auto-review)
- **Question:** What would the judges flag on `main` today, and what would break with future data releases, package versions or a new state?
- **What I did:** (from commits 54e0ea26, 2377c180, 45123f3d, 697da4b2, 4a6c073f, 2f5cb093, 08e657b6, 163c2d6e, 60f07a2d, f707a511, fd9a59dd and merges #534–#537, #540, #541, #545; fragments `logbook.d/2026-11-25-{nightly-review,ws-app-deepdive-fix,ws-codeql-xss,ws-toolchain-pins,ws-ingestion-guards,ws-onboarding-guards,ws-pandas31-map-fill,ws-pytest-xdist}.md`)
  - Ran the six-judge panel and head judge on a clean clone of `main` (30cfd38b), plus three read-only subagents (packages and toolchain, data ingestion, time bombs and the app); re-read the top claims in code before reporting.
  - Fixed the regression it found: the Model page deep dives broke after #529 (`AGG.windowLabel(b)` where only `bs` exists), with a static test (A31).
  - Then, in Ben's order: escaped data values in dashboards and the fee report to close five CodeQL `js/xss-through-dom` alerts (T6); pinned Python 3.12, dependency bounds, uv version and Node 22 on CI, with the suite run once in `tests.yml`; refused HTML pages saved as data (`HtmlNotDataError`, with the ArcGIS pager retrying them) and raised on an empty origin-year baseline; config checks that FIPS matches the state code and a plain error for missing FHFA `zip3_ranges`; `.astype("str")` before `fillna` in nine adapters for pandas 3.1; pytest-xdist and a `slow` marker on 40 tests.
- **Outputs:** judging run `reports/judging/2026-11-25-1656-30cfd38b/` (gitignored); page [Lotline Nightly Review](https://claude.ai/artifact/HHLtadgzkoKieFfWgXkzf8); `src/lotline/app/template.html`; `src/lotline/dashboard/template.html`, `src/lotline/model/dashboard.html`, `reports/dashboard/index.html`, `reports/fees-phase2-run/fees-phase2-results.html`; `.python-version`, `pyproject.toml`, `uv.lock`, `.github/workflows/{tests,compliance}.yml`; `src/lotline/io/{http,arcgis}.py`, `src/lotline/model/baseline.py`; `src/lotline/config/__init__.py`, `src/lotline/adapters/national/fhfa.py`; `tests/slow_tests.txt`, `tests/conftest.py`, `README.md`, `challenge.toml`.
- **Findings:** score 69.4 today, 83.2 ceiling (64.9 on 2026-11-17). No cached raw file (30,658 scanned) would be refused by the HTML guard. Under pandas 3.1.0 the whole suite passes with the fix. Full suite with 6 workers: 2,845 passed in 11 min 41 s (about 14–16 min serial); fast tier 2,805 tests in 2 min 52 s. No model result changed.
- **Decisions:** Ben (2026-11-25): "Run as deep an inspection as you can"; "go with your suggested order"; fix what needs no decision; "Yes, add xdist". Left for Ben: declaring numpy as a direct dependency, `commit_sha` without git, a GEOID survival check for new BPS years.
- **AI:** Claude Code (judging panel and review as subagents); fixes tested, ruff and compliance check; CodeQL fix checked by the PR's CodeQL run. Logged by the nightly review.

### LB-224 · 2026-11-25 · Build: app usability: sliders cite missing middle's own parameters and run P10–P90, plainer labels, fee scope stated, data dashboard loaded on demand (#538, #539, #542, #543) (auto-review)
- **Question:** Can the usability judge's findings (sliders citing the wrong parameters, two "gap" figures, unstated chart scales, internal terms, a 4.7 MB page) be fixed without touching engine numbers?
- **What I did:** (from commits 9f1be779, 64241d78, a4581a7d, 4e29d00f and merges #538, #539, #542, #543; fragments `logbook.d/2026-11-25-ws-{knob-sources,slider-p10-p90,app-usability-small,dashboard-lazy}.md`)
  - Mapped each missing-middle factor in `results.mm_draws` to its config parameters and added a `missing_middle` entry to all five sliders.
  - Sliders now span P10–P90 (centre still the engine's draws); the fee card says the cut applies to houses and 2–4 unit buildings.
  - US-04 to US-06: need-card bar reads "Still short after the reforms"; funnel scale stated on the page; y-axis titles; slider readout and legends in plain words; each source opens with a plain note, config keys one fold deeper.
  - US-08: moved the embedded data dashboard (3.98 MB of 4.66 MB) to `dashboard.js`, loaded the first time the Data tab opens.
- **Outputs:** `src/lotline/app/{template.html,knobs.yaml,build.py}`, `tests/app/test_build.py`, `tests/app/test_ami_strip.py`.
- **Findings:** no engine number changed; parity tests hold; 76 app tests pass; headless render shows the new labels.
- **Decisions:** Ben (2026-11-25): P10–P90 ("let's use P5 and P95, or even P10 - P90"); add the fee-scope sentence; keep the 5+ exclusion and single-number headline; "Can you spin up a PR to fix these? Smaller usability items".
- **AI:** Claude Code; app tests, `node --check`, headless Chrome render. Logged by the nightly review.

### LB-225 · 2026-11-25 · Build: calibration as code, phases 1, 2 and 4: every fitted value traced to one step; data-only and ADU steps rerun with `lotline calibrate` (#544; branches) (auto-review)
- **Question:** Can a judge see, in one command, where every fitted number in config comes from, and can those numbers be re-derived from the data?
- **What I did:** (from commits 61bd0852, ebae3ab6, bc7788b2 (merge #544), 22207b8b on `ws/calibrate-phase2` and 14c92410 on `ws/calibrate-adu` (both pushed, not merged); fragments `logbook.d/2026-11-25-ws-calibrate-{phase1,phase2,adu}.md`)
  - Phase 1: a read-only subagent mapped every fitted parameter to its script, inputs, decision and seed; Claude Code turned the map into a registry of 22 steps, a lock file and `lotline calibrate --list | --check | --write-lock`, plus a runner framework (`--run [--step] [--quick] [--write]`). Deviation from the design: the step registry, not a `fitted_by` field in each YAML entry, records the producer, because four scripts rewrite their YAML whole.
  - Phase 2: runners for four data-only steps; the eligible-proxy pairing moved into the library.
  - Phase 4: the ADU fit-set builders moved into `lotline.model.adu_fit_set` and `adu_refit`, with runners for six ADU steps; dev scripts now import the library.
  - Phase 3 (missing middle) was being worked on in the `.claude/worktrees/calibrate-mm` worktree (uncommitted at the time of this scan).
- **Outputs:** `src/lotline/calibrate/{__init__,steps,data_steps,adu_steps}.py`, `config/calibration.lock.json`, `src/lotline/cli.py`, `src/lotline/model/{adu_fit_set,adu_refit}.py`, tests in `tests/calibrate/` and `tests/model/test_adu_fit_set.py`, `docs/calibration.md`; page [Lotline Calibrate](https://claude.ai/artifact/8XR3iNs2knPpTUFNPPu1Y3).
- **Findings:** `--check` passes: 22 steps account for 130 values. Three data-only steps reproduce exactly; the eligible proxy gives k 0.971 and σ 0.106 against config's 0.998 and 0.060 (2026-11-06) and the original script agrees, so config is out of date (D-056 still passes). The ADU chain rebuilds the same 70 places and 498 place-years field for field and reproduces every value except D-060's rent high ($1,822 vs $1,826, because config's range skipped the D-096 cut); D-099's held-out gain reproduces the decision but not the number in config's source text (−0.37 vs −0.11). No config number changed.
- **Decisions:** Ben (2026-11-25): "start phase 1"; phases 3–4 sent to the model sessions. For Ben: whether to update the eligible proxy and whether the calibration range should follow the anchor's own fit place-years.
- **AI:** Claude Code (Claude Opus 5.5); synthetic registry tests, hand-worked runner tests, field-by-field comparison of old and new chains on real data, ruff and compliance check. Logged by the nightly review.
- **Open / next:** merge phases 2 and 4; finish phase 3; phase 5, refitting the stale steps (Ben's call).

### LB-226 · 2026-11-26 · Build: calibration as code finished: stale fits refitted on today's tables and current forms, missing-middle steps from code, one-off scripts archived (#546, #547, #549, #551, #557) (auto-review)
- **Question:** With every fitted value traced to a step (LB-225), which values are out of date, and can they be refitted with `lotline calibrate --run --write` so a reader reproduces each one from the README?
- **What I did:** (from commits d58194e8, 0c7a3c35, f02ce1cc, 94ab06c1, cf6dcccf, 947ec078, 50afd588, fcca7868, eaf896e3, f3204a84 and merges #546, #547, #549, #551, #557; fragments `logbook.d/2026-11-25-ws-calibrate-{phase2,adu}.md` (updated), `logbook.d/2026-11-26-ws-calibrate-{adu-refit,mm,phase6}.md`; dated deviation entries of 2026-11-26 in `docs/analysis_plan.md`)
  - Phase 2: refitted the eligible proxy (D-056) on today's parcel rolls.
  - Phase 4: wrote the D-060 calibration range on the anchor's own 498 place-years and regenerated the parameter table.
  - Phase 5 (ADU): runners and arithmetic for the three older ADU fits (state spread τ, D-043/D-044; drift σ, D-091; ramp, D-048) on D-096's form; ran each refit and before/after results for WI and MN.
  - Phase 3 (missing middle): runners for `mm_units_per_project`, `mm_year_spread`, `mm_c4`, `mm_fast_ramp`; fit sets moved into `src/lotline/model/mm_fitsets.py`; parity run against the old scripts; then refitted φ, C4 and D-100.
  - Phase 6: classified every file in `scripts/dev/`; moved 110 one-off scripts to `scripts/archive/` with an index, kept 56 with reasons; README section "Reproduce the fitted parameters"; 306 script paths updated in 131 files; fixed a pandas 3.1 regression in `geoparts.township_shares` that stopped the eligible-proxy step.
- **Outputs:** `src/lotline/calibrate/{steps,adu_steps,mm_steps}.py`, `src/lotline/model/{adu_refit,mm_fitsets}.py`, `config/params/{eligible_proxy,adu,adu_state_effect,mm}.yaml`, `config/calibration.lock.json`, `docs/calibration.md`, `docs/analysis_plan.md`, `scripts/archive/` and its `README.md`, `scripts/dev/README.md`, `README.md`, `docs/adding_a_state.md`, tests in `tests/calibrate/` and `tests/model/`.
- **Findings:** eligible proxy k 0.998 → 0.971, σ 0.060 → 0.106 (D-056 still passes; tier-3 states get about 3% fewer eligible lots). D-060 rent high $1,826 → $1,822. ADU: no ramp still wins and drift σ 1.025 is unchanged; τ̂ falls 0.565 → 0, which leaves the five fitted states unchanged but narrows Wisconsin's ADU range (P10–P90 122–2,088 → 201–1,391, P50 506 → 505). Missing middle: 15 of 18 values reproduce exactly; φ 13.63 → 13.03 because the tables grew (713 places kept against 483); after the refit the mature rate is 0.0016571 (was 0.0010387) and the half-way point 4.5 (was 4.0), and missing-middle five-year P50 rises 7–10% in MN, NC, OH, TX and OR. Phase 6 check: 22 steps, 130 values, lock matches; quick runs of every step match config except three coarse-grid values; fast tier 2,879 passed.
- **Decisions:** Ben (2026-11-26): refit the eligible proxy; "Yes, use $1,822"; "Yes, write it" (ADU phase 5); φ first recorded as kept at 13.63 (commit 50afd588), then "Update φ now", which the session recorded as correcting a mis-click.
- **AI:** Claude Code (Claude Opus 5.5) wrote the runners, tests and refits. Checked by parity runs of old scripts against the library on real data, `lotline calibrate --run` / `--check`, hand-worked tests, before/after results bundles, ruff and the compliance check. Logged by the nightly review.
- **Open / next:** the live app picks up the refitted values at its next publish; the full calibration run needs `CENSUS_API_KEY`.

### LB-227 · 2026-11-26 · Build: review loose ends and ingestion guards: commit id without git, config GEOID guard, pandas 3.1, loud column changes, fetch order, HUD year, FHFA vintages, Actions by SHA, lighter Model page (#523, #548, #550, #552, #560–#562; `ws/ingest-guards`) (auto-review)
- **Question:** Can Lotline run from a downloaded copy, and would a re-keyed place, a renamed column, a new HUD or FHFA file, a renumbered TIGERweb layer or a permit layer that rolls old permits out be caught instead of quietly changing inputs?
- **What I did:** (from commits 66ce86ff, f1a13719, 7dfa22c3, 656fe96d, 66849f9f, 60386e2e, f70a671c, b96c307d, e8a917bc, 6cf9ea31 and merges #523, #548, #550, #552, #560, #561, #562; fragments `logbook.d/2026-11-26-ws-{review-loose-ends,pandas-3.1,data-guards,review-fixes-3,review-fixes-4,model-page-light,ingest-guards}.md`). Works the items left for Ben in LB-223 and the 2026-11-25 ingestion review.
  - `commit_sha` falls back to `LOTLINE_COMMIT`, then a `git archive` stamp, then zeros; config GEOIDs missing from the jurisdictions table fail the check; numpy declared directly (approved by Ben).
  - pandas 3.0.6 → 3.1.1 by hand (Dependabot's branch was gone); pandas-4 deprecation warnings made test errors.
  - App wording takes its years from the bundles; BPS, StratMap and FHFA readers stop on missing, renamed or blank columns; `lotline fetch` runs sources in dependency order (`READS` / `RERUN_AFTER`).
  - App build refuses bundles from another schema line; the JS percentile returns NaN on any missing value, as numpy does; the D-025 skip kept (rerun still running after 12 minutes) and now cites #558.
  - HUD fiscal year read from the file; TIGERweb layer name and vintage checked; each FHFA refresh kept under its pull date; every GitHub Action pinned to a commit SHA.
  - Model page loads per-state summary files without draws.
  - On `ws/ingest-guards` (pushed, not merged at this scan): BPS re-key report (`interim/<st>/bps_rekeys.csv`, `lotline unlisted`) and `adapters/snapshots.py`, which keeps every cached snapshot of the Minneapolis and St. Paul permit layers.
  - #523 added a draft HANDOFF status table for review thread 6 to `reports/review/2026-11-code-review.md`.
- **Outputs:** `src/lotline/model/results.py`, `src/lotline/COMMIT`, `.gitattributes`, `src/lotline/build/jurisdictions.py`, `pyproject.toml`, `uv.lock`, `src/lotline/app/{build.py,template.html,aggregate.js}`, `src/lotline/adapters/national/{bps,fhfa,hud_il,tiger_boundaries}.py`, `src/lotline/adapters/states/tx/stratmap_parcels.py`, `src/lotline/registry.py`, `src/lotline/cli.py`, `.github/workflows/*.yml`, `docs/data_provenance.md`, `docs/adding_a_state.md`, tests in `tests/core/` and `tests/app/`; on the branch, `src/lotline/adapters/snapshots.py`.
- **Findings:** all 102 BPS files (1992–2025) parse to the same 483,599 rows under the new checks; `lotline unlisted` lists only 17 expected reform orphans (NC 2, OR 15); Model page fetch about 320 KB instead of 7.7 MB (not yet checked in a browser). Re-keys found: MN 4, OH 3; Minnetonka Beach's old GEOID 2743270 is still in `config/states/mn.yaml` (raised with Ben, not changed). No permits have rolled out of the cached Minneapolis or St. Paul snapshots yet. No model result changed.
- **Decisions:** Ben approved numpy as a direct dependency. Left for Ben and the ADU session: the unknown-2020-population item in `build/place_inputs.py`, which sets the ADU size band of 18 places (a model choice, not a guard).
- **AI:** Claude Code; unit tests, full suite with pandas-4 warnings as errors (2,880 passed), fast tier (2,902 passed after the last PR), ruff, compliance 0 FAIL, provenance regenerated. Logged by the nightly review.
- **Open / next:** merge `ws/ingest-guards`; check the Model page in a browser; Minnetonka Beach's config GEOID.

### LB-228 · 2026-11-26 – 2026-11-27 · Build: modularity plan steps 1–3: a scenario contract the app reads, forecast code apart from fitting code, engine files split by method step (#555, #556, #559, #564, #565; branches) (auto-review)
- **Question:** Can a new reform be added as one module with no edits to the results code, schemas, bundle writer or app, can a reader tell from the folders which code a forecast runs, and can the largest files be split by method step, all without any number changing?
- **What I did:** (from commits 46050d83, 916adce8, 05accc47, 4518bcb2, 5cce3cf1, 6fa6c268, 73daabae, ee11c0f0, c995c80b, a74b1d29, 25832997, 3c48c6c0, 93c5f470, c45a19a5 and merges #555, #556, #559, #564, #565; fragments `logbook.d/2026-11-26-ws-{modularity-plan,scenario-contract,scenario-app,forecast-fit-split,split-results-baseline,adu-move,modularity-mm,modularity-mm-split}.md` and `logbook.d/2026-11-27-ws-adu-split.md`)
  - Plan: counted where scenario names are written out and traced imports from the results bundle and the app; wrote `docs/build/modularity-plan.md` with three steps, adopted step by step by Ben.
  - Step 1: a scenario contract and registry (`NAME`, `LABELS`, `VARIANTS`, `run`), bridge modules for ADU, MM and fees, `build_bundle` looping over the registry, schemas 1.25 with `meta.scenarios`; the app builds its result boxes, lanes, picker, tabs and evidence cards from `meta.scenarios`, proved with a toy scenario run under node and in a browser.
  - Step 2: six unowned modules moved out of `model/` to `calibrate/` and `validation/`; guard test `tests/core/test_module_layout.py`; ADU fitting code moved to `calibrate/adu/` (engine helpers to `model/adu_rates.py`); on `ws/modularity-mm`, missing-middle fitting code moved to `calibrate/mm/` (helpers to `model/mm_rates.py`) and the D-092 check modules archived, leaving `MOVING` empty.
  - Step 3: `results.py` and `baseline.py` split (`results_tables`, `results_baseline`, `validation/baseline_scores.py`) with a 620-line engine-file guard (`OVERSIZE`); on `ws/modularity-mm-split`, `calibrate_mm` split into eight modules and `estimate_mm` into three; on `ws/adu-split`, `scenarios/adu.py` (1,732 lines) split into seven step modules, leaving `OVERSIZE` empty. Old module names re-export everything.
- **Outputs:** `docs/build/modularity-plan.md`; `src/lotline/model/scenarios/{__init__,bundle_adu,bundle_mm,bundle_fees}.py`, `src/lotline/model/{results,results_tables,results_baseline,baseline,adu_rates}.py`, `src/lotline/schemas.py`, `docs/schemas.md`, `src/lotline/app/{build.py,template.html}`, `src/lotline/calibrate/adu/`, `src/lotline/validation/`, `tests/core/test_module_layout.py`, `tests/app/{test_scenario_toy.py,scenario_harness.js}`, `tests/fixtures/scenarios/toy.py`; on branches, `src/lotline/model/mm_rates.py`, `src/lotline/calibrate/mm/`, `src/lotline/model/scenarios/adu_{rules,rule_priors,rule_inputs,params,place_types,paths,own_rate}.py`.
- **Findings:** every results bundle part apart from run-time metadata is byte-identical before and after each step on all six states (MN, NC, OH, TX, OR, WI), by per-part sha256. A toy reform reaches the bundle and gets a result box, lane, picker button, model tab, evidence card and bar with no other edit. The fee model's two-run switch and slider still name fees.
- **Decisions:** Ben (2026-11-26): step 1 adopted; "Owners do them" (step 2 moves); "yes, do steps 2 and 3 after #559 merges". Ben (2026-11-27): "Archive them" (the D-092 check modules and their three test files). Owner choices: `pooled_adu` to `calibrate/adu/`; ADU legal lots as three modules; `mm_counts.py` left whole; limit 620 lines.
- **AI:** Claude Code (Claude Opus 5.5) with scripted, `ast`-based moves so function bodies moved unchanged. Checked by bundle hashes per state, the guard tests, `lotline calibrate --check`, the non-slow tests, ruff and the compliance check. Logged by the nightly review.
- **Open / next:** merge `ws/modularity-mm`, `ws/modularity-mm-split` and `ws/adu-split`; optional split of `tests/model/test_scenario_adu.py`; ADU and MM may fold their bridge modules into their models (step 1.5).
