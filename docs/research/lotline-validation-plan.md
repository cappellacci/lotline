# Lotline: In-state validation plan (v0.1, 2026-10-04)

**Status:** proposal. Once approved, §3 (tests and pass/fail criteria) is copied into `docs/analysis_plan.md` and committed **before** any outcome model is run, per protocol §6. Later changes go in a dated deviations log.
**Assumes:** North Carolina as the target state (recommended in `research/lotline-data-availability.md`; not yet decided). §7 covers what changes for TX or OH.
**Builds on:** `research/lotline-causal-diagram.md` (+ `-mm`, `-fees`), `research/lotline-confounder-register.csv`, `research/lotline-statistical-protocol.md`, `research/lotline-two-prong-design.md`.

---

## 0. The idea

Prove each piece of the model on data where we already know the answer, **inside the target state**, before using it where we don't.

The model has four pieces. Each can be wrong independently, so each gets its own test:

| Piece | Question it answers | Fails if... | Tested in |
|---|---|---|---|
| **Baseline** | What gets built with no policy change? | Rates, the cycle or local demand are handled badly | V1 |
| **Mechanism** | Which parcels pencil, and how fast do they get built? | The pro forma or hazard is mis-specified | V2 |
| **Policy effect** | How much does a reform add? | Confounders (register C04–C08) leak into the estimate | V3, V4, V5 |
| **Transport** | Does an effect measured elsewhere hold here? | Effect modifiers differ and we don't adjust | V4, V7 |

A model can look right overall while two pieces are wrong in opposite directions. Testing them separately is what lets us say *which* assumption is driving a result, which is what the Policy Insight criterion asks for.

**Standing rule:** a failed test is a result, not a reason to quietly retune. We record it, widen the range or shift weight between the evidence and mechanism prongs, and say so in the Model & Assumptions Overview.

---

## 1. North Carolina jurisdictions and their roles

| Jurisdiction | Reform (effective) | Post-period by 2026 | Role | Best data |
|---|---|---|---|---|
| **Durham** | Expanding Housing Choices: duplexes in urban-tier zones, small lots, ADUs to 800 sq ft (2019-09-03). Parking minimums removed (SCAD, 2023-11-21). | ~7 yrs | Treated: ADU + MM. Urban vs suburban tier gives a within-city contrast. | City-county permits: `DWELLING_UNITS`, CO date, PIN. **Freshness uncertain (last modified 2024-11).** |
| **Raleigh** | ADUs by right (2020-07-07); Missing Middle TC-5-20: two-family everywhere **except R-1**, townhouses in R-2/4/6 (2021-07); MM 2.0 (2022-08-08) | ~5–6 yrs | Treated: ADU, MM. **R-1 lots are an in-city comparison group.** | Permits 2000–2026 with `adu_type` and `missing_middle` flags. **`housingunitstotal` nearly empty from 2024**: derive units from `censuslandusecode`. |
| **Charlotte** | UDO: duplexes and triplexes on all N1 lots (2023-06-01) | ~3 yrs | **Blind forward test** (V5) | Mecklenburg permits: no unit count, but `zonecode` (N1) and building type; BPS for Charlotte place |
| **Greensboro** | ADU: owner-occupancy and parking dropped (2024-04-16) | ~2 yrs | Optional second forward test | No open permit dataset; BPS only |
| **Towns affected by *Quality Built Homes v. Carthage*** | Lost water/sewer "future service" impact fees (2016-08-19); system development fees allowed again (2017-10-01) | ~1 yr window | Fee natural experiment (V6), exploratory | BPS place-level; affected-town list to compile |
| **Non-reforming NC places** | None (audit against policy inventory) | — | Controls and donor pool; baseline test (V1) | BPS (reported-only, not imputed) |
| **Statewide** | S.L. 2026-59: ADUs with each single-family home in non-coastal cities over 50,000, from 2027-01-15 | — | Must be written into the baseline | — |

**Out-of-state comparables** (evidence prong and leave-one-out tests): Portland (permits 1995–2026, `IS_ADU`; RLIS taxlots with sale prices), Seattle (permits with `housingunitsadded/removed`), Austin (permits 1970–2026, ADU class R-102), Los Angeles (`ADU_CHANGED`), California APR Table A2.

