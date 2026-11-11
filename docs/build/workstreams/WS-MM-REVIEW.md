# WS-MM-REVIEW · Missing middle: a methodology review, then the same kind of rebuild ADUs just had

**Start:** 2026-11-11 or later. **Branch:** `ws/mm-review` (one worktree; later steps get their own branches).
**Owns:** the review document `docs/research/mm-methodology-review-2026-11.md`, and proposed D-entries in
`docs/analysis_plan.md` written as *Proposed, for Ben's review*. Later steps own whatever Ben approves.
**Does not own:** shared contracts (`schemas.py`, config loaders, CLI, IO), the parser `lotline.parse.permit_text`,
the ADU engine, or `LOGBOOK.md` / `HANDOFF.md`. Open a `contract-change` issue or ask Ben.

## Why this workstream exists

Lotline's headline is a statewide count of homes a reform adds over five years. Ben's test is whether the number
is **accurate**, not whether a checklist is complete. In November the ADU method was rebuilt around that test:
- the D-074, D-075, D-078, D-079, D-080 and D-081 entries;
- counts taken from record-level permits in many more places;
- each source's undercount measured, with precision ÷ recall for parser sources;
- denominators fixed, with permit-level county remainders;
- accuracy tests A–C in all five states;
- a data-tier test for a state with no history.

Missing middle hasn't had that treatment. Its current method (D-024 → D-038 → D-042 → D-054/D-055 → D-058/D-059
→ D-062 → D-063) rests on Census BPS counts of 2–4 unit buildings and a small set of treated places.
**Start with a review.** The question is whether that method can give an accurate statewide number, and what it
would take. Only after Ben has read the review does any change get pre-registered or built.

## Ground rules (from CLAUDE.md, memory and the ADU work)

- **Holdouts are sacred.** V5 St. Paul (MN) is still blind: never read St. Paul or Ramsey outcomes after its
  origin, never bypass the holdout filter, never pass `--unblind`. V5 Charlotte and V9 Oregon are released.
- **The review phase runs no engine, scenario, fit, calibration or dev-run scripts.** Reading existing reports,
  code, configs and processed tables (holdout-filtered) is fine. Tabulating *outcomes* in a new way before a
  method is written counts as a run: say so and ask first.
- **Measure uptake from our own five states**; outside studies are a check only (D-037,
  `project-purpose-own-data`).
- **Decisions are revisable.** Nothing about the current MM method is frozen. Keep what is known about the data;
  question every method choice.
- **Ben files no records requests and emails no staff.** A source that needs one is closed as "no usable source".
- **Don't re-download data.** Use `lotline fetch --offline` (#382) to rebuild from cached raw snapshots. A new
  download is a separate, named step.
- **Pre-register before counting.** Write each method, with its pass rule, before the counts it judges, as the
  ADU entries did. Say what was already looked at.
- **One PR per piece. Ben merges, or says "merge".** Auto-merge is off. Propose HANDOFF decisions in the PR.
- No data or secrets in the repo; no new dependencies without asking; every parameter in `config/params/` with a
  source; tests use synthetic fixtures; logbook fragments in `logbook.d/`; `gh auth switch -u cappellacci`.
- **Disk is tight.** Check `df -h /System/Volumes/Data` before big steps.

## Read first

1. `HANDOFF.md`, then `docs/analysis_plan.md`:
   - **missing middle:** D-014, D-024, D-038, D-042, D-054, D-055, D-058, D-059, D-062, D-063 and D-071 (V5
     Charlotte);
   - **ADU, the template:** D-074, D-075 and D-078–D-081;
   - **the zone-model proposal:** D-072 (#354, not merged), which treats ADUs and missing middle together by zone.
2. `docs/research/lotline-causal-diagram-mm.md`, `docs/research/mm-uptake-evidence.md`,
   `docs/research/lotline-statistical-protocol.md`, `docs/research/lotline-validation-plan.md`.
3. `config/params/mm_hazard.yaml`, `config/params/mm.yaml`, and the `missing_middle` rows in
   `config/reforms/*.csv` (MN 9, NC 27, OH 4, TX 43, OR 275 rows).
4. Code: `src/lotline/model/estimate_mm.py`, `calibrate_mm.py`, `model/scenarios/mm.py`.
5. Results:
   - `reports/mm-d038/`, `mm-d042/`, `mm-d054/`, `mm-d058/`;
   - `reports/v9-oregon-d055/`;
   - `reports/v5-charlotte/README.md`;
   - `reports/engine14/v5_freeze_proposal.md`.
6. **How the ADU rebuild was done:**
   - `reports/nc/wake-roll-adu-diff.md` (undercount from roll comparison);
   - `reports/{mn,oh,tx,or}/adu-coverage-and-undercount.md`;
   - `reports/{nc,tx,oh}/parser-handcheck-2026-11-11.md`;
   - `reports/adu-rebuild-2026-11-11.md` and `-11b`.

## Where the missing-middle method stands (2026-11-11)

- **Estimand:** extra 2–4 unit buildings per eligible parcel a year (rule 1.1, D-014, including vacant
  single-family-zoned lots) after a rule allows them. Homes = buildings × 2.08.
- **The fit (D-054 main fit, adopted by D-055):**
  - θ is 0.12 per 1,000 parcels a year (90%: 0.03–1.0 per 1,000).
  - α is 8.4 (2.8–32): a very wide spread from place to place.
  - The ramp's half-way point is 0.5 years, on the grid floor.
  - The fit uses 13 places and 69 place-years.
- **θ and the ramp trade off along a ridge with two peaks** (D-062): a fast ramp with a low θ, or a slow ramp with
  a high θ. The scenario range is put on the five-year rate.
- **Outcome:** Census BPS buildings with 2 units plus 3–4 units, place level. Places that BPS doesn't report, such
  as Charlotte and the Mecklenburg towns, are counted inside their county row. 5–6 unit buildings and townhouses
  fall outside: BPS files them as 5+ or 1-unit. The Handbook's benchmark is **2–6 units in three stories**
  (D-063).
- **Fragility so far:**
  - D-038's first fit failed its placebo, and its leave-one-out was no better than "no effect".
  - Most of the excess came from Houston and Austin building types the reforms didn't newly allow (D-042).
  - Texas was missed by every model in the leave-one-state-out test (D-054): Lubbock's baseline, then Lubbock
    dropped as an unverified rule (D-059).
  - The folds give θ from 0.013 to 0.24 per 1,000. Most of the excess comes from a few NC towns and Houston.
  - **V9 Oregon (not blind after D-055):** the headline scored well, but place ranges were too narrow (34% above
    P90).
  - **V5 Charlotte passed** (119 observed in P10–P90 of 89–172). The pass is county-wide, partly luck in the
    flat baseline, and homes per building ran below 2.08 (mostly duplexes).
- **Rule rows:** many are single-coder, from Ben's workbook. Some pre-reform rules are not coded (Lubbock's
  Ch. 40), and Oregon dominates the row count.

