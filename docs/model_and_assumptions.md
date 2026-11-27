# Lotline: Model & Assumptions Overview

<!-- Rules §7a(4): max 25 pages, single-spaced. Every section below is required. -->

This document describes Lotline as it stands in the published release app-2026-11-27. Every number in it
comes from a file in this repository, and the file is named next to it. Each section opens with the plain
explanation; the technical detail and equations follow. Terms are defined at first use and collected in the
glossary under "Purpose and scope".

## Purpose and scope

Lawmakers need to know how many homes a reform would add, and how sure they can be. Lotline estimates how much
more housing a state would build over five years if it adopted a housing reform, compared with a baseline in
which nothing changes. It works place by place (cities, townships and the unincorporated parts of counties),
adds the places up to a state total, and always reports a range rather than a single number.

### What Lotline estimates

- **What we measure.** The model is fitted on housing units in building permits (`challenge.toml`,
  `outcome_metric = "permits"`). Permits respond first to a zoning or fee change, and the Census Building
  Permits Survey (BPS) reports them the same way in every state, for every place that issues permits, split
  into buildings of 1, 2, 3–4 and 5+ units.
- **What we report.** The headline is **net new homes**: the permits a reform adds, times the share that get
  finished (completion factors), times the share that are real new homes, minus the share pulled from
  elsewhere in the state (displacement). "Adding up to a state total" below gives the steps.
- **Horizon.** Five years (`config/params/baseline.yaml`, `forecast_horizon_years` = 5, fixed by the
  Handbook). The data run to 2025 (the *forecast origin*); 2026 is a lead year in which only today's rules
  apply, and the reform's five years are **2027–2031** (D-061).
- **Comparison.** Each reform is compared with a *baseline*: what each place would likely build under
  today's rules and economy. The answer is the difference.
- **Unit of analysis.** The permit-issuing jurisdiction. Rates are expressed per 1,000 *eligible parcels*
  (lots where the reform would apply), so a large city and a small township can be compared.
- **Ranges.** Every result is shown as P10, P50 and P90 (see the glossary). The P10–P90 range should contain
  the true value about 8 times in 10.

### The three reforms (Handbook benchmark scenarios)

Lotline runs the baseline and three of the Handbook's five benchmark scenarios (`challenge.toml`,
`scenarios`). The definitions below are the Handbook's, as recorded in `HANDOFF.md` (checklist item S1):

| Scenario | Handbook definition |
|---|---|
| `missing_middle` | "2–6 units on single-family-only parcels, up to 3 stories; setbacks and lot coverage assumed not to constrain." |
| `adu` | "one ADU per parcel with an existing single-family building; detached/semi-detached ≥600 sq ft allowed; no added parking." |
| `fees` | "total development fees cut 50% from a $50,000/unit baseline." |

An ADU (accessory dwelling unit) is a second, smaller home on the same lot as a house: a backyard cottage, a
garage apartment or a basement unit. "Missing middle" means small buildings with 2 to 6 homes (duplexes,
triplexes, fourplexes, townhouse rows and small apartment buildings). The fee scenario cuts the one-time
charges a builder pays to a local government (impact fees, utility connection fees and similar) by $25,000
per unit. We did not model transit-oriented development or parking reform, the Handbook's other two
scenarios.

### Which states

We selected 5 states to build our model, based on their history of reforms, the differences in data quality,
and the variety in their housing markets: Minnesota, North Carolina, Ohio, Texas and Oregon. The same code runs
on each; only a state's configuration file (`config/states/<st>.yaml`) and its local data adapters differ.
**Minnesota is the official benchmark state** whose statewide total is submitted. It has the most detailed
local records of the five (data tier 1, with permit-level ADU counts from the Met Council), so every step of
the method can be checked there. The other four states show that a state with thinner data can still use the
method. Wisconsin was added last with national data only, as a test of how a new state is brought in.

### What Lotline does not do

- It does not predict what happens on a particular lot. Parcels are a counting device for the number of
  places a reform could apply; results are reported for jurisdictions, regions and the state only.
- It does not forecast prices, rents or who lives in new homes. The app shows which incomes new homes could
  serve as context, not as a forecast ("Limitations and edge cases").
- It does not judge whether a reform is a good idea. It estimates production, with its uncertainty.
- It does not model reforms other than the three above, or two reforms together. Each reform is run on its
  own.

### What is built

Everything in the table is built and tested, except where the last column says otherwise.

| Part | Where | Notes |
|---|---|---|
| Data adapters (national and local), holdout filter, provenance | `src/lotline/adapters/`, `validation/holdout.py`, `docs/data_provenance.md` | |
| Eligible-parcel rule (rule 1.1) | `build/eligible.py` | |
| Permit counting (repeated project totals counted once) | `build/permits.py` | |
| Place × year panel (numerator and denominator kept apart) | `build/panels.py` | |
| Baseline forecast with P10/P50/P90 | `model/baseline.py`, `validation/backtest.py` | Backtested (V1) |
| Pro forma (residual land value, 7 building prototypes) | `model/proforma.py` | |
| Real 2025 dollars; completion factors | `model/money.py`, `calibrate/completion.py` | |
| ADU scenario and its uptake rate | `model/hazard.py`, `model/scenarios/adu.py` | Fitted on 5 states (D-096) |
| Missing-middle scenario | `model/scenarios/mm.py`, `config/params/mm_hazard.yaml` | Fitted on 5 states (D-092, C4) |
| Fee scenario, with real local fee levels | `model/scenarios/fees.py`, `model/fee_levels.py` | |
| Statewide totals: completion, net new homes and displacement | `model/results.py`, `model/aggregate.py` | |
| Share of housing need; who the homes could serve | `model/aggregate.py`, `model/shortfall.py`, `model/affordability.py` | Context only |
| Calibration: every fitted value rerun from data | `src/lotline/calibrate/`, `docs/calibration.md` | 19 of 23 steps rerun from data |
| Interactive tool, with a one-at-a-time sensitivity (tornado) chart | `src/lotline/app/`, `lotline app` | |
| Earlier ADU estimators (D-023 staggered adoption, D-025 pooled model) | `calibrate/adu/estimate_adu.py`, `calibrate/adu/pooled_adu.py` | Kept for the record; superseded by D-096. One D-025 test is skipped while a known search problem on zero-heavy panels is open |
| Evidence prong (outcomes of comparable reformed places, reweighted to a state) | `src/lotline/evidence/` | **Not built** (see "From feasibility to permits") |
| Global sensitivity (parameters moved together) | none | **Not built** |
| Market absorption cap | none | **Not built** |

### Glossary

- **Baseline:** the forecast of permits with no policy change.
- **Eligible parcel:** a lot where a reform would apply (rule in "Methodological approach").
- **Net new homes:** permits added, after completion, the net-new share and displacement.
- **P10, P50, P90:** the values below which 10%, 50% and 90% of simulated outcomes fall. P50 is the middle
  value; P10–P90 is the range shown.
- **Shrinkage:** pulling a small, noisy place's estimate toward the average of similar places. A large place
  keeps its own record; a tiny township borrows strength from its county.
- **Negative binomial:** a way to model counts (0, 1, 2, …) that are lumpier than pure chance would make them,
  which permit counts are: one subdivision can double a township's year.
- **Pro forma / residual land value:** a builder's budget for one project. Residual land value is what is left
  for the land after the finished building's value pays for construction, fees, interest and profit.
- **Hazard:** the share of eligible lots that get a new building in a year.
- **Elasticity:** the percentage change in one quantity when another changes by 1%. An elasticity of 0.3
  means a 10% better price brings about 3% more building.
- **Land capture:** the share of a cost cut that ends up in higher land prices instead of reaching builders.
- **Holdout:** outcomes deliberately hidden from the model until a prediction is frozen, so the test is fair.
- **Backtest:** pretending to stand at an earlier year, forecasting, and checking the forecast against what
  then happened.