---

## 2. Integrity rules

1. **Pre-register.** §3 goes into `docs/analysis_plan.md`, committed and tagged (`prereg-v1`) before V3 begins.
2. **Data cut-offs in config, not in our heads.** Every fit reads a `train_until` date per jurisdiction. Test code asserts that no post-cut-off record for a held-out place enters fitting.
3. **Freeze before unblinding.** Predictions for V4 and V5 are written to `results/frozen/` and committed (hash recorded) *before* the observed outcomes are loaded.
4. **No retuning on test places.** If a test fails, parameters may change only via a dated deviation entry. The original failed result stays in the report.
5. **Report everything run.** Every specification attempted appears in an appendix table, not just the preferred one.

---

## 3. The validation ladder

Thresholds marked *(proposed)* are our judgment, to be confirmed when pre-registering. Coverage targets assume a P10–P90 band, which should contain the true value about 80% of the time.

### V0. Data reproduction (pipeline check)

- **Question:** Do our adapters count what the publishers count?
- **Tests:**
  - Rebuild Census BPS annual NC state totals from place files.
  - Rebuild Portland and Seattle published ADU counts (E044, E047) from raw permits.
  - Reconcile Raleigh, Durham and Charlotte local permit totals against BPS for the same places, by year and building size. The ratio of local ADUs to BPS 1-unit permits gives our first estimate of the BPS ADU undercount.
- **Pass *(proposed)*:** BPS totals match exactly; published city counts within ±5% per year; every local-vs-BPS gap above 10% explained in `docs/data_provenance.md`.
- **Also delivers:** a data-regime-break check for C32. Plot ADU counts across each reform date and note any change in how ADUs are recorded.
- **Themes:** all.

### V1. Baseline accuracy (the "what would have happened anyway" engine)

- **Question:** Without any reform, does the baseline forecast hold up through rate and cycle changes?
- **Design:** Fit on data through 2018. Forecast 2019–2025 for **non-reforming** NC places and counties. Repeat with fits ending 2016 and 2020, so one window crosses COVID and one the 2022 rate spike.
- **Benchmarks the baseline must beat:** (a) last-3-year average; (b) a simple trend.
- **Metrics:** mean absolute error per 1,000 parcels; P10–P90 coverage; error by place size (Fay–Herriot shrinkage should help small places).
- **Pass *(proposed)*:**
  - beats both benchmarks on error;
  - coverage 70–90% (below 70% means overconfident; above 90% means too wide to be useful);
  - no systematic bias in the post-2022 window.
- **If it fails:** add rates or regional demand to the baseline explicitly; widen bands; report.
- **Themes:** all. This is the test that answers "was the policy a failure, or were rates too high?"

### V2. Mechanism (feasibility and redevelopment hazard)

- **Question:** Given each parcel's characteristics and prices at a point in time, does the pro forma plus hazard predict which parcels actually redevelop or add units?
- **Design:**
  - **Primary: Portland Metro.** RLIS taxlots have values, year built and sale prices with quarterly archives. Score parcels at a baseline date and observe permits over the next 3 years.
  - **In-state: Wake County.** Use the pre-revaluation December 2023 roll as the baseline state and Raleigh permits from 2024–2026 as outcomes (short window; units from `censuslandusecode`).
- **Metrics:**
  - ratio of total predicted to observed redevelopment;
  - calibration by decile of predicted probability;
  - discrimination (AUC);
  - error by parcel type (lot size, improvement-to-land ratio: C14, C46).
- **Pass *(proposed)*:** total predicted/observed within 0.67–1.5; calibration slope 0.7–1.3; AUC ≥ 0.65.
- **If it fails:** recalibrate the hazard (it is the free parameter, per protocol §5.8). If ranking is poor, the pro forma inputs are wrong. Report which.
- **Themes:** MM mainly; ADU where ADU permits are flagged; fees indirectly (the fee module only works if the pro forma does).

### V3. In-state causal estimates (evidence prong, original)