## The review: questions it must answer

Write `docs/research/mm-methodology-review-2026-11.md`. For each question, say what we know, how good the
evidence is, what accuracy hinges on, and the options with their cost. Recommend one, but don't decide.

1. **The target.** Is "extra 2–4 unit buildings on eligible parcels" the right estimand for the Handbook's 2–6
   units in three stories?
   - What is lost by leaving out 5–6 unit buildings and townhouses?
   - How do we net teardowns and the single-family home a duplex replaces?
   - Are conversions (a house split into units) counted anywhere?
2. **The outcome measure.** BPS gives buildings by size class, place level, with county rows for non-BPS places.
   - Could record-level permits, which ADUs now use in about 30 places, give 2–4 unit counts by parcel, by
     building type and on formerly single-family lots?
   - What would that cost per source?
   - How would we measure their undercount and precision against BPS, and against parcel rolls (a second unit
     appearing on a lot) where two rolls exist?
   - Inventory which permit sources already in `LOTLINE_DATA_DIR` carry unit counts. Don't download.
3. **The denominator.** Rule 1.1 eligible parcels, including vacant lots.
   - Does the #375 permit-level remainder issue apply here too (37119 and 23 other remainders)?
   - Should vacant lots be weighted differently from built lots?
   - Should lot size or frontage limit what is feasible?
4. **The treated set.** Only about 13 places carry the fit. List every reform in the five states that raised
   the unit cap on single-family lots, and how confident its date and dose are: Minneapolis 2020 (still a test
   place), Durham EHO, Raleigh's 2021 missing middle text change, Charlotte's UDO, Austin HOME, Houston's lot-size
   rules, Oregon HB 2001 cities, and others.
   - How many more places could enter with accepted rule rows, as the ADU work did, and how many second-coder
     checks are needed?
   - What do `[predates]` and `[earliest-known]` imply here?
5. **Identification.**
   - Is the own-growth baseline (T−3…T−1) the right counterfactual? D-058 proposed a stability rule.
   - Is a comparison-place baseline (D-042) better?
   - How do we separate a reform's effect from market swings? Charlotte's one-unit buildings fell by half during
     the window.
   - Can the θ and ramp ridge be broken with more places or longer post-periods, or should the model be
     re-parameterized?
6. **Mechanism and transfer.** What carries the effect to a place with no history?
   - Price-to-cost (`F(PCR)`), lot supply, builder capacity, the zone type.
   - Does the D-072 zone model, or a coefficient for each type of place (as D-075 defers for ADUs), apply here?
   - What does the five-state data-tier test (D-075: tier 0 national data only, tier 1 plus coded rules, tier 2
     plus one city's counts) look like for missing middle?
7. **ADU and missing-middle overlap.** Both compete for the same lots (HANDOFF 2026-09-30). Is the overlap rule
   coded and tested, and does the new ADU method change it?
8. **Accuracy tests.** Propose missing-middle versions of ADU tests A–C:
   - new places out of sample;
   - a roll or permit check where two sources exist;
   - a no-reform floor;
   - plus leave-one-state-out and the data-tier test.
   Give pass rules that are written down before any count.
9. **Uncertainty.** Are the place ranges honest? V9's place ranges were too narrow. Which parameters should be
   ranges, and which need sensitivities?

## Deliverables, in order

1. **The review** (above): an Artifact-ready summary at the top, with plain language for Ben. Open a PR, docs
   only; Ben reads it before anything else happens.
2. **After Ben picks options:** a pre-registered D-entry (*method only, before any count*), like D-074/D-075.
3. **Then the counting work**, which should run in parallel sessions per state, with one brief each and the ADU
   pattern:
   - new sources;
   - rule rows proposed in reports, which Ben accepts;
   - a measured undercount and precision;
   - an offline rebuild;
   - one joint refit;
   - the tests;
   - a results page after the run (memory: `run-results-page`).

## Done looks like (for the review step)

- `docs/research/mm-methodology-review-2026-11.md` answers questions 1–9, each with options and a
  recommendation, and cites every claim to a file, report or D-entry.
- A table of candidate data sources, permit and roll, already on disk: what each carries and its licence status.
- A table of candidate treated places: rule, date, dose, coder confidence and whether the place is a holdout.
- A short "what accuracy hinges on" list, ranked.
- A PR with a logbook fragment. Nothing is run, downloaded or changed in `config/`.