## Core assumptions and rationale

A reader should be able to see every choice that shapes a result. Every assumption Lotline makes is a parameter
in `config/params/*.yaml` with a value, a low–high range, a unit and a source. The code never hard-codes them,
and a parameter outside its own range is rejected on load (`src/lotline/config/__init__.py`, `Parameter`).
Choices the research documents left open are logged with a date and a reason in `docs/analysis_plan.md`. The
table below lists the assumptions that shape results most; the full parameter table is in
[`docs/parameters.md`](parameters.md).

| # | Assumption, in plain words | Why | Where it is set |
|---|---|---|---|
| A1 | **Who is eligible.** For ADUs, a lot with one existing single-family house. For missing middle, a lot zoned for single-family homes only that holds one house or is vacant residential land. HOA, floodplain and historic-district lots are excluded where the data say so; unknown counts as eligible and is flagged. | Follows the Handbook definitions; vacant lots are where small buildings most often pencil. | `build/eligible.py` (rule 1.1), `config/params/eligibility.yaml`; D-014 |
| A2 | **Where lot data are missing, count homes instead.** With no usable parcel data, the denominator is the number of one-unit detached homes in the American Community Survey (ACS), marked `low` quality. A place counted from a parcel roll gets the years its roll doesn't cover from its own ACS series, scaled to meet the roll count. | Lets every place in every state be modelled, with the weakness labelled. | `build/eligible.py` (`from_acs`, `scale_history`); D-035 |
| A3 | **With no change, each place keeps its own recent pace**, pulled toward its county's pace when its record is short or small, with a regional boom-and-bust cycle around it. The cycle does not push the average up or down over time. | A simple forecast a reader can check by hand. Shrinkage handles tiny places. | `model/baseline.py`, `config/params/baseline.yaml`; D-002, D-007, D-011 |
| A4 | **The baseline is "spec B".** A place's year-to-year noise is at least what its own history shows, so one subdivision year in a small township is read as noise, not as its normal pace. Demand signals (household growth, price growth) are not used. | Spec C (demand signals) gained little, was worse for 5+ units and had unstable coefficients. | `use_direct_variance` = 1; D-002, D-006, D-007 |
| A5 | **Count a project once.** When 3 or more new-construction permits on one parcel in one year all report the same count of 50+ units, that count is the project's total and is counted once. | City files repeat a project's total on each building's permit; summing it overstates apartments. | `build/permits.py`, `config/params/permits.yaml`; D-008 |
| A6 | **Not every permitted home is finished.** 97% of single-family and ADU permits and 80% of units in 2+ unit buildings are completed (93% for all housing). | Long-run national Census ratios of completions to permits. | `config/params/aggregate.yaml`; `calibrate/completion.py` |
| A7 | **All money is in real 2025 dollars.** Prices and rents are adjusted with the consumer price index (CPI-U); construction costs with the producer price index for residential construction inputs. | Results across years are comparable; a missing index year gives a missing value, never an unadjusted one. | `model/money.py`, `config/params/money.yaml` |
| A8 | **Builders need a profit measured on the finished value** (15% for developers, 10% for a homeowner building an ADU). A project is feasible if what it can pay for land beats the lot's current-use value plus a margin. | Profit on value makes a fee cut move the land budget dollar for dollar, which is easy to check. | `model/proforma.py`, `config/params/proforma.yaml`; D-009 |
| A9 | **Buildings of 3+ attached units cost more to build** (+10% per sq ft) because they fall under the commercial building code; townhouses and duplexes do not. A switch lets triplexes use the residential code where a city allows it. | The commercial code adds sprinklers, accessibility and licensed design. No solid public source gives the size of the step, so the range is wide (3–25%). | `code_step_premium`, `triplex_under_irc`; D-009 |
| A10 | **Half of a fee cut ends up in land prices** (range 25–75%). | Fee incidence research: landowners capture part of any cost cut, more in strong markets. | `fees.yaml` `land_capture_share` |
| A11 | **Building responds weakly to cost cuts.** The fee elasticity has a median of 0.3, with 95% of draws below 1.75 and 5% below 0.05. | Quantity studies of fees are mostly null; 0.3 is a tract-level supply elasticity, 1.75 a metro-wide one. | `fees.yaml` `fee_permit_elasticity`; D-010, D-076 |
| A12 | **Some new ADUs are not new homes** (65% are, range 45–80%; and 10% of ADU permits, range 0–30%, legalize an existing unit), and **some of a place's gain is pulled from elsewhere in the state** (25%, range 0–50%). | ADUs are also used as offices, guest rooms or short-term rentals; reforms partly shift building between places. | `aggregate.yaml` |
| A13 | **Held-out outcomes stay hidden until a prediction is frozen.** St. Paul from 2024 and Charlotte from June 2023 (with Mecklenburg County's BPS rows) were removed from every table until their frozen predictions were on `main` and scored. The published results now use those years, and each bundle says so. | Keeps the forward tests (V5) honest. Two exposures are disclosed. | `config/states/*.yaml`, `validation/holdout.py`; D-012, D-013 |

We made a few less obvious choices, each for a reason a reader can check:

- **A rate per eligible parcel** separates "how many lots could change" from "how often they do". A reform can
  change both: more lots become eligible, and more of them pencil. Numerator and denominator are stored
  separately and combined only when the model needs a rate (`build/panels.py`), so a denominator fix never
  silently rewrites history.
- **Spec B over a richer model.** Decisions D-002 to D-007 record each alternative we tried and why it was kept
  or rejected, including ones that scored better on some cells. A baseline that a reader can check by hand is
  worth more here than a small gain in accuracy.
- **Profit on value (D-009).** The research documents give the feasibility test but not what profit is
  measured on. With profit on value, a $25,000 fee cut raises the land budget by exactly $25,000 per unit,
  plus interest saved when fees are paid at permit. Developer hurdles quoted as 17–25% on cost convert to
  about 15–20% of value (h / (1 + h)).
- **A low fee elasticity (D-010).** An earlier central value of 1.5 had no study behind it. The central value
  now comes from a cited study, and the low end is near zero because most fee studies find no significant
  effect on quantity.

## Data sources and cleaning steps

Anyone should be able to rebuild our numbers from public data. Lotline downloads every dataset with a script
(`lotline fetch`) into a folder outside the repository; nothing is committed. Each download is logged with a
checksum, and `docs/data_provenance.md` is generated from that log. It gives each source's URL, version,
access date, license, numbered cleaning steps and known limitations.

### Sources and what they feed

| Source | What it feeds | States | Key cleaning step |
|---|---|---|---|
| Census Building Permits Survey, annual place files | Baseline numerator: units by building size (1, 2, 3–4, 5+), as reported (Census imputation kept separately) | All | Places joined by GEOID; IDs filed twice in a year summed; held-out rows removed |
| Census BPS state totals | V0 check only: do our place sums match Census? | All | Held-out years not compared (subtraction would reveal them) |
| ACS 5-year estimates (B25024, B25003, B25064, B25077, B25034) | Fallback denominator (one-unit detached homes); rents and home values for the pro forma | All | A 5-year estimate counts for its last year and is carried forward; homes split between places, townships and county remainders without double counting |
| Census 2020 geography files, DHC housing-unit counts and redistricting data | Splitting places that cross county or township lines; names and population | All | 2020 housing-unit shares, fixed for every year |
| Census TIGER/Line 2025 boundaries (places and county subdivisions) | Placing parcels and permit points in jurisdictions | All with parcel or point data | Point-in-polygon with holes and enclaves respected; incorporated places only |
| Census Population Estimates and County Business Patterns | Housing need and place context | All | State and county totals |
| FHFA House Price Index | Price change for spec C; market context for the pro forma | All | County → metro area → state non-metro → state fallback chain |
| FRED: mortgage rate, PPI for residential construction inputs, CPI-U | Real dollars; financing | National | Annual series |
| OMB CBSA delineation, July 2023 | County → metro area; place types | All | Crosswalk only |
| HUD income limits, FY 2026 | Who new homes could serve (context) | All | Matched by HUD area |
| City and county permit files (about 30 sources) | Local checks of BPS; ADU counts BPS hides; reform-era outcomes | MN, NC, OH, TX, OR | Repeated project totals counted once (D-008); holdout filter; no personal fields requested |
| Parcel rolls (state, regional and county) | Eligible parcels | MN, NC, OH, TX, OR | Land use from local codes via a crosswalk; owner names and addresses never read |

### What each state has and what is used

The build uses parcels where a state has them and the ACS fallback elsewhere (`build/eligible.py`,
`combine`). Each state's results carry a data tier: 1 = parcel data with the fields the model needs, 2 =
parcels with land use and lot size only, 3 = national data for most places.

- **Minnesota (tier 1).** Parcel points for the seven-county Met Council area (rolls 2021–2025), Greater
  Minnesota's open-data counties (MnGeo), Ramsey County and the Minneapolis assessor. Permit files for
  Minneapolis, St. Paul, Rochester and the Met Council area. BPS reports townships as their own permit
  issuers, so Minnesota has the most places.
- **North Carolina (tier 3).** NC OneMap parcels in 48 of 100 counties, plus Wake County's 2019 and 2023
  rolls. Permit files for Raleigh, Durham, Cary, Chapel Hill, Greensboro, Asheville, Mecklenburg County and
  New Hanover County. The other 52 counties use the ACS fallback.
- **Ohio (tier 2).** The statewide parcel layer (land use and lot size, no unit counts or values) and the
  Franklin County auditor's files. Permit files for Columbus, Cincinnati, Cleveland, Franklin County and
  Montgomery County.
- **Texas (tier 3).** The statewide StratMap parcel layer and the Travis Central Appraisal District roll for
  Austin. Permit files for Austin, College Station, Dallas, Fort Worth and San Antonio, and Houston's monthly
  summary counts. Texas does not disclose sale prices, so values are appraisals.
- **Oregon (tier 3).** Portland-metro tax lots (Metro RLIS). Permit files for Portland, Bend, Medford and the
  Mid-Willamette Valley (Salem, Keizer).
- **Wisconsin (national data only).** BPS, ACS and the other national sources, with an estimated eligible-lot
  count (D-056), as a test of what a new state gets on its first afternoon.

### Cleaning rules that apply everywhere

- **Holdout filter.** Every adapter applies the holdout filter, and the panel loader checks again; a year is
  held out if any day of it falls in the outcome window (`validation/holdout.py`).
- **Unknown is never zero.** A missing denominator year stays missing. An unknown zoning or lot size is counted
  as eligible but flagged as an assumption, and the share of such parcels sets the denominator's quality:
  `high` up to 5%, `medium` above that, `low` at 50% or more (`eligibility.yaml`).
- **As reported versus as counted.** Adapters keep each source's numbers as published; counting rules such as
  D-008 are applied in a separate build step and can be switched off for comparison.
- **Privacy.** Adapters request no owner names, mailing or site addresses, contractors or loan data (each
  provenance entry lists the fields left out). Outputs are published at jurisdiction level or above, and a
  place with under 20 eligible parcels is not shown on its own (`min_eligible_parcels_publish`, D-015).

## Methodological approach

Lotline answers one question per scenario: how many more homes would be built over five years with the reform
than without it? The flow below shows each step.

```
data adapters ──► eligible parcels (denominator) ─┐
              └─► permits by size (numerator) ────┴─► place × year panel ──► BASELINE forecast
                                                                          │
pro forma: does each building type pay on a lot? ─────────────────────────┤
uptake rates fitted on our own reformed places ───────────────────────────┤
                                                                          ▼
     scenario modules: added permits = eligible lots × share that pencils × uptake over time
                                                                          ▼
     completion ► net new ► displacement ► state total, P10/P50/P90 (sum of draws)
```

### The outcome and the eligible-parcel rule

The outcome is units in permits per year, by place and building size. The *rate* is units per 1,000 eligible
parcels. Eligibility follows one versioned rule, applied the same way in every state (`build/eligible.py`,
`RULE_VERSION` = "1.1"):

- **ADU:** land use is single-family detached, at most one unit where the roll records units, the lot meets
  the minimum size (0 sq ft today: the Handbook sets none), and the lot is not excluded (HOA, floodplain,
  historic district) where those are known.
- **Missing middle:** zoned single-family-only, and either a single-family house (at most one unit) or vacant
  residential land, with the lot at least the minimum (0 today) and not excluded (D-014).
- **Unknowns:** unknown zoning counts as single-family-only; an unknown lot size passes while the minimum is 0;
  an unknown exclusion keeps the parcel. Each is flagged as an assumption.
- **Fallback:** where there are no parcels, ACS one-unit detached homes stand in. That count has no vacant land
  and no zoning, so the missing-middle fallback denominator leaves out vacant lots.

**What missing middle counts.** The Handbook's scenario allows 2–6 homes per lot, up to three stories, and
names townhouses and 2–6 unit buildings as examples. Our missing-middle model counts **BPS buildings of 2
units and of 3–4 units** (`bldgs_2`, `bldgs_3_4`), because that is the only part of the scenario that BPS
reports the same way in every place and every year. Two parts of the Handbook's definition are not counted.
BPS files each fee-simple townhouse as a 1-unit home, so townhouse rows can't be told apart from detached
houses; this matters most where a reform allows lot splits (Houston, Austin). BPS also puts 5–6 unit buildings
in its 5+ class with large apartment buildings.

The reform's strength (`estimate_mm.units_grade`) stops at 4 homes per lot for the same reason: a rule that
allows 6 scores the same as one that allows 4. Height (three stories) isn't used. **So the missing-middle
result is a floor for the scenario.** It is the added building of duplexes, triplexes and fourplexes, not of
everything the Handbook's scenario allows. Widening the count to townhouses and 5–6 unit buildings would need
city permit files with unit counts, which only about 15 places have, so it is left as a next step.

### The baseline: what gets built with no change

The baseline is the yardstick every reform is measured against. Each place keeps building at its own recent
pace, pulled toward its neighbours' pace when its own record is too short or too small to trust. The range
around that reflects lumpy years and the regional building cycle. This is spec B (D-002, D-007), with the
cycle fixed by D-011. The full specification is in the header of `src/lotline/model/baseline.py`; every step
has a hand-worked test in `tests/model/test_baseline_model.py`.

For each place *i* and building-size class, with rates per 1,000 eligible parcels and a level window of
*m* = `level_years` = 5 years ending at the origin:

1. **Recent level (direct estimate).** The place's units over the window divided by its eligible parcels over
   the window: y_i = 1000 · Σ units / Σ eligible parcels. A ratio of sums, so a place's own size weights its
   years.
2. **Group rate.** ḡ is the same ratio of sums over every place in the county, or over the state if the county
   has fewer than `min_group_places` = 5 places.
3. **How noisy is the place's own rate?** Annual counts are treated as negative binomial, with variance
   Var(c) = λ + λ²/k. The inverse dispersion 1/k is estimated from all places in the state by pooled moments:
   1/k = max(0, Σ(s_i² − c̄_i) / Σ c̄_i²), with c̄_i and s_i² the mean and variance of place i's annual counts.
   The sampling variance of y_i uses the count the group rate implies, λ_i = ḡ · P̄_i / 1000 (P̄_i = mean
   eligible parcels): v_i = 10⁶ / P̄_i² · (λ_i + λ_i²/k) / m. It is raised to the place's own observed variance
   of annual rates divided by *m* when that is larger (`use_direct_variance` = 1).
4. **Shrinkage (Fay-Herriot).** The spread between places that is real, not noise, is
   A = max(0, mean (y_i − ḡ)² − mean v_i). Each place's weight on the group is B_i = v_i / (v_i + A), and its
   level is μ_i = (1 − B_i) · y_i + B_i · ḡ, with variance (1 − B_i) · v_i. A big place (small v_i) keeps its
   own rate; a small place moves toward the group's.
5. **Keep each group's total.** Shrinkage on its own lowered state totals (found in the Wisconsin test, D-106).
   Within each group, the shrunk levels are scaled by r = Σ direct × parcels ÷ Σ level × parcels, so the
   group builds the same total at the shrunk rates as at its places' own rates (`benchmark_levels` = 1). Places
   still move toward their group; the group total no longer moves.
6. **Range, by simulation.** For each of 4,000 draws (`simulation_draws`, fixed `simulation_seed`): the true
   level is drawn from a gamma distribution with mean μ_i and the variance above; it is multiplied by a
   regional cycle factor; and each year's count is drawn from a negative binomial around the result. The cycle
   factor is exp(sum of *h* resampled year-to-year log changes in the state's total permits over the 25 years
   before the origin, `cycle_history_years`), so the band widens with the horizon *h*. The changes are centred
   by subtracting log(mean(exp(x))), so each year's factor averages 1 and the mean stays flat when nothing
   changes (D-011). The same resampled years are used for every size class and scenario in a given state,
   origin and draw, so draw *j* is the same run of boom and bust years for single-family and 5+ units.
7. **Outputs.** P10, P50 and P90 of the draws, and the mean. P50 is the point forecast because it minimizes
   absolute error; the mean is reported because means add up to state totals and medians do not.

Two optional terms exist and are off: a state momentum factor (`use_state_momentum` = 0; the backtest showed
mixed results) and the spec C demand multiplier (D-006, D-007; available as `--spec C`).

### Worked example: two places

This is the hand-worked case tested in `tests/model/test_baseline_model.py` (`test_level_estimates_by_hand`
and `test_benchmarked_levels_keep_each_group_total`). It uses a 2-year window ending in 2020 so the arithmetic
stays short; the real window is 5 years.

| | Place A | Place B |
|---|---|---|
| Eligible parcels | 900 | 100 |
| Units in 2019, 2020 | 9, 9 | 0, 0 |
| Direct rate y = 1000 × units / parcel-years | 1000 × 18 / 1800 = **10** | 1000 × 0 / 200 = **0** |
| Group rate ḡ (both places together) | 1000 × 18 / 2000 = **9** | **9** |
| Dispersion 1/k | 0 (A's counts vary less than chance; B's mean is 0) | 0 |
| Expected count λ = ḡ × parcels / 1000 | 8.1 | 0.9 |
| Sampling variance v = 10⁶ / P² × λ / m | 10⁶ / 900² × 8.1 / 2 = **5** | 10⁶ / 100² × 0.9 / 2 = **45** |
| Between-place variance A | mean(1², 9²) − mean(5, 45) = 41 − 25 = **16** | same |
| Weight on the group B = v / (v + A) | 5 / 21 = 0.24 | 45 / 61 = 0.74 |
| Shrunk level μ = (1 − B) y + B ḡ | 10 − (5/21) × 1 = **9.76** | 0 + (45/61) × 9 = **6.64** |
| Group total kept: r = 9.0 / 9.45 = 0.952 | 9.76 × 0.952 = **9.30** | 6.64 × 0.952 = **6.32** |

Place A has a steady record on many lots, so it keeps almost all of its own rate. Place B built nothing in two
years on only 100 lots. That is weak evidence that its true rate is zero, so the model moves it 74% of the way
to the group's rate. Shrinkage alone would raise the pair's total from 9.0 homes a year to 9.45, so both
levels are scaled back until the total is 9.0 again. The simulation then puts a range around each level.

### Benchmarks the baseline must beat

The validation plan (V1) requires the baseline to beat two simple forecasts on mean absolute error: the
average of the last 3 years (`benchmark_mean_years`), and a straight-line trend fitted by least squares over
the last 10 years and floored at 0 (`benchmark_trend_years`). Both are in `model/baseline.py`, with formulas in
its header.

### The pro forma: does a building pay on a lot?

A reform only adds homes where building them pays. A builder can pay for a lot only what is left after
building. Lotline works out that leftover, the *residual land value*, for seven building types (ADU,
single-family house, duplex, triplex, fourplex, 4-unit townhouse row, 6-unit building), for sale or for rent
(`model/proforma.py`):

residual land value = value − hard cost − soft cost − fees − financing − profit

- **Value:** for sale, price per sq ft × sq ft × (1 − selling costs). For rent, a year's rent after vacancy and
  operating costs (net operating income), divided by the cap rate (what investors pay per dollar of income).
- **Hard cost:** construction cost per sq ft × sq ft, plus the commercial-code step for 3+ attached units and a
  small-building premium for ADUs.
- **Soft cost:** a share of hard cost (design, engineering, insurance, permits other than fees).
- **Fees:** fee per unit × units. A cut of $25,000 per unit therefore raises residual land value by $25,000 ×
  units, plus interest saved when fees are paid at permit.
- **Financing:** loan rate × build time × (average share of hard and soft cost borrowed + fees paid at permit).
- **Profit:** a margin on the finished value.
- **Feasible** when residual land value ≥ existing-use value × (1 + margin). For an ADU the house stays, so its
  existing-use value is 0.

Local prices, rents and fee levels are inputs, so a place can use its own data; every other number comes from
`config/params/proforma.yaml`. A range (P10/P50/P90) comes from drawing each parameter from a triangular
distribution over its low, central and high values (`rlv_range`).

**Worked example** (`tests/model/test_proforma.py`, round test parameters: hard cost $200/sq ft, code step
+10%, soft cost 20%, loan 8%, half borrowed on average, build time 1.0 year under the residential code or 1.5
years under the commercial code, fees paid at permit, selling costs 5%, profit 15% of value; market price
$350/sq ft; fee $10,000 per unit):

| Line | Single-family, 2,000 sq ft | Triplex, 3 × 1,000 sq ft, commercial code | Same triplex, residential code |
|---|---|---|---|
| Value (350 × 0.95 × sq ft) | 665,000 | 997,500 | 997,500 |
| Hard cost | 400,000 | 660,000 | 600,000 |
| Soft cost | 80,000 | 132,000 | 120,000 |
| Fees | 10,000 | 30,000 | 30,000 |
| Financing | 20,000 | 51,120 | 31,200 |
| Profit (15% of value) | 99,750 | 149,625 | 149,625 |
| **Residual land value** | **55,250** | **−25,245** | **66,675** |

The triplex does not pay under the commercial code but does under the residential code: a $91,920 swing from
one code rule. That is why the code step (`code_step_premium`) and the triplex switch (`triplex_under_irc`) are
visible parameters. With a lot worth $50,000 in its current use and a 10% margin, the single-family project
(55,250 ≥ 55,000) is just feasible (`test_feasibility_against_existing_use`).

### From feasibility to permits

Knowing that a building pays is not the same as knowing how many get built. The design
(`docs/research/lotline-two-prong-design.md`) gave each scenario two routes:

1. **Mechanism route (built).** Eligible parcels → pro forma feasibility → an annual *hazard* (the share of
   feasible lots actually built on each year) → permits. The hazard is fitted on places in our own five states
   that already reformed (D-037), so the uptake rate comes from the same kind of data the model is applied to.
2. **Evidence route (not built).** Measured effects from reformed places outside our states (Portland,
   Seattle, California, Spokane, Auckland), reweighted to a state's prices and rules. We use outside studies
   only as a plausibility check on the fitted rates (`docs/research/mm-uptake-evidence.md`).

### The ADU hazard: how many eligible lots add an ADU each year

The ADU result depends most on how many owners act once ADUs are allowed. `model/hazard.py` carries one fitted
rate, the *anchor*, from the places it was fitted on to any other place through what makes an ADU worth
building there. Parameters are in `config/params/hazard.yaml`; the fit is described in `docs/calibration.md`
("The ADU chain").

    hazard in year t = ramp(t) × mature hazard
    mature hazard    = u × F(PCR) × (V / V_ref)^β_equity × exp(−β_rate × (r − r_ref)) × place-type multiplier,
                       u = h_ref / F(PCR_ref)

| Piece | Plain words | Value (range) |
|---|---|---|
| h_ref | The anchor: ADU permits per eligible lot a year for a suburb, at the reference rent, home value and rate. Fitted on 70 places and 498 place-years in our five states, St. Paul held out (D-096). | 0.224 per 1,000 (90% interval 0.170–0.303) |
| Place type | Core cities build more ADUs than suburbs; towns get a prior centred on the suburb rate (D-088, D-089). | core city × 5.7 (exp 1.74, range 1.14–2.39 on the log scale) |
| u_place | Each place's own multiplier, gamma with mean 1 and variance α. | α 1.505 (1.035–2.189) |
| PCR | ADU price-to-cost ratio from the pro forma (rented out): value (a year's rent after vacancy and operating costs ÷ cap rate) over cost (hard + soft + fees + interest while building). Rent = the place's median gross rent (ACS) × `adu_rent_to_median_ratio`. | e.g. 1.13 at Portland's 2015–19 rent, 0.79 at $1,100 a month |
| F(PCR) | Share of lots where an ADU pencils. Lots differ (a garage to convert, slope, the owner's plans), so each lot's ratio is lognormal around the place's PCR; a lot pencils above 1 + the owner's margin. F = Φ((ln PCR − ln(1 + margin)) / σ). | σ 0.5 (0.25–0.8), judgment; margin 10% (0–20%) |
| Home equity | Owners pay for most ADUs, often with home equity: median home value relative to the reference. | β_equity 0.25 (0–0.5), judgment |
| Rates | 30-year mortgage rate relative to the 2015–19 mean (3.99%), beyond the construction loan already in the pro forma. | β_rate 0.07 per point (0–0.15), judgment |
| ramp(t) | Share of the mature hazard reached t years after a rule took effect. Our own counts were flat or falling after reforms, not rising, and every fit that could choose dropped the ramp (D-048). | 1 in every year |

The reference values (rent $1,573 and home value $519,222 in 2025 dollars, Portland's ACS 2015–19; the 2015–19
mortgage rate) are recomputed by `scripts/dev/adu_reference.py`. The **calibration range** is where the fit's
places sit (D-060): rent $1,204–1,822 and home value $218,001–589,593, the eligible-parcel-weighted 5th to 95th
percentiles over the fit's place-years, and mortgage rates of 2.96–6.81%.

**Worked example** (`test_mature_hazard_one_place_by_hand`, with a round anchor of 0.004 and no place-type
term; the hazard scales in proportion to the anchor). Rent $1,100, home value half the reference, mortgage rate
2 points above 2015–19. PCR = 148,200 / 187,966 = 0.788; F = Φ((ln 0.788 − ln 1.1) / 0.5) = Φ(−0.666) = 0.253.
At the reference, PCR is 1.127 and F_ref = 0.520, so u = 0.004 / 0.520 = 0.0077. Equity 0.5^0.25 = 0.841;
rates e^(−0.07 × 2) = 0.869. Mature hazard = 0.0077 × 0.253 × 0.841 × 0.869 = **0.00142**, or 1.4 ADUs per
1,000 eligible lots a year, from year 1.

**Outside the calibration range.** Some places have lower or higher rents and home values than the places the
anchor is fitted on. The formula still applies there, but it is extrapolation, so the tool says so. Each place
gets its log distance outside the range (rent, home value and rate added up; 0 inside), a flag, and a wider
interval. Each simulation draw multiplies the hazard by exp(s·z − s²/2), s = `adu_extrapolation_widening`
(1.0, range 0.5–2) × distance, z standard normal. The noise is shared by every place in a draw, so it does not
average out in a state total; the mean stays put and P10–P90 widens with distance.

**Properties the tests check:** the hazard equals the anchor at the reference place; higher price-to-cost never
lowers it (any parameter draw in range); it never leaves [0, 1]; widening keeps the mean.

### The ADU scenario: extra homes over current local rules

The ADU scenario credits the Handbook rule only with ADUs that today's local rules would not already produce.
It lives in `model/scenarios/adu.py`, with parameters in `config/params/adu.yaml`, `market.yaml` and the ADU
shares in `aggregate.yaml` (D-019). The Handbook scenario allows one ADU on every eligible single-family
parcel, at least 600 sq ft, by right, with no parking requirement. For each place and each year t = 1 … 5 of
the window:

    current rules   h_cur(t) = max(c × h_m × ramp(a + t), observed ADU rate)
    Handbook rules  h_hb(t)  = max(c × h_m × ramp(a + t) + (1 − c) × h_m × ramp(t), observed ADU rate)
    gross ADUs(t)   = parcels still without an ADU × h(t)            (each set of rules keeps its own pool)
    ADU permits added(t) = Handbook gross ADUs(t) − current-rules gross ADUs(t)
    additional homes(t)  = ADU permits added(t) × net-new share (0.65; 0.45–0.80) × (1 − formalization share (0.10; 0–0.30))

| Piece | Plain words |
|---|---|
| h_m | The place's mature ADU hazard (previous section). |
| c | How close current local rules are to the Handbook, from the coded rules (`config/reforms/<st>.csv`) in force on 31 December of the window's first year (2027-12-31, D-064). It is 1 if a detached ADU of 600+ sq ft is allowed by right with no owner-occupancy or parking rule, and 0 for an explicit "no ADUs" row. Where ADUs are allowed with parking, a conditional permit, attached units only or a cap under 600 sq ft, it is `adu_partial_rule_share` (m_x, fitted at 0.7 and drawn from a grid of refits, D-096, D-097). An owner-occupancy rule alone has its own share, fitted at 1.0. |
| Unknown rules | **Anything not coded is unknown (D-022).** A blank rule field restricts, in each draw, with the probability that coded rules restrict it. A place with no ADU row draws its class from coded places of its state and size band (<10k, 10–50k, 50k+ people). |
| Observed ADU rate | Where local permits flag ADUs, the place's own ADU permits per eligible parcel a year over the 3 years ending at the origin. ADUs a place already builds are in its baseline, so they are never counted as added. |
| Own counts with drift | Where a place has an observed rate, its own counts set the no-reform rate, times a place drift with mean 1 (σ 1.025). The Handbook rate is that rate times the mechanism's ratio h_hb ÷ h_cur (D-091, D-093). |
| Pool | Each year's ADUs use up parcels, so a parcel gets at most one ADU. |

**Additionality and the baseline.** Census BPS counts a detached ADU as a 1-unit permit, so the baseline's
single-family forecast already holds some ADUs: 0.47% of 1-unit permits in the Twin Cities metro (Met Council
2019–22) and 7.65% in Austin (`baseline_adu_share_of_one_unit`, 3.3% pooled). The scenario adds only the
difference between Handbook and current rules, so its homes go on top of the baseline without counting those
ADUs twice.

**Mortgage rates.** A forward run holds the 30-year rate at 6.60% (FRED annual mean for 2025,
`mortgage_rate_forecast` in `market.yaml`), flat over the window. The 2015–2025 low and high (2.96–6.81%) are
run as a stress sensitivity, not as part of the forecast range. Backtests use each year's actual rate.

**Worked example** (`test_one_jurisdiction_year_by_hand`): 2,000 eligible parcels, mature hazard 0.0014219 (the
hazard example), no ADU rule today. Year 1: 2,000 × 0.0014219 = **2.84 ADU permits added**, all of them extra
because current rules give none; additional homes = 2.84 × 0.65 × 0.90 = **1.66**. Year 2: (2,000 − 2.84) ×
0.0014219 = 2.84 permits added.

**Output.** Per place and year, and as five-year totals: P10/P50/P90 and mean, over 1,000 draws of every
uncertain parameter. Five-year ranges are percentiles of each draw's sum.

### The fee scenario

A fee cut lowers what a home costs to build, and some of that saving reaches builders. Every place takes the
elasticity form (D-010):

    %Δ permits = ε × (1 − λ) × Δfee / TDC × ramp(t)

TDC is the total development cost of a home at the margin of feasibility, taken as the place's median home
value. At an illustrative TDC of $350,000 (the $25,000 cut is about 7%), the central case is 0.3 × 0.5 × 7% ≈
+1%, and a high case is 1.75 × 0.75 × 7% ≈ +9% single-family permits over five years. The response builds over
time (half after 1 year, `fee_ramp_half_years`) because projects already in design are priced at the old fees.

- **Which fees.** The app shows the Handbook benchmark ($50,000 cut to $25,000 everywhere) and real local fees
  cut in half; real local fees cut by up to $25,000 is also built (D-065). Local fees come from
  `model/fee_levels.py` (D-066): per place and building type, in 2025 dollars, with a range, and with missing
  permit and water/sewer charges filled from the median of coded places. Coded fees for a new house have
  medians of about $6,500–9,200 in MN, NC, OH and TX and about $34,000 in Oregon, against the Handbook's $50,000
  (`docs/research/fee-levels-vs-handbook.md`).
- **Building sizes (D-073).** Houses take the form above. Duplexes and 3–4 unit buildings take it with their
  own fee per unit and a cost per unit scaled to the unit's size, so the same fee is a bigger share of a plex
  unit's cost. Buildings of 5+ units get no fee cut, even in the Handbook benchmark, because we have no coded
  fees for them (a stated limit).
- **A route we switched off.** The pro forma threshold route (count lots that cross feasibility when fees fall,
  validation test V6b) is in the code but off (`fee_feasibility_channel` = 0). It gave a change 4–40 times the
  elasticity form's, and only in places with a parcel roll, so a state's result depended on which cities had
  parcel data.
- **Sensitivity.** Raising local fees by half runs through the same steps and shows what an increase costs in
  homes. The pencil-out table (`model/pencil_out.py`) shows for each place what a house, a duplex and a fourplex
  can pay for land at today's fees, after a cut and at the Handbook's levels.

### The missing-middle model (D-092, C4)

Missing middle is where the Handbook's scenario changes the most lots, so its uptake rate matters most. The
model estimates new 2–4 unit buildings per place and year in Census BPS, because that is what BPS reports the
same way everywhere ("What missing middle counts" above). For place i in year t (`config/params/mm_hazard.yaml`,
D-092's challenger C4, refitted on 2026-11-26):

    buildings_it ~ NB(mean B_it + θ × u_i × E_i × dose change_i × F(PCR_i)/F(1) × ramp(t), spread φ)

| Piece | What it is | Value (90% range) |
|---|---|---|
| B_it | The no-reform baseline: the place's mean of its 3 pre-reform years, moved by its own growth in other homes (C0). | From the place's own BPS history |
| θ | The mature rate: new 2–4 unit buildings per eligible lot per year when a reform fully allows them, at a price-to-cost of 1. | 1.66 per 1,000 lots (0.14–19.0) |
| ramp(t) | How fast the effect builds up after adoption (logistic, slope 0.75 years). | Half-way at 4.5 years (1.0–6.0) |
| u_i | The place's own multiplier, gamma with mean 1 and variance α. | α at the search's floor: no extra place spread once years are lumpy |
| φ | How lumpy a place's years are: the variance of a yearly multiplier g with mean 1, so a year's count has variance mean + φ × mean². | 13.03 (12.39–13.70) |
| E_i, dose, F | Eligible lots (rule 1.1), the coded rule's strength, and feasibility from rent and cost. | Per place |
| Homes per building | Gross homes in a new 2–4 unit building; a building on a lot with a house replaces it (teardown). | 2.08 (2.04–2.75) |

**How it was fitted.** 93 places and 299 place-years in MN, NC, OH, TX and OR (86 places in Oregon, after
HB 2001) whose coded rule raised the unit cap or the approval standard in 2013–2025. Every holdout (St. Paul,
Ramsey, Charlotte, Mecklenburg) was checked to be absent. C4 adds a prior from places that always allowed
missing middle (their level, widened for selection). φ was fitted separately on 1,379 pseudo-forecasts of 713
places that no fit or test uses. D-092's pre-registered rule chose C4 over the plain model (θ 1.68 per 1,000):
it beats it by 5 paired standard errors held out and passes the same tests. The forecast draws each place-year's
multiplier g with the same variance φ that the fit uses (corrected 2026-11-27).

**How accurate it is** (`reports/mm-d092/accuracy/`). These checks were scored at the 2026-11-15 values (θ 1.04
per 1,000, half-way 4.0 years, φ 13.63) and have not been rerun since the refit.

- **A place's count:** 78% of 136 places land inside their P10–P90 (the target is 60–95%); the baseline alone,
  held out on 468 unused places, 79%. Single places can miss at the median by 3–6× while still inside the
  range (Franklin County built 142 against 483; Minneapolis 275 against 42).
- **State totals with no reform:** Texas 4,515 built against 1,701–7,183 and Ohio 391 against 45–1,266, both
  inside; Minnesota 32 against a top of 13, a miss on small numbers.
- **A new state:** with Oregon left out, the other states' 7 places predict Oregon's 86: median 915
  (457–4,789) against 703 built. One test, passed.
- **Blind tests:** Charlotte passed (D-055's values). St. Paul, frozen with C4 before any outcome was read,
  **missed**: 55 built in 2024–2025 against 9–28 (median 15). It built 33 in the first full year against about
  6 a year before, which a half-way point of 4 years cannot produce. Its frozen range also used the narrow
  yearly spread corrected on 2026-11-27, so it was narrower than the fitted model implies.
- **The weak spot:** the reform's own effect is not clearly detected. Held out, the model with a reform effect
  beats the same model with none by only about 1.5 standard errors (+5.0, SE 3.4), and a placebo (reforms
  moved three years early) gives a larger effect than the real dates. The scenario's added homes rest on an
  effect the counts are consistent with but cannot pin down, which is why θ's range spans about 140-fold.

**Why the ranges are wide.** 39–44% of 2–4 unit buildings come in projects of 3 or more (run 13), so a place's
count depends on whether one large project lands in the window. φ carries that. A project-based model would
match how building happens but adds no information, so it is a stated next step. Place types (core city,
suburb, town) were tested and did not narrow the ranges (run 12).

**The effect is still growing at year 5.** With the half-way point at 4.5 years, year 5 holds 63% of the
five-year total. A fast-ramp sensitivity (half-way at 0.5 years, the rate of places that adopted on their own,
D-100) is shown next to the main result, never in its place.

### Adding up to a state total

A policymaker needs one statewide figure with its range, counted the same way for every reform. Place results
are summed draw by draw, not median by median, so the state P10–P90 reflects shocks that places share, such as
the regional cycle and the extrapolation noise. Places are made non-overlapping first, so no lot is counted
twice (D-020). In each of 1,000 draws (`results_draws`), `model/aggregate.py` (`homes_from_draws`) then turns
permits added into net new homes:

    homes in place      = permits added × completion factor × net-new share
    net new statewide   = homes in place × (1 − displacement share)

The completion factor is 0.97 for ADUs and 0.80 for 2–4 unit buildings; the net-new share is the ADU share
above (missing middle already subtracts teardowns); the displacement share is 0.25 (0–50%), each drawn
triangular over its range (`aggregate.yaml`). The app repeats the same arithmetic in `src/lotline/app/aggregate.js`
when a reader moves a slider, and a test checks that both give the same totals.

### Results in the published release

Five-year net new homes, 2027–2031, P10 / P50 / P90 (`reports/results/<st>/bundle.json`, release
app-2026-11-27, origin 2025), rounded as the app rounds them:

| State | Missing middle | ADU | Fees: Handbook benchmark | Fees: real local fees halved |
|---|---|---|---|---|
| Minnesota (benchmark) | 178 / 1,240 / 7,800 | 122 / 230 / 505 | 119 / 443 / 1,720 | 22 / 84 / 349 |
| North Carolina | 327 / 2,110 / 13,100 | 75 / 169 / 448 | 635 / 2,370 / 9,140 | 92 / 360 / 1,500 |
| Ohio | 268 / 1,850 / 11,300 | 164 / 345 / 886 | 241 / 883 / 3,460 | 23 / 89 / 362 |
| Oregon | 23 / 178 / 1,170 | 2 / 5 / 19 | 60 / 223 / 870 | 14 / 55 / 227 |
| Texas | 1,150 / 8,390 / 53,200 | 1,190 / 2,310 / 5,310 | 1,510 / 5,560 / 21,700 | 126 / 500 / 2,090 |
| Wisconsin (national data only) | 68 / 514 / 3,380 | 73 / 192 / 583 | 165 / 606 / 2,380 | 23 / 92 / 381 |

Means sit well above medians for missing middle, so the app quotes the median and the range. Oregon's ADU and
missing-middle results are small because most of its places already allow both. Places whose ADU or
missing-middle rule is not coded draw their rule from coded places like them (D-022), so these totals will
move as more rules are coded. `docs/policy_scenario_comparison.md` reads these results for a policymaker.

### Validation ladder and results so far

The validation plan (`docs/research/lotline-validation-plan.md` §3) sets the tests below. Thresholds the plan
marks as proposed were to be confirmed at pre-registration (tag `prereg-v1`), which has not been made.

| Step | Question | Status and result |
|---|---|---|
| V0 Data reproduction | Do our adapters count what the publishers count? | **Run.** BPS place sums within 1% of Census state totals (D-001) in MN 30/32 years, NC 29/31, OH 34/34, TX 21/34 (`reports/*/V0-national.md`; TX 2003–2014 runs 1–2% high). Austin local permits / BPS for homes in 1–2 unit buildings = **0.98** pooled 2010–2025; 5+ units 1.04 with D-008 (`reports/tx/V0.md`). |
| V1 Baseline accuracy | Does the baseline beat the benchmarks out of sample? | **Run** (fits ending 2016, 2018, 2020; 5 states × 3 windows × 4 size classes = 60 cells). With group totals kept (D-106): **21 of 60 cells pass** all three tests; the model beats both benchmarks in 47, coverage is in range in 35, bias in range in 36. State totals land inside P10–P90 in 87–100% of checks by size, but the forecast runs low overall (×1.34). |
| V2 Mechanism | Do the pro forma and hazard predict which parcels redevelop? | ADU and missing-middle rates fitted on our own reformed places, with held-out checks (`docs/calibration.md`). Parcel-level V2 **not run**. |
| V3 In-state causal estimates | What did Raleigh's and Durham's reforms do? | **Not run.** |
| V4 Backtests of known reforms | Would the range have contained what happened? | **Not run** as a separate test. |
| V5 Blind forward tests | St. Paul and Charlotte, predicted before outcomes are seen | **Charlotte: pass** (frozen 2026-11-09, D-071): 119 new 2–4 unit buildings in 2023–2025 against 89–172, median 104 (`reports/v5-charlotte/`). **St. Paul: miss** (frozen 2026-11-15 with C4, D-098): 55 against 9–28, median 15 (`reports/v5-stpaul/`). Exposures disclosed (D-012, D-013). |
| V6 Fee tests | Natural experiment; pro forma threshold; bunching | **V6b pass:** every state's five-year response sits inside the plan's range (0 to +12% for houses, 0 to +18% for 2–4 unit buildings) (`reports/v6b/`). V6a (a measured fee cut in our states) **not run**. |
| V7–V9 Transfer to a new state | Does the method carry to a state it was not built on? | **Oregon (V9): fail** on ADUs (Portland and Bend outside P10–P90), 2–4 unit total just inside (D-051). **Wisconsin (V8): fail**: 112,166 homes permitted in 2021–2025 against 53,126–103,715 (×1.49, D-105). The group-total fix (D-106) was adopted after this test; it is not a rescore. |

A V1 cell passes when the model's error is below both benchmarks', its randomized P10–P90 coverage is 70–90%
(D-003), and the post-2022 bias of its mean is within 25% of its error (D-004). Places with fewer than 20
eligible parcels are forecast but not scored (D-005); known reforming places are excluded
(`config/params/v1_excluded_places.csv`).

## Limitations and edge cases

A reader should see the limits where the numbers are. Each one below is restated next to results in the tool
or in the Policy Scenario Comparison.

- **The reform effects are uncertain.** The missing-middle effect is consistent with the counts but not
  clearly detected (about 1.5 standard errors), and its rate spans about 140-fold. The ADU model missed both
  Oregon cities in the transfer test. Ranges are wide for these reasons, not because of the simulation.
- **The baseline under-forecasts recent building.** Every method under-forecasts NC and TX single-family
  permits in 2023–25 (model mean 70–87% of observed, D-006), and Wisconsin's total was 1.49 times the frozen
  median. Keeping group totals (D-106) narrowed the gap; the rest is growth after the fit window. The scenarios
  scale with the baseline only through the fee module, so the fee results inherit this bias.
- **BPS hides building types.** BPS counts buildings of 1, 2, 3–4 and 5+ units. It does not flag ADUs (most are
  filed as 1-unit homes), it files townhouses as 1-unit homes, and it puts 5–6 unit buildings in with large
  apartments. The missing-middle result counts 2–4 unit buildings only and is a floor for the Handbook's 2–6
  unit scenario.
- **Missing-middle buildings come in clusters, and the model counts buildings, not projects** (D-092 run 13,
  `reports/mm-d092/run13-projects-mpls-fix/`). In 15–20 city permit files, 39–44% of 2–4 unit buildings are in
  projects of 3 or more: one builder putting up a row of duplexes, or a build-to-rent community (the largest is
  about 100–130 duplexes on one Austin parcel in three months). Cities differ a lot: Minneapolis, Cleveland and
  Cincinnati build mostly one at a time; Austin, College Station, Wilmington and Columbus build in large
  groups. The model carries this as a per-year spread (φ) rather than modelling projects.
- **Two reforms on one lot are not modelled.** Each reform is run on its own, so how two reforms share a lot
  is left out. The app's headline adds the three reforms' draws together as an order of magnitude and says
  that a lot two reforms open is counted twice.
- **Denominators are weak in many places.** Where a county has no usable parcel roll, the ACS fallback counts
  homes, not lots, with no zoning and no vacant land (quality `low`). Only Minnesota reaches data tier 1.
- **One boundary vintage.** Parcels and permit points are placed with TIGER/Line 2025 boundaries and places are
  split with 2020 housing shares; annexations and older boundaries are not modelled.
- **Fee evidence is weak.** Quantity studies of fees are mostly null, and the land-capture share is wide. The
  Handbook's $50,000 fee is far above real fees in every state we coded, so the benchmark fee result is not a
  forecast of a realistic local fee cut. Buildings of 5+ units get no fee cut.
- **Pro forma numbers are approximate.** Several `proforma.yaml` values are marked "approx." (taken from a
  public source without re-checking) or rest on judgment (code step, ADU premium, operating costs, owner
  margin, existing-use margin). Ohio parcels lack values and units; Texas has no sale prices.
- **Holdout exposures.** Charlotte's 2023–25 outcomes entered the NC backtests in aggregate through Mecklenburg
  County rows before the fix (D-012). St. Paul post-reform counts were quoted in a research document that we
  may have read (D-013). Both are disclosed.
- **Small places.** Places with under 20 eligible parcels are too noisy to score or show alone; read them
  rolled up to their county.
- **Who the new homes serve is context, not a forecast** (the income strip under the need chart,
  `model/affordability.py`, method in `docs/research/lotline-ami-method.md`). The model predicts how many
  homes, not their rents; the rent shown is the one the model already assumes (the place's median gross rent
  times a judgment ratio), re-expressed as an income. New homes usually rent above the median of existing
  homes. Area median income covers owners too, so a home at "60% AMI" is harder for a typical renter to afford
  than the label suggests. Many ADUs are not rented at market. Break-even leaves out land and the builder's
  profit, so it is a floor on what a new home must earn.
- **The housing-need gap is rough** (the need card, `model/shortfall.py`). It adds the shortage, household
  growth and homes lost, then takes away the no-change forecast of homes permitted. The stock-loss rate is
  national and approximate, and the gap is one uncertain number minus another, so its range is wide and can
  cross zero (North Carolina, Ohio).
- **Not pre-registered as a set.** The V1–V5 thresholds are the validation plan's proposals; the `prereg-v1`
  tag was never made, and V1 was used during development. Each frozen test (V5, V8, V9) has its own method entry
  in `docs/analysis_plan.md`.

## Sensitivity notes

Lotline shows uncertainty two ways: a range on every result (from simulation), and sensitivity checks that
show how results move when a key assumption changes. Every parameter not fixed by the Handbook or a definition
has a low–high range for this purpose.

### How ranges are shown

- **P10/P50/P90** of the simulated draws, for every place, year and scenario (`interval_low_quantile` = 0.10,
  `interval_high_quantile` = 0.90). The baseline's range combines three sources: uncertainty about a place's
  true rate, the regional cycle, and year-to-year lumpiness. A scenario's range adds the uncertainty in its
  fitted rate, its judgment parameters and the place's rules where they are not coded.
- The pro forma's range draws every parameter from its low–central–high triangle (`rlv_range`).
- Ranges are reproducible: the seed is a parameter. With 4,000 baseline draws, summed P10 and P90 moved by less
  than 1% between two seeds (`baseline.yaml`, `simulation_draws` source).

### What matters most

Specification choices we compared both ways (sources in `docs/analysis_plan.md`):

| Choice | Setting 1 | Setting 2 | Effect |
|---|---|---|---|
| Variance floor from own history (D-002) | Off (spec A) | On (spec B, adopted) | V1 cells passed 19 vs 17 (before D-011); B has 13% lower error for 5+ units |
| Demand signals (D-007) | Spec B (adopted) | Spec C | 17 vs 17 cells; single-family error 10.08 vs 10.01; 5+ units 2.82 vs 2.92; C's coefficients unstable |
| Cycle centring (D-011) | Old (mean drifts up about 6% by year 5) | New (mean flat, adopted) | 17 → 13 cells pass; 5+ unit error 2.82 → 2.77 |
| Keep each group's total (D-106) | Off | On (adopted) | V1 passes 20 → 21 of 60; state totals inside P10–P90 for 2-unit buildings 40% → 87% |
| Repeated totals counted once (D-008) | As reported | Rule on (adopted) | Columbus 2023 5+ units 1.41 → 1.02 of BPS; Austin 2022 1.42 → 1.25 |
| Missing-middle ramp (D-100) | Half-way 4.5 years (main) | 0.5 years (sensitivity) | Shown side by side; the fast ramp adds homes sooner |
| Fee route (`fee_feasibility_channel`) | Elasticity (adopted) | Pro forma threshold | Threshold gave 4–40× the change, only where parcel rolls exist |

Parameters that drive scenario results most:

- **Fees:** the land-capture share λ (0.25–0.75) and the fee elasticity ε (median 0.3, 95th percentile 1.75).
  At the illustrative cost above, the five-year single-family effect runs from about 0 to about +9%.
- **Missing middle:** the mature rate θ (0.14–19.0 per 1,000) and the ramp's half-way point (1.0–6.0 years),
  which trade off against each other, then the share of lots that pencil (hard cost, the commercial-code step,
  the developer margin, the cap rate).
- **ADU:** the place-to-place variation in uptake (α 1.505), the anchor (0.170–0.303 per 1,000 for a suburb),
  the partial-rule share, how sharply uptake falls with price-to-cost (σ 0.25–0.8), the net-new share
  (45–80%) and the formalization share (0–30%), and, for places outside the calibration range, the widening.
- **All scenarios:** the displacement share (0–50%) decides how much of a place's gain is new statewide.

### The tornado chart

The app's tornado chart shows what a state's result depends on most. For the reform shown, it moves one factor
at a time to its own P10 and then its P90 across the draws, holding the others as the engine drew them, and
draws the change in the statewide five-year median as a horizontal bar (`tornado` in
`src/lotline/app/aggregate.js`). The factors are the uptake rate, the share of lots that pencil, completion,
the net-new share and displacement. Bars are sorted longest first. A global method that moves parameters
together (Sobol or Morris) is not built.

### Parameter table

Every parameter, with its value, range, unit and source, is listed in the
[Parameter Table](parameters.md). It is generated from `config/params/*.yaml`, so it can't disagree with the
model's config.

## Intended users and use cases

Lotline is built for people who write, analyse or advocate for state housing law and need an estimate they
can check rather than a black box. Its main reader is a state policymaker without a technical background, so
the app leads with one statewide range per reform and keeps the method one click away. Analysts in another
state can rerun it on their own data.

### Who it is for

- State legislators and their staff, including fiscal and policy analysts who must explain a bill's likely
  effect.
- State housing and planning agencies that will carry out a reform and want to know where it bites.
- Advocates, researchers and local governments who want to test assumptions, supply their own data (a
  jurisdiction's parcels, permits or fees enter through an adapter), and see what drives the answer.
  `docs/adding_a_state.md` walks through bringing in a new state.

### Questions it is meant to answer

1. "If we pass a statewide missing-middle bill, roughly how many more homes would we get over five years, and
   how sure are we?" The tool gives a statewide range and the share of the state's housing need it covers.
2. "Which of these reforms adds the most housing in our state?" The tool shows the reforms side by side on one
   scale, each with its range.
3. "Why does the fee cut add so little here?" The tool shows the drivers (land capture, real fee levels versus
   the Handbook's $50,000) and the tornado chart.
4. "How much does the answer depend on data we don't have?" Each result carries its data tier, and the
   calibration flag says when a state sits outside the places the uptake rates were fitted on.

### What it should not be used for

- **Lot-level predictions.** Parcels are used to count where a reform could apply; no result says what will
  happen on a given lot, and the tool does not map predicted homes by parcel.
- **Small-place precision.** Results for places with few eligible lots are wide and are best read at county
  or regional level.
- **Prices or affordability.** Lotline estimates homes, not rents, prices or who benefits.
- **A substitute for local review.** Local rules (owner occupancy, lot splits, utility capacity, local fees)
  can make the real effect smaller or larger than the benchmark scenario.