- **Question:** What did Durham's and Raleigh's reforms actually do, net of confounders?
- **Designs, in order of preference** (see causal diagrams §4 and MM §3):

  | Reform | Primary design | Secondary |
  |---|---|---|
  | Raleigh MM 2021 | Within-city: eligible lots vs **R-1** lots, matched on lot size and value | Synthetic control for Raleigh vs NC/Southeast donors |
  | Raleigh ADU 2020 | Synthetic control; dose by lot size | Event study on ADU-flagged permits |
  | Durham EHC 2019 | Within-city: **urban tier vs suburban tier** | Synthetic control for Durham |

- **Required checks (register IDs in brackets):**
  - flat event-study leads, plus HonestDiD breakdown value [C05, C06];
  - placebo outcome: 20+ unit permits show no break [C04, C07];
  - placebo group: single-family permits on ineligible lots show no break;
  - effect by building type, including single-family rebuilds on eligible lots [C30];
  - concurrent reforms coded and dated (Raleigh MM 2.0, Durham SCAD) [C08];
  - ADU recording consistent across the reform date (from V0) [C32];
  - donor pool audited against the policy inventory [C27].
- **Pass *(proposed)*:** not significance. Each estimate gets a **quality grade**:
  - **A:** all checks pass;
  - **B:** one check fails with a stated bias direction;
  - **C:** more than one fails.

  Only A and B estimates enter the comparables table with full weight; C enters with a flag.
- **Themes:** ADU, MM.

### V4. Backtests (ex-ante prediction of reforms we know the outcome of)

- **Question:** If we had run Lotline the year before each reform, would its range have contained what happened?
- **Design:** For each test place, freeze the model with data only up to the year before the reform, calibrated **without** that place. Predict years 1–5. Unblind and compare.
  - **In-state:** Durham 2019, Raleigh 2020 (ADU), Raleigh 2021 (MM).
  - **Leave-one-place-out across all comparables:** Portland 2010 ADU and 2021 RIP, Seattle 2019, Austin HOME 2023–24, California 2017/2020 ADU, SB 9.
