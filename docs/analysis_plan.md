# Lotline: Analysis plan (pre-registration)

**Status: DRAFT, not yet pre-registered.** Per the validation plan (§2, integrity rule 1), §3 of
`docs/research/lotline-validation-plan.md` (tests and pass/fail criteria) is copied here, reviewed by Ben, committed
and tagged `prereg-v1` **before any V3 outcome model runs**. Until then this file only records decisions made
ahead of pre-registration, so they aren't lost.

## Decisions and deviations log

Dated, append-only. Each entry says what changed from the research documents, why, and who decided.

### D-001 · 2026-10-06 · V0 BPS reconciliation tolerance
- **Was (validation plan §3, V0, proposed):** "BPS totals match exactly."
- **Now:** our BPS place sums must be **within 1% of Census's state total in every compared year**; years outside
  1% are listed in the V0 report for explanation. Exact matches are still counted and reported.
- **Why:** Census revises state and county totals after the annual survey with late reports and corrections that
  the place files don't always carry (Census BPS methodology), so exact agreement isn't achievable even with a
  correct pipeline. First run (2026-10-06): exact match MN 10/32, NC 28/31, OH 20/34, TX 6/34 years; within 1%
  MN 30/32, NC 29/31, OH 34/34, TX 21/34. The check is read as directional evidence that the pipeline counts what
  Census counts.
