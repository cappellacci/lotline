# Lotline: Logbook

A running record of **how** the Lotline entry was built: what question each step asked, what was done, what it produced and what it changed. `HANDOFF.md` says where things stand; this file says how we got there, so the process can be replayed or explained (and it backs the Transparency criterion, Rules §8, 30%).

**Conventions**
- Newest entry at the bottom. Entries are never rewritten; corrections go in a new entry that points back (e.g. "corrects LB-006").
- Every entry names its outputs by path or link so someone else can open exactly what was produced.
- "AI" lines record where Claude did the work and how it was checked, for `docs/disclosures.md`.
- Entries LB-001 to LB-009 were **reconstructed on 2026-09-30** from the docs and artifacts they produced; later entries are written as the work happens.
- Entries are added two ways: by the Claude session doing the work (rule in `CLAUDE.md`), and by a nightly review that scans the repo, project docs and artifacts for anything new since the last scan. Nightly entries are marked *(auto-review)*.

**Last scan:** 2026-10-07T00:55Z

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
| 13. Core data and contracts | Oct 6–7 | Can national data for four states flow through shared, tested contracts, with blind tests protected? | BPS, FHFA, ACS, FRED and 2020 Census adapters; holdout filter; generated provenance and data dictionary; V0 reports; tag `schemas-v1` | LB-027 – LB-034 |

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