- **Benchmarks:** (a) no effect; (b) the literature mean applied unadjusted (no transport).
- **Pass *(proposed)*:**
  - P10–P90 coverage ≥ 60% across all backtests (with ~10 cases, 80% nominal coverage can't be checked precisely);
  - transported predictions beat the unadjusted literature mean on error.
- **If transport doesn't beat the literature mean:** the effect modifiers aren't doing their job. Simplify to the literature range and say so.
- **Themes:** ADU, MM.

### V5. Blind forward test: Charlotte

- **Question:** The cleanest test available before December: a true out-of-sample prediction.
- **Design:** Calibrate on everything except Charlotte. Predict duplex/triplex units on N1 lots, June 2023–2025. **Freeze and commit by Nov 17.** Then load Charlotte's outcomes (BPS 2-unit and 3–4-unit permits; Mecklenburg permits with `zonecode` = N1).
- **Pass *(proposed)*:** observed falls within P10–P90. With one case this is a demonstration, not proof; we present it that way.
- **Optional:** the same for Greensboro ADUs (2024), BPS only.
- **Themes:** MM (ADU via Greensboro).

### V6. Fee tests

- **V6a, *Carthage* natural experiment (exploratory).**
  - Compile the NC towns that charged water/sewer "future service" impact fees before August 2016 and stopped after the ruling.
  - DiD vs. comparable NC places, Aug 2016 to Oct 2017, with flat pre-trends required.
  - Expect low power (one-year window, modest fee amounts). Report as a bound, not a point estimate.
- **V6b, pro forma threshold test.**
  - Using V2's validated pro forma, compute how many parcels cross feasibility with a $25k cut.
  - Repeat with each place's **real** fee level as the starting point, to show the gap between the Handbook's $50k assumption and reality.
- **V6c, out-of-state bunching (optional, if square footage is available).** California ADUs around the 750 sq ft fee exemption (SB 13, 2020), from LA permits (`SQUARE_FOOTAGE`).
- **Pass *(proposed)*:** V6a pre-trends flat; V6b predicted response falls inside the literature range (0 to +12% single-family, 0 to +18% small multifamily over 5 years). Outside that range triggers a review of λ and ε.
- **Themes:** fees.

### V7. Transport check and second-state stress test

- **Question:** Is the statewide run on solid ground, and does the framework carry to another state?
- **In NC:**
  - Overlap diagnostics for every unreformed NC place against the calibration set: price-to-cost ratio, bindingness, pre-reform permit rate.
  - Places outside the range get a low-confidence flag and more weight on the mechanism prong (protocol §5.5).
- **Second state (TX or OH):** re-run **V0 and V1** only.
  - Data reproduction and baseline accuracy are testable anywhere.
  - Policy effects there are not.
  - This answers the sponsor's "extend to another state" goal (podcast notes) with evidence rather than a claim.
- **Pass *(proposed)*:** V1 criteria met in the second state without code changes beyond a new adapter.
- **Themes:** all.

---

## 4. What each theme gets from the ladder

| Test | ADU | Missing Middle | Fees |
|---|---|---|---|
| V0 data | ✓ (BPS undercount estimate) | ✓ (townhouses hidden in 1-unit) | ✓ (real fee levels) |
| V1 baseline | ✓ | ✓ | ✓ |
| V2 mechanism | partial | ✓ primary | ✓ (via pro forma) |
| V3 in-state causal | Raleigh 2020, Durham 2019 | Raleigh 2021 (R-1 contrast), Durham 2019 (tier contrast) | — |
| V4 backtests | ✓ | ✓ | — |
| V5 blind forward | Greensboro (optional) | **Charlotte** | — |
| V6 fee tests | (SB 13 bunching) | — | ✓ |
| V7 transport, 2nd state | ✓ | ✓ | ✓ |

Fees remain the weakest-validated theme. That is a finding to state, not hide.

---

## 5. Scorecard (what goes in the deliverables)

One table in the Model & Assumptions Overview (Rules §7a, D4) and one slide:

| Test | What was checked | Result | Pass? | What we changed |
|---|---|---|---|---|
| V0 … V7 | | | | |

The tool's interface shows a short "How well has this held up?" note next to each scenario, linking to the scorecard. This serves Transparency (30%) and Methodological Soundness (15%), and it gives judges a concrete answer to "how do you know?"

---

## 6. Timeline (coding opens Oct 14; due Dec 16)

| When | Work | Ladder |
|---|---|---|
| Oct 4–13 | Data scouting (data-availability §4); compile *Carthage* town list; confirm Durham permit freshness; finalize thresholds; draft `docs/analysis_plan.md` | — |
| Wk 1–2 (Oct 14–27) | Adapters for BPS, Raleigh, Durham, Mecklenburg, Portland, Seattle | V0 |
| Wk 2–3 (Oct 21–Nov 3) | Baseline forecast | V1 |
| Wk 3–5 (Oct 28–Nov 17) | Pro forma + hazard | V2, V6b |
| Wk 4–6 (Nov 4–24) | In-state causal designs (after `prereg-v1` tag) | V3, V6a |
| Wk 5–6 (Nov 11–24) | Backtests; **freeze Charlotte prediction by Nov 17** | V4, V5 |
| Wk 7 (Nov 25–Dec 1) | Unblind Charlotte; overlap diagnostics; second-state V0–V1 | V5, V7 |
| Wk 8–9 (Dec 2–16) | Scorecard, write-up, slides | §5 |

**Critical path:** V0 adapters, then V1 and V2 in parallel. V3 can slip without blocking the statewide run. V1 and V2 cannot.

---

## 7. If the target is not North Carolina

| State | In-state treated places | What changes |
|---|---|---|
| **TX** | Austin HOME (Dec 2023/May 2024; ~2.5 yrs post); Houston lot-size reforms (1998, 2013) | Austin permits are excellent (ADU class R-102, completions, demolitions), so V3–V4 work. Non-disclosure state: V2 must use appraisal values, not sale prices. No *Carthage*-style fee shock identified. |
| **OH** | Columbus Zone In (2024), Cincinnati Connected Communities (June 2024) | Post-periods ~2 years: V3 weak, V5 possible. Franklin County Auditor has monthly parcel archives since 2014, which makes V2 strong. |

In either case, V0, V1, V2 and V7 run unchanged; V3–V5 depend on in-state reforms.

---

## 8. Decisions needed

1. Approve the ladder and the *(proposed)* thresholds, or adjust them.
2. Confirm NC as target (this plan's assumption).
3. Agree the integrity rules in §2, especially freezing predictions before unblinding.
4. Decide whether the tool shows results against real local fees as well as the Handbook's $50k (fees doc §5).