- **Decided by:** Ben, 2026-10-06 (PR #66).
- **Open:** Texas 2003–2014 runs 1–2% high (Denton County unincorporated, 2014); for WS-TX to explain.

### D-002 · 2026-10-14 · V1 baseline specification B (variance floor from a place's own history)
- **Was (WS-ENGINE spec A, declared before the first run):** a place's level and its uncertainty from its last 5 years only.
- **Now (spec B):** the same, plus a floor on a place's year-to-year variance from its own longer history, so a one-off subdivision year in a tiny township isn't read as its normal pace.
- **Why / how decided:** added **after** the first Minnesota run showed the problem. It is logged here as a deviation for that reason. On the V1 windows, A passes 19 of 48 cells and B 17, but B has 13% lower error for 5+ unit buildings. Both are reported (PR #93).
- **Decided by:** Ben, 2026-10-14.

### D-003 · 2026-10-14 · V1 coverage uses randomized coverage for whole-number outcomes
- **Was (validation plan V1):** "P10–P90 coverage 70–90%", read as the share of outcomes inside the interval.
- **Now:** randomized (probability-integral) coverage. For counts that are mostly 0, the inclusive check reads ≥90% almost everywhere and flatters any model. The inclusive share is still reported.
- **Decided by:** Ben, 2026-10-14 (PR #93).

### D-004 · 2026-10-14 · V1 bias is judged on the model's mean
- **Was:** "no systematic bias in the post-2022 window" (statistic unspecified).
- **Now:** mean signed error of the model's **mean** forecast (not its P50) for 2023 on, within ±25% of the model's post-2022 MAE. Means add up to state totals; medians of skewed counts don't.
- **Decided by:** Ben, 2026-10-14 (PR #93).

### D-005 · 2026-10-14 · V1 scores only places with at least 20 eligible parcels
- **Was:** every non-reforming place scored.
- **Now:** places with fewer than `v1_min_eligible_parcels` = 20 eligible parcels at the forecast origin are still forecast (and rolled into their county for reporting) but left out of V1 scoring: a few lots swing their rates for every method.
- **Effect (2026-10-14 run):** still 17 of 48 cells pass. Single-family model MAE 10.08 vs 9.66 for the 3-year mean, so the model now loses on single-family. 5+ units: 2.82 vs 3.29 (3-year mean) and 3.94 (trend).
- **Decided by:** Ben, 2026-10-14 (PR #93).

### D-006 · 2026-10-14 · Pre-declared next V1 specification: two demand signals (before any run)
- **Why:** every method under-forecasts NC and TX single-family building in 2023–25 (model mean 70–87% of observed). Recent pace alone can't anticipate a demand surge.
- **Specification C, fixed now, run once:** spec B with the place's level multiplied by `exp(β_h · g + β_p · q)`, where
  - `g` = growth of occupied housing units in the place's county: ACS B25003_001 for the 5-year window ending at the forecast origin vs the **non-overlapping** window ending 5 years earlier, annualized;
  - `q` = FHFA house-price change over the 3 years to the origin, from the panel's fallback chain (county → CBSA → state non-CBSA → state), annualized;
  - `β_h`, `β_p` are estimated by pooled Poisson regression on **fit years only** (all years ≤ origin, within state), never on the forecast years;
  - no other changes; same windows, parameters and pass criteria (D-003 to D-005).
- **Reporting:** spec C is compared with spec B and both benchmarks in every cell. Whichever passes more cells is not automatically adopted; Ben decides, and the choice is logged as D-007.
- **Decided by:** Ben, 2026-10-14 (choice of signals proposed by Claude Code, approved before running).

### D-007 · 2026-10-15 · Baseline stays spec B; spec C (demand signals) not adopted
- **Compared (PR #95, both runs from `python -m lotline.model.backtest --spec B|C`, fits ending 2016/2018/2020,
  MN NC OH TX):** B and C each pass 17 of 48 V1 cells. Single-family MAE 10.08 (B) vs 10.01 (C); 5+ units 2.82
  vs 2.92. NC/TX single-family post-2022 bias of the mean −8.00/−11.08 (B) vs −7.16/−9.53 (C); every NC/TX
  single-family cell still fails under both.
- **Decision:** keep spec B as the baseline. C's gain is small, it is worse for 5+ units, and its fitted
  coefficients are unstable (signs flip across states and windows; |β| up to 66 for 2–4 unit buildings, where
  household and price growth are correlated).
- **Kept for reproducibility:** spec C remains available as `--spec C` (default B).
- **Open:** a more stable demand form (one combined signal, or a statewide cycle term), pre-declared before
  any run, to address the NC/TX single-family under-forecast.
- **Decided by:** Ben, 2026-10-15.

### D-008 · 2026-10-19 · Repeated project totals counted once
- **Was:** permit units summed as each city reports them (WS-OH Columbus and Cincinnati adapters, PRs #106/#112).
  Several city files put a multi-building project's **total** on every building's permit: Columbus 2023, nine
  permits on one parcel each say 198 units; Austin 2022, nine permits on one parcel each say 280.
- **Now:** when permits are counted (`lotline.build.permits.count_units`), if at least
  `repeated_total_min_permits` = 3 new-construction permits on the same parcel, jurisdiction and year all report
  the same count of at least `repeated_total_min_units` = 50 units, that count is counted **once** (on the lowest
  `permit_id`); the others count 0. Demolitions and permits with no parcel are never grouped. The adapters'
  tables stay as reported.
- **Parameters:** `config/params/permits.yaml` (ranges 20–100 units, 2–5 permits).
- **Sensitivity, both ways:** the rule on is the primary count; `dedupe=False` gives the as-reported count, and
  both are shown wherever permit counts are compared or used.
- **Effect (2026-10-19, 5+ units vs BPS):** Columbus 2023 1.41 → 1.02 of BPS; Austin 2022 1.42 → 1.25. Over
  2018–2025 the rule removes 1,963 units (13 permits) in Columbus and 4,167 (31) in Austin; none in Cincinnati,
  whose excess over BPS has a different cause (open).
- **Why:** counting a project nine times overstates multifamily building, the outcome most reforms target.
- **Decided by:** Ben, 2026-10-19.
- **Amended by:** D-036 (2026-10-26), which extends the rule to permits with no parcel.

### D-009 · 2026-10-19 · Pro forma specification choices the research docs leave open
- **Research docs (methods review §2a, register C43/C46/C48/C54):** feasible when value − (hard + soft + fees +
  financing + target profit) ≥ existing-use value × (1 + margin); code step at 3+ units; fee carry depends on
  payment timing. They don't say what the profit is measured on, or how the code step and fees enter.
- **Chosen (`src/lotline/model/proforma.py`, `config/params/proforma.yaml`):**
  - profit = margin × finished value (not × cost), so a fee change moves residual land value one-for-one, plus
    interest when fees are paid at permit (`fee_paid_at_permit`). The register's NZ hurdles (17–25% on cost)
    are converted to value (h / (1 + h) ≈ 15–20%);
  - the code step is a percentage added to hard cost per sq ft for triplexes, fourplexes and 5–6 unit
    buildings, with a longer build time; townhouses stay under the residential code; a switch
    (`triplex_under_irc`) covers places such as Austin (PM2024-0002) that let triplexes use it;
  - land capture λ enters as the share of a fee cut that does not reach builders (fees causal diagram,
    (1 − λ)); the "revenue replaced" toggle (C51) is left to `model/scenarios/fees.py`, since it acts on
    infrastructure capacity, not on project cost;
  - an ADU keeps the house, so its existing-use value is 0.
- **Why:** the simplest forms that match the docs' equations and keep each line checkable by hand.
- **Reporting:** a fee cut is reported both as the cut itself (exactly $25,000 per unit when fees are paid at
  completion) and with the interest saved when fees are paid at permit.
- **Decided by:** proposed by WS-ENGINE; accepted by Ben, 2026-10-19 (the "approx." parameter values are to be
  checked against their sources in a follow-up PR before V2 uses them).

### D-010 · 2026-10-19 · Fee elasticity re-anchored to the evidence register; low end 0
- **Research docs (methods review §3c; fees causal diagram):** ε 0.5–3, central 1.5, with a note that E081
  argues for the low end and that the low case must include zero. The central value had no study behind it,
  and the high case (3 × 0.75 × ~7% ≈ +16%) fell outside the V6 pass band (judging panel MS-03).
- **Chosen (`config/params/fees.yaml` `fee_permit_elasticity`):** central **0.3** (E081, tract-level unit
  elasticity), low **0** (E058 and E062: fee effects not significant), high **1.75** (E080 and E082, metro-wide
  supply elasticities). E059/E060 (non-water/sewer fees can raise building) are handled by the revenue-replaced
  toggle in `scenarios/fees.py`, not by a negative ε.
- **Cost to price:** the studies estimate elasticities with respect to price. For the project at the margin of
  feasibility, price ≈ total development cost (land included), so a fee cut of (1 − λ) × Δfee reaching
  builders acts like a price rise of (1 − λ) × Δfee / TDC. The formula %Δ permits = ε × (1 − λ) × Δfee / TDC ×
  ramp(t) is unchanged; it slightly overstates the effect where projects earn above-normal profit.
- **Effect:** at an illustrative TDC of $350k (the $25k cut ≈ 7%), central ≈ +1% and high ≈ +9% single-family
  permits over 5 years, inside V6's 0 to +12% band (test: `test_fee_elasticity_range_includes_zero_...`).
  No results change yet: no model code reads ε. The V6b pro forma route remains the primary fee estimate; ε is
  the fallback where parcel data are missing.
- **Decided by:** Ben, 2026-10-19 (accepting MS-03 via the coordinator).

### D-011 · 2026-10-19 · Baseline cycle: shared calendar years, and centred so the mean stays flat
- **Was (`model/baseline.py`):** the cycle shocks were demeaned (x − mean x) and resampled from the same
  random-number stream as the per-place draws, after them. Two problems (judging panel MS-06, MS-07):
  (a) which cycle years a draw got depended on how many places were in the run, so single-family and 5+ unit
  draws were coupled or not by accident; (b) E[exp(Σ shocks)] > 1, so the mean drifted up with the horizon
  (about +6% by year 5).
- **Now:** (a) one matrix of resampled calendar years per state, origin and draw (`cycle_years`, seeded by
  simulation seed, state and origin only), shared by every size class and scenario; a size class with no
  change for a drawn year takes another of its years. (b) shocks centred by log(mean(exp(x))), so each
  year's factor averages 1 and the mean stays flat when nothing changes. Tests: `test_cycle_keeps_the_mean_
  flat_over_the_horizon`, `test_cycle_coupling_does_not_depend_on_which_places_are_present` (both fail on
  the old code).
- **Effect on V1 (spec B, MN NC OH TX, run 2026-10-19):** **17 → 13 of 48 cells pass.** All of it comes
  from (b): with (a) alone the run is unchanged (17 cells; model MAE 10.084 / 0.368 / 0.196 / 2.824 for
  1 / 2 / 3–4 / 5+ units vs 2.822 before for 5+). With both: beats benchmarks 40 → 41 cells, coverage OK
  33 → 32, **bias OK 26 → 21**; MAE 10.08 → 10.13 (single-family), 0.368 → 0.367, 0.196 → 0.193,
  2.82 → 2.77 (5+). The six flipped cells (MN 2018 1, 2; MN 2020 3–4, 5+; TX 2018 5+ fail now; MN 2018 3–4
  passes now) all turn on the bias test, which judges the mean (D-004). The model already under-forecasts
  after 2022; the old upward drift of the mean was partly hiding that.
- **Why:** the old pass count leaned on an artefact. The under-forecast after 2022 is now visible and is
  the thing to address (e.g. state momentum or spec C), not to tune away here.
- **Decided by:** Ben, 2026-10-19 (accepting MS-06 and MS-07 via the coordinator); the drop to 13 of 48 is
  for Ben to note in the PR.

### D-012 · 2026-10-19 · Charlotte holdout extended to Mecklenburg County BPS rows (disclosed leak)
- **Found:** BPS has no Charlotte place row. Charlotte-Mecklenburg Code Enforcement reports Charlotte's permits, and the Mecklenburg towns', under Mecklenburg County (37119). The V5 holdout filtered only Charlotte's place GEOID (3712000), so the 2023–2025 rows for 37119, which carry Charlotte's post-UDO outcomes, were not held out. Found by WS-NC while building parcels (#123), confirmed by WS-CORE.
- **Where they went:** the processed NC `bps_place_year` table and therefore the V1 backtests (D-002 to D-007), whose NC scores for windows reaching 2023–2025 include these rows in aggregate. No Charlotte- or Mecklenburg-specific outcome figure was printed, plotted or reported; V0 never compared NC years from 2023 on (held-out years are skipped by date window). The V5 Charlotte prediction has not been made, so it can't have been tuned to them.
- **Fix:** holdouts can name `reporting_geoids`, held out over the same window; Charlotte names 37119 (`config/states/nc.yaml`). Holdout places are always jurisdictions in their own right (`build/jurisdictions.local_geoids`), so no adapter can relabel their rows as the county's. The processed NC BPS table was rebuilt: 37119 now ends in 2022. Mecklenburg towns' 2023+ outcomes are hidden too (the cautious side).
- **Consequence:** NC V1 results that used 2023–2025 must be re-run with the rebuilt table and reported with this note; the V5 Charlotte test proceeds, with this disclosure in its report.
- **Decided by:** Ben, 2026-10-19 (fix and disclose).
- **Re-run note (2026-10-20, WS-ENGINE):** V1 spec B re-run on the rebuilt tables (`python -m lotline.model.backtest
  --state MN NC OH TX --spec B`, eligibility rule 1.1): **17 of 48 cells pass** (was 13 after D-011);
  beats benchmarks 39 (was 41), coverage OK 34 (32), bias OK 25 (21). Model MAE by size class 11.62 / 0.370 /
  0.188 / 2.13 for 1 / 2 / 3–4 / 5+ units (was 10.13 / 0.367 / 0.193 / 2.77). Passes by state: MN 6, NC 2,
  OH 6, TX 3. The change cannot be pinned on D-012 alone: since D-011 the same run also picked up rule 1.1
  denominators (D-014), the ACS fallback for rolls with unknown land use (D-017), one GEOID per BPS ID (#158)
  and new full parcel rolls. Rates are per eligible parcel, so denominator changes move every state's MAE
  (single-family MAE rose in all four states). The backtest's `--rule-version` default now follows
  `build.eligible.RULE_VERSION` (it was pinned to 1.0, which no longer exists).

### D-013 · 2026-10-19 · St. Paul post-reform figures removed from a research doc (disclosed exposure)
- **Found:** the judging panel (2026-10-19) flagged that `docs/research/lotline-mn-scouting.md` quoted St. Paul's post-reform outcome counts for held-out years (from a public Minneapolis Fed article), written during scouting before the holdout rules existed.
- **Fix:** the figures were replaced with a note; WS-CORE made the edit with the line masked and did not read them. They remain in git history and in the public source; the history is not rewritten.
- **Consequence:** the people and agents building Lotline may have seen these figures before the V5 St. Paul prediction is frozen. The V5 prediction must not use them, and its report will disclose this exposure. The test remains a forward test of the model, which has no access to them.
- **Decided by:** Ben, 2026-10-19.

### D-014 · 2026-10-19 · Missing-middle eligibility includes vacant single-family-zoned lots (rule 1.1)
- **Was (rule 1.0):** a parcel was eligible for missing middle only if it held an existing single-family house (at most one unit) on single-family-only zoning, the same building test as ADUs.
- **Now (rule 1.1):** missing middle also counts **vacant residential lots** on single-family-only zoning. The Handbook defines the scenario as "2–6 units on single-family-only parcels"; only the ADU definition requires an existing single-family building.
- **Why:** the judging panel's methodology review (MS-02, 2026-10-19). Vacant lots carry the lowest existing-use value, so they are where small multi-unit buildings are most likely to pencil; leaving them out understated the missing-middle denominator and departed from the Handbook definition.
- **Limits:** where a jurisdiction has no usable parcels, the ACS fallback (one-unit detached homes) has no vacant land, so its missing-middle denominator still excludes vacant lots; those denominators are already `low` quality.
- **Decided by:** Ben, 2026-10-19.

### D-015 · 2026-10-19 · Places below 20 eligible parcels are not published on their own
- **Rule:** results for a place with fewer than `min_eligible_parcels_publish` eligible parcels (20; range 10–50; `config/params/aggregate.yaml`) are folded into its county or region in the tool and reports, never shown by themselves.
- **Why:** the judging panel's transparency review (TR-07, 2026-10-19). Small places have rates too noisy to read, and so few parcels that a result could point at individual properties. 20 matches the V1 scoring floor (D-005).
- **Decided by:** Ben, 2026-10-19.

### D-016 · 2026-10-19 · Data tiers follow the loaded parcels
- **Was:** every jurisdiction was tier 3 (national data only) unless a state config listed it by hand; none did, so Austin, Columbus and Cincinnati, which have parcel rolls, were labelled tier 3.
- **Now:** `build/jurisdictions.tiers_from_parcels` assigns tiers from each jurisdiction's latest roll. Tier 1: land use known for at least 90% of parcels and year built for at least 80% of built parcels; tier 2: land use only; tier 3 otherwise (`config/params/tiers.yaml`; tier definitions from the state briefs and BUILD_PLAN §5). `data_tiers` in a state config still overrides.
- **Why:** the Model & Assumptions draft (#135) found every jurisdiction at tier 3; tiers drive how results are labelled and how wide their ranges are.
- **Decided by:** Ben, 2026-10-19.

### D-017 · 2026-10-20 · Parcel rolls with mostly unknown land use use the ACS denominator
- **Found:** with Ohio's statewide parcels (#150), Summit County sends no land use, so Akron's roll counted **0 eligible parcels rated `high` quality**: parcels of unknown use are never eligible, and the quality share counted only unknown units, lot size and zoning. Lucas County (55% unknown) gave Toledo a large undercount.
- **Now:** a jurisdiction-roll is used as a parcel denominator only if its land use is known for at least `tier2_min_land_use_share` (0.9, the tier 2 threshold from D-016) of its parcels; otherwise that jurisdiction uses the ACS fallback (`build/eligible.usable_rolls`). On Ohio's 2023 rolls this moves 18% of parcels, including all of five counties (Hardin, Lucas, Meigs, Muskingum, Summit at jurisdiction level), to the fallback.
- **Decided by:** Ben, 2026-10-20.

### D-018 · 2026-10-20 · ADU hazard: functional forms the research docs leave open
- **Research docs:** the two-prong design and protocol §5.5–5.8 say the mature hazard comes from comparable
  places and is transported by effect modifiers (price-to-cost first, C22 equity and rates for ADUs), with a
  ramp over event time and no silent extrapolation. They don't give the functional forms, the reference place
  or how to widen outside the comparables' range.
- **Chosen (`src/lotline/model/hazard.py`, `config/params/hazard.yaml`):**
  - anchor: 4 ADU permits per 1,000 eligible lots a year (2–5), the adu-study-design calibration band, with
    **Portland 2015–19** as the reference place (ACS 2015–19 rent and value, `scripts/dev/adu_reference.py`);
    the comparables pooling of protocol §5.7 is not built yet, so this is the band, not a fitted posterior;
  - price-to-cost enters through the **share of lots that pencil**, F = Φ((ln PCR − ln(1 + margin)) / σ), a
    lognormal spread of lot-level ratios around the place's ratio; uptake among lots that pencil is the same
    everywhere (u = h_ref / F(PCR_ref)). This makes uptake rise with profit, stay a probability and match the
    anchor at the reference;
  - reference and target share the same cost parameters (national hard cost), so with national costs only
    rent (and home value, rates) transports; Portland's higher local costs are not netted out (open);
  - equity as a power of median home value and rates as an exponential in the mortgage rate, both judgment
    with ranges that include no effect;
  - logistic ramp in years since adoption, half-way at 2 years;
  - calibration range = the span of Portland, Seattle and Los Angeles (rent, home value) and 2015–23 (rates);
    outside it the hazard gets mean-preserving lognormal noise with log-sd = w × log distance (w = 1).
- **Why:** the simplest forms that use the pro forma, keep each step checkable by hand and make extrapolation
  visible. The fitted comparables model (protocol §5.7) can replace the anchor and σ later without changing
  the interface.
- **Decided by:** proposed by WS-ENGINE, 2026-10-20; for Ben to confirm in the PR.

### D-019 · 2026-10-20 · ADU scenario: increment over current rules, additionality, and a first check against observed ADUs
- **Research docs:** the Handbook defines the scenario (one ADU per eligible single-family parcel, ≥600 sq ft,
  no parking); the protocol (§5.10) asks for net-new and formalization adjustments; the judging panel asked for
  the increment over existing local rules (MS-01), a wider net-new range and a formalization share (MS-09), and
  additionality for ADUs already counted as 1-unit permits (MS-10). How to combine these is left open.
- **Chosen (`src/lotline/model/scenarios/adu.py`):**
  - current rules from the coded reforms in force at the origin: Handbook-equivalent (c = 1), partial (owner
    occupancy, parking, discretionary, attached only or a cap under 600 sq ft: c = `adu_partial_rule_share`
    0.3, judgment) or none (c = 0); uncoded rubric fields count as not restrictive and are listed;
  - the Handbook adds (1 − c) × h_m × ramp(t) on top of the current rule's own ramp; observed ADU rates
    (2019–22, where permits flag ADUs) are a floor under both paths, so ADUs already built are never "added";
  - a separate pool of parcels without an ADU under each set of rules (at most one ADU per parcel);
  - `adu_net_new_share` low end 0.50 → 0.45 (E039 ≈ 48%); new `adu_formalization_share` 0.10 (0–0.30,
    judgment from E049, E050); new `baseline_adu_share_of_one_unit` 0.033 (0.0047 Twin Cities metro – 0.0765
    Austin, `scripts/dev/adu_baseline_share.py`);
  - forward runs draw a flat 2026–30 mortgage rate from `mortgage_rate_forecast` (6.60%; 2.96–6.81%, the
    2015–25 annual range as a stress range, `market.yaml`); validation uses each year's actual rate;
  - where a place's only parcel roll is after the origin (Austin's 2026 roll), that roll is used and flagged
    (a denominator, not an outcome).
- **First check against observed ADUs** (`scripts/dev/adu_current_rules_check.py`, 2016–22, before every
  holdout window, actual rates, central-parameter draws; raised by WS-CORE on #161). Model ADU permits under
  each place's coded current rules vs observed: **Minneapolis 315 vs 179 (1.8x)**, **Raleigh 172 vs 81
  (2.1x)**, **Austin 4,230 vs 2,302 (1.8x)** (Austin's ADU rules are not coded; treated as mature). The
  closer fit in Minneapolis before 2021 rests on the judgment partial share (0.3) under its owner-occupancy
  rule; after the rule was dropped (2021–22) Minneapolis built 16–17 a year, against a mature Handbook hazard
  of 2.71 per 1,000 parcels (~200 a year): an order of magnitude. Austin, inside the calibration range on rent
  (distance 0), builds 1.98 per 1,000 a year against the model's 4.06. Durham could not be checked: its
  ADU-eligible parcel count is 5 (a denominator fault, reported to WS-NC/WS-CORE).
- **Reasons, in the order the evidence supports them:** (1) the anchor: Portland's ~4 per 1,000 is gross,
  includes formalization and a $7–12k fee waiver (E047) and long-built ADU know-how (C24); Austin and Raleigh,
  post-reform and with rents near or inside the range, run at about half of it; (2) transport through rent
  alone: with national construction costs, Minneapolis's price-to-cost (1.0) is only 11% below Portland's, so
  σ = 0.5 lowers its hazard by ~20%, far less than observed; local costs (climate, foundations) and lot or
  design rules (size, setbacks, internal ADUs keeping owner occupancy) are not in the model; (3) Minneapolis's
  rule coding leaves size and parking uncoded, so "Handbook-equivalent" may overstate its rules.
- **Superseded proposal:** a hand-set anchor of 0.002 was proposed here and **declined by Ben (2026-10-20)**:
  a hand-picked anchor is arbitrary. Instead the anchor is estimated from Lotline's own post-reform data with
  the pre-registered split below.
- **Pre-registration (written and committed before any fit was run, 2026-10-20):**
  - *Quantity:* `adu_mature_hazard_ref` (θ, the reference place's mature ADU permits per eligible parcel a
    year), estimated on the log scale. Expected count for place i in year y: μ = θ × k, with
    k = eligible parcels × (mature hazard at θ = 1, from that year's ACS rent and value, newest vintage ≤ y,
    2025 dollars, and that year's actual mortgage rate) × the largest c × ramp(years since effective, at
    mid-year) over the coded ADU rules in force (`config/reforms/*.csv`, read at run time) — the scenario's
    current-rules path without the observed floor (the floor would make the fit circular). All other
    parameters at their central values.
  - *Likelihood:* negative binomial, Var = μ + αμ², α estimated (Poisson when α → 0).
    `adu_partial_rule_share` is estimated jointly only if its 90% profile interval is narrower than its
    judgment range (0.1–0.6); otherwise it stays at 0.3 (judgment) and the report says so.
  - *Interval:* 90% profile-likelihood interval for θ (α, and s if estimated, profiled out); it becomes θ's
    low–high range in `hazard.yaml`.
  - *Observed counts:* ADU permits per place-year, the larger of the flagging sources each year (Met Council or
    city), from holdout-filtered tables. A place-year enters only if a coded ADU rule is in force by 1 July and
    its permit source flags ADUs that year.
  - *Fit set:* Minneapolis 2016–2025; every other Twin Cities place with a coded ADU rule, 2016–2025 (Met
    Council flags from 2016); Austin 2016–2023 once its ADU rules are coded (its 2024–25 counts, 90 and 9, look
    incomplete and are excluded in advance).
  - *Test set:* Raleigh 2021–2025 (rule in force from July 2020); Durham once its eligible-parcel count is
    fixed. Reported: observed vs predicted (median and 90% interval from a parametric bootstrap: log θ normal
    from the profile interval, NB counts) per year and in total.
  - *Never used:* St. Paul (V5, all years), Charlotte (V5), any held-out row.
  - *Decision rule:* the fitted θ and interval replace the anchor whatever the test shows; a test total outside
    its 90% interval is reported as a transport failure, not refitted.
- **Results of the pre-registered fit (run 2026-10-20 after the pre-registration commit fd21217;
  `scripts/dev/calibrate_adu.py`):**
  - *Data used:* fit set = Minneapolis (2016–25) and 10 Twin Cities suburbs with coded ADU rules (Apple
    Valley, Blaine, Bloomington, Eagan, Edina, Maplewood, Minnetonka, Plymouth, Roseville, St. Louis Park):
    64 place-years, 243 ADU permits, 222 of them Minneapolis's. Austin is not in it: its ADU rules are not
    coded yet (the pre-registered rule). Test set = Raleigh 2021–25. Durham is not tested: the roll the test
    would use has 5 ADU-eligible parcels.
  - *Partial-rule share:* profile maximum at s = 1.00, 90% interval 0.26–1.00, wider than the judgment range,
    so **not identified; kept at 0.3 (judgment)**.
  - ***Anchor: θ = 0.000467 per parcel a year, 90% profile interval 0.000275–0.000868*** (0.47 per 1,000; α =
    6.6). Written to `hazard.yaml` as value and range, per the decision rule.
  - *Test (Raleigh 2021–25):* observed 230; predicted mean 112, median 62, 90% predictive interval 2–445.
    Inside, so not a transport failure by the pre-registered rule, but the interval is wide because α is large
    and the mean is half of what Raleigh built.
  - *Cross-check with Portland (4 per 1,000; E046, E047):* the estimate is 0.12 of it. Reasons, none of which
    the fit can separate: Portland's count is gross permits, including legalized units (formalization, E049)
    and a $7–12k fee waiver from 2010 (E047); Portland's higher construction costs are not netted out (the
    model uses national costs for both); "per 1,000 lots" in the Portland figure is undefined (E022; protocol
    §0); and the fit set is mostly one Midwestern city plus suburbs whose ADU rules remain restrictive.
  - *Misfit, reported not fixed:* with s held at 0.3 the fitted path underpredicts Minneapolis 2016–20 (under
    its owner-occupancy rule: about 30 a year observed vs 2–8 fitted) and overpredicts it from 2023 (13–16 vs
    13–21). The current-rules check with the new anchor gives 0.3x observed in Minneapolis (45 vs 179,
    2016–22), Raleigh (24 vs 81) and Austin (592 vs 2,302, rules uncoded). Heavily restricted suburbs (permits
    by conditional use, owner on site, extra parking, occupant caps) with no ADUs carry the same s = 0.3 as
    Minneapolis's lighter rule and pull θ down.
  - *Exploratory, not pre-registered and not used:* treating Austin's uncoded rules as mature
    Handbook-equivalent adds 2,545 permits; then s is identified (0.22, 0.10–0.56) and θ = 0.000779
    (0.000400–0.001751); Raleigh 230 vs mean 187 (90% 8–704). WS-CORE notes Austin's rules cover SF-3 lots of
    5,750+ sq ft only, so this overstates Austin's coverage (D-021 proposal).
  - *Effect on the development run* (origin 2025; five-year sums of place means, added ADU permits / additional
    homes): MN 1,362 / 753; NC 2,088 / 1,154; OH 1,584 / 876; TX 7,859 / 4,340 (with the 0.004 band anchor
    they were 9,607, 17,561, 10,722 and 54,180 permits; NC also falls through D-020).
- **Next specification (to be pre-registered before it is run, not run here):** a partial-rule share graded
  by the number of Handbook conditions a rule fails, rule coverage (D-021), and a place random effect in place
  of a single α; refit when Austin's rules are coded and Durham's roll is fixed.
- **Fit 2 pre-registration (written and pushed before fit 2 was run, 2026-10-20; follows D-022):**
  - *Unchanged from fit 1:* quantity θ, NB likelihood, 90% profile interval, fit and test sets, the
    partial-share rule (estimated jointly only if its 90% interval is narrower than 0.1–0.6), the decision
    rule (fit 2's θ and interval replace fit 1's in `hazard.yaml` whatever the test shows).
  - *Blank rubric fields are integrated, not dropped:* a place-year whose rule class depends on blank fields
    enters with a two-component mixture, P(y) = q·NB(y; θ·k_A) + (1 − q)·NB(y; θ·k_B), where path A has those
    rules restricted (partial) and path B Handbook-equivalent, and q = 1 − Π(1 − p_field) with p_field the
    coded share restricting that field (`scenarios.adu.field_probabilities`, coded rules in force at the
    fit's run date, state share if 5+ values, else pooled). All rules of one place-year that depend on blanks
    move together (amendments share their resolved fields). Dropping them instead would remove Minneapolis's
    2021–25 years and most suburbs.
  - *Place-years with no coded rule* stay out of the fit (as in fit 1); *explicit "no ADUs"* place-years have
    an expected count of 0 and are left out, with any observed ADUs there reported.
  - *Parking:* a citywide parking reform with a zero minimum in force by 1 July fills a blank ADU parking
    field (D-022).
- **Fit 3 pre-registration (written and pushed before fit 3 was run, 2026-10-20; Ben's next specification):**
  - *Fit set:* Minneapolis, the Twin Cities places with coded ADU rules (St. Paul never), and **Austin
    2016–2023** (its rules are now coded; 2024–25 excluded as before). Place-years need a coded rule in force
    by 1 July and permits that flag ADUs that year. *Test set:* Raleigh 2021–25 and Durham 2021–25 if every
    roll the test uses has 1,000+ ADU-eligible parcels (after the NC rebuild). Never: St. Paul, Charlotte,
    any held-out row.
  - *Expected count:* μ_it = θ × u_i × parcels × h_m(θ = 1; that year's rent, value, actual rate) × max over
    the rules in force of c(type) × coverage × ramp(age at mid-year). Rule types (D-022): Handbook c = 1;
    owner occupancy only c = m_o; other restrictions (parking, not by right, attached only, cap under 600 sq ft)
    c = m_x; both c = m_o·m_x. Coverage per D-021 (zones, lot minimum; judgment shares where parcels can't
    measure it).
  - *Place effects:* yes. u_i ~ Gamma(mean 1, variance α), shared across a place's years, with counts Poisson
    given u_i (closed-form marginal likelihood per place). This replaces fit 2's per-year NB, whose large α
    (7.5) reflected differences between places, not years.
  - *Blank rubric fields (D-022):* integrated at place level: each place's blank fields restrict or not
    together over its years, with probabilities from the coded rules (state share if 5+ values, else pooled);
    the place likelihood is the probability-weighted sum over those combinations.
  - *Parameters:* θ (log scale), α, m_o, m_x. m_o and m_x on a grid 0.1, 0.2, …, 1.0; each is estimated if its
    90% profile interval (others profiled) is narrower than its judgment range (m_o 0.2–1.0, m_x 0.1–0.6),
    else held at its judgment value (m_o 0.5, m_x 0.3). θ's 90% interval: profile likelihood with α and any
    estimated share profiled out.
  - *Test prediction:* parametric bootstrap: log θ normal from its interval, a new u per test place, a
    blank-field combination per place, Poisson counts per year; observed vs median and 90% interval per year
    and in total.
  - *Decision rule:* θ, α (as `adu_place_effect_variance`) and any estimated share replace the configured
    values whatever the test shows; a test total outside its 90% interval is reported as a transport failure,
    not refitted. The scenario draws a new u per place in each simulation draw from the fitted α.
- **Fit 2 results (run 2026-10-20 after the fit-2 pre-registration, commit f5ee618):** the first run read
  every observed count as 0 (a variable-name bug in `place_years` overwrote the observed counts with the field
  counts); it was discarded, the bug fixed with a regression test, and the same specification re-run once:
  θ = 0.000790 (90% 0.000526–0.001255), α = 7.5, partial share not identified (0.06–1.00, kept at 0.3); Austin
  entered the fit set through WS-TX's coding (2,545 permits, fitted 306); Raleigh 230 vs mean 127 (90% 1–499).
  Superseded by fit 3.
- **Fit 3 results (run once on 2026-10-20 after the fit-3 pre-registration, commit 4aa1113, and the NC rebuild
  that fixed Durham):**
  - *Data:* fit set 16 places, 115 place-years, 2,799 ADU permits (Minneapolis 222, Austin 2016–23 2,545,
    14 suburbs 32); test set Raleigh and Durham 2021–25 (Durham's roll now has 67,180 ADU-eligible parcels).
  - ***θ = 0.001038 per parcel a year, 90% profile interval 0.000453–0.003173*** (0.26 of Portland's 4 per
    1,000); place-effect variance α = 4.735; ***m_o = 1.0 (0.9–1.0), estimated***; m_x not identified
    (0.1–1.0), kept at 0.3. Written to `hazard.yaml` (anchor, `adu_place_effect_variance`) and `adu.yaml`
    (`adu_owner_occupancy_share`) per the decision rule.
  - *Fitted place multipliers:* Austin 10.95, Edina 1.30, Minnetonka 1.29, Minneapolis 0.50, Richfield and
    Roseville 0.39, Burnsville 0.33, Plymouth 0.15, Bloomington 0.06, Blaine 0.02, Eagan, Lakeville and St.
    Louis Park ≈ 0.
  - *Minneapolis by year, observed vs typical-place mean:* 2016 28 vs 15.1; 2017 30 vs 29.6; 2018 25 vs 39.3;
    2019 35 vs 47.4; 2020 28 vs 56.0; 2021 16 vs 60.2; 2022 17 vs 53.0; 2023 14 vs 48.6; 2024 16 vs 49.2; 2025
    13 vs 49.8.
  - *Test:* Raleigh 2021–25 observed 23, 55, 54, 37, 61 (total 230) vs predicted mean 9.0, 19.9, 30.2,
    38.9, 43.1 (total 141; median 11; 90% 0–687); Durham observed 32, 35, 77, 51, 44 (239) vs 15.0, 23.5,
    28.6, 51.7, 53.1 (172; median 15; 90% 0–865). Inside, so not a transport failure by the rule; the
    intervals are wide because a new place's multiplier is unknown.
  - *Reading:* rent, home value and rates explain little of the difference between places; the owner-occupancy
    rule had no measurable effect; Minneapolis's decline after 2020 is not captured (the model rises with the
    ramp and rents). The Portland gap reasons above still apply.
- **Fit 4 pre-registration (written and pushed before fit 4 was run, 2026-10-20; Ben: fit 3 is not on trend):**
  - *Unchanged from fit 3:* fit set (Minneapolis 2016–25, the Twin Cities places with coded ADU rules, Austin
    2016–23), test set (Raleigh and Durham 2021–25), place-year inclusion rule, Poisson counts with a gamma
    place effect (variance α) shared over a place's years, blank rule fields integrated per place, coverage
    (D-021), graded shares m_o and m_x, holdouts (St. Paul never; Charlotte never; no held-out row).
  - *Expected count:* μ_it = θ · u_i · parcels · h_m(θ = 1, β_rate = 0; year t's rent, home value and **real
    construction cost**) · max_r c(type) · coverage · ramp · exp(−β_rate (r_t − r_ref)) · (1 − s_sub)^MM_it ·
    exp(Σ_j b_j x_itj).
  - *Construction cost by year (new):* the pro forma's hard cost per sq ft (2025 level) × the real cost index
    (PPI residential construction inputs / CPI-U, year t ÷ 2025; `market_geo_year.ppi_resid_inputs`). The
    reference place (Portland 2015–19) uses its own era's mean index (2015–19), so only cost changes relative
    to the reference transport.
  - *Rate effect (new, estimated):* β_rate with each year's actual 30-year rate. It replaces the judgment value
    if its 90% profile interval is narrower than 0.30; otherwise the judgment value 0.07 (0–0.15) stays.
  - *Substitution with missing middle (new, C47):* MM_it = 1 when a coded missing-middle rule allowing 2+
    units in single-family zones is in force by 1 July (`config/reforms/*.csv`, theme missing_middle,
    `unit_cap` ≥ 2 or blank, `by_right` not False; a blank `by_right` counts with the share of coded
    missing-middle rows that are by right). Uptake × (1 − s_sub). s_sub is estimated, with a 90% profile
    interval; it is "identified" only if that interval is narrower than 0.8; otherwise s_sub = 0 in the
    scenario and the report says so. In the fit set only Minneapolis (3 units from 2020-01-01) has MM_it = 1.
  - *Covariates for later:* the fit takes a generic table of place-year covariates x_itj with log-linear
    coefficients b_j, so dated ADU programs (fee waivers, pre-approved plans) and fee histories can enter later
    under their own pre-registration. None is added in fit 4.
  - *Diagnostic only (not used for any parameter):* a second fit adds a post-2020 indicator (years ≥ 2021)
    with coefficient γ, reported with its interval. If γ's interval excludes 0, the report says the trend is
    still not explained.
  - *Estimation:* maximum likelihood by coordinate ascent over (log θ, log α, β_rate, s_sub, m_o, m_x);
    90% profile intervals for θ, β_rate, s_sub, m_o and m_x (others re-maximized at each grid point). m_o and
    m_x follow fit 3's rule (estimated only if their interval is narrower than their judgment range).
  - *Test prediction and decision rule:* as fit 3; θ, α, β_rate (if identified), s_sub (if identified), and any
    identified share replace the configured values whatever the test shows. Forward runs keep 2025's real
    construction cost (index 1) and draw the rate path as before.
- **Fit 4: withdrawn before it was run (Ben, 2026-10-20).** The pre-registration above (commit cf123ba) stays
  as written, but no fit 4 was run: adding terms to chase the observed trend was rejected. The ADU estimation
  will be re-specified from the causal diagram (§3) and protocol §5.6–5.7 (staggered-adoption count model
  with year effects, place random effects, an eligible-parcel offset, event-time ramp effects and pre-period
  effect modifiers). Only a tested building block from that round is kept: `hazard.adu_price_to_cost` and
  `adu_mature_hazard` accept a real construction-cost index (`hazard.cost_index_by_year`, PPI residential
  inputs / CPI-U relative to 2025); it defaults to 1, so no current result changes.
- **Decided by:** scenario choices proposed by WS-ENGINE; estimation and split decided by Ben, 2026-10-20.

### D-020 · 2026-10-20 · Scenario geography: units that never share a parcel
- **Found (WS-CORE):** `places_from_store` modelled local-only places (`in_bps` False: Charlotte, Concord and
  other Mecklenburg and Cabarrus towns, 23 MN townships) and the county remainder rows that contain them, so
  their parcels were counted twice.
- **Now (`scenarios/adu.non_overlapping`):** local-only places stay as their own scenario units (they carry
  their own rules); their eligible parcels are subtracted from the remainder of each county they sit in, split
  by Census 2020 county shares (`geoparts.county_shares`), clipped at 0 and flagged. Only remainders whose
  denominator is the ACS fallback overlap: `eligible.allocate_homes` keeps local-only homes in them, while a
  remainder counted from a parcel roll holds only the parcels assigned to the county row (each parcel has one
  jurisdiction). Columns `eligible_parcels_reported` and `overlap_removed` show the change. The baseline
  permit series stays on BPS reporting units.
- **Effect (2026-10-20 tables):** eligible parcels removed: NC 344,992 of 3,413,981 (Mecklenburg's
  remainder 275,566 → 18,920), MN 10,459, OH 0, TX 0. WS-CORE's figures (NC 419,293, OH 4,000) also counted
  remainders built from parcel rolls (e.g. Union County, 27,997, which holds none of its towns' parcels).
- **Open:** places BPS files under a county that are not in `jurisdictions` (Wilmington, Hickory, Salisbury,
  Statesville) carry no rules of their own; a county row's c should become a parcel-weighted mix of the rules
  of the places inside it (with D-021's coverage share).
- **Decided by:** proposed by WS-CORE, implemented by WS-ENGINE, 2026-10-20; for Ben to confirm in the PR.

### D-021 · 2026-10-20 · Proposed: rule coverage (zones, minimum lot sizes) in the ADU rule classifier
- **Gap (WS-CORE):** `rule_restrictions` reads only the rubric's yes/no fields. A rule limited to some zones
  or to lots above a minimum size (Austin's 2015/2023 ADU rules: SF-3 only, lots of 5,750+ sq ft) reads as
  Handbook-equivalent for the whole place. This overstates current rules (understating the Handbook gain) and
  makes such a place a full-coverage observation in the anchor fit (D-019).
- **Proposal (for a follow-up PR; not built here):** each place's eligible parcels split into covered and
  not covered by its rule. Coverage share = share of ADU-eligible parcels whose zoning is in `coverage_zones`
  and whose lot meets `min_lot_sqft`, computed from parcel zoning and lot size where the roll has them; where
  it doesn't, a sourced default by rule scope ("citywide" 1.0; district- or lot-size-limited, judgment 0.5,
  range 0.2–0.8). Then c_place = c × coverage share (uncovered parcels have no rule and get the full Handbook
  increment), in the scenario and in the anchor fit alike. A county remainder's c = the parcel-weighted mix
  of the rules of the places inside it (D-020's open item). `min_lot_sqft > 0` with no parcel data counts as
  limited coverage rather than "partial", so the two adjustments don't overlap.
- **Decided by:** proposed by WS-CORE and WS-ENGINE, 2026-10-20; for Ben.
- **Implemented (2026-10-20, Ben approved):** `scenarios/adu.rule_coverage` and `coverage_map`. Zones and lot
  minimums are measured on each place's single-family detached parcels (latest roll) among parcels whose zoning
  or lot size is known (a written-out district name also matches its code's acronym, e.g. "Urban Neighborhood
  1" = UN1); where a roll can't measure a limit, `adu_rule_zoned_coverage_share` 0.75 (judgment). With no
  zones or lot minimum, a rule covers everything unless its text names a limited area explicitly ("only
  inside/within/in", "within …", new subdivisions, a half-mile corridor): `adu_rule_limited_coverage_share`
  0.2 (judgment). The uncovered share of a rule's type probabilities moves to "none". Examples measured:
  Minneapolis 2023 zones 94%; St. Paul 2016/2018 54%; Austin 2015 rule 64%, 2010 rule 49% (lot minimum from
  parcels × zones judgment). County rows: `county_mix` blends the rules of coded places BPS files under the
  county (Wilmington) by their share of the row's eligible parcels (ACS one-unit detached homes); the mean c
  is right, though a draw still picks one type for the whole row.

### D-022 · 2026-10-20 · Anything not coded is unknown (option C)
- **Decided by Ben (2026-10-20):** a place with no ADU row, and a blank rubric field in a coded row, are
  unknown, never "no rule" or "no restriction".
- **Now (`scenarios/adu.py`):**
  - rules are one of five types: none, owner occupancy only, other restrictions (parking, not by right,
    attached only, cap under 600 sq ft), both, Handbook-equivalent; c = 0, m_o, m_x, m_o·m_x, 1;
  - a blank field restricts with the share of coded rules that restrict it (state share if 5+ coded values,
    else pooled over the four states); a row's type is a probability over the five types;
  - a place with no ADU row takes the mean type probabilities of the coded places in its state and size band
    (<10k, 10–50k, 50k+ people in 2020), falling back to the state's pooled mean, then the all-state mean,
    below 5 coded places (`adu_rule_min_coded`);
  - explicit "no ADUs" rows stay "none" (#164); a citywide parking reform with no minimum settles a blank ADU
    parking field;
  - each simulation draw samples each place's type; the central path uses the expected c; outputs report each
    place's type probabilities, whether its type was drawn, and the drawn shares; a drawn rule with no known
    date is taken as long in force (`adu_unknown_rule_age_years` 10).
- **Counts behind it (config/reforms on main, 2026-10-20; rules in force on 31 December 2025):** coded field
  values restricting / known, pooled: owner occupancy 23/36, parking 18/34, by right 5/37, detached 5/40, size
  0/29. Coded places by state and band (none/partial/Handbook/uncertain): MN 50k+ 5/11/3/1, MN 10–50k 1/4/0/0;
  NC 50k+ 0/0/1/3; OH 50k+ 4/7/1/0, 10–50k 2/1/0/0; TX 50k+ 10/6/2/0. Small places in every state borrow
  their prior from the state's pooled coded places or the all-state mean.
- **Bias to watch:** states coded their largest places first, so priors for small places come from large
  ones. As WS-CORE's ordinance lookup codes more places, the priors and field shares update from the CSVs
  with no code change.
- **Calibration:** blank fields are integrated over (D-019 fits 2 and 3); places with no ADU row stay out of
  the fit.

### D-023 · 2026-10-20 · ADU effect estimated with a staggered-adoption count model (pre-registered; supersedes the D-019 fits)
- **Why:** the D-019 fits calibrated one anchor to places that already allowed ADUs, with no comparison places and no year effects. That departs from the causal diagram (`docs/research/lotline-causal-diagram.md` §3) and the statistical protocol (§5.6–5.7). Common shocks after 2021 (rates, construction costs, the market) could not be separated from the reform, and the modifiers' strength was imposed by judgment, not estimated. Fits 1–3 are superseded as estimates of the effect; fit 4 was withdrawn unrun (Ben, 2026-10-20).
- **Estimand:** additional ADU permits per eligible single-family parcel caused by an ADU rule, by years since it took effect, and how that effect varies with pre-reform conditions. "Additional" means relative to the same place without the rule (protocol §1).
- **Data:**
  - **Places and years:** every Twin Cities metro place with Met Council residential permits, 2016–2025; ADUs are flagged from 2016, so 2016 is the first year and the measurement is the same before and after each reform (C32).
  - **Outcome:** ADU permits per place-year. Minneapolis uses the larger of Met Council and city counts, as in `calibrate_adu.observed_adu_counts`.
  - **Exposure:** eligible parcels (rule 1.1) as the offset.
  - **Excluded:** St. Paul, entirely; it is the V5 blind test. Charlotte from 2023-06-01 is never used.
  - **Places with no dated ADU rule are left out of estimation,** not imputed. The adoption-date run (2026-10-20) fills them, and a place enters once its rule history is coded with a source.
- **Treatment and dose (C10, C11, C13):** D_it = the place's ADU rule in force on 1 July of year t, graded as: none = 0; permit or conditional use required; by right with owner occupancy; by right without it. The grade is multiplied by rule coverage (D-021). The adoption year T_i is the first year a by-right rule is in force. Places never treated (explicit "no ADUs") and not yet treated are the comparisons.
- **Model:** Poisson pseudo-maximum likelihood (PPML) on counts with the log(eligible) offset, place fixed effects and year fixed effects, estimated with Wooldridge's extended two-way fixed-effects estimator (cohort × event-time effects) for staggered adoption. TWFE with unit trends is not used (protocol §5.6).

  E[ADUs_it] = Eligible_it · exp( α_i + γ_t + Σ_k β_k · 1[t − T_i = k] + Σ_m θ_m · (X_im − X̄_m) · 1[t ≥ T_i] + ρ · (r_t − r̄) · 1[t ≥ T_i] + δ · MM_it )

  | Term | Meaning | Causal diagram |
  |---|---|---|
  | α_i | Place fixed effect | C06, C14, C15 (level differences) |
  | γ_t | Year fixed effect | National rates, costs, COVID and the cycle (C01–C03, C42) |
  | β_k | Event-time effects, k = 0…5+ | Ramp and builder learning (C24); grade and coverage enter by scaling the indicator with D_it |
  | θ_m | Effect modifiers, measured before adoption (bad-controls rule, C17) | Price-to-cost from the pro forma at the pre-adoption year (C40); median home value as the owner-equity proxy (C22); pre-reform 1-unit permits per 1,000 eligible parcels (C06); ACS household growth over the 5 years before adoption as the local-demand proxy (C04; a shift-share employment index replaces it if added later) |
  | ρ | Mortgage rate × treated | Rates as an effect modifier (C01, C22): the same rule yields less at higher rates |
  | δ | 2–4 units legal by right on the same lot | ADU ↔ missing-middle substitution (C30); reported as weakly identified if fewer than 5 places change status |

- **Inference:** wild cluster bootstrap by place (999 draws). Randomization inference that permutes adoption years among treated places is reported alongside, because treated places are few.
- **Checks, from causal diagram §5 (all reported, pass or fail):**
  1. **Pre-trend leads** k = −3…−1: jointly not different from 0 at the 10% level.
  2. **Placebo adoption dates** 2 years early: no effect.
  3. **Placebo outcome,** permits in 5+ unit buildings: no effect.
  4. **Excluding 2020–21:** effects within their 90% intervals.
  5. **Leave-one-treated-place-out:** no single place moves the pooled effect by more than its 90% interval.
- **Out-of-sample test (transport, protocol §5.5, §5.8):** with the Minnesota estimates and each place's own pre-reform modifiers, predict ADU permits for Austin (2016–2023, coded rules), Raleigh (2021–2025) and Durham (2019–2025). The test passes if each place's observed total lies in its 80% prediction interval, and the coverage of yearly 80% intervals across the three is between 60% and 95%. Places outside the Minnesota modifier range are flagged, and their intervals widened as in `hazard.widen`.
- **Forecast use:** for a target place, the scenario's added ADUs = Eligible × [exp(η_with rule) − exp(η_without)] summed over 2026–2030. η uses the place's α (or, for places without ADU data, a hierarchical prior by state, size band and modifiers; protocol §5.7), the event-time β, its own modifiers, ρ at the stated rate path (`mortgage_rate_forecast`) and γ_2026–2030 held at the 2025 level with the rate effect added. Uncertainty comes from bootstrap draws of all coefficients plus Poisson-gamma noise. The net-new and formalization shares (D-019) then apply as before.
- **Robustness (reported, not used to choose):** negative-binomial with place random effects (protocol §5.7); the Borusyak imputation estimator; the dose as a binary by-right indicator.
- **What would change the plan:** if the pre-trend check fails, report it and use HonestDiD bounds; there is no re-specification without a new dated entry. If too few places have dated rules after the adoption-date run, report the estimates as underpowered rather than adding assumptions.
- **Code:** `src/lotline/model/estimate_adu.py`, tested by recovering known β, θ and ρ from simulated staggered-adoption panels before any real run.
- **Implementation choices (Ben, 2026-10-20, before the real run):** dose grades in equal steps (1/3, 2/3, 1; `adu.yaml`); T_i is the first year a rule with P(by right) >= 0.5 is in force on 1 July; modifiers are measured at T-1 (price-to-cost with that year's rent and real construction cost; log home value; mean 1-unit permits per 1,000 eligible parcels over T-3..T-1; log household growth T-6..T-1); places that adopted before 2010 (Bloomington, Plymouth) don't inform the modifier terms; a new place's level comes from its own pre-adoption years where it has them, otherwise a draw from the Minnesota places. Hastings was removed before the run (Ben's lookup matched St. Paul's Ord. 23-43).
- **Decided by:** Ben, 2026-10-20.
- **Implementation notes (2026-10-20, WS-ENGINE; choices the specification leaves open, for Ben to confirm
  before the real run):**
  - *Dose values:* the grades are ordered in D-023 but not valued; equal steps are used: permit or conditional
    use 1/3, by right with owner occupancy 2/3, by right without it 1 (`adu.yaml` `adu_dose_grade_*`), times
    coverage (D-021). Blank by_right / owner_occ fields enter with their coded shares (D-022), so the dose is
    an expectation. The binary by-right dose is the robustness check.
  - *Adoption year T_i:* the first year (from 1990) a rule whose P(by right) ≥ 0.5 is in force on 1 July.
    Places adopting before 2016 have only late event times in the panel; cohort cells that are constant within
    a place are collinear with its fixed effect and dropped by the estimator (reported).
  - *Modifiers (year T_i − 1):* price-to-cost from the pro forma with that year's ACS rent (newest vintage,
    not before 2010) and real construction cost (`hazard.cost_index_by_year`); log median home value; BPS
    1-unit permits per 1,000 eligible parcels, mean of T − 3 … T − 1; household growth = log of ACS households
    (B25003) at T − 1 over T − 6 (vintages from 2015 and 2010 at the earliest). Places adopting before 2010
    get modifiers measured after adoption; they are listed.
  - *PPML:* places with no ADU permit in any year are dropped (no finite fixed effect; no information under
    Poisson fixed effects); regressors collinear with the fixed effects are dropped; both are reported.
  - *Bootstrap:* the wild cluster score bootstrap uses Webb six-point weights (few clusters) and CR2-adjusted
    cluster scores; without CR2, standard errors ran ~10–15% low on simulated panels. Intervals are basic
    bootstrap intervals; the lead test is a Wald test with the bootstrap covariance.
  - *Randomization inference:* statistic = the overall effect (event-time cells averaged with counterfactual
    expected permits as weights).
  - *Transport:* a target place's level α comes from its own pre-adoption years (with its sampling error) when
    it has permits then, else a draw from the Minnesota places' α; Minnesota year effects; count noise is
    Poisson-gamma with the panel's overdispersion (moment estimate). Raleigh's panel starts in 2019 and
    Durham's in 2016 so their pre-adoption years inform α; only D-023's test years are scored.
  - *Smoke test of the panel (2026-10-20, counts only):* 21 Twin Cities places with dated ADU rules × 2016–2025
    (164 left out for no dated rule; St. Paul excluded); 12 ever treated (6 adopting in 2016–2025), 9 never
    treated; 13 places have no ADU permit in any year. With today's coding the estimate would be underpowered;
    the run waits for the adoption-date research.
- **First real run aborted (2026-10-20):** the one-time run failed numerically: PPML separation (cohort ×
  event-time cells, and possibly place and modifier combinations, with all-zero outcomes put the maximum
  likelihood at infinity), giving coefficients in the hundreds, exp overflows in the bootstrap and
  randomization inference, absurd transport means, then a crash writing `--out`. The run was treated as
  aborted and **no estimate from it was looked at or interpreted**; its log is committed unread as
  `reports/adu-d023/aborted-2026-10-20-log.txt` (warnings may be truncated). **Fix, mechanical and independent
  of the results:** separation removed before fitting (Correia, Guimarães & Zylkin 2019): places and years
  with all-zero outcomes, one-signed indicator columns whose rows all have zero outcomes (dropped with their
  rows), then the iterated-rectifier check for any remaining separated observations, repeated until nothing
  changes, every drop reported; modifiers entered as z-scores over the treated places (θ per standard
  deviation); the fit fails loudly (`EstimationError`) on non-convergence, |η − offset| > 30, a coefficient
  beyond ±20, or an effectively zero standard error, and the same guards apply in the bootstrap,
  randomization inference, leave-one-out and transport (which also refuses a predicted mean above 5% of
  eligible parcels a year); `--out` is a directory of named CSVs, written only after every stage succeeds.
  Tested on synthetic panels with all-zero cohort cells and with a separating modifier. **One rerun follows.**
- **Rerun (2026-10-20, the one rerun after the fix) stopped by the numerical guard:** the point fit converged
  (11 iterations) but kept only **143 of 760 place-years**: 53 places with no ADU permit in any year and 87
  separated observations were dropped; 21 cohort × event-time cells were dropped (all-zero outcomes or no
  variation left) and 8 more as collinear with the fixed effects, and **all four modifier terms θ and δ were
  collinear with the fixed effects** in what remained. The wild score bootstrap then produced a draw beyond
  the coefficient bound and the run raised `EstimationError`; nothing was written. No estimate was printed
  (the script prints estimates only after the bootstrap). Log: `reports/adu-d023/run-2026-10-20-log.txt`.
  Under "what would change the plan" the result is reported as **underpowered**; no assumption was added and
  no further run was made. Options for Ben (each needs a new dated entry before any run): pool event times
  and cohorts (e.g. one post-adoption effect, or k = 0–1, 2–3, 4+), report the D-023 robustness estimators
  (negative binomial with place random effects, which keeps places with zeros; the Borusyak imputation
  estimator) as primary, or widen the panel (more places with dated rules, earlier ADU-flag years).

### D-024 · 2026-10-20 · Missing-middle effect estimated on a pooled four-state panel (pre-registered; approved before any estimate)
- **Why:** the missing-middle scenario needs an estimate, from observed reforms, of how many extra 2–4 unit
  homes get permitted when 2–4 units become legal on single-family lots. This entry fixes the estimand, sample,
  model, checks and out-of-sample test **before any estimate is run**. It mirrors D-023 and applies its lesson:
  check first whether the data can carry place fixed effects (smoke counts below).
- **Estimand:** additional homes permitted in 2–4 unit buildings per missing-middle eligible parcel, caused by
  a rule that allows 2–4 units on single-family lots, by years since the rule took effect, and how that varies
  with pre-reform conditions. "Additional" means relative to the same place without the rule (protocol §1).
  Gross homes: demolitions and the single-family rebuild they replace are netted out in the scenario, not here
  (causal diagram MM §1).
- **Why a pooled four-state panel, not Minnesota alone:** in the Twin Cities only Minneapolis has a coded
  missing-middle rule (St. Paul is the V5 blind test). One treated city cannot support a staggered design. The
  four reform states have 7 treated places with coded rules, all measured the same way by Census BPS.
- **Data (`src/lotline/model/estimate_mm.py`, `build_panel`):**
  - **Places and years:** every BPS permit-issuing place in MN, NC, OH and TX with at least 10,000 people
    (2020 Census; `mm_estimation_min_population`), plus every place with a coded missing-middle rule;
    2010–2025 (`mm_panel_first_year`, `mm_panel_last_year`): the first year with eligible-parcel rolls and ACS
    for every place, giving Minneapolis and Durham ten years before their reforms.
  - **Outcome:** BPS homes in 2-unit and 3–4 unit buildings (`units_2 + units_3_4`), the same measurement in
    every state and year. Townhouses are 1-unit buildings in BPS and stay out; 5–6 unit buildings are mixed
    into BPS 5+ with large apartments and stay out. A place-year with no BPS row is missing, never 0.
  - **Exposure:** missing-middle eligible parcels (rule 1.1, D-014) as the offset, from the nearest roll; the
    ACS fallback (D-017) supplies 330 of the 560 places' denominators. Place effects absorb level errors;
    only changes over time matter.
  - **Excluded:** St. Paul entirely (V5); Charlotte, Mecklenburg County and every place reporting under it
    entirely (holdout from 2023-06-01, D-012; Charlotte's reform falls in the window).
- **Treatment and dose:** from coded `missing_middle` rows in `config/reforms/*.csv`, in force on 1 July of
  year t. Dose D_it = units grade × approval grade × coverage:
  - units allowed on a single-family lot: 2 → 1/3, 3 → 2/3, 4 or more → 1. The outcome only counts 2–4 unit
    buildings, so a rule allowing more than 4 (St. Paul, Houston) counts as a full dose. The Handbook scenario
    allows 2–6 units: 5–6 unit buildings come from the pro forma side, not this estimate;
  - approval: by right 1, by permit or conditional use 1/3 (`mm_dose_grade_permit`, equal steps as in D-023);
  - coverage of single-family zones measured on parcels as in D-021 (`adu.rule_coverage`, reused as is);
  - blank fields take coded shares (D-022): a blank `by_right` takes the share of coded missing-middle rules
    that are by right (3 of 3 today); a blank cap takes the mean units grade of coded caps.
  - Adoption year T_i: the first year a rule with P(by right) ≥ 0.5 is in force on 1 July. Treated today:
    Minneapolis 2020, Durham city and Durham County 2020, Raleigh 2022, Austin, Houston and Cincinnati 2024.
- **Comparisons:** places with no coded missing-middle rule are unknown under D-022. With only coded
  places there are **no never-treated comparisons**: the 2024 adopters would be the only controls for
  2020–2023, and 2024–2025 would have none. **Decided:** places with no coded rule count as never treated for
  this estimate only. This is a deviation from D-022, stated here. It rests on two points: no statewide rule
  allowing 2–4 units on single-family lots is coded for any of the four states (the pipeline's Minnesota
  records found none as of 2025), and a place mislabelled as untreated pulls the estimate toward zero. The robustness checks bound that risk. To shrink it:
  - places the ordinance pipeline found legalizing 2–4 units should be coded with dates before the run (St.
    Louis Park 2025; Bloomington 2025–26 needs a manual lookup; `docs/research/ordinances/`; WS-MN);
  - places the pipeline found not to allow them (Brooklyn Park, Coon Rapids, Rochester) should be coded as
    explicit "no" rows.
- **Model (main):** Poisson pseudo-maximum likelihood with the log(eligible parcels) offset, place fixed effects
  and **state × year** fixed effects. The four states' markets moved differently, and each state has 56–232
  places. Effects are estimated with Wooldridge's extended two-way fixed effects, pooled into three event-time
  bins:

  E[y_it] = Eligible_it · exp( α_i + γ_{s(i),t} + Σ_b β_b · D_it · 1[t − T_i ∈ b] + Σ_m θ_m · z_im · 1[t ≥ T_i]
  + ρ · (r_t − r̄) · 1[t ≥ T_i] + δ · ADU_it ),  b ∈ {0–1, 2–3, 4+}

  | Term | Meaning | Causal diagram (MM) |
  |---|---|---|
  | α_i | Place fixed effect (includes duplexes some zones already allowed) | C05, C06, C14 (levels) |
  | γ_st | State × year effect | Rates, costs, COVID and the cycle by state (C01–C03, C42) |
  | β_b | Effect by years since adoption, pooled 0–1, 2–3, 4+, scaled by dose | Ramp and builder learning |
  | θ_m | Modifiers measured at T − 1, as z-scores over treated places. Main: price-to-cost of a rental duplex from the pro forma (C40; constant factors cancel in the z-score) and log median home value (the existing-use value a teardown must beat, C46). Robustness only: 2–4 unit homes per 1,000 eligible parcels over T − 3…T − 1 (C06) and log household growth T − 6…T − 1 (C04; the shift-share demand index from thread 3 replaces it when it lands, by a dated note) | Modifiers 1–2 of MM §2 |
  | ρ | Mortgage rate × treated | Developer financing (C45; the national 30-year rate stands in for construction-loan rates) |
  | δ | P(a by-right ADU rule is in force); uncoded places take the coded mean of their state, size band and year | ADU on the same lot competes (C47) |

  - **Why fixed effects here and not for ADUs (smoke counts):** every treated place has 2–4 unit homes in
    most years. A place fixed-effects model keeps 420 of 560 places; the 140 it drops (no 2–4 unit home in any
    year) are all comparisons, and under Poisson fixed effects they carry no information about the effect.
    With seven treated places, the main model has only two modifiers. More would be fitted from as many
    places as parameters.
  - Separation removal, numerical guards and failing loudly are as in D-023 (`estimate_adu.ppml`).
  - **Pre-specified fallback:** if the PPML fit raises `EstimationError` or drops a treated place, the negative
    binomial with place random effects (protocol §5.7; D-025's estimator if approved) becomes the main model,
    with the same terms. No new entry is needed for that switch, and the failure is reported.
- **Inference:** seven treated places is too few for the wild cluster bootstrap to be trusted alone. Reported:
  - the wild cluster score bootstrap by place (Webb weights, CR2, 999 draws, as in D-023) for intervals;
  - randomization inference as the test of "no effect": the seven adoption-year and dose paths are reassigned
    at random to places in the same state and size band (D-022 bands), 999 times. The p-value is the share of
    reassignments with an overall effect at least as large.
- **Checks (all reported, pass or fail; pass rules fixed now):**
  1. **Pre-trend leads** k = −3…−1: jointly not different from 0 at the 10% level.
  2. **Placebo adoption dates** 2 years early, using only pre-adoption years: the 90% interval contains 0.
  3. **Placebo outcome,** BPS homes in 5+ unit buildings: the 90% interval contains 0.
  4. **Substitution (reported, no pass rule):** BPS 1-unit homes as the outcome. A fall is the single-family
     rebuild being replaced (C30), which the scenario nets out; it is not noise.
  5. **Excluding 2020–21:** every bin's effect stays inside the main 90% interval.
  6. **Leave one treated place out** (Durham city and county also left out together, one ordinance): the
     overall effect stays inside the main 90% interval.
  7. **Comparison contamination:** re-fit (a) on places of 50,000+ people only (121 places) and (b) without
     comparison places the ordinance pipeline lists as having a missing-middle ordinance or an unknown status.
     Pass: the overall effect stays inside the main 90% interval.
  8. **Local measurement (reported):** for Minneapolis (Met Council and city permits), Durham and Raleigh
     (city permits), local 2–4 unit counts vs BPS, before and after adoption. If they differ by more than 25% in
     the post years, that city's local-count estimate is shown next to the BPS one.
- **Out-of-sample tests (protocol §5.5, §5.8):**
  - **A (headline): predict North Carolina.** Fit without Durham city, Durham County and Raleigh; NC's year
    effects still come from NC's comparison places. Predict their post-adoption 2–4 unit homes from their own
    pre-adoption level (α from their 2010–2019 or 2010–2021 years, with its sampling error), their modifiers and
    the fitted effects. Pass: each place's observed post-adoption total lies in its 80% prediction interval, and
    the coverage of yearly 80% intervals across the three places is between 60% and 95%.
  - **B: predict Minneapolis** the same way from a fit without it; same pass rule for its single total.
  - Either way, the later bins (2–3, 4+) then rest on one or two cities. This is stated with the results.
    Places outside the fitted modifier range are flagged and their intervals widened as in `hazard.widen`.
- **Forecast use:** for a target place, the scenario's added 2–4 unit homes = Eligible × [exp(η with the
  Handbook rule) − exp(η without)], summed over 2026–2030. The Handbook rule is 4+ units by right citywide
  (dose 1). Observed doses run 0.2–1 (only Houston is at 1), so dose 1 leans on the dose scaling; the binary
  dose check below shows how much. η uses the place's α where it is in the panel, otherwise a draw from places
  in the same state and size band. It also uses the bins' β, the place's modifiers, ρ under
  `mortgage_rate_forecast`, and γ held at the 2025 level with the rate effect added. Uncertainty comes from
  bootstrap draws of all coefficients plus Poisson-gamma noise. Demolitions and the rebuild substitution are
  then netted out in the scenario.
- **Robustness (reported, not used to choose):** the negative binomial with place random effects (it keeps
  the 140 all-zero places and gives the prior for places outside the panel); the Borusyak imputation
  estimator; a binary by-right dose; all four modifiers; the 50,000+ sample; Met Council 2–4 unit permits
  for the Twin Cities alone (2016–2025: 64 places, 1 treated, 40 with no 2–4 unit permit in any year; too thin
  to stand alone).
- **Not in this entry:** the within-city design the causal diagram ranks strongest, which compares eligible
  and ineligible lots in the same city (Raleigh R-1; Durham's suburban tier). It needs permits geocoded to
  zones, a later entry.
- **What would change the plan:** if the pre-trend check fails, report it and use HonestDiD bounds. If leave
  one out fails, report which place drives the effect and show the NB pooled estimate next to it. No other
  re-specification without a new dated entry.
- **Smoke test of the panel (2026-10-20, counts only; `scripts/dev/estimate_mm.py --smoke`):**
  - 560 places × 2010–2025 (MN 100, NC 56, OH 172, TX 232); 8,763 place-years with an outcome (197 missing
    from BPS); 2,682 places under the population floor and 2 holdout places excluded.
  - Treated: 7, all inside the panel years (2020: 3, 2022: 1, 2024: 3). Comparisons: 553, all uncoded.
  - 140 places have no 2–4 unit home in any year, none of them treated; a place fixed-effects model keeps 420;
    73% of place-years are zero.
  - Treated place-years by bin: 0–1: 14 (7 places); 2–3: 8 (4 places); 4+: 6 (3 places).
  - With coded comparisons only: 7 places, 0 never-treated comparisons.
  - 50,000+ sample: 121 places, 10 with no 2–4 unit home in any year.
  - Every treated place has all four modifiers. ADU rules are coded for 102 of the 560 places.
- **Decided by:** Ben, 2026-10-20, as proposed (including the `mm.yaml` choices: the 10,000-person floor and
  the 1/3 permit grade), before any estimate was run.
- **Run (2026-10-20, WS-ENGINE-MM; `scripts/dev/estimate_mm.py --full`, outputs in `reports/mm-d024/`):**
  - **First run aborted (17:06):**
    - PPML diverged (|η − offset| = 119.9), so the pre-specified fallback fired.
    - The script's fallback was a Poisson-gamma place random-effects model (Hausman, Hall & Griliches 1984),
      written in `estimate_mm.fit_re`. Its main estimates and added homes were printed.
    - Randomization inference then crashed: a reassignment's fit raised a plain `ValueError` that the loop did
      not catch. Nothing was written. The log is committed as is: `aborted-2026-10-20-log.txt`.
  - **Fix (mechanical, independent of the results) and one rerun (20:35, Ben: "try again"):**
    - divergence and overflow in `fit_re` raise `EstimationError`;
    - Newton steps are safeguarded: damped when not uphill, and never accepted if they lower the likelihood;
    - log a is held at a bound of 15 when the counts show no place heterogeneity;
    - randomization inference and every check count a failed fit instead of crashing.
    - Same specification and seed. The main fit is deterministic, and its estimates match the aborted run's
      exactly.
  - **The fallback is not "D-025's estimator", which D-024 names.** D-025 (`pooled_adu`) was on main from
    16:30, before both runs. The rerun kept the 17:06 fallback, as instructed. D-025's estimator was run as a
    robustness model, through `estimate_mm.fit_nb` with its code unchanged: on the D-024 panel relabelled so
    that its year effects are D-024's state × year effects and its δ is D-024's ADU term.
    - It converged on the real panel. At its maximum the analytic and numerical scores agree, and no place's
      likelihood jumps.
    - Its mode search can fail on synthetic panels with many never-permitting places (shared notes,
      2026-10-20), but not on this one.
    - **Ben to decide** whether D-025's estimate (below) replaces the fallback's as D-024's main estimate.
      That would follow D-024's wording; the checks would then need running for it.
  - **Implementation choices:**
    - state × year effects as one integer code per state and year;
    - randomization inference: each treated place's whole package moves (adoption year, calendar-year dose
      path, modifiers), within state and size band, to places with any 2–4 unit home;
    - the overall effect weights the bins by counterfactual expected homes (`estimate_adu.aggregate`, as in
      D-023);
    - added homes = fitted minus treatment-off means; their intervals hold place and year effects at the
      estimate;
    - check 7b dropped 16 Minnesota comparison places by name;
    - check 8 re-fits with a city's local counts when they differ from BPS by more than 25%.
  - **Main estimates (Poisson-gamma fallback; log scale; 90% basic bootstrap intervals):**
    - overall **0.77 (0.07 to 1.54)**, i.e. about 2.2 times the 2–4 unit homes at full dose;
    - years 0–1: 0.79 (0.20 to 1.38); 2–3: 1.14 (−0.62 to 2.91); 4+: −0.13 (−2.40 to 1.89);
    - price-to-cost: θ = 0.91 (0.05 to 1.78) per SD; home value: θ = −1.00 (−1.61 to −0.41) per SD;
      rate: ρ = 0.11 (−0.14 to 0.36); ADU rule: δ = −0.53 (−1.09 to 0.08).
    - Read the intervals as narrower than stated. On simulated panels with seven treated places, nominal 90%
      intervals covered 68–85% (`--coverage`).
  - **Randomization inference: p = 0.70** (956 reassignments, 43 not fitted). The effect is no larger than
    where the reform's timing and dose are moved to other places.
  - **Added 2–4 unit homes in the treated places' post-adoption years: 2,650 in all.**
    - **Houston alone accounts for 2,422 (1,426 to 3,188), about 91%.** It is the only full-dose place,
      has no zoning, and its deed restrictions bind (flagged by the methodology review).
    - The others: Durham city 150 (6 to 236), Raleigh 119 (−16 to 189), Minneapolis 93 (−109 to 201),
      Durham County 6, Cincinnati −8, Austin −131 (−286 to −12).
  - **Checks:**
    1. Leads: **pass** (p = 0.59).
    2. Placebo dates: **fail**, 0.54 (0.03 to 1.00).
    3. Placebo outcome (5+ units): **fail**, −1.11 (−1.53 to −0.54).
    4. Substitution (1-unit homes): 0.00 (−0.38 to 0.39).
    5. Excluding 2020–21: **pass**.
    6. Leave one out: **fail**. Without Minneapolis the overall effect is −0.02; the others give 0.56–1.34.
       D-024's rule asks for the NB pooled estimate alongside, and D-025's NB is the robustness line below.
    7. Contamination: 50,000+ only, **pass** (0.94); without the 16 pipeline-flagged places, **pass** (0.74).
    8. Local measurement: Met Council and Minneapolis agree with BPS (ratio 1.00); Raleigh too (0.98). The
       Minneapolis city source is 1.63× and Durham's 1.59×; re-fits with their local counts give 0.03 (−0.46
       to 0.65) and 0.51 (−0.27 to 1.39).
  - **Robustness:**
    - PPML: did not estimate (the same divergence).
    - Imputation estimator: did not estimate (its PPML diverged: |η − offset| = 124.4).
    - **D-025's negative binomial: −0.25 (−1.10 to 0.77)**; bins 0.07, −1.29, −1.85. Its place-year
      overdispersion is large (κ ≈ 5.5, σ ≈ 2.4). The Poisson-gamma model has none beyond the place effect,
      so it weights large-count place-years such as Houston's far more.
    - Binary dose: 0.69 (0.30 to 1.13).
    - All four modifiers: 1.35 (0.34 to 2.45).
    - Met Council, Twin Cities alone: −0.79 (−3.02 to 1.82).
  - **Out-of-sample tests:**
    - **A (North Carolina): fail.** Durham city 279 observed vs 80% interval 35–283 (inside); Raleigh 263
      vs 90–378 (inside); Durham County 12 vs 0–7 (outside). Yearly coverage 75%.
    - **B (Minneapolis): fail.** 304 observed vs 63–290; yearly coverage 67%.
    - D-024's rule (every total inside its 80% interval) passes only about half the time for three places
      even when the model is right (0.8³ ≈ 0.51). This is noted, not changed.
  - **Reading:** this run gives no credible estimate of the missing-middle effect.
    - The central estimate is positive, but randomization inference finds nothing unusual (p = 0.70).
    - Two placebo checks fail, one city drives the result, and D-025's model, which fits overdispersion
      better, gives a negative estimate with an interval spanning 0.
    - Both out-of-sample tests fail, and Houston supplies nine-tenths of the added homes.
    - The scenario should not take this as its missing-middle evidence prong without a new dated entry.
  - **Open:** WS-MN has not yet coded St. Louis Park's 2025 rule or the explicit "no" rows; check 7b covers
    that gap.
- **Switch to D-025's estimator (2026-10-21, Ben; written before the run of its checks):**
  - **Why:** D-024 names "D-025's estimator if approved" as the fallback. D-025 was approved and on main
    (16:30, 2026-10-20) before both runs, and its estimator converges on the real panel. The 2026-10-20 runs
    used the Poisson-gamma model instead.
  - **Decision:** D-024's main estimate is now D-025's negative binomial with normal place random effects
    (`pooled_adu`, unchanged, through `estimate_mm.fit_nb`). The Poisson-gamma run stays reported as the
    comparison. Its point estimate on the real panel is already known from the 2026-10-20 robustness line:
    −0.25 (−1.10 to 0.77).
  - **One run (Ben approves exactly one):** the same `--full` pipeline, spec and seed, with `nb` as the main
    model (`--method nb`). It covers:
    - the wild score bootstrap (999 draws) and added homes;
    - randomization inference (999 reassignments);
    - checks 1–8, where leave-one-out covers Minneapolis and Houston dependence (each treated place left out,
      plus Durham city and county together);
    - robustness: PPML, Poisson-gamma, binary dose, four modifiers, Met Council alone;
    - out-of-sample tests A and B with the same pass rules.
  - **Convergence rule (fixed now):**
    - A fit that raises `EstimationError` is not used: BFGS did not converge, the Hessian was not negative
      definite, a coefficient left ±20, or an SE was effectively 0.
    - For randomization inference, failed reassignments are skipped and counted. p is the share of the
      fitted reassignments with |overall effect| ≥ the observed one.
    - **If more than 10% of reassignments fail, p is reported as unreliable,** because failures may not be
      random.
    - A check whose fit fails is reported as "could not be estimated", which counts as a fail.
  - **The overall effect** weights the bins by counterfactual expected homes (as for the fallback), so the
    two models compare like with like. D-025's own place-year weighting is not used here.
  - Outputs go to `reports/mm-d024-nb/`, next to the fallback's `reports/mm-d024/`.
- **Run with D-025's estimator (2026-10-21, 06:35–19:47; `--full --method nb`, outputs in
  `reports/mm-d024-nb/`):** the one approved run. It completed.
  - **Side by side** (log scale with 90% intervals; e^x − 1 is the proportional change in 2–4 unit homes at
    full dose):

    | | D-025 negative binomial (main) | Poisson-gamma fallback (2026-10-20) |
    |---|---|---|
    | Overall effect | **−0.25 (−1.05 to 0.86)** | 0.77 (0.07 to 1.54) |
    | Years 0–1 / 2–3 / 4+ | 0.07 / −1.29 / −1.85 | 0.79 / 1.14 / −0.13 |
    | Randomization inference | p = 0.96 (973 fitted, 26 failed: reliable) | p = 0.70 (956 fitted, 43 failed) |
    | 1. Pre-trend leads | pass (p = 0.59) | pass (p = 0.59) |
    | 2. Placebo dates | pass: 0.39 (−0.17 to 0.95) | **fail**: 0.54 (0.03 to 1.00) |
    | 3. Placebo outcome, 5+ units | pass: −2.01 (−3.21 to 1.29) | **fail**: −1.11 (−1.53 to −0.54) |
    | 4. Substitution, 1-unit homes (no rule) | −0.64 (−0.96 to −0.34) | 0.00 (−0.38 to 0.39) |
    | 5. Excluding 2020–21 | pass | pass |
    | 6. Leave one out (Minneapolis; Houston) | pass (−0.68; −0.57; all −0.71 to −0.12) | **fail** (Minneapolis out: −0.02) |
    | 7. Contamination (a) 50,000+; (b) pipeline-flagged dropped | pass (−0.19); pass (−0.51) | pass (0.94); pass (0.74) |
    | 8. Local counts re-fit (Minneapolis; Durham) | −0.64; −0.33 | 0.03; 0.51 |
    | Out-of-sample A (NC) / B (Minneapolis) | **could not be estimated** (rate guard) | **fail** / **fail** |
    | Added 2–4 unit homes, all 7 places | 2,631; Houston 2,338 (−1,390 to 4,048) | 2,650; Houston 2,422 (1,426 to 3,188) |

  - **D-025's other terms:**
    - price-to-cost: θ = 1.19 (0.34 to 1.99) per SD;
    - home value: θ = −1.23 (−1.99 to −0.44) per SD;
    - rate × treated: ρ = 0.43 (0.13 to 0.70);
    - ADU rule: δ = 0.06 (−0.80 to 1.04).
  - **D-025's robustness:**
    - binary dose: −0.23 (−0.79 to 0.52);
    - four modifiers: −0.83 (−1.80 to 0.50);
    - Met Council alone: −2.22 (−5.38 to 1.60);
    - Poisson-gamma: 0.77, as before;
    - PPML and the imputation estimator: did not estimate (PPML diverges).
  - **Out-of-sample:** both tests stopped at the guard that refuses a predicted rate above 5% of eligible
    parcels a year in any draw (D-023's rule, applied to every draw). Durham's and Minneapolis's draws
    combine wide bin effects with the modifier and rate terms. Under the convergence rule this counts as a
    fail.
  - **Added homes:** D-025's total comes from the modifier and rate terms, not the bins. With ρ > 0 and the
    2024–25 rates, and Houston's modifiers, its predicted gain is positive although the bin effects are
    negative. Its interval spans 0.
  - **Interval coverage:** the simulation that found too-narrow intervals (68–85%) tested PPML. D-025's
    coverage on this design has not been measured.
  - **Reading for a policymaker:**
    - D-025's estimate is the more trustworthy of the two. It allows for the year-to-year noise in permit
      counts, and it passes the three checks the fallback failed (placebo dates, placebo outcome, leave one
      out).
    - What it finds: within 2–6 years of the rule, the seven cities show no detectable rise in 2–4 unit
      permits relative to similar places. The central estimate is a 22% fall (−0.25). The interval runs from
      a 65% fall to a 136% rise, and the reshuffled reform dates produce effects this large 96% of the time.
    - **Neither estimate is credible enough to drive the scenario effects:**
      - the fallback fails three checks and both out-of-sample tests;
      - D-025's is too imprecise to size an effect, and its out-of-sample tests could not be run.
    - **Recommendation:** use the in-state estimate as validation only. The scenario's missing-middle effect
      should come from the pro forma and the external evidence. This result says a large short-run jump is not
      what these cities saw, and the pro forma's ramp should be consistent with that.
  - **Run time:** 13 hours, 12.5 of them randomization inference (999 refits at roughly 6 minutes each on 8
    workers, against about 1.5 minutes measured for single fits).
  - **Code as run:** `pooled_adu` as of commit 448be4c. Main's later changes to it were not used: score
    accumulation by `bincount` (identical to 1e-10, faster) and D-025's own retry-from-main-estimates
    convergence rule. D-024's convergence rule (above) applied instead.
- **Four-state refresh (2026-11-02; written and pushed before any estimate on the new data; thread 14):**
  - **Why:** the data threads closed (OH and TX 2026-11-01; NC and MN 2026-11-02). The new data
    gives almost four times as many treated places (27 against 7), the main reason to rerun after the
    October run gave no credible estimate.
  - **What changed in the sample (same rule: BPS places of 10,000+ in MN, NC, OH and TX plus every coded
    place, 2010–2025; holdouts as before):**
    - 560 places (MN 100, NC 56, OH 172, TX 232); 27 treated, **20 adopting inside 2010–2025** (MN 3, NC 10,
      OH 2, TX 5), against 7 treated in October. Counts and reconciliation with the readiness reports:
      `reports/engine14/panel_counts.md`.
    - Ohio's 172 include 16 townships of 10,000+ that issue permits (the OH report counted 156 places).
    - Ohio's and Texas's eligible-parcel tables were rebuilt after #252 (interpolation between two rolls).
  - **Rule date tags** (`model/rule_tags.py`, #264): a `[predates]` rule, or an earliest-known one dated on or
    before 2010-01-01 (the "allowed before the window" placeholder), is in force from 1990 and never an
    event; "none" rows (one home per lot) are controls; `[earliest-known]` or blank-adoption-date rows and
    `DATE UNCONFIRMED` rows are events at their coded dates in the main run.
  - **Specification, checks and pass rules unchanged:** D-025's estimator as the main model (switch of
    2026-10-21), same seed, the wild score bootstrap (999), randomization inference (999), checks 1–8,
    robustness (PPML, Poisson-gamma, Borusyak imputation, binary dose, four modifiers, Met Council alone), the
    2026-10-21 convergence rule, and the overall effect weighted by counterfactual expected homes. Leave one
    out now covers 27 treated places plus Durham city and county together.
  - **One tag sensitivity (Ben, 2026-11-02: keep the tag sensitivities light):** firm dates only. It leaves
    out the places whose in-panel event is `[earliest-known]`, has a blank adoption date or is
    `DATE UNCONFIRMED`: 8 NC places (Burlington, Garner, Monroe, Mooresville, Morrisville, Sanford, Wake
    Forest, Wilson), 552 places and 20 treated. A dropped place leaves the panel entirely (neither treated
    nor a comparison: its rule is real, only its date is in doubt). The separate "without `[earliest-known]`"
    and "without `DATE UNCONFIRMED`" runs are not made: the first drops the same places and the second none.
    Reported with the robustness lines; never used to choose.
  - **Out-of-sample tests:** A (North Carolina: Durham city, Durham County, Raleigh) and B (Minneapolis), as
    before: each target is left out, the model refitted and its counts predicted. They now have more
    post-reform years (Durham 2020–2025, Raleigh 2022–2025, Minneapolis 2020–2025). Same pass rules.
  - **Run once:** `uv run python scripts/dev/estimate_mm.py --full --method nb --workers 8 --out
    reports/mm-d024-4state/`, log in the same folder; whatever it shows is reported.
  - **Decided by:** Ben, 2026-11-02 ("let's run the engine"); written by WS-ENGINE before the run.
- **The four-state run (2026-11-02 19:57 to 2026-11-03 01:08, commit 0ca15cc; results in `reports/mm-d024-4state/`,
  log `run-2026-11-02-log.txt`; written after the run):**
  - **Fit:** BFGS converged on 560 places and 8,763 place-years; nothing dropped, no separation. Check 7b left
    out 15 pipeline-flagged comparison places, as specified.
  - **Main estimates (D-025's NB; log scale; 90% wild score bootstrap intervals):**
    - overall **1.75 (0.27 to 3.27)**, i.e. about 5.8 times the 2–4 unit homes at full dose;
    - years 0–1: 0.93 (−0.30 to 2.04); 2–3: 1.33 (−0.70 to 3.06); 4+: 3.28 (0.45 to 6.07);
    - price-to-cost: θ = −0.45 (−1.69 to 0.79); home value: θ = −0.02 (−1.23 to 1.14); rate: ρ = 0.01
      (−0.33 to 0.38); ADU rule: δ = −0.46 (−1.13 to 0.18).
  - **Randomization inference: p = 0.29** (999 reassignments, all fitted). Reshuffled adoption paths give an
    effect this large about three times in ten.
  - **Added 2–4 unit homes in the treated places' post-adoption years: about 5,560.**
    - **El Paso supplies 3,006 (54%)** and Houston 1,289 (23%); Lubbock 395, Minneapolis 324, the rest less
      than 150 each.
    - El Paso is one of the 7 places whose rule is in force for the whole panel (the `[predates]` and
      before-the-window rows; with Apex, Asheboro, Goldsboro, New Bern, Dayton and Grove City). Its 16 "post"
      years all sit in the 4+ bin. With place *random* effects (not fixed), that bin is identified partly by
      comparing these places with others across places, not by a change within them. Together the 7 supply
      3,364 of the added homes. This is a property of the specification, noted here, not changed.
  - **Checks:**
    1. Leads: **pass** (p = 0.83).
    2. Placebo dates (−2 years): **pass**, 0.43 (−0.11 to 0.97).
    3. Placebo outcome (5+ units): **fail**, 1.77 (0.80 to 4.66). The same places' 5+ unit permits rose by as
       much as their 2–4 unit permits, which points to growth in these places rather than the rule.
    4. Substitution (1-unit homes): −0.47 (−1.03 to 0.19).
    5. Excluding 2020–21: **pass** (1.76).
    6. Leave one out: **pass**. 1.18 without El Paso, 2.22 without Austin, 1.54–2.02 for the others;
       1.66 without Durham city and county.
    7. Contamination: 50,000+ only, **pass** (1.73); without the 15 pipeline-flagged places, **pass** (1.68).
    8. Local measurement (reported): Met Council 1.00 and Raleigh 0.98 against BPS; the Minneapolis city
       source 1.63, Durham 1.59.
  - **Robustness (overall effect):** Poisson-gamma 2.15 (1.40 to 3.11); PPML 2.14 (0.97 to 3.51); Borusyak
    imputation 0.65 (point only, 15 places); **binary by-right dose 0.59 (−0.11 to 1.41)**; four modifiers
    2.09 (0.57 to 3.71); **firm dates only 0.93 (−0.25 to 2.87)**; Met Council alone −2.02 (−5.24 to 1.81).
    PPML and the imputation estimator converged this time.
  - **Out-of-sample tests:**
    - **A (North Carolina): fail.** Durham city 279 observed vs 80% interval 40–293 (inside); Raleigh 263 vs
      29–243 (outside); Durham County 12 vs 0–5 (outside). Yearly coverage 69%.
    - **B (Minneapolis): pass.** 304 observed vs 268–1,967; yearly coverage 83%. The interval is wide and its
      centre (992) is three times what was observed.
  - **Reading (WS-ENGINE's, for Ben to confirm):** still **no credible estimate** of the missing-middle
    effect, by the same standard as October:
    - the central estimate is large and positive, but randomization inference finds it unremarkable
      (p = 0.29);
    - the placebo outcome fails with an effect of the same size, so the reformed places grew in general;
    - the effect shrinks to an interval spanning 0 under the binary dose and firm-dates-only fits, and to 0.65
      under the imputation estimator, which uses only within-place change;
    - more than half of the added homes come from one always-treated place (El Paso), identified across places;
    - out-of-sample test A fails.
    - What changed from October: more treated places, the leads, placebo dates and leave-one-out checks now
      pass, and every estimator converges. What did not: the timing test and the placebo outcome. The
      recommendation from October stands: use the in-state estimate as validation only. The scenario's
      missing-middle effect comes from the pro forma and the external evidence.
  - **Run time:** 5 h 11 min (randomization inference 4 h 35 min on 8 workers).

### D-025 · 2026-10-20 · ADU effect: pooled hierarchical negative binomial (pre-registered; main model replacing D-023's)
- **Why:** D-023's fixed-effects PPML was underpowered on the Twin Cities panel (53 places never recorded an
  ADU, 143 of 760 place-years kept, no modifier identified, the bootstrap tripped the guard; D-023 notes).
  Ben approved options 1 and 2 together (2026-10-20): pool the event-time effects and make the protocol's
  pooled model (§5.7) the main model. Written and pushed before any run of it on real data.
- **Main model (`src/lotline/model/pooled_adu.py`):**

  y_it ~ NegBin(mean μ_it, variance μ + κμ²),
  μ_it = Eligible_it · exp( a + u_i + γ_t + Σ_b β_b · D_it · 1[t − T_i ∈ band b] + Σ_m θ_m · z_im · 1[t ≥ T_i]
                            + ρ · (r_t − r̄) · 1[t ≥ T_i] + δ · MM_it ),  u_i ~ Normal(0, σ²)

  - bands b: event time k = 0–1, 2–3, 4+; D_it as in D-023 (grade × coverage, blanks per D-022);
  - u_i: place random effects (partial pooling: places with no ADU stay in, shrunk to the mean);
    γ_t: year fixed effects (first year 0); log(eligible parcels) offset;
  - z_im: the D-023 pre-adoption modifiers as z-scores over the treated places (θ per SD); places adopting
    before 2010 don't inform them (Ben, D-023 run choices); modifiers stay in and are flagged **weakly
    identified** when their 90% interval spans more than 1 on the log scale; never dropped silently;
  - r̄: the panel's mean rate.
- **Estimation:** maximum marginal likelihood; each place's integral over u_i by adaptive Gauss-Hermite
  quadrature with 31 nodes (15 proved too few for skewed places against brute-force integration in
  development); BFGS with analytic scores (posterior-weighted quadrature sums; checked against numerical
  derivatives); log σ and log κ mapped through tanh to stay within ±6 and ±8, and a variance parameter at its
  limit (no place heterogeneity, or Poisson counts) is held there and reported.
- **Separation and identification:** columns with no non-zero value, or whose non-zero rows all have zero
  counts, are dropped and reported; the iterated rectifier (Correia, Guimarães & Zylkin 2019) on the fixed
  design drops any separated rows; columns that become collinear are then dropped, intercept first; all
  reported. The fit fails loudly (`EstimationError`) if BFGS doesn't converge, a coefficient other than the
  intercept leaves ±20, the Hessian (free parameters) is not negative definite, or an SE is effectively 0.
- **Inference:** wild cluster score bootstrap by place, 999 draws, Webb weights (one Newton step from the
  estimate with the analytic place scores); basic bootstrap 90% intervals. **Overall effect** = the band
  effects averaged with weights equal to the treated place-years in each band. Randomization inference: 999
  permutations of adoption years among treated places, re-fitting the model; statistic = the overall effect.
- **Checks (D-023, same pass rules, applied to this model):** pre-trend leads k = −3…−1 jointly zero (Wald
  with the bootstrap covariance, pass p ≥ 0.10); placebo adoption 2 years early on pre-adoption data
  (overall effect's 90% interval contains 0); placebo outcome, permits in 5+ unit buildings (same); excluding
  2020–21 (band effects and overall effect inside the main 90% intervals); leaving out each treated place
  (overall effect inside the main 90% interval).
- **Robustness (reported, not used to choose):** D-023's fixed-effects PPML with the pooled bands (reported
  as "did not estimate" with the guard's message if it fails); the Borusyak-Jaravel-Spiess imputation
  estimator for counts (PPML with place and year effects on untreated place-years, imputed untreated means for
  treated place-years, effect per band = log Σy / Σμ̂0; place-cluster pairs bootstrap, 999 draws); the main
  model with a binary by-right dose.
- **Transport test (D-023 rule):** Austin 2016–2023, Raleigh 2021–2025, Durham 2019–2025, predicted with
  this model's bootstrap draws and year effects, each place's own pre-adoption modifiers, its random effect
  from its pre-adoption years (posterior mode and curvature, a normal draw) when it has permits then, else
  u ~ Normal(0, σ²), negative-binomial counts; widened outside the Minnesota modifier range (as D-023). Passes
  if each place's observed total lies in its 80% interval and yearly 80% coverage is 60–95%. Raises on
  non-finite or absurd (> 5% of eligible parcels a year) means.
- **Sample, holdouts, exclusions:** as D-023 (Twin Cities places with Met Council permits, 2016–2025; St.
  Paul out entirely; Charlotte from 2023-06 never used; places with no dated ADU rule left out and counted).
- **Simulation properties (development, before any real run):** on synthetic panels with ~70% all-zero
  places and ~50–130 ADU permits, band effects, θ, ρ and δ were covered by their 90% intervals in at least
  22 of 30 panels each; with no reform effect and a −0.7 common shock from 2022, the overall effect's 90%
  interval contained 0 in 87–97% of 70 panels, with a small negative lean (~−0.15, a third of its spread).
- **Run once;** whatever it shows is reported. No re-specification without a new dated entry.
- **Decided by:** Ben, 2026-10-20 (options 1 and 2); details written by WS-ENGINE before the run.
- **The run (2026-10-20, once; log `reports/adu-d025/run-2026-10-20-log.txt`):** the main model converged on
  the full panel (76 places, 760 place-years, 31 treated, 53 with no ADU in any year; no column dropped, no
  separated rows, no variance parameter at a bound) and its estimates with bootstrap intervals were printed.
  The run then **stopped at randomization inference**: one of the 999 refits with permuted adoption years
  did not converge (BFGS) and the guard raised `EstimationError`, so randomization inference, the five checks,
  the robustness estimators and the transport test were not computed and no CSV was written. The main-model
  estimates are reported as they stand, without those checks. Not re-run. Decision needed (new dated entry):
  how to treat a permutation refit that does not converge (e.g. count and report failed permutations and
  compute the p-value over the rest, or restart BFGS from the main estimate), then run the remaining stages
  once.
- **Convergence rule for repeated refits (Ben, 2026-10-20; written before the remaining stages are run):**
  in any stage that refits the model many times (randomization inference, the wild bootstrap, leave-one-out
  and the checks), a refit that does not converge is retried once, starting from the main-model estimates;
  if it still fails it is excluded and counted, and results are reported over the rest ("998 of 999
  converged; p over 998"). Isolated failures never stop the run. A stage stops, and is reported as not
  computed, only if failures exceed 5% of its refits; a stage that is a single refit (a check, the binary
  dose) is reported as not computed if it fails after the retry, and the run continues. Wild-bootstrap draws
  are one Newton step, not refits: a draw beyond the coefficient bound is excluded and counted the same way.
  The remaining stages (randomization inference, the five checks, robustness, transport) are then run once,
  reusing the main model as estimated: its fit is recomputed deterministically only to recover the Hessian
  and place scores, and checked to match the logged estimates.
- **Remaining stages run (2026-10-20, once; log `reports/adu-d025/remaining-2026-10-20-log.txt`, 5 h 07 min):**
  the main model was recomputed and matched all 22 logged estimates to 1e-4 (reused, unchanged); its wild
  bootstrap kept 999 of 999 draws. **Randomization inference: 928 of 999 permutation refits converged (84 on
  the retry from the main estimates, 71 excluded = 7.1%), above the 5% limit, so the stage is not computed.**
  A defect in the run script then stopped the whole run instead of only that stage (the stage failure was not
  caught), so the five checks, the robustness estimators and the transport test were not run. Fixed in code
  (the script now records a failed stage and continues; randomization inference stops as soon as its 5%
  limit is broken) but **not re-run**: running the checks, robustness and transport needs Ben's go-ahead.
  Reading: about 1 in 14 permuted adoption-date panels does not converge even after a retry.
- **Checks, robustness and transport run (2026-10-21, once; log `reports/adu-d025/stages-2026-10-21-log.txt`;
  Ben approved; refits sped up first by an identical score accumulation, 7442d47):** main model reused
  (matched all 22 logged estimates; bootstrap 999/999 kept). Randomization inference not re-attempted: **not
  computed: 71 of 999 (7.1%) failed, above the 5% limit**. Checks against D-023's pass rules:
  1. pre-trend leads: Wald 5.94, **p = 0.025 → fails** (the D-023 rule calls for HonestDiD bounds);
  2. placebo dates (−2 years): **not computed** (the refit did not converge after a retry);
  3. placebo outcome (5+ units): 0.48 (−0.62 to 1.64) → passes;
  4. excluding 2020–21: overall 2.91, every band and the overall effect inside the main intervals → passes
     (the refit converged on the retry);
  5. leave one treated place out: 31 of 31 refits converged (3 on retry); no place moves the overall effect
     outside its interval → passes.
  Robustness: fixed-effects PPML (193 rows kept; two modifiers collinear with fixed effects): bands −0.16,
  −0.59, −0.39 with SEs ≈ 2.4 (uninformative); Borusyak imputation: only 7 treated place-years imputable
  (162 not: their places have no permits before adoption): bands −0.52 (−1.71 to 0.68), −1.55 (−3.09 to
  −0.35), 4+ not estimable, overall −0.94 (−2.25 to 0.30); binary dose: overall 1.50 (0.33 to 2.67), bands
  1.48, 1.23, 1.61. **The robustness estimators do not support the main estimate's size, and the imputation
  estimate has the opposite sign on very few rows.** Transport: **not computed**: the code checked single
  predictive draws against the 5% limit, while this entry specifies the predicted mean; with σ ≈ 2.1 Austin's
  draws (no pre-adoption years, so u from the prior) exceeded it. Fixed to check the mean, with a test, and a
  transport failure now records the stage instead of stopping the run; **not re-run** pending Ben.
- **Transport re-run (2026-10-21, once, Ben approved; log `reports/adu-d025/transport-2026-10-21-log.txt`):**
  transport only, with the guard on the predicted mean; main model reused (matched all 22 logged estimates).
  **Fails the D-023 rule:** totals inside their 80% intervals: Austin no (observed 2,545 vs P10–P90 0–279),
  Raleigh no (230 vs 0–49), Durham yes (269 vs 9–272); yearly coverage 15% (rule 60–95%). No place is outside
  the Minnesota modifier range. Austin has no pre-adoption years in its window (adopted 2010), so its effect is
  drawn from the prior; in Raleigh (2022 on) and Durham (2020 on) the missing-middle term δ = −2.69, identified
  from Minneapolis alone, pushes predictions far below what was observed.
- **HonestDiD bounds: choices fixed before running (2026-10-21, WS-ENGINE; Ben asked for them because the
  pre-trend test failed, as D-023 pre-registers; Rambachan & Roth 2023):**
  - *Event study input:* the pre-trend-leads refit (the one check 1 used): the lead coefficients for event
    times k = −3, −2, −1 are the pre-period coefficients, relative to the omitted periods (k ≤ −4 and the
    never-treated). That reference, not k = −1, is normalised to 0, so the restrictions chain from
    δ_{−4} = 0 through the estimated δ_{−3}, δ_{−2}, δ_{−1}.
  - *Target:* the pooled post-adoption effect at realised doses, θ = the mean over treated place-years with
    k ≥ 0 of β_band(k) × dose_it (same bands, weights by place-years). The bias for that target is
    Σ_k ω_k δ_k, where ω_k is the share of those place-years at event time k (k = 0 … the panel's largest),
    since the leads are indicators, not dose-scaled.
  - *Relative magnitudes, Δ^RM(M̄):* every post-period step |δ_k − δ_{k−1}| ≤ M̄ × M_pre, with
    M_pre = max(|δ_{−3}|, |δ_{−2} − δ_{−3}|, |δ_{−1} − δ_{−2}|). The bias is in δ_{−1} ± M̄ M_pre Σ_k ω_k (k + 1)
    (ω ≥ 0, so the extreme is every step at the bound). M̄ ∈ {0.5, 1, 1.5, 2}.
  - *Smoothness, Δ^SD(M):* post-period second differences at most M, extrapolating the last pre-period slope
    s = δ_{−1} − δ_{−2}. The bias is in Σ_k ω_k [δ_{−1} + (k + 1) s] ± M Σ_k ω_k (k + 1)(k + 2) / 2.
    M ∈ {0, 0.05, 0.1, 0.2} (log points per year²; M = 0 is linear extrapolation).
  - *Inference:* the identified set's bounds are recomputed on each of the leads refit's 999 bootstrap draws
    (θ, δ and M_pre all re-drawn). The 90% robust interval runs from the 5th percentile of the lower bound to
    the 95th percentile of the upper bound. This is simpler than Rambachan & Roth's conditional (ARP) and
    FLCI intervals, and conservative.
  - *Reported:* identified set and robust interval for each M̄ and M, the breakdown M̄ (the smallest at which the
    interval includes 0), the original θ, and the ω_k. No result is used to choose a specification.
  - *Code:* `pooled_adu.honest_bounds`, tested on a synthetic event study with a known linear violation.
- **Implementation note: faster refits, estimates unchanged (2026-10-22, Claude Code; not a new decision):**
  real runs were slow (randomization inference took hours; hard refits run to the BFGS iteration limit).
  `pooled_adu` now (1) evaluates all 31 quadrature nodes at once with the same arithmetic in the same order,
  so log-likelihoods, scores, BFGS paths and estimates are **bit-identical** to the first runs'; (2) computes
  the Hessian analytically (Louis' identity) instead of by central differences of the analytic gradient,
  which agrees to 1e-7 relative and doesn't enter the estimate (`hessian="numerical"` keeps the old one);
  (3) can run the independent refits (randomization inference, leave-one-out, the single-refit checks) in
  parallel processes, with every permutation drawn up front in the serial order and results read back in
  order, so outputs, convergence counts and the 5% stop are the serial run's (`--workers`).
  **Checked on synthetic panels:** 999 permutations gave the same p and the same 999 permuted effects to the
  last bit (719 s → 342 s serial, 95 s on 8 processes); 360 hard refits (6 panels with retries and exclusions)
  gave identical effects and identical counts (303 first, 27 retried, 30 excluded) 3.5× faster. A warm start
  of BFGS from the main fit's curvature was tried and **not adopted**: its estimates differ from a cold
  start's at the stopping tolerance (~1e-4) and on the hard panels it excluded 41 refits instead of 30
  (`WARM_START`, off). A real rerun still needs Ben's approval; the scripts' check against the logged
  estimates (1e-4) is how it would confirm equivalence. Tests: `tests/model/test_pooled_adu.py` (speed
  section).
- **Four-state refresh (2026-11-02; written and pushed before any estimate on the new data; thread 14):**
  - **Why:** the data threads closed; Ben decided on 2026-10-30 to pool Texas into this estimate, and the
    Minnesota rules gained second-coder dates and tags.
  - **Sample:** Twin Cities places with Met Council permits, 2016–2025 (as before; 76 places: 43 with an
    in-window change, 28 "no ADUs" controls and 5 with only older rules), **plus Texas's four record-level
    cities over the years their sources count ADUs in full:**
    - Austin 2016–2023 (treated): its R-102 ADU flag stops with HOME (February 2024): 243, 90 and 9 ADU
      permits in 2023–2025 while two-unit permits rise to 384, so 2024–2025 measure a coding change;
    - San Antonio 2021–2025 (treated; the file starts 2020-07);
    - Fort Worth 2016–2025 (comparison): its ADUs are non-rental (#222) and still count, since the outcome is
      ADUs built, not rented;
    - Dallas 2016–2023 (comparison; the file ends 2024-11).
    - In all: 80 places, 791 place-years, 31 treated (21 adopting in the panel years), 53 with no ADU in any
      year, 3,192 ADU permits (Austin about four-fifths). `reports/engine14/panel_counts.md`.
  - **Not pooled now (the open sample questions, answered conservatively):** North Carolina stays out of the
    sample, so the transport test stays out of sample. Ohio's 15 places stay out: their counts are lower
    bounds from ADU-only permit files, and 6 of their 7 changes fall in 2023–2025. Either can be pooled later
    with a new dated entry.
  - **Rule date tags:** read by `model/rule_tags.py` (#264), as in D-024's refresh entry.
  - **Specification, checks and pass rules unchanged:** the model, estimation, bootstrap (999),
    randomization inference (999), the five checks, robustness, the D-031 sensitivity runs and the
    2026-10-20 convergence rule. Year effects stay common to all places, as pre-registered (no state-by-year
    effects); with Texas in, a Texas-wide shock is absorbed only through the year effects shared with
    Minnesota. This is noted as a limitation, not changed.
  - **One tag sensitivity (Ben, 2026-11-02: keep it light):** firm dates only, a fresh fit with the wild
    bootstrap: 9 MN places leave the panel (71 places, 27 treated). Reported, never used to choose.
  - **Transport test:** Raleigh 2021–2025 and Durham 2019–2025, same rule; Austin is now in the sample and
    leaves the test.
  - **HonestDiD:** if check 1 (pre-trend leads) fails, the bounds are computed once with the choices fixed on
    2026-10-21 (`--honest`).
  - **Run once:** `uv run python scripts/dev/estimate_pooled_adu.py --full --workers 8 --out
    reports/adu-d025-4state/`, log in the same folder; whatever it shows is reported.
  - **Decided by:** Ben, 2026-11-02 ("let's run the engine"); written by WS-ENGINE before the run.
- **The four-state run (2026-11-02, 19:56, once; commit 0ca15cc; log
  `reports/adu-d025-4state/run-2026-11-02-log.txt`): no estimate.** The main model **did not converge**:
  BFGS reached its 500-iteration limit (19,445 likelihood evaluations, 27 s), so the guard raised
  `EstimationError` and no stage ran (no bootstrap, checks, sensitivity or transport; no CSV). Not re-run.
  - **Diagnosis (convergence information only, no coefficient read or reported; the same deterministic fit
    with the guard off):** 19 columns, none dropped, no separated rows; no coefficient near ±20; neither
    variance parameter at its bound. So this is slow convergence, not an identification failure. The likely
    cause is scale: Austin's 2,500 ADU permits in 8 years now sit beside Minnesota places with a few each.
  - **Decision needed (new dated entry, Ben):** for example, the October refit rule applied to the main model
    (a retry with a higher iteration limit, or from a Minnesota-only start), or Texas pooled differently.
    Until then D-025's October estimate on Minnesota alone stays the one on record.

### D-029 · 2026-10-20 · Baseline calibration fixes and state-total scoring (pre-declared before any run)
- **Why:** a review on synthetic data (2026-10-20, coordinator session) found five problems in the baseline
  engine. In simulation, log forecast error against log(origin level / 5-year mean) had correlation 0.66,
  state-year P10–P90 coverage was 74% and 5-year total coverage 68% (nominal 80%). (1) The cycle's random
  walk starts at 1 from the level-window mean, not at the state's level in the origin year
  (`model/baseline.py`), a likely cause of the NC/TX under-forecast (D-006, D-011). (2) Spec C applies
  exp(β_h · g + β_p · q) with uncentred signals while dropping β_0 (`model/demand.py`), so a place at average
  demand gets a multiplier that is not 1; D-007's rejection of spec C rests on that bug, and its test
  re-implemented the formula and missed it. (3) The negative-binomial 1/k and the place's own variance
  (`use_direct_variance`) are estimated on raw annual counts that already contain the cycle, so cycle variance
  is counted twice. (4) The same `default_rng(simulation_seed)` is restarted for every size class, so classes
  share random numbers by accident. (5) The backtest scores only place-years, never state totals, and the V1
  windows have been used to choose specifications.
- **Fixed now, before any run (each with a hand-worked synthetic test):**
  1. **Cycle starts at the origin-year state level** (`cycle_start_at_origin` = 1). Each place's level is
     multiplied by a_s = S_T / S̄, where S_t is the state's total of the size class over the places that have a
     level, S_T its origin-year value and S̄ its mean over the level window; the random walk then runs from
     there, so E[S_{T+h}] = S_T when nothing changes. The level's variance scales by a_s². This is
     `state_momentum` with a 1-year recent window; if `use_state_momentum` = 1 its factor replaces a_s (never
     both). 0 restores the old start.
  2. **Spec C centred at the fit-sample means.** Multiplier = exp(β_h (g − ḡ) + β_p (q − q̄)), with ḡ, q̄ the
     means of g and q over the Poisson fit sample (the regression is fitted on the centred signals; slopes are
     unchanged, β_0 becomes the drift at average demand). β_0 stays unapplied, as D-006 intended: a place at
     average demand keeps spec B's level.
  3. **Dispersion on detrended counts** (`detrend_dispersion` = 1). Before 1/k and the place's own variance of
     annual rates are computed, each place-year count (and rate) is divided by the state's cycle index for that
     year, s_t = S_t / S̄ over the level window (s_t = 1 where S_t = 0). With no cycle (s_t ≡ 1) both estimates
     are exactly as before. 0 restores the raw estimates.
  4. **Random numbers per size class**: the per-place draws come from `default_rng([seed, size class column,
     state, origin])`, so classes and states never share random numbers by accident. The cycle years stay
     shared on purpose (D-011).
  5. **State-total scoring in V1.** For every state, fit end, size class and forecast year, the scored places'
     draws are summed draw by draw (so the shared cycle is kept), and compared with the sum of the same places'
     observed counts; also the window total (all forecast years, places scored in every year). Reported: the
     randomized P10–P90 coverage (D-003), the PIT histogram in deciles (non-randomized PIT, Czado et al. 2009),
     the CRPS of the summed draws, and absolute error of the P50 of the sum against the benchmarks' sums.
     These are **reported, not new pass criteria**; 80% is the reference.
- **V1 is a development set.** The 2016/2018/2020 windows have been used to choose among specs A, B and C,
  state momentum, the D-011 cycle fix and the scoring floor, so V1 scores are in-sample for specification
  choice and are labelled "development set" in the backtest output and reports. Confirmatory evidence comes
  only from the holdout tests.
- **Runs declared now (MN NC OH TX, fit ends 2016/2018/2020, eligibility rule as on `main`):** spec B old
  (`main` before this change) and new (all five fixes), place-level and state-level; attribution runs of the
  new code with `cycle_start_at_origin` = 0 and with `detrend_dispersion` = 0; spec C once with the fix. All
  are reported in the PR, whatever they show. No parameter is tuned on these runs; adopting the new baseline,
  and whether spec C deserves another look, is Ben's decision, logged as a later entry.
- **Decided by:** pre-declared by Claude Code (WS-ENGINE) at the coordinator session's request, 2026-10-20;
  Ben to confirm in the PR.

### D-030 · 2026-10-20 · ADU scenario: how the uncertainty draws are made
- **Was (`scenarios/adu.py` `draw_params`, `run`):** every parameter drawn triangular(low, central, high),
  including the estimated anchor `adu_mature_hazard_ref` (1.038e-3, 90% profile interval 0.453e-3–3.173e-3),
  whose triangular median is 1.47e-3, 41% above the estimate; the place-effect variance α fixed at 4.735; the
  extrapolation noise z drawn independently for every place, so it averaged out in state totals; the 2015–25
  mortgage stress range drawn triangular(2.96, 6.60, 6.81) (mean 5.46%) as if it were a forecast, independently
  of the cap rate and construction-loan rate; and the judgment parameters drawn independently of an anchor that
  was fitted at their central values.
- **Now:**
  - the anchor and α are lognormal with median at the estimate and log-SD from the 90% interval,
    (ln high − ln low) / 3.29 (anchor 0.592, the fit's own predictive-check convention; α 0.281 from the fit's
    observed information, giving 2.98–7.52); their correlation from the observed information (0.004);
  - each draw shifts log anchor and log α by Σ_j g_j (p_j − central p_j), g_j = d log θ̂ / d p_j from refitting
    the D-019 fit 3 likelihood with each judgment parameter moved by ±10% of its range
    (`scripts/dev/calibrate_adu.py --draw-terms` → `config/params/adu_anchor.yaml`; 19 parameters enter the
    fit, the largest being the partial-rule share, −3.05 per unit, and the ramp half-life, +0.27 per year);
  - the extrapolation noise is √s · z_draw + √(1 − s) · e_place with `adu_extrapolation_shared_share` s = 1.0
    (choice: it is a transport-model error; place-to-place differences are already in the fitted place
    effects); 0.5 is a sensitivity;
  - the mortgage rate is held at the central 6.60% in the forecast draws; its 2015–25 low and high are run as
    sensitivities (`scripts/dev/adu_dev_run.py`), so the cap-rate and loan-rate draws no longer mix with a
    rate scenario.
- **Effect (development run, origin 2025, five-year additional homes, P10 / P50 / P90):** Minnesota
  779 / 1,556 / 2,880 → 271 / 845 / 2,623; North Carolina 1,044 / 2,272 / 4,847 → 355 / 1,212 / 4,059; Ohio
  574 / 1,262 / 2,920 → 133 / 506 / 2,462; Texas 4,074 / 8,211 / 16,607 → 1,334 / 4,417 / 15,515. Rates at
  2.96% raise every state by about 30%; at 6.81%, under 2%.
- **Found while doing it, not changed here:** re-running the fit 3 likelihood on today's coded rules gives
  41 places and 253 place-years (θ̂ 0.000879, α̂ 3.52), not the 16 places and 115 place-years behind the
  configured 0.001038 and 4.735; the observed-information SE and the slopes come from today's fit set and are
  applied around the configured values. Refreshing the anchor itself is a separate decision.
- **Why:** reviewing the ADU ranges (2026-10-20) found them biased upward at the median and too narrow at the
  state level. Every result must be a range that a reader can trust (Rules; CLAUDE.md).
- **Decided by:** proposed by Claude Code (ADU draws fix), for Ben to confirm.

### D-031 · 2026-10-21 · ADU effect: additive imputation as robustness to D-025, and review fixes ported to the D-025 path (written after D-025's main estimate was seen; not the main estimator)
- **What had been seen when this was written:** D-025's main estimate (overall 2.26 on the log scale, 90%
  interval 0.22–4.21) and its 2026-10-21 checks and robustness results (above). **This entry cannot change
  the D-025 main result.** It adds a robustness estimator, fixes defects in code the remaining D-025 stages
  use, and declares sensitivity runs before those stages are run. It was first drafted on 2026-10-20 (under a
  number since reserved by handoff 09) as a proposed replacement for D-023's main estimator. Ben kept D-025 as the main model (2026-10-21),
  so it was renumbered and reframed. No D-031 estimate has been computed on real data.
- **The 2026-10-20 review of D-023 (checked against the code and reproduced on synthetic panels), and what
  still applies:**
  1. treated places with no ADU before adoption had their pre-years dropped as separated, and their cohort
     cells entered the aggregate as near-zero contrasts (a simulated true log-50 effect came out near
     2.5–3.2); 2. places treated before 2016, and the 2016 cohort, have no untreated year, so already-treated
     places identified the year effects; 3. with singleton cohorts θ × post was collinear with the cohort
     cells; 4. the CR2 score bootstrap undercovered with singleton cohorts (37% for a 90% interval over 30
     synthetic panels). These are defects of D-023's fixed-effects design, which D-025 replaced. D-025's own
     imputation robustness run shows the data side of defect 1: 162 of 169 treated place-years could not be
     imputed, because their places had no permits before adoption.
  5. Permit or conditional-use places count as never treated, and the dose before T is ignored. This still
     holds in D-025 and is **not changed** here; the D-031 estimator handles it with a replaced-rule control.
  6. Randomization inference permuted T but not the dose path: **applies to `pooled_adu`; fixed (a).**
  7. D-023's transport used the largest year effect after the panel. D-025's transport refuses years
     outside the estimation years, so this does not apply.
  8. Household growth was measured from max(T − 1, 2015), giving 2010–15 adopters post-adoption growth. It
     is in the shared panel builder: **fixed (b).**
- **Deviations from D-025, written before its remaining stages (randomization inference, placebo dates,
  transport, HonestDiD) are run:**
  - **(a) Randomization inference moves each place's dose path with its permuted adoption year**
    (`estimate_adu.permute_adoption`): dose_new(t) = dose_old(t − (T_new − T_old)), held at the first
    observed value before the panel and the last after it. The 2026-10-20 attempt (7.1% of refits failed)
    permuted T only. A permuted place's post years then carried its old dose, often 0 or a permit grade. That
    may have contributed to the failed refits; this is not tested.
  - **(b) Household growth** = log(households at T − 1 / households at T − 6), and **missing** unless both
    ACS vintages exist (`estimate_adu.household_growth`). For places adopting in 2010–15 the modifier
    becomes missing, which means a zero deviation in the design. The D-025 main fit used the defective
    values, so `estimate_pooled_adu.py --remaining` will stop at its 1e-4 match check. **Decision for Ben:**
    (i) re-estimate the main model once on the corrected panel, report both, and condition the remaining
    stages on the corrected one (recommended: the defect is a measurement bug, independent of results); or
    (ii) keep the main model as estimated and report the corrected-growth refit as a sensitivity.
  - **(c) Sensitivity runs of the D-025 model** (`pooled_adu.sensitivity_runs`). Each is one refit under
    the D-025 convergence rule, with score-bootstrap intervals, reported beside the main estimate and not
    used to choose:
    1. *excluding places treated before 2016*, which have no untreated year in the panel (review point 2);
    2. *T at the announcement year* (C29): the coded `announced_date`, else the council `adoption_date`, of
       the rule that made the place by right; places with neither keep T and are counted. The dose path moves
       with T. With no anticipation this moves zero-effect years into band 0–1, so a smaller 0–1 band is
       expected; a larger effect points to anticipation;
    3. *parking and process reforms as time-varying controls* (C08, C21): 1 if a citywide zero-minimum
       parking reform (`adu.parking_waived`) or any coded process reform is in force on 1 July. A control
       with no variation is dropped and reported; on 2026-10-21 `config/reforms/mn.csv` codes 2 parking
       rows and no process rows.
- **D-031 robustness estimator: imputation on the additive scale** (`estimate_adu.impute`, reported
  beside D-025's log-scale imputation):
  - untreated model by PPML on untreated place-years only: E[y(0)] = Eligible · exp(α_i + γ_t + λ'Z), with
    Z = the replaced ADU rule's dose (carried forward from T − 1 in treated years), parking, process and
    missing middle;
  - ATT_k = 1,000 · Σ (y − μ̂0) / Σ Eligible for k ∈ {0–1, 2–3, 4+} and overall, in additional permits per
    1,000 eligible parcels a year; the ratio Σ (y − μ̂0) / Σ μ̂0 is secondary;
  - places treated in or before 2016, and treated places with no kept untreated year, are excluded and
    listed; an upper bound that counts every permit of the zero-pre places as additional is reported
    beside the ATT;
  - range: stratified place bootstrap (treated and untreated places resampled separately, 999 draws);
  - fewer than 3 contributing treated places means "not estimable". Given D-025's imputation run (7
    imputable treated place-years), this is the expected outcome in Minnesota. The estimator's value there is
    to state the exclusions and the zero-pre bound plainly.
- **Evidence (synthetic panels, `tests/model/test_estimate_adu.py`):** each regime test asserts that D-023
  fails and D-031 passes on the same panel. Zero pre-periods: D-023 2.5–3.2 against log 50; D-031's
  additive ATT within 10%. A 2016 cohort: D-023 ≈ −0.1 against ~0.9; D-031 within 15%. Pre-panel adopters
  whose effect keeps growing past k = 5: D-023 ≈ 0 against ~0.45; D-031 within 15%. Singleton cohorts:
  D-023 drops θ as collinear and undercovers; D-031 is unbiased, and its bootstrap covered 77% for a nominal
  90% over 30 panels, so with fewer than 10 contributing places its range is labelled "probably too narrow".
- **Not carried over from the first draft:** randomization inference as primary for this estimator, its own
  seven checks and transport, and the hierarchical-NB priors (D-025 already has θ).
- **Decided by:** Ben, 2026-10-21 (D-025 stays the main model; this estimator is robustness). Details by
  Claude Code; **(a)–(c) and the household-growth choice await Ben's approval.**
- **Plan for the corrected-growth refit (2026-10-21, written before running; Ben chose option (i) for (b)
  and approved each run once):**
  - *Panel:* the D-025 panel with household growth measured by `household_growth` (missing unless the T − 1
    and T − 6 vintages exist). `estimate_pooled_adu.py --hh-growth as_run` reproduces the first main model's
    panel, so both can be compared; the run prints every place whose household growth changes.
  - *Runs, once each:* `--full --hh-growth corrected`. This is the main model, its wild score bootstrap, and
    the remaining stages under the D-025 convergence rule: randomization inference with dose paths moved
    (D-031 (a)), the five checks, the robustness estimators (fixed-effects PPML, log-scale imputation,
    binary dose, D-031 additive imputation), the D-031 (c) sensitivity runs, and the transport test (guard on
    the predicted mean). The as-run main's transport is WS-ENGINE's 2026-10-21 re-run (above) and is not
    repeated.
  - *Comparison reported:* θ_hh_growth, the band effects and the overall effect, as-run against corrected,
    with their 90% intervals. "Household growth matters for this test" is defined in advance: the overall
    effect moves by more than a quarter of the as-run interval's half-width (0.5 log points), or its 90%
    interval starts or stops containing 0, or the transport verdict changes. Otherwise it does not matter
    here.
  - *HonestDiD for the corrected main:* computed with WS-ENGINE's `pooled_adu.honest_bounds` (the choices
    fixed above) once it is on `ws/engine-17-d025-results`; pending if it is not there when the refit ends.
    No separate implementation.
  - *Logs:* `reports/adu-d025/corrected-2026-10-21-log.txt`, CSVs in `reports/adu-d025/corrected-2026-10-21/`.
- **Corrected-growth refit (2026-10-21, once; log `reports/adu-d025/corrected-2026-10-21-log.txt`, CSVs in
  `reports/adu-d025/corrected-2026-10-21/`; 2 h 15 min):** household growth became missing for 5 places
  (Eagan 2014, Hugo 2012, Lakeville 2013, Minneapolis 2015, Richfield 2015). Every stage was computed.

  | | As-run main (2026-10-20) | Corrected main |
  |---|---|---|
  | θ_hh_growth (per SD) | −0.37 (−1.67 to 1.05) | 0.17 (−1.63 to 2.08) |
  | Band 0–1 | 2.32 (0.61 to 3.93) | 2.36 (0.56 to 4.00) |
  | Band 2–3 | 1.88 (−0.52 to 4.15) | 1.97 (−0.60 to 4.36) |
  | Band 4+ | 2.38 (−0.01 to 4.72) | 2.53 (−0.15 to 5.11) |
  | Overall | 2.26 (0.22 to 4.21) | 2.37 (0.12 to 4.51) |
  | Randomization inference | not computed (7.1% of refits failed, T-only permutation) | p = 0.111 over 970 of 999 (2.9% failed; dose paths moved) |
  | Pre-trend leads (pass p ≥ 0.10) | p = 0.025, fails | p = 0.052, fails |
  | Placebo dates | not computed | not computed |
  | Placebo outcome | 0.48 (−0.62 to 1.64), passes | 0.69 (−0.50 to 1.86), passes |
  | Excluding 2020–21 | passes | passes (3.18) |
  | Leave one out | passes | passes |
  | Transport (WS-ENGINE's as-run re-run vs this run) | 1 of 3 totals inside, yearly 15%: fails | 1 of 3 totals inside (Durham), yearly 15%: fails |

  The other estimates were close to the as-run ones (bands within 0.15, θ for price-to-cost −0.65 vs −0.58,
  δ −2.75 vs −2.69). Robustness on the corrected panel: fixed-effects PPML −0.16 / −0.59 / −0.39 (SEs ≈ 2.4);
  log-scale imputation overall −0.94 (−2.25 to 0.30) on 7 imputable rows; binary dose 1.57 (0.41 to 2.71);
  D-031 additive imputation **not estimable** (2 contributing treated places: 9 treated in or before 2016,
  22 with no ADU before adoption). D-031 (c) sensitivity runs, each inside the main 90% interval: excluding
  the 7 places treated before 2016, 2.92 (1.14 to 4.62); T at the announcement year (11 places re-dated),
  2.99 (1.13 to 4.98); parking and process controls, 3.01 (1.37 to 4.70).
  **Reading, by the rule fixed in the plan:** household growth **does not matter for this test**. The
  overall effect moves by 0.11, under the 0.5 threshold; its interval still excludes 0; the transport
  verdict is unchanged. θ_hh_growth is uninformative either way (intervals ±1.5 around 0). The randomization
  inference that now computes cannot be credited to household growth: this run also moved dose paths (D-031
  (a)), and refit failures fell from 7.1% to 2.9%. Its p = 0.111 means the overall effect is not
  distinguishable at 10% from effects produced by reshuffled adoption years. HonestDiD bounds for the
  corrected main are **pending** WS-ENGINE's `honest_bounds`.
- **HonestDiD run plan (2026-10-21, written before running; Ben approved one run per main):**
  - *Code review:* `pooled_adu.honest_bounds`, `honest_set`, `rm_breakdown` and `event_study_inputs`
    (68c7ae6, WS-ENGINE) were checked against the choices fixed above (3f0d5e2). The relative-magnitudes and
    smoothness bias formulas, the grids, the inputs from the leads refit and the bootstrap union interval
    all match, and no defect was found. One point for readers: θ is the effect at realised doses (each
    band × the place-year's dose), so it is smaller than the main model's "overall", which averages the
    per-unit-dose bands.
  - *Runs, once per main:* `estimate_pooled_adu.py --honest LOG --hh-growth as_run|corrected`. Each run
    recomputes that main model and checks it against its log to 1e-4 (as-run: `run-2026-10-20-log.txt`;
    corrected: `corrected-2026-10-21-log.txt`). It then refits the pre-trend-leads model exactly as check 1
    did (leads k = −3…−1, D-025 convergence rule, 999 wild-bootstrap draws, seed 1). From that refit it
    computes `honest_bounds` and the breakdown M̄ (`rm_breakdown`, grid step 0.01) for the pooled effect.
  - *Per band (an extension of the pooled target, using the same `honest_set`):* θ_b = mean over the band's
    treated place-years of β_b × dose, with ω restricted to the band's event times and renormalised.
  - *Reported:* identified sets, robust 90% intervals and breakdown M̄ for each target and main; the event
    study (leads and bands with 90% intervals); charts of the robust interval against M̄ with the breakdown
    marked. Nothing here changes the D-025 main result or chooses a specification.
- **HonestDiD runs (2026-10-21, once per main; logs `reports/adu-d025/honest-asrun-2026-10-21-log.txt` and
  `honest-corrected-2026-10-21-log.txt`): bounds not identified, and the printed bounds are invalid.**
  Both mains were reproduced (all 22 logged estimates matched) and both leads refits converged with 999 of
  999 draws. **But lead_1 (δ_−1) was dropped from both refits as "all counts zero where it applies":** the 22
  treated place-years one year before adoption had 0 ADU permits (k = −3: 5 permits in 19 place-years;
  k = −2: 1 in 21; k = −1: 0 in 22; k = 0: 9 in 22; places adopting 2017+, `permits_by_event_time.csv`).
  δ_−1's estimate is therefore −∞. `event_study_inputs` counted the dropped lead as 0, so every bound and
  breakdown value printed in those logs rests on δ_−1 = 0 and **is not valid**. The bounds CSVs were not
  kept; the logs are kept as the record.
  - *Fix (D-031, this PR):* `event_study_inputs` now raises if a lead or band was not estimated, with a test,
    and the `--honest` stage reports "not computed". This is a defect in the committed code, not a change of
    the choices fixed above.
  - *What can still be said, from valid quantities:* θ at realised doses from the leads refit is 1.47
    (−0.11 to 3.04) as-run and 1.52 (−0.25 to 3.34) corrected. **The pooled effect's 90% interval includes 0
    before any allowance for a trend violation**, so the pooled breakdown M̄ is 0 whatever δ_−1 is. The
    0–1-year band alone excludes 0: 1.60 (0.37 to 2.79) as-run, 1.61 (0.28 to 2.99) corrected. Its robustness
    to trend violations cannot be computed as specified. Leads: δ_−3 = 1.44 (0.49 to 2.44) as-run, 1.41 (0.36
    to 2.52) corrected; δ_−2 ≈ −0.2 with intervals spanning ±2.
  - *Reading:* the pre-adoption path (a blip at k = −3, then nothing the year before) looks like owners
    holding projects until the rule passed (C29), but with 0–5 permits a year across ~20 places it cannot
    be told apart from noise. The data are too thin for a trend-violation analysis.
  - *Options for Ben (each needs its own dated note before any run):* (1) pool leads k = −2…−1 into one lead
    (1 permit in 43 place-years: estimable, very weak), keeping the choices above; (2) run the same bounds on
    the announcement-dated sensitivity model (2.99, 1.13 to 4.98), whose re-dating moves the dip into the
    post period; (3) report HonestDiD as not identified and rest on the randomization inference (p = 0.111)
    and the failed leads test. Recommended: (3).
- **HonestDiD decision (Ben, 2026-10-21): option (3).** HonestDiD is recorded as **not identified** for the
  D-025 ADU effect. The inference rests on randomization inference (p = 0.111, corrected main) and the
  failed pre-trend leads test (p = 0.025 as-run, 0.052 corrected). Options (1) and (2) are not run.
  - *Ben's reasoning:* more data should make HonestDiD informative later. Concretely:
    - more adopting places with ADU permits in the years just before adoption, so δ_−1 (and δ_−2) can be
      estimated instead of sitting at −∞;
    - longer pre-adoption periods, so the largest pre-period step M_pre rests on more than three noisy leads;
    - the multi-state panel, which pools those years across states.
  - HonestDiD is rerun, with the code already tested here (`--honest`, which refuses unestimated leads), once
    that panel exists. No other run follows from this note.

### D-032 · 2026-10-20 · Proposed: fee scenario mechanics (`scenarios/fees.py`, thread 02)
- **Fee level:** `local` mode uses each place's coded single-family fee per unit from `config/fees`. That is the
  SFD and OTHER rows, each component at its newest year with a per-unit amount, summed. `handbook` mode uses the
  Rules' $50,000 everywhere. Both are reported. The cut is 50% of the level; builders keep (1 − λ) of it.
- **Channels:** (a) feasibility where parcel data give candidate lots (vacant residential land values) and a
  new-home value; %Δ permits = lots feasible after the cut / lots feasible before − 1 (permits scale with
  feasible lots). (b) Elasticity everywhere else (D-010): %Δ = ε × saving / TDC, with TDC = the place's ACS
  median home value. That is an existing-home price used as the price of a home at the margin of feasibility,
  which tends to understate TDC and so overstate the effect.
- **Ramp:** the response phases in with the logistic ramp, half 1 year (0.5–2) and slope 0.5 (0.25–1), both
  judgment. Projects in design when the cut lands were priced at the old fee.
- **Baseline:** added units = the baseline model's mean units a year × %Δ × ramp. In the development run the
  baseline covers all four BPS size classes, while the dose comes from the single-family prototype. That is a
  v1 simplification: per-unit fees and TDC differ for 2–4 and 5+ unit buildings. The range comes from the
  scenario's parameters, not from the baseline's draws.
- **No revenue toggle yet:** the "revenue not replaced" offset (fees causal diagram, C51) has no sourced size.
  It stays open.
- **Decided by:** proposed by thread 02 in the fee-scenario PR; for Ben to confirm.

### D-033 · 2026-10-20 · Proposed: feasibility-channel inputs from parcel rolls
- Candidate lots are VACANT_RESIDENTIAL parcels with a land value in the newest roll ≤ origin + 1.
- New-home value is the median (land + building value) per sq ft of detached homes built in the last 7 years,
  × 2,150 sq ft. These are assessed values in the roll's own dollars, taken as 2025 dollars.
- A place uses the channel only when at least 20 lots were feasible before the cut, so the ratio is not noise.
- In the MN development run only Minneapolis qualifies. Dakota and Anoka County rolls code no vacant
  residential parcels, and several places lack year built or building sq ft.
- **Decided by:** proposed by thread 02; for Ben to confirm.

### D-034 · 2026-10-20 · Proposed: when a coded local fee is complete enough to use
- A place's coded fee is used only if it includes a water/sewer fee. Utility fees are usually the largest
  component and the one most often missing (fees causal diagram §2). Otherwise the place takes the national
  prior ($50k).
- Batch 1 consequences: Minneapolis (no SAC coded) and Austin (one $335 item) take the prior. That jumps
  from too low to too high, so the output lists `fee_source` and `fee_components` for every place.
- **Decided by:** proposed by thread 02; for Ben to confirm. An alternative is a component-wise prior
  (fill only the missing components).

### D-035 · 2026-10-22 · Eligible-parcel history for places counted from a parcel roll: ACS scaled to the roll (#208)
- **Found:** a jurisdiction counted from a parcel roll had a denominator only in its roll year(s), while ACS-fallback
  jurisdictions had one in every ACS end year (2010–2024). In NC that left 218 jurisdictions, Raleigh, Durham and
  Greensboro among them, with no denominator in the baseline level window, the V1 backtests or the fee scenario.
  The same holds wherever a state counts from a current roll only (MN outside the Met Council archives, OH, TX).
- **Now (`build/eligible.scale_history`, called by `combine`):** each real roll year is an anchor with scale factor
  parcels / ACS one-unit-detached homes, the ACS end year being the roll year or the nearest one within
  `scale_max_year_gap` (3 years; `config/params/eligibility.yaml`). Every other ACS year gets ACS × factor; with
  two or more anchors the factor is linear between them and flat outside. Real roll years keep their real counts.
  Filled rows have `denominator_source = "parcels_scaled_acs"` (new schema value) and the quality of the nearest
  roll. The ADU scenario's overlap step treats them like roll counts (`PARCEL_SOURCES`).
- **Why:** option 1 of #208. Mechanical, works in every state that has ACS, keeps ACS's year-to-year movement and
  ends exactly at the roll. Year-built backcasting (option 2) misses demolitions, splits and vacant lots and is
  tier 1 only; it stays a check, not the main path.
- **Limits:** the factor carries the roll's mix (vacant lots, zoning, exclusions) back in time unchanged, and ACS
  sampling noise moves the filled years. Rolls newer than ACS (NC OneMap 2026) anchor the latest ACS year (2024).
- **Decided by:** Ben, 2026-10-21 (option 1 in #208, real rolls kept wherever they exist).
- **Addendum 2026-11-01: interpolate between two real rolls.**
  - **Found:** with yearly county rolls (Franklin 2016–2025, Montgomery 2011–2026) and Wake's 2019 and 2023 rolls,
    the scaled years between real rolls moved with ACS sampling noise rather than with the parcels. Dayton's 2020
    came out at 45,399 against real counts of 43,819 (2018) and 43,669 (2021). Wake's fast-growing towns lagged
    their real growth between 2019 and 2023 by up to 14%.
  - **Now:** a year strictly between two real roll years takes the real counts interpolated linearly, rounded,
    with `denominator_source = "parcels_interpolated"` (new schema value, schemas 1.9; `PARCEL_SOURCES` includes
    it). Years before the first roll or after the last keep the scaled ACS series.
  - **Effect:** 13 OH jurisdictions (all Montgomery: Dayton 2020 → 43,719) and 13 NC jurisdictions (Wake towns,
    2020–2022; Raleigh +1–1.3%) change. Single-roll places are unchanged.
  - **Decided by:** Ben, 2026-11-01 (WS-OH Montgomery review, decision 5: "separate PR").

### D-036 · 2026-10-26 · Repeated project totals on permits with no parcel number (amends D-008, #221)
- **Was (D-008):** permits with no `parcel_id` were never grouped. Fort Worth (`fw_permits`) and Dallas
  (`dallas_permits`) publish no parcel number, and some projects put the project's total on every building's
  permit: Fort Worth 2024, seven consecutive permits each say 404 units; Dallas 2023, eleven same-day permits
  each say 471. Their 5+ unit counts reach 2.6× (Fort Worth) and 7.5× (Dallas 2024) of Census BPS.
- **Now (`lotline.build.permits.flag_repeated_totals`, used by `count_units`):** permits with no parcel are
  grouped by jurisdiction, year, **day** (`issue_date`, else `application_date`) and the same unit count of at
  least `repeated_total_min_units` = 50, when the group has at least `repeated_total_min_permits` = 3 permits.
  Within a group, only permits whose floor area per unit is below `repeated_total_max_sqft_per_unit` = 300 sq ft
  **or whose floor area is missing** are read as repeating the total: their count goes once on the lowest
  `permit_id` among them; the others of them count 0. Permits with a plausible floor area per unit stay as
  reported. Permits with no date and demolitions are never grouped. The parcel branch of D-008 is unchanged.
- **Why the 50-unit floor stays:** same-day runs of 3+ permits with the same count are common below 50 units
  (2,131 of 3,240 two-to-49-unit permits in Fort Worth, 4,278 of 6,638 in Dallas, 2010–2025: rows of duplexes
  and fourplexes). The floor keeps every one of them as reported.
- **Why floor area per unit:** among 50+ unit permits, the same-day groups claim a median 75 (Fort Worth) and
  100 (Dallas) sq ft per unit, against 1,150 and 592 for the rest; 87% and 92% of the grouped units sit on
  permits under 300 sq ft per unit. No home is that small (building-code minimum dwelling size, see the
  parameter's source), so such a permit carries a project total. About a fifth of Fort Worth's grouped permits
  have normal floor area: likely real identical buildings, which the area test keeps.
- **Parameter:** `repeated_total_max_sqft_per_unit` in `config/params/permits.yaml` (300; sensitivity 200–500).
- **Sensitivity, both ways:** as in D-008, the rule on is the primary count and `dedupe=False` gives the
  as-reported count.
- **Effect measured before the area test (issue #221, counts only, 5+ units vs BPS 5+):** these grouped every
  same-day repeat regardless of floor area (Fort Worth on filing date, Dallas on issue date), so the final rule
  removes somewhat less (87–92% of the grouped units fall under the area test). To re-measure on the final rule.

  | Fort Worth | As reported | Removed | BPS 5+ | Ratio before → after |
  |---|---|---|---|---|
  | 2016 | 6,402 | 153 | 3,845 | 1.67 → 1.63 |
  | 2018 | 5,527 | 230 | 3,705 | 1.49 → 1.43 |
  | 2020 | 5,391 | 2,475 | 2,100 | 2.57 → 1.39 |
  | 2023 | 8,050 | 2,312 | 3,144 | 2.56 → 1.83 |
  | 2024 | 15,455 | 8,464 | 5,877 | 2.63 → 1.19 |
  | 2025 | 3,729 | 949 | 3,348 | 1.11 → 0.83 |

  | Dallas | As reported | Rule on | BPS 5+ | Ratio before → after |
  |---|---|---|---|---|
  | 2010 | 4,211 | 1,684 | 1,716 | 2.45 → 0.98 |
  | 2011 | 5,219 | 4,256 | 3,414 | 1.53 → 1.25 |
  | 2019 | 8,360 | 5,756 | 5,712 | 1.46 → 1.01 |
  | 2021 | 8,457 | 7,989 | 7,533 | 1.12 → 1.06 |
  | 2022 | 19,003 | 7,599 | 7,485 | 2.54 → 1.02 |
  | 2023 | 13,810 | 5,321 | 4,179 | 3.30 → 1.27 |
  | 2024 | 29,037 | 8,276 | 3,871 | 7.50 → 2.14 |

  Dallas 2024 ends 2024-11-12 in the source. Fort Worth 2022 (1.80×) has no repeats; part of its excess has
  another cause (open). 1-unit homes are 0.84–1.01 of BPS throughout, so the excess is specific to repeated
  multifamily totals.
- **Limits:** a project whose buildings are filed on different days is not caught; a single or paired permit
  with an implausible area per unit (47% of Dallas's ungrouped 50+ unit permits) is not caught either. An
  area-only rule would be a further decision.
- **Applies everywhere:** the branch runs on any permit with no parcel, so it can also touch no-parcel rows in
  other cities' files (e.g. the MN and Austin v0 comparisons, which call `flag_repeated_totals`).
- **Decided by:** Ben, 2026-10-26 (#221: group by same day and same count, protect duplexes and fourplexes;
  collapse only implausible floor area per unit).

### D-037 · 2026-11-03 · Scenario effect sizes come from the mechanism route; the in-state estimates validate it (reversible)
- **Why:** the in-state estimates can't size an effect. Ben deferred this choice on 2026-10-21 (in-state
  estimates or the mechanism route) until the multi-state data arrived. It has arrived, and neither model gives a
  usable estimate: D-024's four-state run gives no credible estimate (randomization inference p = 0.29, the
  placebo outcome fails), and D-025's four-state main model did not converge. The deeper reason is power. The
  smallest overall effect each run could detect (80% power, 10% two-sided test: 2.49 × the overall effect's
  standard error, on the log scale):

  | Run | Overall effect (SE) | Smallest detectable effect | As a multiple of permits | Upper 90% bound, as a multiple |
  |---|---|---|---|---|
  | D-024, October, Poisson-gamma (`reports/mm-d024`) | 0.77 (0.44) | 1.09 | 3.0× | 4.6× |
  | D-024, October, negative binomial (`reports/mm-d024-nb`) | −0.25 (0.59) | 1.46 | 4.3× | 2.4× |
  | D-024, four states (`reports/mm-d024-4state`) | 1.75 (0.93) | 2.31 | 10× | 26× |
  | D-025, October, Twin Cities (`reports/adu-d025/corrected-2026-10-21`) | 2.37 (1.36) | 3.38 | 30× | 91× |

  Plausible short-run effects of these reforms are well below these thresholds. With about 20 adopting places,
  short post-periods and mostly-zero counts, more of the same data will not close the gap. The design problems the
  four-state run exposed (selection into reform, cross-place identification of always-treated places, rules
  coded as allowed rather than binding, outcome measurement) widen it further.
- **Decision (route 1):** each scenario's five-year effect is built from mechanisms and anchored to evidence
  from well-studied reforms:
  - homes added = eligible parcels × the share that pencil out (`proforma.py`) × an uptake hazard × a ramp;
  - every input is drawn over its range (as in D-030), so the result is a range.
  - **ADU:** no change to the scenario. It already works this way (`scenarios/adu.py`; anchor
    `adu_mature_hazard_ref`, D-019 fit 3, with Portland's 4 per 1,000 as the research band; draws per D-030).
    D-025 moves to validation.
  - **Missing middle:** to build, on the same structure:
    - eligible parcels (rule 1.1, D-014) × feasible share from the pro forma × a developer uptake hazard
      (`mm_mature_hazard_ref`, new, in `config/params/hazard.yaml`) × a ramp;
    - the anchor and its range come from external evidence compiled with sources (for example Minneapolis 2040,
      Houston's 1998 lot-size change, Portland's Residential Infill Project, Auckland's 2016 upzoning).
    - Until that is built and reviewed, missing-middle scenario numbers are labelled provisional.
- **What the in-state results are used for:**
  1. **Consistency check.** Run the mechanism model for the places D-024 and D-025 treated, over their
     post-adoption years. Report whether the implied overall effect falls inside each in-state 90% interval
     ("consistent" / "inconsistent"). This is reported, not used to tune. Both D-024 runs are shown: the October
     negative binomial's upper bound (2.4×) constrains; the four-state run's (26×) barely does.
  2. **Out-of-sample tests.** Predict the held-out places (D-024: Durham, Durham County, Raleigh, Minneapolis;
     D-025: Raleigh, Durham) with the mechanism model and score them with the same pass rules. This is the
     test that decides whether route 1 is working.
  3. **V5.** The Charlotte and St. Paul freezes use the mechanism model's effect. The V5 freeze proposal
     (`reports/engine14/v5_freeze_proposal.md`) is amended accordingly.
- **Kept reversible (Ben, 2026-11-03: decisions here serve a workable model and are revisited when the
  evidence changes):**
  - *Nothing is retired.* The estimation code, runs and reports stay on `main` and runnable. D-024 and D-025
    can be re-run under new dated entries as before.
  - *The source is a switch, not a rewrite.* The scenario output contract (handoff 09) carries the effect
    source as a parameter, `effect_source` (`mechanism`, the default from now on, or `in_state`). The
    in-state path stays wired, so switching back is a parameter change plus a dated entry. Until the contract
    exists, no code reads it; the ADU scenario already runs on the mechanism route.
  - *Both are shown.* Wherever a scenario effect is reported (results dashboard, scenario comparison), the
    in-state estimate sits beside it, so the size of a switch is always visible.
  - *Revisit when any of these happens:*
    - an in-state estimate converges, passes randomization inference at p < 0.10, its placebo outcome and its
      out-of-sample tests;
    - the mechanism model fails its own out-of-sample tests or is inconsistent with the in-state intervals
      in a way its ranges can't explain;
    - new data (more post-adoption years, local permit series, more states) brings the smallest detectable
      effect under about 2× (0.7 on the log scale).
- **Not decided here:** the external evidence for the missing-middle anchor, its range and ramp (a separate
  dated entry, before any missing-middle scenario number is reported); whether D-025 is re-run after its
  non-convergence (still Ben's call; it is now a validation run, so it is less urgent).
- **Supersedes:** the deferral of 2026-10-21. This is the dated entry D-024's October reading asked for before
  the scenario takes a missing-middle evidence prong.
- **Decided by:** Ben, 2026-11-03 ("Lets proceed with route one but ensure that this is not an irreversible
  decision"); written by WS-ENGINE.
- **Amendment (2026-11-03, later the same day; Ben): our own four states set the rates; outside evidence only
  checks them.**
  - **What changes:** "anchored to evidence from well-studied reforms" above is replaced. The uptake rates
    (the mature hazard, the ramp, the units per project, and the modifiers through the pro forma) are
    **calibrated on the post-reform places of MN, NC, OH and TX**, as D-019 already does for the ADU anchor
    (fit 3: Minneapolis, Austin and 14 Twin Cities suburbs). Studies from other places (Portland, Houston,
    Auckland, California) are a plausibility check. A calibrated value far outside them has to be explained,
    but they don't set the values. Where our data can't identify a parameter (for example the ramp's late
    years, given short post-periods), the entry says so and states what fills the gap.
  - **Why (Ben):** the purpose of collecting the four states' data is to measure what enacting these rules
    actually produced. A rate from another market only stands in for that.
  - **Why this works where D-024 and D-025 did not:** those estimate a *difference* between reformed and
    comparison places, which needs a credible comparison group and the power to detect a gap. The uptake rate
    is a *level*: how often an eligible lot in a reformed place gets an ADU or a 2–4 unit building after the
    rule. We observe that directly.
  - **What the calibration must handle for missing middle:**
    - building that was already happening before the rule: subtract each place's pre-reform 2–4 unit rate, or
      count permits on newly eligible lots where permits carry a parcel number;
    - general growth in reforming places (the four-state placebo outcome failed): net it out with the place's
      5+ unit trend or the comparison places' year effects;
    - short post-periods: say how much of the ramp the data identifies.
  - **The test is a backtest, as Ben describes it: V4, leave one place out.** For each reformed place,
    calibrate without it, using only data up to the year before its reform. Predict its years 1–5 and compare
    with what was permitted. Score:
    - P10–P90 coverage across places (V4's proposed pass: at least 60%; nominal 80%);
    - error per 1,000 eligible parcels, against two benchmarks: no effect, and the outside-evidence rate
      applied unadjusted.

    Durham, Raleigh and Minneapolis remain the pre-declared out-of-sample tests above. Charlotte and St.
    Paul remain V5, untouched.
  - **Expected accuracy, stated now:** a single city's count will come with a range, not a point. In D-019 the
    place-to-place multiplier varies widely (`adu_place_effect_variance`), and D-025's transport test missed
    Austin. Statewide totals should be tighter than single cities, because place errors partly cancel.
  - **Applies to:** missing middle (D-038, PR #272, to be redone this way) and a refit of the ADU anchor on
    the four-state data (D-019 fit 3 predates the NC and TX permit work), under its own dated entry.
  - **Decided by:** Ben, 2026-11-03 ("we need to be rolling our own"); written by WS-ENGINE.

### D-038 · 2026-11-03 · Missing-middle uptake calibrated on our four states: method (pre-registered before the fit)
- **Status:** method written and pushed before any fit was run. Required by the D-037 amendment (Ben, 2026-11-03:
  "we need to be rolling our own"); Ben's instruction is the go-ahead to run it once. It replaces this entry's
  first draft (an anchor taken from Portland and Houston), which becomes the plausibility check below. Only the
  panel's structure was looked at before writing this: which places adopted, when, at what dose, with how many
  eligible parcels. No outcome was tabulated.
- **What it estimates (`config/params/mm_hazard.yaml`):** θ = `mm_mature_hazard_ref`, the yearly chance that an
  eligible parcel (rule 1.1, D-014) gets a new 2–4 unit building once a full-dose rule has matured, at the
  reference price-to-cost; α = `mm_place_effect_variance`; the ramp's half-way point; and the homes per
  building. 5–6 unit buildings and townhouses are outside this count: BPS files them as 5+ and 1-unit.
- **Data:** the D-024 four-state panel (`estimate_mm.build_panel`, BPS 2010–2025, holdout-filtered tables,
  rule-date tags through `rule_tags`). Outcome `y_buildings` = BPS buildings with 2 units plus buildings with
  3–4 units. Exposure `eligible` = rule 1.1 eligible parcels from the nearest roll. A place-year missing from
  BPS is skipped, never set to 0.
- **Fit set:** every place with an in-window adoption year 2013 ≤ T ≤ 2025 (at least three pre-reform panel
  years), dose > 0, eligible parcels > 0. That is 16 places: Wilson, Morrisville, Wake Forest, Sanford,
  Burlington, Mooresville, Garner (NC); League City, Lewisville, Austin, Houston, Lubbock (TX); Cincinnati,
  Euclid (OH); Richfield, St. Louis Park (MN).
  - **Left out, never read for this fit:**
    - Minneapolis, Durham city, Durham County and Raleigh: the D-037 out-of-sample tests, predicted afterwards.
    - St. Paul, Charlotte and Mecklenburg: holdout, excluded by `build_panel`.
  - **Not used, because they have no pre-reform years in the panel:** places whose rule predates 2010 (Apex,
    Asheboro, Goldsboro, New Bern, El Paso, Grove City, Dayton).
- **Model.** Place i, year t ≥ T_i, event age a = t − T_i + 0.5 (a rule in force by 1 July of T was adopted on
  average at the start of T):

      y_it ~ Poisson(B_it + θ · u_i · k_it),   u_i ~ Gamma(mean 1, variance α)
      B_it = β_i · g_it                         (building that would have happened anyway)
      k_it = E_it · d_it · F_i / F_ref · ramp(a_it; half, slope)

  - *Pre-reform baseline:* β_i = mean of y_buildings over T−3 … T−1 (years with data). It is plugged in, not
    estimated jointly.
  - *General growth:* g_it = m_it / m_i,pre. Here m is the place's homes permitted outside 2–4 unit buildings
    (BPS units_1 + units_5p), as a centred 3-year mean (years with data); m_i,pre is its mean over T−3 … T−1.
    g is capped to [0.25, 4]. This nets out the general growth that failed D-024's four-state placebo.
  - *Exposure and dose:* E_it = eligible parcels; d_it = the panel's dose (units grade × approval × coverage,
    D-024; Handbook-equivalent = 1).
  - *Feasibility:* F_i = Φ((ln PCR_i − ln(1 + developer_margin)) / σ). PCR_i is the panel's `pcr` (a rental
    duplex's price-to-cost at T−1). σ = `mm_feasibility_dispersion`, 0.5 (judgment, the ADU value, range
    0.25–0.8). F_ref = F at PCR = 1, so θ is the mature hazard where a rental duplex's value equals its cost
    before profit.
  - *Ramp:* the logistic of `hazard.ramp`, with slope fixed at 0.75 (judgment, as for ADUs). The half-way point
    is estimated on the grid 0.5, 1.0, …, 6.0 years.
- **Estimation:** maximum likelihood. Each place's u is integrated out numerically (trapezoid on a log-u grid).
  θ is on the log scale; α and the half-way point are profiled out. θ's 90% interval is its profile-likelihood
  interval {θ : 2(ℓ̂ − ℓ_p(θ)) ≤ 2.706}; the same rule gives the half-way point's interval on its grid. Only
  NumPy and the standard library are used (as `calibrate_adu`).
- **What the data can and cannot identify (stated before the fit):**
  - Post-periods are short: 6 of the 16 places have at most two post years, and only Wilson, Morrisville, Wake
    Forest and Sanford have more than six.
  - The early ramp and the average hazard over the observed ages are identified. The mature level beyond the
    oldest well-observed age depends on the ramp.
  - The result reports the exposure-weighted age distribution and the mean realized hazard over the observed
    ages alongside θ.
  - Where the half-way point's 90% interval reaches a grid edge, that side of its range is filled by the outside
    evidence (1.5 years low, 5 years high: Portland, Auckland, Houston; first draft of this entry), and the
    entry says so.
- **Homes per building (`mm_units_per_project`):** (2–4 unit homes) / (2–4 unit buildings) from local permit
  files with unit counts (Raleigh, Durham, Greensboro, Mecklenburg before 2023-06 through the holdout filter,
  Met Council DTQ, the Texas city files). Each source's post-2015 ratio is reported. The central value is the
  building-weighted mean; low and high are the lowest and highest source ratios. BPS's own ratio for the fit
  places is the check.
- **Checks reported (none changes the estimate):**
  1. *Placebo date:* the same fit with T moved 3 years earlier, using pre-reform years only. Expected: θ near 0
     (its interval covers 0 or sits far below the main estimate).
  2. *Growth control:* g from units_5p alone; g from the comparison places' (status uncoded, same state)
     2–4 unit buildings by year; and g = 1.
  3. *Feasibility:* F ≡ 1 (no transport), and σ at 0.25 and 0.8.
  4. *Baseline window:* T−5 … T−1.
  5. *Tags:* dropping events tagged `earliest_known` or `unconfirmed` (`rule_tags.SENSITIVITIES`).
  6. *On eligible lots:* where a fit place's local permits carry parcel numbers that match its roll, the share of
     2–4 unit buildings on rule-1.1 eligible parcels, before and after T. A rise supports reading the excess as
     the reform's. Descriptive; it is reported as not done where the join is not possible.
  7. *Plausibility:* θ, and the implied rate per 1,000 eligible parcels at each place's own F and dose, against
     the outside table (`docs/research/mm-uptake-evidence.md`: Portland 0.55–0.85 projects per 1,000 a year,
     Houston 0.35). A gap of more than 3× either way is explained in the results.
- **V4 backtest: leave one place out (D-037 amendment).**
  - **Refit:** for each fit place j with T_j ≥ 2015, refit on the other fit places using calendar years ≤ T_j − 1
    only.
  - **Predict:** j's years T_j … T_j + 4 (to 2025) as a predictive distribution:
    - θ lognormal from the refit's interval;
    - the refit's half-way point;
    - a new u ~ Gamma(α);
    - Poisson counts on j's own baseline and its realized g.
    - Sensitivity: g held at 1, a true forecast.
  - **Score:**
    - P10–P90 coverage of each place's observed total over its predicted years (V4's proposed pass: at least
      60%; nominal 80%);
    - mean absolute error of the median, in buildings per 1,000 eligible parcels a year.
  - **Benchmarks:**
    - no effect: B only;
    - the outside rate unadjusted: B + 0.0005 × E × d × ramp(half 2.5).
  - **Places with no refit:** if a refit has fewer than two places with post-reform years, j is not scored by
    the fit and is reported as such.
  - **Test places:** the D-037 out-of-sample tests (Minneapolis, Durham, Durham County, Raleigh) are predicted
    with the full fit afterwards, under the same scores, and reported separately.
- **Into `mm_hazard.yaml`:**
  - θ: the estimate and its 90% interval.
  - α: the estimate, with the interval from its profile.
  - The half-way point: as above.
  - Homes per building: as above.
  - `mm_feasibility_dispersion`: judgment, 0.5 (0.25–0.8).
  - Draws are lognormal for θ and α, as D-030.
  - The fit runs once. A later change is a new dated entry.
- **Code:** `src/lotline/model/calibrate_mm.py` (likelihood, profile, backtest; unit tests against hand-worked
  examples in `tests/model/test_calibrate_mm.py`); `scripts/dev/calibrate_mm.py` (the run); results to
  `reports/mm-d038/` (no outcome panel written to the repo).
- **Results (2026-11-03, after the single run; `reports/mm-d038/`):**
  - **Fit set as run: 15 places, 74 post-reform place-years.** Mooresville drops out under the stated rule: it
    has no BPS rows before 2023, so no pre-reform baseline.
  - **θ = 1.08 per 1,000 eligible parcels a year (90% interval 0.36–5.35).**
    - α = 7.3 (3.2–19.8): the place multiplier varies widely, as it does for ADUs.
    - Half-way point 2.0 years. No other grid point is inside the 90% set, so the range is the neighbouring
      grid points, 1.5–2.5.
    - The mean realized hazard over the observed ages is 0.95 per 1,000.
    - Exposure-weighted ages run 0.5–2.5 (P10–P90). The ramp is identified only over the first three years.
  - **Houston carries the estimate.** Its 2024–25 2–4 unit buildings were 1,642 against a baseline of 550; it
    is the only large excess. Austin is next (251 against 133).
    - Exploratory fits, not pre-registered and not used: without Houston 0.57 per 1,000 (0.17–3.36); without
      Houston and Austin 0.24 (0.06–2.43).
    - Lubbock fell below its baseline (25 against 191). Most small places had no excess.
  - **Checks:**

    | Check | θ per 1,000 (90% interval) | Reading |
    |---|---|---|
    | Main | 1.08 (0.36–5.35) | — |
    | 1. Placebo date T − 3 (14 places) | 0.32 (0.10–1.84) | **Not passed as pre-registered.** About 0.3 of the main estimate, and its interval overlaps it. Part of the excess may be growth the control misses. |
    | 2. Growth from units_5p | 1.15 (0.37–6.53) | Robust |
    | 2. Growth from state comparisons | 1.19 (0.31–5.60) | Robust |
    | 2. No growth control (g = 1) | 1.18 (0.41–5.88) | Robust |
    | 3. F ≡ 1 (no feasibility) | 0.81 (0.28–4.02) | Robust |
    | 3. σ = 0.25 | 2.71 (0.68–18.9) | The anchor moves with σ, because it is defined at PCR = 1 |
    | 3. σ = 0.8 | 0.93 (0.32–4.54) | — |
    | 4. Baseline T−5 … T−1 | 0.71 (0.23–3.67) | Somewhat lower |
    | 5. Tag-sensitive events dropped (9 places) | 1.60 (0.35–26.2) | Wide |

    - Check 6 (eligible lots) was **not done**. None of Cincinnati's or Austin's parcel-numbered permits matched
      their rolls' `parcel_id` (formats differ). Fixing the join is a follow-up.
    - Check 7 (plausibility): the implied mature rates at each place's own dose and PCR are 0.07–0.76 per
      1,000. That is inside the outside table's 0.35–0.85 for full-dose rules (Portland 2021–24 average and
      2023; Houston's 2007–20 average). No gap over 3×.
  - **V4 backtest (12 places with T ≥ 2015):**
    - The refits on data before each target's reform gave θ = 0.08–0.45 per 1,000, with half-way at 0.5.
      Before the 2024 adopters, the fit set showed little excess.
    - P10–P90 coverage: **8 of 12 (67%)** for the fit, against 7 of 12 for no effect and 5 of 12 for the
      outside rate. That passes V4's proposed 60%, but through wide intervals.
    - Mean absolute error of the median: 0.235 buildings per 1,000 eligible parcels a year, against 0.234 (no
      effect) and 0.237 (outside rate). **No better than no effect.** Houston (−1.2) and Lubbock (+1.0)
      dominate the error.
    - With growth held at 1 (a true forecast): coverage 8 of 12; error 0.228 against 0.227 and 0.231.
  - **D-037 out-of-sample tests (full fit, years 1–5):**
    - P10–P90 covered **4 of 4**: Minneapolis, Durham city, Durham County and Raleigh.
    - No effect covered 1 of 4; the outside rate covered 1 of 4.
    - Every median is below the observed count, because the gamma's median sits far below its mean.
    - Error of the median 0.089 per 1,000 a year, against 0.103 (no effect) and 0.066 (outside rate, which is
      closest).
  - **Homes per building:**
    - The local permit files give 0.75–2.43 homes per 2–4 unit "building", which is impossible. They file one
      permit per unit or per duplex side, so they can't count buildings.
    - The pre-registered BPS check is used instead: 2.08 for the fit places, 2016–2025 (state ratios 2.04–4.0).
      BPS 2–4 unit buildings are mostly duplexes.
  - **Into `mm_hazard.yaml`:** θ 0.001076 (0.000362–0.005347); α 7.29 (3.18–19.78); half-way 2.0 (1.5–2.5);
    homes per building 2.08 (2.04–4.0); slope and σ as judgment.
  - **What this means for the scenario:**
    - The anchor is usable, and its range is wide.
    - A single place's result is very uncertain (α); state totals are tighter.
    - The point estimate is mostly a Houston number.
    - The placebo result and the backtest's lack of accuracy gain say the in-state signal is weak outside the
      two large Texas cities.
  - **For Ben to decide:**
    1. Accept the fit as is.
    2. Widen the ramp range to the outside series' 1.5–5 years.
    3. Whether the placebo shortfall calls for a different growth control. That would be a new dated entry
       and a new run.
- **Decided by:** method by WS-ENGINE, 2026-11-03, on Ben's instruction (D-037 amendment); results for Ben to
  confirm in PR #272.
- **Coding change after the run (2026-11-03, Ben's decision).** `config/reforms/tx.csv` gains
  TX-4805000-missing_middle-2010 and TX-4835000-missing_middle-2010. Both are tagged `[predates]` and capped
  at 2 units:
  - Austin SF-3 already allowed duplexes and two-family use before HOME;
  - Houston already allowed duplexes on single-family lots before Livable Places.

  Evidence is in causal diagram v0.2 §6.5–6.7 and `docs/research/ordinances/tx-corrections-2026-11-03.csv`.
  - **Effect on the panel.** Both places now have a missing-middle rule in force before the window (T before
    2013), so they leave the D-038 adopter set. Their 2023–24 reforms become dose increases.
  - **Effect on the results above.** They were run on the old coding and are not rerun here. The exploratory
    fit without Houston and Austin gave 0.24 per 1,000. A run on the new coding belongs to D-042.
  - **Effect on D-022 blank shares.** These move slightly: P(by right) 0.842 → 0.846, units grade
    0.298 → 0.299.
  - **D-024 and D-025.** Not rerun.

### D-039 · 2026-11-03 · ADU anchor refit on the four states, with a leave-one-place-out backtest (written before the fit)
- **Why:** D-037's amendment (Ben, 2026-11-03): uptake rates are calibrated on our own four states, and outside
  studies only check them. The ADU anchor `adu_mature_hazard_ref` comes from D-019 fit 3 on Minneapolis, 10 Twin
  Cities suburbs and Austin, made before the NC, OH and TX permit work and the Minnesota second coding. (D-038 is
  the missing-middle anchor, PR #272.)
- **Model:** fit 3 unchanged: the same likelihood (gamma place effects, graded rule shares, blank fields
  integrated per place, coverage), the same judgment values and ranges for the owner-occupancy and
  other-restriction shares, the same 90% profile-likelihood interval, central parameters as on `main`.
- **What enters:** a place-year enters when a coded ADU rule is in force by 1 July and a permit source flags
  ADUs that year (`calibrate_adu.place_years`). Holdouts go through the IO layer's filter.

  | State | Places | Years | Note |
  |---|---|---|---|
  | MN | every place with a coded ADU rule except St. Paul (V5) | 2016–2025 | as fit 3; Met Council flags from 2016 |
  | TX | Austin (4805000) | 2016–2023 | as fit 3; HOME ends the R-102 flag in 2024 |
  | TX | San Antonio (4865000) | 2021–2025 | its permit file starts 2020-07 (D-025 amendment) |
  | NC | Mint Hill, Matthews, Cornelius, Huntersville (Mecklenburg towns), Greensboro, Durham County | 2016–2025 | Mecklenburg towns' counts are parser-based (NC readiness) |
  | OH | Cincinnati (3915000) | 2024–2025 | the only OH place whose ADU count is complete; Dayton and Dublin are lower bounds and stay out |

  A count before the fit (place-years and ADU permits only, no estimate) found 42 MN places with 306 ADU
  permits, Austin 3,082 (2010–2025; fewer in the fit years), San Antonio 242, the six NC places 51, and
  Cincinnati 8. Austin dominates the counts; its gamma place effect absorbs its level.
- **Test set (unchanged, held out of every fit):** Raleigh 2021–2025, and Durham city 2021–2025 if every roll it
  uses has 1,000+ eligible parcels (D-019's rule). These are D-037's ADU out-of-sample tests.
- **Backtest (V4, leave one place out):**
  - For every fit place, refit without it and predict its in-window years with `calibrate_adu.predict_place`
    (a new place effect drawn from the fitted variance; seed 20261020).
  - Report per place: observed vs predicted median and P10–P90 for its total and each year, plus years since
    its rule.
  - **Scores:**
    - P10–P90 coverage of place totals and of place-years, nominal 80%. V4's proposed pass is 60% or more of
      place totals.
    - Mean absolute error per 1,000 eligible parcels per year, against two benchmarks: (a) no effect (0 ADUs)
      and (b) the outside rate unadjusted (Portland's 4 per 1,000 × eligible parcels × the rule's ramp). The
      model should beat both.
    - The same scores for the test set.
  - **Deviation from V4, stated now:** the refit keeps the other places' years after the left-out place's
    reform (a cross-place test, not a strict freeze at the year before the reform), and market inputs are
    actual, not forecast. A strict freeze leaves too little data before most reforms (Minneapolis's rule dates
    from 2014). So the backtest measures how well the rate transfers to an unseen place, which is what a new
    state needs.
- **What changes in config:** nothing until Ben confirms. The fit is reported next to fit 3's 0.001038
  (0.000453–0.003173). If Ben adopts it, `config/params/hazard.yaml` is updated with this entry as its source,
  and `--draw-terms` is re-run for `adu_anchor.yaml` (D-030).
- **Run once:** `uv run python scripts/dev/calibrate_adu.py --four-state`, log in `reports/adu-anchor-4state/`.
- **Decided by:** Ben, 2026-11-03 ("proceed with the next steps", after the D-037 amendment); written by
  WS-ENGINE before the fit.
- **The run (2026-11-03 04:15–06:07, once, commit 0ccb4f3; `reports/adu-anchor-4state/`, log
  `run-2026-11-03-log.txt`; written after the run):**
  - **Fit:** 51 places, 296 place-years. **θ = 0.001112 per eligible parcel a year (90% 0.000743–0.001742)**,
    against fit 3's 0.001038 (0.000453–0.003173): the same level, with an interval 2.3-fold wide instead of
    7-fold. That is 0.28 of Portland's 4 per 1,000 (fit 3: 0.26). Place-effect variance α = 2.46.
    Owner-occupancy share estimated at 1.0; the other-restriction share stays at its judgment value of 0.3.
  - **Test set (held out):** Durham is tested this time (every roll has 1,000+ eligible parcels).

    | Place | Observed | Median | P10–P90 |
    |---|---|---|---|
    | Raleigh 2021–25 | 230 | 29 | 0–265 |
    | Durham 2021–25 | 239 | 54 | 1–443 |

    Both are inside, but the medians are far too low. Error per 1,000 eligible parcels a year: model 0.52,
    no effect 0.62, Portland unadjusted 2.72. The model has the smallest error.
  - **Backtest (V4, leave one place out, 51 refits):**
    - P10–P90 covers **48 of 51 place totals (94%)** and 95% of place-years. That passes V4's 60%, but it is
      above the nominal 80%: the intervals are wider than they need to be. V1's rule reads coverage above 90%
      as too wide to be useful.
    - The misses: **Austin, 2,545 observed vs P10–P90 3–455 (median 76)**; Fridley, 10 vs 0–6; Denmark
      Township, 2 vs 0–1.
    - Error per 1,000 eligible parcels a year: model median 0.149, no effect 0.141, Portland unadjusted 3.01.
      The median does no better than "no effect", because most places permit almost no ADUs and the large
      adopters are under-predicted.
  - **Correction to the log, after the run:** the Portland benchmark first ignored the blank-field ramp
    (`ramp_blank`), giving 0 for places like Durham. The code is fixed, and the benchmark column in both
    backtest CSVs was recomputed from the same place-years. The log's benchmark lines (1.814, 2.539) are as
    run; the corrected values are above. The fit and the model's predictions are unaffected.
  - **Reading (WS-ENGINE's, for Ben to confirm):**
    - The four states pin down the **average** ADU uptake rate well, and it agrees with fit 3 and with the
      outside evidence: about a quarter of Portland's rate.
    - They do not yet say **which** places will be big adopters. The place-to-place variation (α ≈ 2.5) is
      larger than anything the rent, home-value and rate terms explain. So a single city's prediction is a
      wide range whose median understates cities like Austin, Raleigh and Durham and is near zero for most
      suburbs.
    - Next steps this points to:
      1. explain the place effects with what we have coded (lot sizes and coverage, fees, parking, how the
         rule is written, city size), each a candidate modifier under a new dated entry;
      2. backtest statewide totals, where place errors partly cancel. The tool's headline numbers are
         statewide, so that test matters most, and this run's per-place CSVs don't keep the draws needed for it.
  - **Config:** unchanged. Adopting θ = 0.001112 (0.000743–0.001742) in `hazard.yaml` and re-running
    `--draw-terms` is Ben's call.

### D-040 · 2026-11-03 · Statewide backtest of the ADU anchor (written before the run)
- **Why:** D-039's backtest scores single places and finds the place-to-place variation unexplained. The tool's
  headline numbers are statewide totals, where place errors partly cancel. Ben chose this test next
  (2026-11-03, "Statewide backtest").
- **Model and data:** D-039 unchanged: fit 3, the same fit set and years per state, the same test set
  (Raleigh and Durham city, 2021–2025), holdouts filtered by the IO layer. No new data.
- **Joint draws (new function, `calibrate_adu.predict_places`):** a state total needs the places drawn
  together. `predict_place` seeds each place alike, so summing its output would give every place the same place
  effect and overstate the spread. Per draw: one θ from its interval, shared by every place predicted from that
  fit (θ's uncertainty is common to all of them); an independent place effect u ~ Gamma(mean 1, variance α) and
  blank-field combination per place; Poisson counts per place-year. 20,000 draws, seed 20261020.
- **Main test, leave one state out (4 refits):** for each of MN, NC, OH and TX, refit on the other three
  states' fit-set places and predict every fit-set place in the held-out state jointly. The state total is the
  sum over its places and in-window years. This is the closest test of D-037's purpose: rates estimated
  elsewhere, applied to a state the fit has not seen (HANDOFF's V8). NC is reported with and without Raleigh and
  Durham (never in any fit).
- **Second test, leave one place out, summed by state (51 refits, as D-039):** each place is predicted from the
  fit without it, with the same seed for θ across refits (so θ draws stay aligned) and independent place
  effects; the draws are summed within each state. This asks whether the statewide sum is right when the
  state's other places are in the fit.
- **Scores, per state and test:** observed total; P10, P50, P90; inside P10–P90; observed ÷ P50; P90 ÷ P10.
  Benchmarks: no effect (0) and Portland's 4 per 1,000 × eligible parcels × ramp (as D-039, corrected).
  With four states there is no coverage rate to read. The bar, stated now: a state total is **useful** if it is
  inside P10–P90 **and** its P50 is within a factor of 2 of the observed total; **inside only** if the
  interval holds it but the median is further off; **missed** otherwise.
- **Scope, stated now:** "state total" here is the sum over the coded places in the fit set, not the whole
  state. The tool's statewide number also extrapolates to uncoded places; this test does not check that step.
  TX is two places and Austin is most of its count; OH is Cincinnati alone (2 years). Their results are read as
  single cases.
- **What changes in config:** nothing. The result feeds Ben's choice on adopting D-039's θ and on D-037's
  next steps.
- **Run once:** `uv run python scripts/dev/calibrate_adu.py --statewide --out reports/adu-statewide`, log in
  that folder.
- **Decided by:** Ben, 2026-11-03; written by WS-ENGINE before the run.
- **The run (2026-11-03 08:23–10:08, once, commit 38eeff4; `reports/adu-statewide/`, log
  `run-2026-11-03-log.txt`, `statewide.csv`, state-total draws in `draws_loso.npz` and `draws_lopo.npz`;
  written after the run):**
  - **Main test, leave one state out.** The fit without each state:

    | Fit without | θ per 1,000 (90%) | α | Places |
    |---|---|---|---|
    | MN | 4.67 (2.30–11.61) | 0.61 | 9 |
    | NC | 1.11 (0.69–1.89) | 3.07 | 45 |
    | OH | 1.11 (0.74–1.77) | 2.56 | 50 |
    | TX | 0.78 (0.37–1.68) | 1.94 | 49 |

    | State | Observed | P50 | P10–P90 | Observed ÷ P50 | Verdict |
    |---|---|---|---|---|---|
    | MN (42 places) | 306 | 1,115 | 450–2,796 | 0.27 | missed (over) |
    | NC fit set (6) | 50 | 57 | 13–193 | 0.88 | useful |
    | NC with Raleigh and Durham (8) | 519 | 213 | 52–781 | 2.44 | inside only |
    | OH (Cincinnati) | 8 | 3 | 0–23 | 2.67 | inside only |
    | TX (Austin, San Antonio) | 2,785 | 319 | 45–1,420 | 8.73 | missed (under) |

  - **Second test, leave one place out, summed by state:** MN 306 vs P50 629 (268–1,919), inside only; NC
    fit set 50 vs 61 (16–189), useful; NC with Raleigh and Durham 519 vs 235 (66–755), inside only; OH as
    above; TX 2,785 vs 356 (43–1,769), missed.
  - Portland's rate, unadjusted, over-predicts every state by 7–30-fold (MN 8,836, TX 12,069).
  - **Reading (WS-ENGINE's, for Ben to confirm):**
    - One of four state totals is useful by the bar set in advance (NC's six towns), two more are inside only,
      and MN and TX are missed in opposite directions. **The anchor does not yet transfer to an unseen state.**
    - The fit moves with which state is left out: without MN (Austin and San Antonio dominating) θ is 4.7 per
      1,000; without TX it is 0.8. One shared rate with a symmetric place effect cannot fit Texas's two large
      cities and Minnesota's suburbs at once.
    - The intervals are wide (P90 ÷ P10 of 6–30) yet still miss, so widening them is not the fix; the level
      itself is off by state or place type.
  - **Exploratory, not pre-registered (from D-039's backtest CSVs, grouped after seeing these results):**
    summing the leave-one-place-out predictive means, suburbs, towns and the county area permitted 126 ADUs
    against 474 predicted (0.27×), while the seven large cities (Minneapolis, Austin, San Antonio, Raleigh,
    Durham, Greensboro, Cincinnati) permitted 3,492 against 1,580 (2.2×, mostly Austin, Raleigh and Durham).
    That points at a place-type modifier (central city vs suburb, or city size), the first candidate under
    D-039's step 1. It needs its own dated entry before it is fitted.
  - **Config:** unchanged.

### D-041 · 2026-11-03 · ADU counts made consistent across the four states, then a four-state comparison (written before the fits)
- **Why:** the diagnosis after D-040 (`reports/adu-statewide/diagnosis-2026-11-03.md`) found that the four
  states count different things. Ben (2026-11-03): fix the counts first; run every test across all four states
  and compare them, since that may show something about the data a pooled test hides.
- **Count rule 1, co-built units (main: excluded):**
  - **Definition:** an ADU permit is *co-built* if the same source issued a permit for a new single-family house
    (`building_type_std` SFD, `units_new` ≥ 1, not a conversion) on the same parcel within one calendar year
    either side.
  - **Why exclude:** the mechanism models an ADU added to an existing home on an eligible lot. A new house and
    second unit built together is new construction, a different channel the tool would need to model
    separately.
  - **Where it can be checked:** every source with parcel IDs (Austin, Raleigh, Durham, the Mecklenburg towns,
    Cincinnati, Minneapolis's own records). Met Council, San Antonio and Greensboro have no parcel IDs and
    can't be checked. San Antonio's permits are all for existing buildings.
  - **Shares measured before any fit** (counts only, no prediction):

    | Place | Share co-built |
    |---|---|
    | Austin 2016–23 | 66% (1,677 of 2,541) |
    | Raleigh | 18% |
    | Durham | 7% |
    | Minneapolis | 7% |
    | Mecklenburg towns | 11–22% (1–2 each) |
    | Durham County, Cincinnati | 0% |

  - **Window:** `adu_cobuilt_window_years`, 1.
- **Count rule 2, survey reporting rate (main: ρ = 0.57):**
  - **The problem:** Met Council's survey records fewer ADUs than are permitted. Over 2017–2025, it has 111 of
    the 194 ADUs in Minneapolis's own permit records.
  - **The fix:** place-years whose count comes from the survey are fitted and predicted as reported counts:
    expected = ρ × θ × k (Poisson thinning). θ then means the true rate.
  - **When a count comes from the survey:** the larger source each year is used, as now (D-019), with ties
    going to the city's own records.
  - **The range:** `adu_survey_report_rate` 0.57, range 0.3–1.0. The low end is judgment (suburbs may report
    worse than Minneapolis); the high end is no correction, as D-039.
  - **Limitation, stated now:** ρ can't correct a city that never reports.
- **Four-state comparison (every run reports, per state):**
  1. counts before and after each rule;
  2. the fit on each state alone: θ, α and θ's interval. "Not estimable" if the fit fails or the interval
     reaches the search bounds; OH is one place with 2 years, so its fit is expected to be weak;
  3. leave one state out (D-040);
  4. leave one place out, with coverage per state and totals summed by state (D-040);
  5. the test set (Raleigh, Durham);
  6. a descriptive check of the market term: correlation of log observed rate with log `h1`, pooled and
     within each state.
- **Runs:**
  - **Main:** co-built excluded, ρ = 0.57; all of 1–6.
  - **Sensitivities:** S1 co-built included; S2 ρ = 1.0; S3 ρ = 0.3. Each runs 1, 2, 3, 5 and 6; leave one
    place out runs for the main only.
- **Bars:** D-040's verdict (useful / inside only / missed) for state totals; V4 coverage for places. Every
  result is shown next to D-039 and D-040.
- **Config:** the two rules' parameters go in a new `config/params/adu_counts.yaml`, used by the calibration
  only. The scenario and its draws are unchanged until Ben adopts a refit.
- **Run once:** `uv run python scripts/dev/calibrate_adu.py --counts --out reports/adu-counts`.
- **Decided by:** Ben, 2026-11-03 ("Yes, fix counts first"; four-state comparison in the same message);
  written by WS-ENGINE before the fits.
- **Results (2026-11-03, commit 4047239; `reports/adu-counts/`, log `run-2026-11-03-log.txt`):**
  - **Counts.** Minnesota uses the survey count in 241 of its 249 place-years; no other state uses it.

    | Group | D-039 count | Co-built removed | Change |
    |---|---|---|---|
    | MN (42 places) | 306 | 285 | −7% |
    | NC fit set (6) | 50 | 45 | −10% |
    | OH (Cincinnati) | 8 | 8 | 0 |
    | TX (Austin, San Antonio) | 2,785 | 1,108 | −60% |
    | Test set (Raleigh, Durham) | 469 | 410 | −13% |

  - **Fit on each state alone (main).** These are the comparison Ben asked for.

    | State | θ per 1,000 (90%) | α | Places, place-years |
    |---|---|---|---|
    | All four (main) | 1.23 (0.81–2.11) | 2.28 | 51, 296 |
    | MN | 1.25 (0.71–2.54) | 3.46 | 42, 249 |
    | NC | 1.27 (0.54–1.77) | 0.00 | 6, 32 |
    | OH | 2.34 (1.10–5.65) | 0.00 | 1, 2 |
    | TX | 4.17 (3.95–4.39) | 0.00 | 2, 13 |

    - MN and NC agree closely once the counts are fixed. In D-039 they could not be compared, since MN was
      read from an under-reporting survey.
    - TX stays about 3.3 times higher even with co-built units removed. With 2 places, α can't be estimated
      (0), so its narrow interval is too narrow.
    - OH (1 place, 2 years) is weak, as expected.
    - The owner-occupancy share m_owner is estimated at 1.0 pooled and in MN, but 0.2–0.5 in the small state
      fits. It is weakly identified on its own, and partly takes the place of the state-level differences
      in θ.
    - None of the state fits reached the search bounds.
  - **Leave one state out (main, compared with D-040):**

    | State | Observed | P50 | P10–P90 | Obs ÷ P50 | Verdict | D-040 verdict |
    |---|---|---|---|---|---|---|
    | MN | 285 | 570 | 283–1,140 | 0.50 | useful | missed (over) |
    | NC fit set | 45 | 68 | 16–229 | 0.66 | useful | useful |
    | NC with Raleigh and Durham | 455 | 255 | 63–933 | 1.78 | useful | inside only |
    | OH | 8 | 3 | 0–26 | 2.67 | inside only | inside only |
    | TX | 1,108 | 432 | 48–2,003 | 2.56 | inside only | missed (under) |

    θ without each state: without MN 2.08 (1.24–4.19); without NC 1.31; without OH 1.24; without TX 1.16.
    In D-040 the spread was 0.78–4.67, about sixfold; here it is 1.16–2.08, under twofold.
  - **Test set (main, full fit):** Raleigh and Durham 410 against P50 159 (17–704). Inside only, 2.6 times
    under.
  - **Leave one place out (main):** coverage 92% (47 of 51 places), 94% of place-years, against D-039's 94%
    and 95%. Mean absolute error per 1,000 eligible parcels a year is 0.099, against no effect 0.098 and
    Portland unadjusted 1.97. D-039 had 0.149, 0.141 and 2.54.

    Misses are Fridley (10 against P90 4), Orono (5 against 4), Denmark township (2 against 1) and Austin
    (868 against P90 684).

    Summed by state: MN 285 against 469 (useful); NC 45 against 69 (useful); TX 1,108 against 464 (inside
    only).
  - **Market term:** the correlation of log observed rate with log `h1` is −0.11 pooled, −0.18 in MN and +0.24
    in NC (8 places). OH and TX have too few places. The sign is still wrong pooled and in MN.
  - **Sensitivities, leave one state out:**

    | Run | θ all | MN | NC | OH | TX | Test set |
    |---|---|---|---|---|---|---|
    | Main (excl., ρ 0.57) | 1.23 | useful | useful | inside only | inside only | inside only |
    | S1 co-built included | 1.52 | missed | useful | useful | missed | inside only |
    | S2 ρ = 1.0 | 0.86 | missed | useful | inside only | inside only | inside only |
    | S3 ρ = 0.3 | 2.16 | useful | inside only | useful | useful | useful |

    S1 reproduces D-040's pattern: the co-built rule is what moves TX and the without-MN fit.
  - **Reading (WS-ENGINE's, for Ben to confirm):**
    - **Most of D-040's state misses came from counting.** With co-built units out and the survey corrected,
      three of four held-out state totals are useful and none is missed. The fit no longer depends much on
      which state is left out. In MN and NC, fitted separately, the rate is the same, about 1.25 per 1,000.
    - **What the four-state view shows that the pooled test hid:** Texas is a different regime, not just
      noise. It sits about three times above MN and NC after both fixes. With only Austin and San Antonio we
      can't tell whether that is Texas, large cities, or Austin's market. The large-city pattern in D-040's
      exploratory note (Raleigh and Durham also above P50) points the same way. That remains the first
      candidate modifier, and it needs its own dated entry.
    - **Still not shown:** at the place level the model ties the no-effect benchmark (0.099 against 0.098).
      The market term still has the wrong sign in MN. So the model gets state totals right, but not which
      place builds more.
    - **ρ matters, and S3 is not a reason to pick 0.3.** S3 scores best, but 0.3 is the judgment end of the
      range. Choosing it after seeing the results would be fitting to the backtest. The main value, 0.57,
      is measured from Minneapolis. A suburban reporting rate would need suburban permit records.
  - **Config:** unchanged. θ in `hazard.yaml` is not adopted. If Ben adopts the D-041 main fit, it replaces
    D-039's 1.112 with 1.232 (0.809–2.106).

### D-042 · 2026-11-03 · Missing-middle uptake, second pre-registered fit: newly allowed types, comparison-place baseline, builder capacity (method only, before any fit)
- **Status:** fit run once on 2026-11-03 (results at the end of this entry; not taken into params). The method
  was written after the v0.2 causal-diagram review (`docs/research/lotline-causal-diagram-mm.md` §6) and the
  coding change noted under D-038.
  - **What was looked at before writing:** the panel's structure (places, adoption years, status, eligible
    parcels), parcel-value vintages, and national FRED series.
  - **D-038's own outputs.** D-038's results were already known, including its exploratory fits. Those fits are
    why Houston and Austin are examined here; this entry says so rather than hide it.
  - **The run.** It needs Ben's go-ahead after the code and tests are pushed, and runs once.
- **Why a second fit.** D-038's fit had three problems:
  - its placebo was not passed (0.32 per 1,000);
  - the leave-one-out error was no better than assuming no effect (0.235 against 0.234);
  - most of its excess came from Houston and Austin building types the reforms did not newly allow (§6.5–6.7).

  D-042 changes three things and keeps the rest of D-038.
- **Change 1: count only what each reform newly allows.**
  - **Event.** A place's event is its first rule in force on 1 July of a year 2013–2025 that raises the unit
    cap on most of its eligible parcels. The prior cap is the cap in force the year before, from
    `config/reforms/*.csv`:
    - 1 where no rule was in force;
    - otherwise the in-force rule's `unit_cap`, if its coverage holds at least half of the eligible parcels
      (D-024 coverage shares), else 1.
  - **Outcome y.** BPS buildings in the size classes above the prior cap:
    - prior cap 1: 2-unit plus 3–4 unit buildings, as in D-038;
    - prior cap 2: 3–4 unit buildings only.
  - **Dose.** The dose is the increase: d(new rule) − d(prior rule), by D-024's formula.
  - **What this means for each place.** Austin and Houston, the only places with an earlier rule followed by an
    in-window increase, enter with prior cap 2.
    - Austin's outcome excludes the 2-unit class, where post-HOME ADUs are filed (§6.6).
    - Houston's excludes the duplexes it already allowed (§6.5).
    - Every other fit place has prior cap 1.
  - **Known undercounts, stated now:**
    - Houston 5–8 unit buildings are inside BPS 5+ and are missed;
    - Austin duplexes newly allowed in SF-1 and SF-2 are missed (BPS cannot separate zones);
    - townhouses are 1-unit in BPS.
- **Change 2: a baseline from comparison places, not from the place's own other homes.**
  - **Formula.** B_it = β_i · c_s(i),t / c_s(i),pre.
    - β_i: place i's mean outcome over T−3 … T−1, as D-038.
    - c_st: the 3-year centred mean of the same size classes as i's outcome, summed over **comparison places**
      in i's state. These are places with no missing-middle event 2010–2025: status `coded_not_treated` (a
      coded rule that never allows 2+ units by right) or `uncoded`.
    - c_s,pre: c_st's mean over T−3 … T−1.
    - The ratio is capped to [0.25, 4].
  - **Thin pools.** If a state's comparison sum averages under 20 buildings a year over i's T−3 … T−1, the
    four-state comparison pool is used for i. The rule is fixed now, before any comparison outcome is
    tabulated.
  - **Why uncoded places are included.** Coded controls are too few outside Texas: the panel has 4 in MN, 2 in
    NC, 0 in OH and 33 in TX (uncoded: 93, 40, 168 and 193). An uncoded place could hold an unrecorded reform
    (C27). That would raise the comparison index and pull θ toward zero, so the bias is conservative.
  - **Why.** The comparison index carries rates and the national 2–4 shift (C55), state cycles, costs and demand
    (C01, C02, C04, C42). It uses no treated place's post-reform permits, which removes the bad-control problem
    (C56).
- **Change 3: one place-level modifier, builder capacity.**
  - **Formula.** θ_i = θ · exp(b · z_i). Here z_i = ln(1 + h_i) − mean over the fit set, and h_i is the panel's
    `pre_permits`: 2–4 unit homes per 1,000 eligible parcels, mean of T−3 … T−1 (C24, C48).
  - **How b is estimated.** It is profiled on the grid −2, −1.75, …, 2, with its 90% profile interval. θ is the
    hazard at the fit-set mean capacity.
  - **Why only one.** About seven places carry information. Land value share (C46) is the other candidate, but
    only 5 of the 14 fit places have a parcel-value vintage from before their reform:
    - those with one: Richfield, St. Louis Park, Garner, Lewisville and Lubbock;
    - none for Wilson, Wake Forest, Morrisville, Burlington, Sanford or League City, and Ohio has no values.

    A post-reform vintage is partly the reform's effect (C17), so land share is a check (below), not a fitted
    modifier.
- **Unchanged from D-038:**
  - the Poisson-gamma likelihood with u integrated out;
  - exposure × dose × F(PCR)/F(1) × ramp, with σ = 0.5;
  - the ramp half-way point on the grid 0.5–6.0, with slope 0.75;
  - α profiled;
  - θ's 90% profile interval;
  - homes per building from BPS (the D-038 deviation, kept);
  - the holdout filter and the left-out places.
- **Fit set.** D-038's 2013–2025 adopters, plus Austin and Houston as cap-increase events (event year 2024 for
  both).
  - **Expected count: 15.** These are Wilson, Morrisville, Wake Forest, Sanford, Burlington, Mooresville,
    Garner, League City, Lewisville, Lubbock, Cincinnati, Euclid, Richfield, St. Louis Park, Austin and Houston,
    less any with no pre-reform BPS years. Mooresville had none in D-038.
  - **Never read for the fit:** Minneapolis, Durham city, Durham County and Raleigh (the D-037 tests).
  - **Never read at all:** St. Paul, Charlotte and Mecklenburg (holdouts).
- **What the data can identify (stated before the fit):**
  - The ramp is identified only over the observed ages. D-038's exposure ran 0.5–2.5 years.
  - b rests on the spread of pre-reform capacity among the places with any outcome.
  - With prior cap 2, Austin's and Houston's outcomes are small counts (3–4 unit buildings), so they add little
    weight. That is intended.
- **Checks reported (none changes the estimate):**
  1. **Placebo date T − 3**, pre-reform years only. Pass if its 90% upper bound is below the main θ.
  2. **Comparison set:** `coded_not_treated` only. This is Texas places only, since the other states have too
     few.
  3. **D-038's baseline** (own other homes), with changes 1 and 3 kept.
  4. **A national baseline index:** the US 2–4 unit share of permits (FRED PERMIT24NSA over PERMITNSA, C55)
     in place of c.
  5. **Without Houston and Austin.**
  6. **Land share as a second modifier.** The median land / (land + building) value over eligible
     single-family parcels, from the parcel vintage nearest to T. It is flagged where that vintage is after T
     (C17). It is also reported on the five places with a pre-reform vintage.
  7. **σ at 0.25 and 0.8.**
  8. **Dropping events tagged `earliest_known` or `unconfirmed`.**
  9. **Plausibility against the outside table**, as D-038 check 7.
- **V4 backtest: leave one place out, as in D-038.**
  - **Refit and predict:** for each fit place j with T_j ≥ 2015, refit on calendar years ≤ T_j − 1 and predict
    j's years T_j … T_j + 4. The comparison index is realized; a sensitivity holds it at 1.
  - **Score:** P10–P90 coverage and the median's mean absolute error per 1,000 eligible parcels a year.
  - **Benchmarks:**
    - no effect: B only;
    - the outside rate unadjusted;
    - the D-038 specification refitted the same way.
  - **Test places:** the D-037 tests are predicted afterwards with the full fit and reported separately.
  - **Reading rule for Ben's question (do the confounders matter?), fixed now.** Supported if all three hold:
    - the D-042 median error is at least 10% below the no-effect benchmark;
    - coverage is at least 60%;
    - α is below D-038's 7.3.

    Otherwise the finding is that these inputs do not predict a place's uptake, and the scenario must carry
    the wide place-to-place range.
- **Not modelled:**
  - a rate × θ interaction: every large place is exposed only at about 6.7% rates, so it is not identified
    (§6.3 row 1);
  - lot-split rule type (only two places);
  - spillovers, infrastructure, HOAs and the code step.
- **Into `config/params/mm_hazard.yaml`, if Ben accepts:**
  - θ, α, the half-way point and b, with their intervals;
  - a new key `mm_builder_capacity_slope` for b.
  - Draws stay lognormal for θ and α, and b is drawn normal from its interval.
  - The D-038 values are kept in the file's history.
- **Code:**
  - extend `src/lotline/model/calibrate_mm.py` (event and prior cap, outcome classes, comparison index,
    modifier);
  - unit tests against hand-worked cases in `tests/model/test_calibrate_mm.py`;
  - the run in `scripts/dev/calibrate_mm_d042.py`, with results to `reports/mm-d042/`.
- **Decided by:** method drafted by WS-ENGINE, 2026-11-03, on Ben's instruction ("Draft D-039"), for Ben to
  approve before the run.
  - **Renumbered D-042 on 2026-11-03.** D-039 to D-041 are the ADU entries (#274, #275, #277). The draft,
    code and run are unchanged. Approved by Ben, 2026-11-03 ("Approve, build and run").
- **Before the run (code pushed first; the dry run built the inputs, printed only their structure, fitted
  nothing):**
  - **Richfield has no event under the stated rule.** Its 2010 row already allowed two-family dwellings (by
    conditional use, cap 2). Bill 2023-2 made them by right without raising the cap. The script requires the
    cap in force at the event to exceed the prior cap, so Richfield leaves the fit set and is listed.
  - **The prior cap counts any in-force cap, by right or not, as written above.** A by-right reading would
    instead give Richfield prior cap 1 and an event. That reading is not used.
  - **Mooresville** again has no pre-reform BPS year.
  - **Fit set: 14 places.**
  - **Land share** uses single-family detached parcels with land and building values above 0. The vintage
    nearest the event is after it for 9 of 13 places.
  - **Check 6 adds the land-share slope as a second modifier with b held at its main estimate.** A joint
    two-slope grid was too costly. The check is labelled as such.
- **Results (one run, 2026-11-03, `scripts/dev/calibrate_mm_d042.py`, outputs in `reports/mm-d042/`; about
  2 h 20 min):**
  - **Fit set: 13 places, 69 place-years.** Cincinnati also left at run time: Connected Communities covers
    less than half of the eligible parcels, so the cap in force on most parcels stays 1 and, under the stated
    rule, there is no cap rise. Raleigh (a test place) has no cap rise for the same reason. Dropped from the
    pre-registered list: Cincinnati, Mooresville and Richfield.
  - **Main fit.** θ = 0.17 per 1,000 eligible parcels (90%: 0.056–0.89). α = 6.2 (2.2–20). The ramp's
    half-way point sits on the grid floor, 0.5 years (0.5–1.0). b = −2.0, the grid edge, and its 90% interval
    is the whole grid (−2 to 2): the profile moves 1.2 log-likelihood units end to end, so builder capacity is
    not identified.
  - **Checks:**
    1. Placebo date T − 3: θ = 0.095 per 1,000, but its upper bound (112 per 1,000) is far above the main θ.
       **Not passed** under the stated test (the placebo is uninformative rather than positive).
    2. Coded comparison places only: 0.086.
    3. D-038's own-growth baseline: 0.095.
    4. National 2–4 unit share index: 0.17.
    5. Without Houston and Austin: 0.23 (11 places; half-way point 2.0).
    6. Land share as a second modifier: 0.16 (nearest vintage), 0.17 (pre-event vintages only). The nearest
       vintage is after the event for 9 of 12 places with values.
    7. σ = 0.25: 0.43; σ = 0.8: 0.14.
    8. Tagged events dropped: 0.004 (7 places).
  - **V4 backtest (10 places scored).** Mean absolute error per 1,000 a year:

    | Specification | MAE | P10–P90 coverage |
    |---|---|---|
    | D-042 fit | 0.185 | 70% |
    | D-042, index held at 1 | 0.172 | 70% |
    | No effect | 0.153 | 60% |
    | Outside rate | 0.163 | 50% |
    | D-038 specification | 0.119 | 80% |

    Lubbock dominates every specification's error (about 1.0–1.4 per 1,000). Its pre-reform 2–4 unit pace
    (115 buildings a year) collapsed to 25 in two years after the reform.
  - **Test places (full fit).** Minneapolis observed 106 against a P10–P90 of 149–234. Durham city observed 100
    against 32–96. Durham County observed 0, inside 0–22. Both city misses are also missed by no effect.
  - **Reading rule.** The error is 21% above no effect, not 10% below; coverage is 70% (passes); α is 6.2,
    below 7.3 (passes). **Confounders supported: no.** As pre-registered, the finding is that these inputs
    (the comparison-place baseline and builder capacity) do not predict a place's uptake in our four states.
    The scenario must carry the wide place-to-place range.
  - **What this does and does not say.** The D-042 changes made θ smaller and its interval no narrower, and
    they did not improve prediction. The D-038 specification on the corrected coding did better in the
    backtest (0.119), but it was not the pre-registered main fit here, and choosing it after seeing this
    table would be a new decision. The capacity slope's sign rests mostly on Lubbock (the highest-capacity
    place, with a fall). With 13 places and α ≈ 6, the data cannot separate a modifier from place noise.
  - **Not written to `config/params/mm_hazard.yaml`.** Ben decides whether to keep D-038's values, take the
    D-042 θ with its range, or record a new entry. No b key is added.
- **Decision (Ben, 2026-11-03): keep D-038's values** ("Keep D-038 values"). `config/params/mm_hazard.yaml`
  keeps θ = 1.08 per 1,000 (0.36–5.35), α = 7.29 and the half-way point 2.0. D-042 is recorded as a run that
  did not support the confounder model; its θ is not used. Known limits of the kept values, stated in the
  params notes:
  - D-038 was fitted before the Austin and Houston pre-reform rows were added, so it counts types those
    places already allowed (§6.5–6.7);
  - its placebo was not passed, and its own backtest was no better than no effect.


### D-043 · 2026-11-03 · A range for θ in a state the model was not fitted on (method only, before any fit)
- **Why:** Lotline's purpose is transfer to any state (HANDOFF decision 2026-10-28, test V8). A state with no
  ADU history needs no local ADU data: its rate is θ moved to its own rents, home values and mortgage rates
  (`model/hazard.py`). But the range carried with θ, 0.81–2.11 per 1,000 in D-041, only measures how well θ
  is pinned down across our four states pooled. It leaves out how much states differ from each other after
  the transport, which is the main uncertainty for a new state. Fitted alone, the four states give 1.25 (MN),
  1.27 (NC), 2.34 (OH) and 4.17 (TX). A new state's range has to carry that spread.
- **What is known already, stated now:** this entry is written after D-041's results. The per-state values
  above are seen, so pre-registering here fixes the method and the rule for reading it, not blindness to the
  data. The state-to-state spread rests mostly on Texas, which has 2 places, and Ohio, which has 1.
- **Model (main):**
  - Each state s gets its own multiplier: θ_s = θ × v_s, with log v_s normal, mean 0 and standard
    deviation τ (`adu_state_effect_sd`). θ is then the median state's rate, not the pooled rate.
  - Everything else is D-041's main fit unchanged: the expected count, the count rules (co-built units
    excluded, ρ = 0.57), the negative binomial with α, and the owner share.
  - θ, α and τ are estimated together by maximum likelihood. Each state's multiplier is integrated out with
    Gauss–Hermite quadrature (40 nodes) over its place-years. τ's 90% interval is its profile-likelihood
    interval, as for θ (χ² 1 df, 2.706), searched on 0–2.5.
  - **Unseen-state draw:** each simulation draw gives a state that is not in the fit set one multiplier,
    exp(τ z) with z standard normal, shared by every place in that state. This keeps the median at θ.
- **How it combines with the extrapolation widening (main: both, added in quadrature):**
  - The existing widening (`adu_extrapolation_widening`, D-030) stands for error in the transport formula and
    grows with a place's distance outside the reference cities' range. τ stands for what differs between
    states after the transport.
  - The two partly overlap: some of the four states' spread is itself transport error. The main run treats
    them as independent, giving a shared log-sd of sqrt(τ² + (w·d)²). This is the cautious choice for a new
    state.
  - **Sensitivity C1:** the larger of the two, max(τ, w·d), with no overlap counted.
- **Checks reported with the fit:**
  1. **K1, empirical spread:** the root mean square of log(observed ÷ P50) over D-041's four
     leave-one-state-out state totals. Written down now: MN 0.50, NC fit set 0.66, OH 2.67, TX 2.56.
     These are D-041 numbers already seen, so they are a check on τ, not a second estimate.
  2. **K2, without Texas:** τ refitted on MN, NC and OH, to show how much one state drives it.
  3. **K3, state multipliers:** each fitted state's estimated v_s with its interval.
- **Validation: leave one state out with τ.** For each state, refit θ, α and τ on the other three and predict
  the left-out state's total with the unseen-state draw. That matches how a new state would be run.
  - Bars: D-040's verdicts (useful, inside only, missed) and the ratio P90 ÷ P10, next to D-041's.
  - With three states, τ is weaker still; a fit whose τ interval reaches 2.5 is reported "not estimable" for
    that state.
- **Reading rule (written now):**
  - **Estimable:** τ's upper 90% bound is below 2.5. Then `adu_state_effect_sd` is τ̂, with low and high at
    its 90% interval. A τ̂ of 0 is a valid result, not a failure. Its range still runs to the upper bound.
  - **Not estimable:** the upper bound reaches 2.5. Then τ falls back to K1's value as judgment, with low
    0.5 × K1 and high 1.5 × K1, and the source says so.
  - **The range is wide enough** if the leave-one-state-out run has no state missed. It is useful for policy
    if the median P90 ÷ P10 for a state total is under 10. If it is not under 10, the tool still reports that
    range for a new state: a wide honest range is the correct answer with four states. The write-up says what
    more states would do to it.
  - Nothing in this entry is chosen by comparing backtest scores across runs.
- **Scope:**
  - **Changes:** the range for a state that is not in the fit set (V8's Wisconsin, any state a user brings).
  - **Unchanged:** the four fitted states' own runs, which keep pooled θ. Whether they should use their own
    v_s instead is a separate question, for a separate entry.
  - **Order with V8:** V8 counts any parameter change made during the transfer test against it, so this entry
    has to be run and decided before V8 starts.
- **Code, when Ben approves the method:**
  - `calibrate_adu.py`: the marginal likelihood, with a unit test on a hand-worked two-state example.
  - `--state-effect` in `scripts/dev/calibrate_adu.py`, writing to `reports/adu-state-effect/`.
  - The unseen-state draw in `scenarios/adu.py`.
  - The parameter in `config/params/hazard.yaml`, only after Ben adopts the result.
- **Run once:** `uv run python scripts/dev/calibrate_adu.py --counts --state-effect --out
  reports/adu-state-effect`.
- **Decided by:** Ben, 2026-11-03 ("Its ok if it's a statewide theta as the goal is to calculate a number based
  on the state", then "Yes, draft it"); written by WS-ENGINE before any fit. **Status:** method only, not run.
- **Results (2026-11-03; code committed with these results, on 886885b; `reports/adu-state-effect/`, log
  `run-2026-11-03-log.txt`):**
  - **How it was run:**
    - The rule shares were held at fit 3's values on the same places: owner 1.0, other 0.3 for the full fit;
      owner 0.4 without MN. θ, α and τ were fitted with the shares fixed.
    - With τ = 0, the full fit reproduces D-041 exactly: θ 1.232 and log-likelihood −383.718.
    - Sensitivity C1 changes only the scenario draw (`hazard.widen_unseen_state`). The calibration backtest
      has no extrapolation widening, so C1 can't be shown in it.
  - **τ:**

    | Fit | θ per 1,000 (90%) | α | τ (90%) |
    |---|---|---|---|
    | All four states | 1.23 (0.81–2.08) | 2.28 | 0 (0–0.67) |
    | Without MN | 2.10 (1.16–4.02) | 0.15 | 0.39 (0–1.16) |
    | Without NC | 1.31 (0.78–2.73) | 2.98 | 0 (0–0.94) |
    | Without OH | 1.24 (0.80–2.15) | 2.40 | 0 (0–0.72) |
    | Without TX (K2) | 1.16 (0.71–1.99) | 2.39 | 0 (0–0.72) |

  - **K1 (empirical spread):** 0.79, from D-041's ratios 0.50, 0.66, 2.67 and 2.56. That sits above τ's upper
    bound of 0.67.
  - **K3 (state multipliers):** all 1, since τ̂ = 0.
  - **Leave one state out with τ, next to D-041:**

    | State | Observed | P50 | P10–P90 | Verdict | P90 ÷ P10 | D-041 verdict | D-041 P90 ÷ P10 |
    |---|---|---|---|---|---|---|---|
    | MN | 285 | 596 | 275–1,295 | inside only (0.48) | 4.7 | useful (0.50) | 4.0 |
    | NC | 45 | 68 | 15–232 | useful | 15.5 | useful | 14.3 |
    | OH | 8 | 3 | 0–26 | inside only | ∞ | inside only | ∞ |
    | TX | 1,108 | 430 | 48–2,009 | inside only | 41.9 | inside only | 41.7 |
    | NC with Raleigh and Durham | 455 | 255 | 62–949 | useful | 15.3 | useful | 14.8 |

    None is missed. The median P90 ÷ P10 over the four states is 28.7; D-041's was 28.0. MN moves from useful
    to inside only because its ratio moved from 0.50 to 0.48, across the bar's factor of 2.
  - **Reading by the rule written before the fit:**
    - **τ is estimable** (upper bound 0.67, below 2.5). So `adu_state_effect_sd` is 0, with a range of 0–0.67.
    - **The range is wide enough:** no state is missed.
    - **It is not useful for policy by the bar:** the median P90 ÷ P10 is 28.7, above 10. As stated, the tool
      still reports it.
  - **What this means (WS-ENGINE's reading, for Ben to confirm):**
    - **τ = 0 does not mean the states are alike.** It means four states can't tell state differences apart
      from place differences. The place effects are wide (α 2.3), and OH and TX have one and two places. So
      Texas being high fits just as well as two high places.
    - **The upper bound, 0.67, is the informative number.** It is close to K1's 0.79. A new state's total
      could plausibly be about ×0.4 to ×2.4 of the central estimate from this source alone (P10–P90 at
      τ = 0.67).
    - **Under the rule, the central run adds no state spread.** A new state's central range would show only θ's
      uncertainty and its own places' effects; the state spread appears only in the sensitivity at the high end.
      That follows the rule, but it understates the uncertainty that motivated this entry.
    - **Fixing that is a change of method and needs its own dated entry.** One option is to draw τ from its
      profile interval in each simulation draw instead of fixing it at τ̂. Not done here.
    - **Why the leave-one-state-out ranges are wide:** OH and TX are one or two places, so their ranges are
      dominated by single places' effects. That is true with or without τ. A new state with many places, such
      as Wisconsin, would average its place effects out, so its range would be set mostly by θ and τ.
  - **Config:** unchanged. `adu_state_effect_sd` is not added to `hazard.yaml` until Ben decides. The scenario
    function exists (`hazard.widen_unseen_state`, rules "both" and "larger") but is not wired into
    `scenarios/adu.run` yet.

### D-044 · 2026-11-04 · Draw τ from its likelihood in every simulation draw (method only, before any run)
- **Why:** D-043 fitted the state multiplier's spread τ at 0, with a 90% interval of 0–0.67. Its rule set the
  parameter to the estimate, so a new state's central run would carry no state spread. That understates what
  four states can tell us: τ could be as large as 0.67, close to the 0.79 already seen in D-041 (K1).
  Ben (2026-11-04): draw τ from its interval.
- **Method (main):**
  - Compute τ's profile log-likelihood ℓ_p(τ) on a grid, τ = 0, 0.05, …, 2.5 (51 points). At each point θ and
    α are maximized, with the rule shares held as in D-043.
  - Each grid point gets probability ∝ exp(ℓ_p(τ)), which is a flat prior on 0–2.5.
  - Each simulation draw picks one τ from that distribution and one z ~ N(0, 1). The state's multiplier is
    exp(τ z), shared by every place in the state.
  - θ is drawn as now, from its interval, independently of τ.
- **Sensitivity T1:** τ from a half-normal whose 90th percentile is τ's upper 90% bound (σ = upper ÷ 1.645).
  This shape is simpler and leans less on the tail of the profile.
- **Reported:**
  1. The τ distribution: its median, 90th percentile and the share of draws at 0, for the full fit and each
     leave-one-state-out fold.
  2. The unseen-state multiplier exp(τ z) over all draws: P10, P50 and P90. This is what a new state's total
     carries from the state spread alone.
  3. Leave one state out with τ drawn, using each fold's own distribution and D-040's verdicts and P90 ÷ P10,
     next to D-041 and D-043. Main and T1.
- **Reading rule (written now):**
  - **Adopt for unseen states** if no state is missed in item 3, main. If a state is missed, report it and
    keep D-043's result.
  - Report the median P90 ÷ P10 against D-043's 28.7. A wider range is the expected cost, not a reason to
    reject the method.
  - T1 is reported, not chosen between: the main is the profile.
- **Config, when Ben adopts:** the full fit's grid and probabilities are written to a new
  `config/params/adu_state_effect.yaml`, generated by the script with its source. The scenario uses it only
  for states outside the fit set, through `hazard.widen_unseen_state` with τ drawn per draw.
- **Run once:** `uv run python scripts/dev/calibrate_adu.py --tau-draws --out reports/adu-tau-draws`.
- **Decided by:** Ben, 2026-11-04 ("Draw τ from interval"); written by WS-ENGINE before the run.
- **Results (2026-11-04, commit 508d83c; `reports/adu-tau-draws/`, log `run-2026-11-04-log.txt`):**
  - **τ's distribution** (the profile with a flat prior on 0–2.5), and the multiplier exp(τ z) a new state
    carries from it:

    | Fit | τ̂ (90% interval) | τ median | τ P90 | Share at τ = 0 | Multiplier P10–P90 |
    |---|---|---|---|---|---|
    | All four states | 0 (0–0.67) | 0.30 | 1.05 | 9% | 0.58–1.71 |
    | Without MN | 0.39 (0–1.16) | 0.55 | 1.70 | 4% | 0.41–2.41 |
    | Without NC | 0 (0–0.94) | 0.45 | 1.55 | 7% | 0.45–2.18 |
    | Without OH | 0 (0–0.72) | 0.35 | 1.25 | 8% | 0.55–1.87 |
    | Without TX | 0 (0–0.72) | 0.35 | 1.25 | 8% | 0.54–1.91 |

    The profile falls slowly above its 90% bound, so the flat prior puts about 10% of draws above 1.0.
  - **Leave one state out, τ drawn:**

    | State | Observed | Main P50 (P10–P90) | Main verdict | Main P90 ÷ P10 | T1 P90 ÷ P10 | D-043 P90 ÷ P10 |
    |---|---|---|---|---|---|---|
    | MN | 285 | 596 (200–1,784) | inside only (0.48) | 8.9 | 6.7 | 4.7 |
    | NC | 45 | 67 (11–314) | useful | 28.6 | 21.5 | 15.5 |
    | OH | 8 | 3 (0–29) | inside only | ∞ | ∞ | ∞ |
    | TX | 1,108 | 426 (39–2,513) | inside only | 64.4 | 49.1 | 41.9 |
    | NC with Raleigh and Durham | 455 | 252 (46–1,250) | useful | 27.2 | 21.4 | 15.3 |

    - **Misses:** none, in the main or in T1. Verdicts match D-043 everywhere.
    - **Median P90 ÷ P10 over the four states:** main 46.5, T1 35.3, D-043 28.7, D-041 28.0.
    - **Means are pulled up by the large-τ draws.** MN's mean is 1,483 against a P50 of 596. Ranges and
      medians are what the tool reports.
  - **Reading by the rule written before the run:**
    - No state is missed, so the method is adopted for states outside the fit set, subject to Ben's decision
      on config.
    - The wider range is the expected cost.
  - **WS-ENGINE's notes, for Ben to confirm:**
    - **The state spread is now carried.** For a new state, the median multiplier is 1 and its P10–P90 is
      0.58–1.71, before θ's own uncertainty and place effects.
    - **The tail is a choice.** The flat prior lets τ reach above 1.0 one draw in ten, which is what most
      widens the backtest ranges. T1, the half-normal, is narrower. The main stays as pre-registered.
    - **What would narrow this:** more states. Each new state's data, once it has ADU history, can join the
      fit and sharpen τ.
  - **Config:** unchanged. On adoption, the script writes `config/params/adu_state_effect.yaml` from
    `reports/adu-tau-draws/tau_profile.csv` (the full fit's grid and probabilities), and the scenario wires
    `hazard.widen_unseen_state` with τ drawn per draw for states outside the fit set.
  - **Adopted (2026-11-04, Ben).**
    - `scripts/dev/calibrate_adu.py --state-effect-config` wrote `config/params/adu_state_effect.yaml`: τ's
      51 grid probabilities from the full fit, `adu_state_effect_sd` (0, interval 0–0.668, for T1), and the
      four fitted states. No refit; the values are the D-044 run's.
    - `scenarios.adu.run` applies `hazard.widen_unseen_state` (rule "both") to every place whose `state` is
      not a fitted state: τ drawn per draw (`adu.state_noise`, seed + 4), one z per draw and state.
    - Places in MN, NC, OH and TX get a multiplier of exactly 1, so their runs are unchanged draw for draw
      (tested). The totals table flags affected places in `outside_fit_states`.
    - When a state joins the fit, re-run D-044 and regenerate the file; no code change.

### D-045 · 2026-11-04 · Why the ADU fit misses: a residual audit (method only, before the run)

- **Question:** the four-state fit (D-041 count rules) leaves a large place-to-place spread (α = 2.28) and
  misses in opposite directions by state when one is held out: MN observed ÷ P50 = 0.48, TX 2.58. Are the misses
  about how counts and denominators were built (measurement), about the transport's shape (model), or within
  what the model's own noise allows? Ben asked for this before any new fit (2026-11-04).
- **What this is not:** no parameter changes and no new fit. It reads the D-041 main fit (all four states) and
  its leave-one-state-out fits, recomputed with the same code and settings. Holdouts are untouched: the
  inputs are D-041's fit set and Raleigh and Durham (already used as tests); St. Paul (V5) is not read.
- **Items (all on `cal.place_data` with `count_settings()`):**
  1. **Place table**, one row per fit place and per test place:
     - observed Y; expected E = θ̂ Σ_c w_c Σ_t k_ct at the full fit (in-sample) and at the fit without the
       place's own state (out-of-state);
     - log ratios ln((Y + 0.5) / (E + 0.5)), and the place effect's posterior mean (Y + r) / (r + E), r = 1/α̂;
     - observed ADU permits per 1,000 eligible parcels a year;
     - count source kept, survey share of years, share of ADU permits dropped as co-built;
     - eligible parcels, `denominator_source`, `denominator_quality`, `data_tier`;
     - rent, home value, price-to-cost at central values, h1, mean rule age, share of years under a partial
       rule.
  2. **Group ratios** ΣY / ΣE (in-sample and out-of-state) by state, count source, survey or not, denominator
     source, rule-age band (< 2, 2–5, ≥ 5 years), price-to-cost tertile and calendar year.
  3. **Shape check:** pooled weighted least squares of the place log ratio (in-sample) on one covariate at a
     time with state fixed effects, weights E / (1 + α̂ E) (the negative binomial information). Covariates:
     log rent, log home value, log price-to-cost, mean rule age, log eligible parcels. 90% interval from 2,000
     place bootstraps within states. Effect reported as the ratio across the covariate's interquartile range.
  4. **Count cross-check:** every place-year covered by two or more ADU-flagging sources, with each source's
     count, and the share of the larger source.
  5. **Noise floor:** from each leave-one-state-out fit's own predictive draws for the held-out state (as in
     D-041), the share of draws within ×2 of their median, P(useful | model right), and the K1 a correct model
     would give (RMS of log draw ÷ P50).
- **How each item is read (fixed before the run):**
  - **Measurement:** within a state, group ratios by count source or denominator source differ by more than
    ×2 (with ≥ 10 expected in each group); or two sources covering the same place-years differ by more than
    ×1.5 in total; or co-built exclusion removes more than 30% of a place's ADU permits.
  - **Shape:** a covariate's effect across its interquartile range is at least ×1.5 (or at most ×0.67) and its
    90% interval excludes 1.
  - **Noise:** a state with P(useful | model right) below 0.5 cannot fail the ×2 bar by noise alone being
    excluded; its "inside only" is not evidence of misfit. K1 = 0.79 is compared with the K1 a correct model
    gives.
  - **Outcome:** a short list of fixes. Measurement fixes go first (new count or denominator rules,
    pre-registered as their own entry). Shape findings name the covariates for approach 2 (free shape terms)
    and approach 3 (the empirical benchmark). Nothing in config changes from this entry.
- **Results (run 2026-11-04 on 992546d; `reports/adu-fit-audit/`, log `run-2026-11-04-log.txt`):**
  - **The refits reproduce D-041.** Full fit θ 1.232 per 1,000, α 2.284, rule shares 1.0 and 0.3.
  - **Noise floor (item 5): state misses are mostly within the model's own noise.**
    - A correct model would be "useful" for MN 80% of the time, for NC 51%, for TX 38% and for OH 25%.
    - So TX's and OH's "inside only" verdicts are not evidence of misfit. MN's (observed ÷ P50 exactly 0.50)
      is the one state where a correct model should usually have done better.
    - The four-state K1 a correct model gives is 1.24. The observed K1 is 0.76. At the state level the fit is
      no worse than its own noise; the problem is that the noise (α) is large.
  - **Where the place spread comes from (items 1 and 2):**
    - City-records places (10) come in at ΣY/ΣE 0.94 in-sample and 1.01 out-of-state. The 41 survey-counted
      MN suburbs come in at 0.32 (0.41 out-of-state), after the survey reporting rate ρ = 0.57.
    - Many large suburbs report no ADU permit in any year, raw or after rules: Eagan (expected 25),
      Lakeville (30), St. Louis Park (22), Bloomington (33; its 3 raw permits were all dropped as co-built).
      The 15 suburbs in every year of the panel total 2 to 8 ADUs a year against 13 to 28 expected (ratio
      about 0.15).
    - Within TX the two cities differ ×8.7: Austin 3.40, San Antonio 0.39. Austin's count is after dropping
      1,677 of its 2,545 secondary-apartment permits as co-built (66%).
  - **Measurement flags (pre-registered readings):**
    - Two sources differ by more than ×1.5: Minneapolis 2017–2025, city records 194 ADU permits against the
      Met Council survey's 111 (×1.7). This is consistent with ρ = 0.57, which is already applied; it is the only
      place-year overlap that checks ρ.
    - Co-built exclusion removes more than 30%: Austin (66%), Andover (100%, 1 permit), Bloomington (100%,
      3), Crystal (80%, 4 of 5).
    - The Met Council file has 2.78 single-family permits per parcel ID, so its parcel ID is not lot-level.
      Co-built matching there can flag ADUs wrongly; the numbers affected are small.
    - Not flagged: no within-state count-source or denominator-source split met the ×2 rule with ≥ 10
      expected in each group.
  - **Shape (item 3):**
    - Home value: places with higher home values have more ADUs than the model expects. Across the
      interquartile range the effect is ×1.86 (90% interval 1.31–2.55). Flagged.
    - Eligible parcels: places with more parcels have fewer ADUs per parcel than expected. Across the
      interquartile range the effect is ×0.55 (0.35–0.80). Flagged. This may be the suburban zeros above,
      not size itself.
    - Rent and price-to-cost: ×0.79 (0.44–1.30). Rule age: ×0.69 (0.31–1.07). Neither is flagged.
  - **Beyond the pre-registered readings (reported, not ruled on):** the in-sample ratio falls every
    calendar year, from 2.92 in 2016 to 0.48 in 2025.
    - On a fixed panel of the 16 places present in all ten years it falls from 1.30 to 0.32, so this is not
      only places entering.
    - Minneapolis: observed about 28 a year in 2016–20 and 14 a year in 2021–25. Expected rises from 10 to 71
      over 2016–21.
    - Austin: observed flat at 87–126 a year. Expected rises from 22 to 41.
    - The ramp (uptake building for years after a reform) is not what these places show: their counts are
      flat or falling.
  - **WS-ENGINE's reading, for Ben:**
    - **Measurement first:** decide whether a Met Council suburb that never reports an ADU is a true zero or
      a reporting gap. This drives most of α and MN's low level.
    - **Then shape**, with three candidate free terms for approach 2: the ramp (or no ramp), the
      home-value elasticity, and possibly the size effect. Approach 3's empirical benchmark should include
      the same covariates.
    - Nothing in config changes from this entry.
- **Follow-up, 2026-11-04: are the suburban zeros true zeros or reporting gaps?** (Ben: "zeros first".
  Descriptive only, no fit: `scripts/dev/fit_audit_zeros.py`, `reports/adu-fit-audit/zeros_*.csv`, log
  `zeros-run-2026-11-04-log.txt`.)
  - **Correction to the results above:** "city-records places come in at 0.94" is driven by Austin (3.40).
    Without Austin, city-records places come in at 0.42, about the same as the survey-counted suburbs. The
    survey/city split is not the finding.
  - **The zeros line up with one rule feature: no detached ADUs.**
    - Places whose rules in force allow attached ADUs only: 7 observed against 87 expected (0.08). That is
      after the 0.3 multiplier the fit already gives "other" restrictions. They include Lakeville (0 against
      30), Eagan (0 against 25) and Bloomington before 2022 (0 against 20).
    - MN survey-counted suburbs that allow detached ADUs: 0.46. Minneapolis (city records): 0.42. So where
      the rules are alike, the survey counts like the city's own records.
  - **An independent source agrees.** County assessor rolls (Dakota, Ramsey, Washington, Anoka; Hennepin
    records no unit counts) show 31 of 166,326 older single-family parcels going from 1 to 2 units between
    the 2021 and 2025 rolls. Eagan has 1 of 21,255; Lakeville and Apple Valley have none. The check misses
    some ADUs (Stillwater: 7 in the survey, none in the rolls), so it confirms near-zeros but cannot size a
    count.
  - **Reading:** the zeros are true zeros. They are not a survey reporting gap. They come from the rule-type
    structure: `type_of` puts "no detached ADUs" in "other" with parking, conditional-use permits and small
    size caps, all sharing one multiplier (m_other = 0.3). Attached-only places produce about a twelfth of
    what that multiplier allows. No count rule is needed.
  - **What is left after this:** places that allow detached ADUs still differ by state: MN 0.43, NC 1.21, OH
    0.95, TX 1.28. That is a level or shape question for approaches 2 and 3, not measurement.
  - **Proposed next entry (D-046, for Ben's approval):** give "no detached ADUs" its own multiplier, fitted
    as m_owner and m_other are, and refit with the leave-one-state-out backtest.

### D-046 · 2026-11-04 · "No detached ADUs" gets its own rule multiplier (method only, before any fit)

- **Why:** D-045's follow-up found that places whose rules allow attached ADUs only produce 7 ADU permits
  against 87 expected (0.08), after the 0.3 multiplier the fit gives every "other" restriction. `type_of`
  puts "no detached ADUs" in "other" with parking, conditional-use permits and size caps under 600 sq ft.
  Ben approved this entry on 2026-11-04 ("Yes, D-046").
- **Change, calibration only:**
  - A rule's multiplier becomes c = m_o^[owner occupancy] × m_x^[other restrictions, without detached] ×
    m_d^[no detached ADUs]. A rule with no restriction keeps c = 1.
  - A blank detached field is integrated over its field probability, as every blank field is (D-022).
  - Everything else is D-041's fit 3: counts (co-built excluded, survey ρ = 0.57), the 51 fit places, gamma
    place effects, θ and α by profile likelihood, and Raleigh and Durham as the test set.
- **Estimation:**
  - Grids: m_o and m_x on D-019's grid 0.1, 0.2, …, 1.0; m_d on 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7,
    1.0.
  - Each share's 90% interval comes from its profile over the other two (2Δℓ ≤ 2.706). A share is
    estimable when its interval is narrower than its range; m_o and m_x keep D-019's ranges and judgment
    values, and m_d's range is 0.01–1.0 with judgment value 0.3, today's treatment.
  - θ's 90% interval profiles over the grid points inside the joint 90% region of the estimable shares
    (2Δℓ ≤ 6.251, χ² with 3 degrees of freedom); shares that are not estimable stay at their judgment value.
    This replaces fit 3's profile over the whole grid, which would take hours with three shares. A test checks
    that it gives fit 3's interval when m_d is fixed.
  - The grid is evaluated in parallel; results do not depend on the number of workers.
- **Reported:**
  1. The full fit: θ, α, m_o, m_x, m_d with intervals, and the log-likelihood next to D-041's (−383.718).
     The models are not nested (a detached-only rule moves from m_x to m_d), so the gain is reported against
     one added parameter.
  2. In-sample ΣY / ΣE for attached-only places (D-045: 0.08) and for the rest.
  3. Leave one state out, as D-041: state totals with P10/P50/P90, verdicts, K1 (RMS of log observed ÷ P50
     over the four states; D-041 0.791) and median P90/P10 (D-041 28.0). Test set from the full fit.
- **Adoption rule, fixed now:** adopt if all three hold:
  - m_d is estimable and its 90% interval excludes the fitted m_x;
  - the log-likelihood improves by at least 1.353 (2Δℓ ≥ 2.706, one added parameter);
  - leave one state out has no state missed and K1 no larger than 0.791.
  - Otherwise report it and keep D-041.
- **On adoption:** `adu.yaml` gets the m_d share with its source. The scenario's rule types (`TYPES`,
  `type_of`, rule priors) are split to match, in their own PR with tests. Nothing in config changes in this
  entry.
- **Results (run 2026-11-04 on b1148ba; `reports/adu-detached/`, log `run-2026-11-04-log.txt`):**
  - **Full fit:** θ 1.337 per 1,000 (0.869–2.294), α 2.031.
    - m_o is 1.0 (0.8–1.0) and m_x is 0.3 (0.2–1.0).
    - m_d is 0.3, with a 90% interval of 0.1–1.0. It is estimable (narrower than 0.01–1.0), but the interval
      includes m_x.
    - Log-likelihood −382.464, a gain of 1.254 over D-041.
  - **Folds:** without MN, m_d is not estimable (0.01–1.0); the other three folds match the full fit.
  - **Attached-only places, in-sample:** 0.21 (D-041 0.08). The change comes from the structure, not from
    m_d differing from m_x. A rule that is attached-only and has another restriction now gets m_x × m_d =
    0.09, where it got 0.3.
  - **Leave one state out:**
    - MN useful (observed ÷ P50 0.55), NC useful (0.58), OH useful (2.00, on the boundary), TX inside only
      (2.16). D-041 had OH and TX inside only.
    - K1 0.658 (D-041 0.791). None missed. Median P90/P10 23.4 (D-041 28.0).
    - Test set from the full fit: Raleigh and Durham inside only, observed ÷ P50 2.27.
  - **Adoption rule:** m_d's interval does not exclude m_x, and the gain (1.254) is under 1.353. **D-046 is
    not adopted; D-041 stays.**
  - **WS-ENGINE's notes, for Ben:**
    - The backtest is better on every pre-registered measure, but the likelihood does not separate m_d from
      m_x. With α near 2, ten attached-only places with zeros are weak evidence: under the fitted spread,
      a zero against 30 expected has a probability near 0.17.
    - Any change to adopt the split structure anyway (m_d tied to m_x, so restrictions compound) would be a
      new entry, written before it is fitted. It should not be read off this run.
    - The large place spread (α) remains the main problem. Approaches 2 and 3 target it.

### D-047 · 2026-11-04 · Approaches 2 and 3: let the data set the shape, and race the mechanism against an empirical model (method only, before any fit)

- **Why:** D-045 found the misfit is mostly place-to-place (α 2.28), with the ramp and home value the
  clearest shape signals. D-046's detached multiplier did not separate from m_x. Ben chose to run
  approaches 2 and 3 next (2026-11-04).
- **Common to both:**
  - D-041's data, count rules, 51 fit places, and Raleigh and Durham as the test set.
  - Rule shares are held at D-041's fit (m_o 1.0, m_x 0.3), with the D-019 rule types; no detached split.
    This keeps the comparison about shape only.
  - Leave one state out as D-041: each fold refits everything without the state, then predicts its state
    total with joint draws (one parameter draw per simulation draw shared by the state's places, an
    independent place effect per place).
  - Measures: verdicts, K1 (RMS log observed ÷ P50 over the four states; D-041 0.791), median P90/P10
    (D-041 28.0), α, and the test set from the full fit.
- **Approach 2: the mechanism with three shape terms set by the data.**
  - The expected count keeps D-041's form, θ × parcels × h1 × reporting rate × max over rules of c ×
    coverage × ramp, with three changes:
    - The ramp's half-life is on the grid: no ramp (ramp = 1), 0.5, 1, 2 (today's central), 3.5, 6 years.
      The slope stays 0.75.
    - The equity elasticity β_e is on the grid 0, 0.25 (today's), 0.5, 0.75, 1, 1.5, 2. h1 is rescaled by
      (V / V_ref)^(β_e − 0.25).
    - A size elasticity β_s is on the grid −0.6, −0.4, −0.2, 0, 0.2. Expected counts are multiplied by
      (mean eligible parcels / 10,000)^β_s.
  - At each grid point, θ and α are fitted by maximum likelihood (α profiled, as fit 3). Each shape term's
    90% interval comes from its profile over the other two (2Δℓ ≤ 2.706). θ's interval profiles over the
    grid points inside the joint 90% region (2Δℓ ≤ 6.251), as D-046.
  - Predictions use each fold's estimated shape, with θ drawn from its interval.
  - **Adoption rule:** adopt if the log-likelihood gains at least 3.126 over D-041 (2Δℓ ≥ 6.251, three
    added parameters), no state is missed, and K1 is below 0.791. On adoption, the shape values go to
    `hazard.yaml` with this source, and the size term is wired in its own PR.
- **Approach 3: an empirical benchmark with no Portland transport and no pro forma.**
  - Poisson-gamma, log μ_t = log(eligible parcels_t × reporting rate_t) + b0 + b1 log(rent / 1,500) + b2
    log(home value / 300,000) + b3 (mortgage rate − 5) + b4 log(eligible parcels / 10,000) + b5 restricted_t
    + b6 attached-only_t + b7 log(1 + rule age_t), with a gamma place effect (variance α).
  - Inputs, all from the fit's inputs:
    - restricted_t: the probability, over blank-field combinations, that no rule in force is
      Handbook-equivalent.
    - attached-only_t: the same probability that every rule in force forbids detached ADUs.
    - Rule age: years since the oldest rule in force.
  - Maximum likelihood by Nelder–Mead (NumPy, written for this entry), best of five starts.
  - Predictions draw the coefficients from a normal with the inverse observed information (numerical
    Hessian), α at its estimate.
  - **Reading rule:** a benchmark, never adopted into config. If its K1 is lower than approach 2's by more
    than 0.10 with no state missed, the mechanism is not earning its keep. That would be reported to Ben as
    a reason to revisit D-037. Otherwise the mechanism stays.
- Nothing in config changes in this entry.
- **Amendment, 2026-11-04, before any run:** in approach 3, a covariate with no variation in a fold's fit
  set is not identified (for example attached-only without MN). It is held at 0 with no variance in that
  fold. The intercept and α are always estimated. The covariance is symmetrized before drawing.
- **Results (run 2026-11-04 on 5c667f1; `reports/adu-shape/`, log `run-2026-11-04-log.txt`):**
  - **Approach 2, full fit:**
    - The grid picks no ramp, equity elasticity 0 and size 0. No ramp is the only value inside its 90%
      interval, and the same holds in every fold. Equity sits at the grid's lower edge (interval 0–0); size's
      interval is −0.2 to 0.2.
    - θ 0.630 per 1,000 (0.421–0.986). θ is lower than D-041's because early years now count at full
      strength.
    - α 2.259. Log-likelihood −324.259, a gain of 59.5 over D-041, almost all of it from dropping the ramp.
  - **Approach 2, leave one state out:** MN, NC and OH useful; **TX missed**, observed ÷ P50 17.3.
    - The fold without TX picks size −0.4, from MN-dominated data.
    - Austin (151,000 eligible parcels) and San Antonio (362,000) are larger than any fit place in that
      fold; the largest, Minneapolis, has 75,000. So the size term cuts their prediction by 3 to 4 times.
    - K1 1.482; median P90/P10 18.8. Test set from the full fit: inside only, observed ÷ P50 3.3.
  - **Approach 2 adoption rule:** the gain passes; missed 1 and K1 1.482 fail. **Not adopted.**
  - **Approach 3, full fit:** log-likelihood −294.027, α 1.344.
    - Coefficients: rent −5.33 (SE 1.38), home value +1.87 (0.63), restricted +0.49 (0.17), attached-only
      −1.54 (0.70). Rate, size and rule age are near 0.
    - The rent sign is the opposite of the pro forma's. Rent and home value move together, so the two are
      partly trading off.
  - **Approach 3, leave one state out:** MN and NC useful; OH (observed ÷ P50 0.20) and TX (2.95) inside
    only; NC with Raleigh and Durham missed (2.66).
    - K1 1.042; median P90/P10 15.0. Test set from the full fit: **missed**, observed ÷ P50 4.3.
  - **Approach 3 reading rule:** its K1 (1.042) is more than 0.10 below approach 2's (1.482), with no state
    of the four missed, so the rule as written says "revisit D-037".
    - **The rule was mis-specified:** it compared approach 3 with approach 2 only, not with D-041. D-041's
      K1 is 0.791, lower than both, and D-041 misses nothing, including the test set.
    - WS-ENGINE reads this as: the mechanism transfers better than the empirical model. The written rule's
      trigger is reported as fired; Ben decides.
  - **What the two approaches show together:**
    - In-sample, both fit far better than D-041: AIC 662.5 (approach 2) and 606.1 (approach 3) against
      775.4.
    - Out of state, both transfer worse. The shapes learned from 51 places, 42 of them MN, do not carry to
      other states. Texas's cities are outside the fit's size range, and rent and home value trade off.
    - **The one robust finding is the ramp.** No ramp wins in every fold with a tight interval, and the
      audit's year-by-year residuals pointed the same way. The equity and size terms are not robust.
  - **WS-ENGINE's proposal, for Ben (D-048, not yet written):** D-041 with the ramp removed and nothing
    else changed, scored on the same leave-one-state-out test. Nothing in config changes from this entry.
- **Correction (2026-11-04):** the D-047 chart and PR comment said D-041's test set (Raleigh and Durham, from
  the full fit) was useful. It was inside only: observed 410 against P50 159
  (`reports/adu-counts/statewide.csv`). The group "NC with Raleigh and Durham" was useful.

### D-048 · 2026-11-04 · D-041 without the ramp (method only, before any fit)

- **Why:** D-047 approach 2 chose no ramp in every fold, and no other ramp value was inside its 90%
  interval. The D-045 audit found counts flat or falling while the ramp expected them to rise 3–5×. Ben
  approved this entry on 2026-11-04 ("Yes, D-048").
- **Change:** a rule's ramp is 1 from its effective date (`calibrate_shape.shaped` with `NO_RAMP`, the
  central equity elasticity and size 0). Nothing else changes: D-041's counts, fit places and test set, fit
  3's rule-share grid and profile likelihood, and its gamma place effects.
- **Reported:**
  1. Full fit: θ, α, m_o, m_x with intervals, and the log-likelihood next to D-041's (−383.718). The ramp
     was never fitted, so no parameter is added.
  2. Leave one state out as D-041: verdicts, K1 (D-041 0.791), median P90/P10 (D-041 28.0).
  3. Test set from the full fit (D-041: inside only, observed ÷ P50 2.58).
- **Adoption rule, fixed now:** adopt if no state of the four is missed, K1 is below 0.791, and the test set
  is not missed. Otherwise keep D-041.
- **On adoption (each in its own PR, after Ben confirms):**
  - The scenario's ramp becomes 1 from adoption: `adu_ramp_half_years` and `adu_ramp_slope_years` are
    replaced by a documented no-ramp setting with this source.
  - θ, α and the D-030 anchor terms (`adu_anchor.yaml`) are refitted under D-048 and written to config.
  - Five-year totals will rise, because reforms reach full strength in year 1. The dashboard and the
    scenario comparison must say so.
- **Results (run 2026-11-04 on 3c5228d; `reports/adu-no-ramp/`, log `run-2026-11-04-log.txt`):**
  - **Full fit:** θ 0.659 per 1,000 (0.443–1.023), α 2.214, m_o 1.0, m_x 0.3. Log-likelihood −327.881, a
    gain of 55.8 over D-041 with no added parameter. In-sample, no ramp is decisively better.
  - **Leave one state out:** MN, NC and OH useful; **TX missed** (observed 1,108, P50 236, P90 977); NC with
    Raleigh and Durham inside only (2.00). K1 0.870; median P90/P10 22.0.
  - **Test set:** inside only, observed ÷ P50 3.42 (D-041 2.58).
  - **Adoption rule:** TX missed and K1 not below 0.791. **Not adopted; D-041 stays.**
  - **WS-ENGINE's notes, for Ben:**
    - **D-041's better transfer is partly the ramp compensating.** In MN, many places' rules are young, so
      the ramp shrinks their expected counts and the fit raises θ to match. Without TX, θ is 1.16 per 1,000
      with the ramp and 0.56 without. TX's rules are old (ramp near 1), so its prediction scales with θ.
      The ramp helped TX through θ, not through a better description of TX.
    - **The yardstick is too noisy to choose between these models.** D-045's noise floor: a correct model
      gives K1 about 1.24 on four state totals, and is useful for TX only 38% of the time. So K1 0.79 against
      0.87, and TX inside or just missed, are within noise. Austin alone (3.4× expected under D-041, ×8.7
      San Antonio's rate) decides the TX verdict for every model tried.
    - Proposed next entry: a sharper model-comparison yardstick, held-out log score per place, before
      choosing between D-041 and D-048.
- **Adopted 2026-11-05 (Ben: "Adopt D-048"), after D-049.** No pre-registered rule triggered it: Ben chose it
  on D-049's evidence (three yardsticks favour no ramp; only the noisy state-total test opposes it).
  - **Ramp:** `adu_ramp_half_years` and `adu_ramp_slope_years` are replaced by `adu_ramp_share` = 1 (fixed),
    read through `hazard.adu_ramp`. The old logistic stays as `hazard.PRE_D048_RAMP`; the scripts behind
    D-039 to D-049 now pass it (`calibrate_adu.pre_d048`) so their recorded runs still reproduce.
  - **θ and α written to config** (`hazard.yaml`): θ 0.000659 (0.000443–0.001023), α 2.214 (1.406–3.486 from
    the observed-information log-SE 0.276). These replace D-019 fit 3's 0.001038 and 4.735 (16 places, with
    the ramp); D-041's θ was never written to config.
  - **Anchor terms** (`adu_anchor.yaml`) regenerated with `--draw-terms` on the D-048 fit set (51 places, 296
    place-years) instead of D-019's 16 places.
  - **Deviation from "each in its own PR":** the ramp, θ/α and anchor terms are one PR. The ramp without the
    refit would pair a no-ramp scenario with a θ fitted with the ramp.
  - **Correction to "five-year totals will rise":** that held θ fixed. θ falls by 37%, so for a typical place
    the five-year mean is about 7% lower than under the config it replaces (×0.929 = 0.659 × 5 / (1.038 ×
    3.417), where 3.417 is the old ramp's sum over years 1–5). Year 1 is about 3× higher, year 2 ×1.27, years
    3–5 about ×0.65–0.80. Against D-041's θ the five-year mean would be ×0.78.
  - **Not redone here:** D-044's state effect (`adu_state_effect.yaml`) was estimated from D-041's folds,
    which had the ramp. D-048's fold θs run from 0.56 (without TX) to 1.16 per 1,000 (without MN). The state
    effect should be re-estimated under D-048; until then it is D-041's.

### D-049 · 2026-11-04 · A sharper yardstick: held-out log score per place (method only, before any scoring)

- **Why:** D-040's yardstick scores four state totals. D-045's noise floor showed it cannot separate the
  models tried since: a correct model would average K1 ≈ 1.24 and be useful for TX 38% of the time, and
  Austin alone decides TX for every model. Ben approved this entry on 2026-11-04 ("Yes, sharper
  yardstick").
- **Score:** each fit place is scored by the fold that left its whole state out. Its held-out log score is
  log P(y_i), the probability of its observed yearly counts:
  - Mechanism models (D-041, D-046, D-047 approach 2, D-048):
    P(y_i) = ∫ Σ_c w_c P_NB(y_i | θ k_ic, α) dN(log θ; log θ̂, se²).
    - P_NB is `frailty_loglik_place`, the place effect integrated in closed form.
    - c runs over blank-field combinations; k uses the fold's rule shares, m_d (D-046) or shape (D-047 2,
      D-048).
    - θ's uncertainty (se from its 90% interval) is integrated by 20-node Gauss–Hermite.
  - Approach 3: the mean over 4,000 coefficient draws from N(β̂, Σ) of P_NB(y_i | μ_i(β), α).
  - The test places (Raleigh and Durham) are scored the same way under each model's full fit and reported
    separately.
- **Fits used:** the fold fits already run.
  - Taken from their CSVs: D-046 (`reports/adu-detached/fits.csv`), D-047 approach 2
    (`reports/adu-shape/approach2_fits.csv`) and D-048 (`reports/adu-no-ramp/fits.csv`).
  - Refitted with the same code and seeds: D-041's folds (its CSV omits m_x per fold; D-045 showed the
    refit reproduces D-041) and approach 3 (its covariance was not saved).
  - No new model is fitted.
- **Reported:** per model, the total held-out log score over the 51 places, its sum by state, and the
  average per place-year. Against D-041: ΣΔ_i and its paired SE, sd(Δ_i) × √51. Places in one state share a
  fold, so the by-state sums are shown next to it. The test set's score is reported as well.
- **Decision rule, fixed now:** the model with the highest total is proposed to Ben for adoption if it
  beats D-041 by more than 2 paired SE, is not worse than D-041 in more than one of the four states, and is
  not worse on the test set by more than 2 log units. Otherwise D-041 stays. Adoption itself is Ben's call
  and gets its own PR, as written under each model's entry.
- **Results (run 2026-11-04 on f90cdb3; `reports/adu-model-scores/`, log `run-2026-11-04-log.txt`):**
  - **Held-out log score over the 51 places (higher is better), change from D-041 with 2 × paired SE:**

    | Model | Total | Δ vs D-041 | 2 × paired SE | Δ MN | Δ NC | Δ OH | Δ TX | Test Δ |
    |---|---|---|---|---|---|---|---|---|
    | D-041 | −432.4 | — | — | — | — | — | — | — |
    | D-046 | −425.5 | +6.9 | 8.5 | +6.4 | +0.3 | +0.1 | +0.2 | +0.2 |
    | D-047 approach 2 | −341.8 | +90.7 | 113.1 | +69.8 | −0.6 | +1.8 | +19.6 | −0.8 |
    | D-047 approach 3 | −322.2 | +110.2 | 141.2 | +76.5 | +0.9 | +1.3 | +31.4 | −1.7 |
    | D-048 | −379.9 | +52.5 | 52.2 | +27.6 | −0.2 | +1.8 | +23.3 | +0.5 |

  - **Decision rule as written:** the top model, approach 3, gains 110.2, which is under its 2 SE (141.2).
    **D-041 stays.**
  - **What the rule did not weigh:**
    - The rule looks only at the top model. D-048 alone clears every bar: +52.5 against 52.2 (2 SE), worse
      only in NC (−0.2), and +0.5 on the test set. Its margin over 2 SE is 0.3, so it is not robust.
    - Every alternative scores better than D-041 in total, and every one that drops the ramp gains in MN, OH
      and TX.
    - The gains concentrate in a few large places. Under D-048: Austin +23.2, Minneapolis +10.8, Orono +4.3,
      and the attached-only suburbs (Lakeville, Bloomington, Eagan) about +2.2 each. The paired SE is
      therefore large.
  - **The two out-of-state yardsticks disagree on D-048.** On state totals TX is missed (D-048 results). On
    places, TX scores better than under D-041 (+23.3), because D-041 also predicts Austin poorly at the place
    level; its state total was inside only because the range was wide.
  - **Note:** blank-field combinations with weight 0 give log 0 = −inf in the mixture; they drop out of the
    sum as intended (the run log's warnings).
  - **WS-ENGINE's reading, for Ben:** three yardsticks now favour no ramp: in-sample (+55.8), held-out place
    scores (+52.5, three of four states plus the test set) and the audit's year pattern. Only the noisy
    state-total test goes against it. Adopting D-048 is Ben's decision; the written rules did not trigger it.

### D-050 · 2026-11-05 · D-044's state effect re-estimated under D-048 (method only, before any run)

- **Why:** D-048 was adopted on 2026-11-05, but `adu_state_effect.yaml` still holds D-044's τ grid, which was
  estimated with the ramp. The scenario would then pair a no-ramp θ with a state spread from a ramped fit.
  Ben approved this entry on 2026-11-05 ("Yes, redo state effect").
- **Change:** D-044 exactly (τ grid 0–2.5 in steps of 0.05, a flat prior, θ and α maximized at each point, the
  same seeds), run on D-048's places: the ramp is 1 from a rule's effective date (`adu_ramp_share`). Nothing
  else changes.
- **Reported:** as D-044: τ's distribution for the full fit and each fold, the unseen-state multiplier
  exp(τ z) P10–P90, and leave one state out with τ drawn (main and T1), with D-040's verdicts and the median
  P90 ÷ P10 over the four states. D-044's results are shown next to them.
- **Rule, written now:** D-044's method and D-048 are both adopted, so the config is regenerated from this
  full fit's grid and probabilities whatever the backtest shows. A state missed in leave one state out is
  reported to Ben as a finding, not used to keep the ramped τ.
- **Run once:** `uv run python scripts/dev/calibrate_adu.py --tau-draws --no-ramp --out reports/adu-tau-draws-d048`,
  then `--state-effect-config` from that folder.
- **Results (run 2026-11-05 on 783528a; `reports/adu-tau-draws-d048/`, log `run-2026-11-05-log.txt`; the
  log's table titles still say "D-044", the script's label):**
  - **τ's distribution** and the multiplier exp(τ z) a new state carries (D-044's in brackets):

    | Fit | τ̂ (90% interval) | τ median | τ P90 | Share at τ = 0 | Multiplier P10–P90 |
    |---|---|---|---|---|---|
    | All four states | 0 (0–0.89) [0–0.67] | 0.40 [0.30] | 1.35 [1.05] | 7% [9%] | 0.50–2.02 [0.58–1.71] |
    | Without MN | 0.60 (0–1.76) | 0.80 | 1.80 | 2% | 0.31–3.17 |
    | Without NC | 0 (0–1.21) | 0.55 | 1.80 | 5% | 0.38–2.58 |
    | Without OH | 0 (0–0.95) | 0.45 | 1.50 | 7% | 0.47–2.23 |
    | Without TX | 0 (0–0.71) | 0.35 | 1.30 | 8% | 0.54–1.92 |

  - **Leave one state out, τ drawn (main):**

    | State | Observed | P50 (P10–P90) | Verdict | P90 ÷ P10 |
    |---|---|---|---|---|
    | MN | 285 | 484 (107–2,268) | useful | 21.2 |
    | NC | 45 | 74 (12–368) | useful | 30.7 |
    | OH | 8 | 6 (0–58) | useful | ∞ |
    | TX | 1,108 | 231 (25–1,221) | inside only | 48.8 |
    | NC with Raleigh and Durham | 455 | 224 (39–1,108) | inside only | 28.4 |

    - **No state missed in the main run.** TX, missed by D-048 without τ (P90 977), is inside with τ drawn.
    - **T1 (half-normal) misses TX** (P90 1,094 against 1,108). T1 is reported, not chosen (D-044).
    - Median P90 ÷ P10 over the four states: 39.8 (D-044 46.5, D-041 28.0).
  - **Config:** `adu_state_effect.yaml` regenerated from this full fit, as the rule says. Without the ramp
    the state spread is somewhat larger: a new state's multiplier P10–P90 is 0.50–2.02, up from 0.58–1.71.

### D-051 · 2026-11-04 · V9 Oregon transfer prediction: what is frozen and how it is made (method only, before any run)
- **Renumbered 2026-11-05:** written as D-046; renumbered D-051 (Ben) because #285's ADU fit entries also
  used D-046 to D-050.
- **Status:** method written before any Oregon prediction was made. Ben chose (2026-11-04) to build and test the
  runner now and **freeze later**, once the engine refresh (handoff 14) and D-043/D-045 (#279, #285) settle, and
  before 2026-11-20. Whatever ADU and missing-middle parameters are in `config/params/` on `main` at the freeze
  commit are the ones used; the freeze file records their values and the commit. A dry run before the freeze
  is a prediction only (it reads no Oregon outcome) and is not committed to `results/frozen/`.
- **What was looked at before writing:** Oregon's input tables, by row counts only
  (`docs/build/or-readiness.md`); the coded Oregon rules; no Oregon outcome after 2017 (holdout
  `V9-OR-TRANSFER`, #281, #287, #288). The V9 entry in the validation plan and Ben's conditional-forecast
  decision (2026-11-04: observed market inputs for 2018–2025 are allowed).
- **Targets (validation plan V9).** Every target is a count per calendar year 2018–2025 and an 8-year total,
  each as P10/P50/P90 and the mean of the predictive draws:
  1. **ADU permits, Portland (4159000) and Bend (4105800).** Scored against the D-041 count rules applied to
     the Portland and Bend permit adapters after unblinding (ADU-flagged permits by issue year; co-built ADUs
     excluded; city records, so report rate 1).
  2. **New 2–4 unit buildings (Census BPS, 2-unit plus 3–4 unit buildings), per HB 2001 place** in the BPS
     universe (58: 33 large-tier places, 3 Metro county remainders, 22 medium-tier places) **and their sum**,
     the headline Oregon target. The 38 places first covered in 2025 are predicted too, and reported in a
     second total.
- **Fit used.** Oregon is not in any fit (`REFORM_STATES` unchanged). ADU: `adu_mature_hazard_ref`,
  `adu_place_effect_variance`, the ramp and price-to-cost terms from `hazard.yaml` and `adu.yaml`; if D-043's
  `adu_state_effect_sd` is on `main`, its value. Missing middle: `mm_hazard.yaml` (D-038 values unless replaced).
- **ADU expected count.** For place i and year t, as `calibrate_adu.place_years`, with three differences
  forced by the blind (no Oregon permits exist in the pipeline):
  - every year 2018–2025 is predicted (no permit-coverage filter);
  - no observed-rate floor;
  - report rate 1.
  
  k_it = eligible parcels (newest roll ≤ 2017; Oregon uses the ACS fallback, held at 2013–2017) × h_m(θ = 1)
  at the newest ACS rent and value ≤ t and the year's actual 30-year mortgage rate × max over the ADU rules in
  force on 1 July t of (rule share × ramp(age)). The rules come from `config/reforms/or.csv`, state rows
  (SB 1051, HB 2001, SB 458) and local rows alike, with D-022's blank-field shares from the four states' coded
  rules. A year with no ADU rule in force has k = 0.
- **Missing-middle expected count.** y_it ~ Poisson(B_i + θ u_i k_it), as D-038, with the baseline fixed
  before the window because Oregon's 2018+ BPS is blind:
  - B_i: the place's mean 2–4 unit buildings over 2015–2017, held flat (no growth index: the index uses
    post-2017 homes). Known bias, stated now: if 2018–2025 building in other classes rose, B is low and the
    excess is credited to the reform.
  - **Amended 2026-11-04, after the first dry run and before any freeze** (a prediction only; no Oregon
    outcome seen). The first dry run treated Bend, whose duplex/triplex rule predates 2018 (`[predates]`), as
    mature from 1990 and added its full uptake on top of a baseline that already holds it. So k counts only
    the dose a rule adds above 2017's (as D-042's "count only what each reform newly allows"), and T is the
    first year a rule raises it:
  - k_it = eligible parcels (theme `missing_middle`, newest roll ≤ 2017) × (dose_t − dose_2017) × F(PCR)/F(1) ×
    ramp(t − T +
    0.5). dose_t is D-024's dose of the strongest rule in force on 1 July t (`estimate_mm.rules_by_year`).
    T is the first year from 2018 whose rule (P(by right) ≥ 0.5) raises the dose above 2017's. PCR is a rental duplex's
    price-to-cost in year T − 1, as `estimate_mm.build_panel` computes it: the newest ACS rent ≤ T − 1 and
    that year's construction cost index (`estimate_mm.plex_price_to_cost`; market inputs, allowed). Margin
    and dispersion as D-038 (`developer_margin`, `mm_feasibility_dispersion`).
- **Uncertainty (one set of draws, `adu_simulation_draws`, seed from config).**
  - **Shared across places and years:** θ (lognormal from its 90% interval, as D-030) and, if adopted, one
    state multiplier (D-043).
  - **Amended 2026-11-05, before any freeze:** D-044 (adopted) and D-050 replaced a fixed
    `adu_state_effect_sd` with τ drawn each draw from `adu_state_effect.yaml`'s grid; the file's
    `adu_state_effect_sd` is now the maximum-likelihood value (0) and is for reference only. V9 follows the
    scenario (`scenarios.adu.state_noise`): s_d = exp(τ_d z_d), one z_d per draw shared by Oregon's places,
    median 1. The runner had read the reference value, which gave Oregon no state multiplier.
  - **Shared across years only:** one place multiplier u_i ~ Gamma(mean 1, variance α) per place.
  - **Independent:** Poisson noise per year.
  - **Held at their values:** the missing-middle ramp half-way point and σ (D-038 fitted them with θ).
  - **ADU judgment parameters:** drawn as the scenario draws them (`scenarios.adu.draw_params`, D-030).
  - **ADU widening:** the ADU hazard is widened where a place lies outside the calibration range
    (`hazard.widen`), as the scenario does.
  - **Totals:** draws are summed place by place before percentiles are taken.
- **Scoring (after unblinding, written now).**
  - **Per target:** randomized P10–P90 coverage (D-003), obs ÷ P50, and D-040's verdict (useful / inside only /
    missed), for each 8-year total and for the 2018–2022 subtotal.
  - **Oregon 2–4 unit total:** also the CRPS against a no-reform benchmark (B only).
  - **Pass (as V9):** both ADU totals and the 2–4 unit total fall inside P10–P90.
  - **Reported, not tuned:** misses are reported with each place's rent and home value next to the four states'
    range (Amy's demand point). No parameter changes before the write-up.
- **The freeze file.** `results/frozen/V9-OR-TRANSFER.json` holds: the git commit; the parameter values used;
  the input table versions (manifest hashes); per target and year P10/P50/P90/mean; the 8-year totals; the
  draws' seed. It is committed and merged to `main` before `--unblind V9-OR-TRANSFER` is ever passed
  (`validation.holdout.check_unblind`).

- **Results, missing middle (scored 2026-11-05, after the freeze; ADU results follow below).** Ben said "unblind and score" on 2026-11-05. `scripts/dev/v9_or_score.py` regenerated the
  frozen draws, checked them identical to the file, and unblinded Oregon BPS in memory only. Outputs are in
  `reports/v9-oregon/`. 2–4 unit buildings, observed against P10 / P50 / P90:

  | Target | Observed | P10 | P50 | P90 | obs ÷ P50 | Verdict | CRPS model / no-reform |
  |---|---|---|---|---|---|---|---|
  | Headline, 62 places, 2018–2025 | 1,753 | 1,738 | 2,658 | 6,469 | 0.66 | useful (just inside) | 691 / 279 |
  | Headline, 2018–2022 | 1,099 | 913 | 992 | 1,228 | 1.11 | useful | 62 / 174 |
  | All 96 places, 2018–2025 | 1,942 | 1,889 | 2,813 | 6,622 | 0.69 | useful (just inside) | 662 / 318 |
  | All 96 places, 2018–2022 | 1,207 | 1,006 | 1,085 | 1,321 | 1.11 | useful | 70 / 187 |

  - **Pass rule (D-051) for the 2–4 unit total: met, barely.** The observed total sits 15 buildings above P10.
  - **The model over-predicts HB 2001's response.** Observed building ran 165–268 a year, with no rise after
    the 2021–2022 adoptions. The model's headline P50 climbs from 259 in 2022 to 712 in 2025. Over 8 years the
    no-reform benchmark (each place's 2015–2017 mean, held flat) scores better (CRPS 279 against 691). To 2022,
    before most rules took effect, the model is better (62 against 174), because its range is right while the
    benchmark's is too narrow.
  - **Places:** the 62 headline places have mean randomized coverage 0.57 (0.80 if calibrated), with 21% below
    P10 and 18% above P90, so place ranges are too narrow on both sides. Among the 34 places first reached in
    2025, 38% are above P90 in 2018–2025, before any rule reached them. Their 2015–2017 baseline is too low
    (D-051's stated bias).
  - **Reported, not tuned** (D-051). Nothing in `config/params/` changes because of this score.

- **Results, ADU (scored 2026-11-05, after the freeze).** Ben said "merge and commit" after #300 added the
  Portland and Bend permit adapters. Counts follow D-041: ADU-flagged permits by issue year, with co-built
  ADUs dropped (`calibrate_adu.adu_counts`, `count_settings()`). Outputs are in `reports/v9-oregon/adu_*.csv`.

  | Target, 2018–2025 | Observed | P10 | P50 | P90 | Verdict |
  |---|---|---|---|---|---|
  | Portland, transfer | 1,930 | 3 | 151 | 1,418 | missed (under) |
  | Portland, own history (D-052) | 1,930 | 4,070 | 8,580 | 17,832 | missed (over) |
  | Bend, both variants | 414 | 0 | 22 | 206 | missed (under) |

  The 2018–2022 subtotals miss the same way: Portland 1,446 observed against 1–703 (transfer) and 2,256–8,548
  (own history); Bend 271 against 0–126.
  - **V9's pass rule (D-051) fails.** Both ADU totals fall outside P10–P90. The 2–4 unit total is just inside.
  - **Portland's permits fell after 2018:** 532 in 2018, then 276, 194, 203, 241, 191, 156 and 137 (D-041
    counts). Its 2010–2017 history rose from 63 to 486. The model has no term that turns a rise into a fall.
    D-052's stated limit applies: the own-history variant folded Portland's fee-waiver years into u_i and
    assumed they carried on. The 2018 extension (`OR-4159000-fees-2018`) came with conditions.
  - **Counting flagged permits without the co-built rule** (2,260 for Portland, 2018–2025) misses the same
    way. So the townhouse co-built question WS-OR raised in #300 doesn't change any verdict.
  - **POST-HOC, not pre-registered (a diagnostic only):** the own-history variant re-run on the adapters' own
    D-041 counts (Portland 2010–2017, Bend 2013–2017) gives Portland 2,752–12,590 and Bend 533–1,890 (P10–P90).
    Both still miss, so the mismatch between Ord. 189050's counts and D-041's isn't the cause.
  - **Reported, not tuned.** Nothing in `config/params/` changes because of this score.

### D-052 · 2026-11-05 · V9: a second ADU variant updated on each place's own pre-2018 permits (method only, before any freeze)
- **Status:** Ben chose this on 2026-11-05, after the D-051 dry run and before any freeze. It adds a variant;
  D-051's transfer prediction is unchanged and is frozen too. Both go in `results/frozen/V9-OR-TRANSFER.json`,
  ADU targets tagged `variant: transfer` or `variant: own_history`. (Written as D-049; renumbered D-052 on
  2026-11-05 because #285 took D-045 to D-050 for the ADU fit work. D-051 was D-046 for the same reason.)
- **Why.** In the D-051 dry run almost all of Portland's and Bend's ADU range comes from the unknown place
  multiplier u_i, drawn from the four states' spread. A jurisdiction that wants to use Lotline usually has some
  of its own history. Freezing both variants measures what that history is worth, which is the sparse-data
  question the challenge asks.
- **Data.** Published yearly ADU permits for Portland and Bend for years before 2018, from city ordinances,
  staff reports or city reports, one row per place and year in `config/validation/or_adu_history.csv` with the
  URL, section and a short quote. Years 2018 and later are refused by the loader (`v9.load_history`). Years
  before the ACS series (2010) are kept in the file but not used. A missing year is skipped, not filled.
  As coded on 2026-11-05: **Portland 2010 (86) and 2016 (615)**, from Ord. 189050's findings (2009's 24 is
  kept but predates the ACS series). **No Bend count** was found in an official source, so Bend's
  own-history variant equals its transfer prediction until one is coded before the freeze.
- **Method.** For each draw d (same θ, judgment parameters, widening z_d, state multiplier s_d and blank-rule
  reading as the transfer variant):
  - M_i = Σ over history years with a count of eligible_t × widen(h_m) × s_d × max_r(rule share × ramp(age)),
    the expected permits at u_i = 1, with that year's rent, value, mortgage rate, eligible count (newest roll
    ≤ t) and rules in force on 1 July t; no pool depletion.
  - Y_i = Σ of the published counts over the same years.
  - u_i | history ~ Gamma(shape 1/α_d + Y_i, rate 1/α_d + M_i), the gamma-Poisson posterior; then the
    prediction runs exactly as D-051.
  - The random streams for everything except u_i are the transfer variant's, and Poisson noise has one stream
    per place, so the two variants differ only through u_i and a place with no count is identical in both.
    (The per-place streams changed the transfer dry run's draws, not its method.)
- **Known limits, stated now.** Published counts may define an ADU permit differently from D-041's count rules
  (for example, counting conversions or co-built units); the source row says what was counted. Portland's
  2010–2017 counts include the years of its SDC waiver, which the model has no term for; the posterior folds
  its effect into u_i and so assumes it carried on after 2018 (its 2018 extension is the `OR-4159000-fees-2018` row).
- **Scoring.** As D-051 for each variant, plus the gain: the CRPS of the own-history variant against the
  transfer variant for each ADU total.
- **Result (2026-11-05, after the freeze; full table under D-051).** The own-history variant did worse than
  the transfer variant for Portland: CRPS 4,934 against 1,242 over 2018–2025. Bend had no count, so its two
  variants are identical. Portland's pre-2018 history was a rise (the fee-waiver years) that ended in 2018.
  Carrying it forward over-predicted about fourfold. A short local history helps only if what drove it
  continues.

### D-053 · 2026-11-06 · Does the ACS fallback denominator stand in for real eligible-parcel counts? (method only, before any run)
- **Why:** The app will show every state in `config/states/` that has a results bundle (HANDOFF decision
  2026-11-06). A state with no parcel data would use `build/eligible.from_acs` (one-unit detached homes,
  B25024_002, allocated to permit-issuing jurisdictions; `denominator_source = acs_sf_fallback`, quality
  `low`) in place of `from_parcels`. That fallback counts homes, not parcels, and cannot see zoning or lot
  size, so it should over-count eligible parcels by roughly the share of single-family homes that are *not*
  on single-family-only, lot-size-eligible parcels. Whether it is usable decides whether the tool shows
  50 states or the onboarded ones only. Five states have both denominators, so the question can be tested
  where the answer is known.
- **What is known already, stated now:** the `from_acs` and `from_parcels` tables exist for MN, NC, TX, OH
  and OR and have been looked at individually (V0 reports, data dashboard). No one has compared their state
  totals. The pass rule below was chosen before that comparison (Ben, 2026-11-06, from three options:
  within 2× in every state; this rule; or ranking the proxy's error against the tornado chart, which does not
  exist yet).
- **Method (main):**
  - For each state s and theme (ADU first; MM as a check), the state total E_s = Σ `from_parcels` eligible
    parcels over jurisdictions with a parcel-based denominator, and the proxy total A_s = Σ `from_acs`
    homes over the same jurisdictions and the same 5-year end year (the newest roll's year, as the
    eligible-year rule picks it). Jurisdictions without a parcel denominator are left out of both sums, so
    the comparison is like for like.
  - Ratio r_s = E_s ÷ A_s. The scale factor is the geometric mean of the ratios: k = exp(mean log r_s).
  - **Leave one state out:** for each s, k_(−s) from the other four; the held-out ratio is
    q_s = E_s ÷ (k_(−s) × A_s).
  - Spread: σ = standard deviation of log r_s over the five states (n − 1).
- **Reading rule (written now):**
  - **Pass:** every q_s lies in [0.7, 1.4]. Then `eligible_proxy_scale` = k with low/high at
    k × exp(∓σ), and `eligible_proxy_sd` = σ, both in `config/params/` with this entry as the source. For any
    state with no parcel denominator, each simulation draw multiplies the ACS homes by k × exp(σ z),
    z standard normal, once per state per draw, so the proxy's uncertainty is carried in the range.
  - **Fail:** any q_s outside [0.7, 1.4]. The tier is not built; the app shows onboarded states only, the
    rest grey with a "bring your own state" link; the ratios are reported as a finding in D4 (limitations)
    and the data dashboard. A fail is a result, not a problem to fix by changing the proxy after seeing it.
  - A systematic ratio (all five on one side of 1) is expected and is what k absorbs; it is not a fail.
  - Nothing in this entry is chosen by comparing the ratios across alternative proxies. If a second proxy
    (for example, owner-occupied one-unit detached, B25032) is to be tried, it gets its own entry first.
- **Checks reported with the run:** the five r_s and q_s with E_s and A_s; the same by theme; the share of
  each state's parcel-based eligible count that sits in jurisdictions the ACS allocation puts in "rest of
  county"; TX and NC flagged for their unknown-land-use shares (36.5% and 19.2%, data dashboard), which make
  E_s itself uncertain there.
- **Known limits, stated now:** five states is a small set and OR is a transfer state whose parcel coverage
  is newer; the rule says nothing about within-state allocation, only state totals, so tier-3 bundles carry
  statewide results and the "in this place" view is off for them; the proxy is theme-blind, so the MM check
  is expected to be worse than ADU.
- **Scope:** changes nothing for the five onboarded states. Adds two parameters and one draw step for
  tier-3 states only. Runs after the Oregon V9 freeze is recorded and before WS-APP builds the state map.
- **Code, when run:** `scripts/dev/eligible_proxy_test.py` writing `reports/eligible-proxy/`; a unit test on
  a hand-worked three-state example of k, q_s and σ; the draw step in the scenario modules behind a
  `denominator_source == "acs_sf_fallback"` condition, with a test that a parcel-based state is untouched.
- **Decided by:** Ben, 2026-11-06 ("For 1 I think the middle option works"); drafted by Cowork; to be run by
  WS-ENGINE. **Status:** method only, not run.
