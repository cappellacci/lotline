# Lotline: Model & Assumptions Overview

<!-- Rules §7a(4): max 25 pages, single-spaced. Every section below is required. -->

**Status: first draft, 2026-10-19. This is a living document.** It describes what Lotline does today and what
it is designed to do by the December 16 deadline. Anything not yet built is marked **planned**. Every number
here comes from a file in this repository, and the file is named next to it. Plain-language explanations come
first in each section; technical detail and equations follow. Terms are defined at first use and collected in
the glossary under "Purpose and scope".

## Purpose and scope

Lotline estimates how much more housing a state would permit over five years if it adopted a housing reform,
compared with a baseline in which nothing changes. It works place by place (cities, townships and the
unincorporated parts of counties), adds the places up to a state total, and always reports a range rather
than a single number.

### What Lotline estimates

- **Outcome:** housing units in building permits (`challenge.toml`, `outcome_metric = "permits"`). Permits
  respond first to a zoning or fee change, and the Census Building Permits Survey (BPS) reports them the same
  way in every state, for every place that issues permits, split into buildings of 1, 2, 3–4 and 5+ units.
- **Horizon:** five years after a starting year, called the *forecast origin* (`config/params/baseline.yaml`,
  `forecast_horizon_years` = 5, fixed by the Handbook).
- **Comparison:** each reform scenario is compared with a *baseline*: what each place would likely permit
  under today's rules and economy. The answer is the difference, "units added by the reform".
- **Unit of analysis:** the permit-issuing jurisdiction. Rates are expressed per 1,000 *eligible parcels*
  (lots where the reform would apply), so a large city and a small township can be compared.
- **Ranges:** every result is shown as P10, P50 and P90 (see the glossary below). The P10–P90 range should
  contain the true value about 8 times in 10.

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
per unit. Transit-oriented development and parking reform, the other two benchmark scenarios, are not in the
working set; parking is optional if time allows (`CLAUDE.md`).

### Which states

Lotline is developed and tested on four states with very different data: Minnesota, North Carolina, Ohio and
Texas (HANDOFF decision of 2026-10-04). The same code runs on each; only a state's configuration file
(`config/states/<st>.yaml`) and its local data adapters differ. One state will be the official benchmark state
whose statewide total is submitted; that choice is still open (Minnesota is recommended in `HANDOFF.md`).
Running four states is the test that a state with thin data can still use the method.

### What Lotline does not do

- It does not predict what happens on a particular lot. Parcels are a counting device for the number of
  places a reform could apply; results are reported for jurisdictions, regions and the state only.
- It does not forecast prices, rents, affordability or who lives in new homes.
- It does not judge whether a reform is a good idea. It estimates production, with its uncertainty.
- It does not model reforms other than the three above, or local rules layered on top of them, except as
  clearly labelled extra scenarios (none are defined yet).
- It produces ADU scenario results only as development runs (not yet published); missing middle and fees are
  not built. See "Status" below.

### Status: what is built and what is planned

| Part | Status (2026-10-19) | Where |
|---|---|---|
| Data adapters (national and local), holdout filter, provenance | **Built**, tested | `src/lotline/adapters/`, `validation/holdout.py`, `docs/data_provenance.md` |
| Eligible-parcel rule (rule 1.1) | **Built**, tested | `build/eligible.py` |
| Permit counting (repeated project totals counted once) | **Built**, tested | `build/permits.py` |
| Place × year panel (numerator and denominator kept apart) | **Built**, tested | `build/panels.py` |
| Baseline forecast with P10/P50/P90 | **Built**, tested, backtested (V1) | `model/baseline.py`, `model/backtest.py` |
| Pro forma (residual land value, 7 building prototypes) | **Built**, tested | `model/proforma.py` |
| Real 2025 dollars; completion factors | **Built**, tested | `model/money.py`, `model/completion.py` |
| Scenario modules (ADU, missing middle, fees) | ADU **built**, tested (2026-10-20); missing middle and fees **planned** | `model/scenarios/adu.py`, `config/params/adu.yaml`, `market.yaml` |
| ADU effect estimation, staggered adoption (D-023) | **Built**, tested on simulated panels (2026-10-20); **not yet run** on real data (waits for the adoption-date coding) | `model/estimate_adu.py`, `scripts/dev/estimate_adu.py` |
| Redevelopment hazard and ramp-up (how fast feasible lots get built) | **Built for ADUs**, tested (2026-10-20); missing middle **planned** | `model/hazard.py`, `config/params/hazard.yaml` |
| Evidence prong (comparable places, transport) | **Planned** | `src/lotline/evidence/` is empty |
| Combined scenarios (no lot counted twice) | **Planned** | `model/combine` (BUILD_PLAN §5) |
| Statewide aggregation, net-new and displacement shares | **Planned** (parameters set) | `config/params/aggregate.yaml` |
| Market absorption cap | **Planned** (proposed by the judging panel; not yet in the build plan) | none yet |
| Global sensitivity (tornado chart) | **Planned** | `model/uncertainty` (BUILD_PLAN §5) |
| Interactive tool | **Planned** (Phase 5, from Nov 18) | `src/lotline/app/` |

### Glossary

- **Baseline:** the forecast of permits with no policy change.
- **Eligible parcel:** a lot where a reform would apply (rule in "Methodological approach").
- **P10, P50, P90:** the values below which 10%, 50% and 90% of simulated outcomes fall. P50 is the middle
  value; P10–P90 is the range shown.
- **Shrinkage:** pulling a small, noisy place's estimate toward the average of similar places. A large place
  keeps its own record; a tiny township borrows strength from its county.
- **Negative binomial:** a way to model counts (0, 1, 2, …) that are lumpier than pure chance would make them,
  which permit counts are: one subdivision can double a township's year.
- **Pro forma / residual land value:** a builder's budget for one project. Residual land value is what is left
  for the land after the finished building's value pays for construction, fees, interest and profit.
- **Elasticity:** the percentage change in one quantity when another changes by 1%. An elasticity of 0.3
  means a 10% better price brings about 3% more building.
- **Land capture:** the share of a cost cut that ends up in higher land prices instead of reaching builders.
- **Holdout:** outcomes deliberately hidden from the model until a prediction is frozen, so the test is fair.
- **Backtest:** pretending to stand at an earlier year, forecasting, and checking the forecast against what
  then happened.

## Core assumptions and rationale

Every assumption Lotline makes is a parameter in `config/params/*.yaml` with a value, a low–high range, a unit
and a source; the code never hard-codes them, and a parameter outside its own range is rejected on load
(`src/lotline/config/__init__.py`, `Parameter`). Choices the research documents left open are logged with a
date and a reason in `docs/analysis_plan.md` (decisions D-001 to D-014). The table below lists the assumptions
that shape results most. The full parameter table is under "Sensitivity notes".

| # | Assumption, in plain words | Why | Where it is set |
|---|---|---|---|
| A1 | **Who is eligible.** For ADUs, a lot with one existing single-family house. For missing middle, a lot zoned for single-family homes only that holds one house **or is vacant residential land**. HOA, floodplain and historic-district lots are excluded where the data say so; unknown counts as eligible and is flagged. | Follows the Handbook definitions; vacant lots are where small buildings most often pencil. | `build/eligible.py` (rule 1.1), `config/params/eligibility.yaml`; D-014 |
| A2 | **Where lot data are missing, count homes instead.** With no usable parcel data, the denominator is the number of one-unit detached homes in the American Community Survey (ACS), marked `low` quality. | Lets every place in every state be modelled, with the weakness labelled. | `build/eligible.py` (`from_acs`); statistical protocol §6 |
| A3 | **With no change, each place keeps its own recent pace**, pulled toward its county's pace when its record is short or small, with a regional boom-and-bust cycle around it. The cycle does not push the average up or down over time. | A simple forecast a reader can check by hand; it beat both benchmarks on error in 41 of 48 backtest cells. Shrinkage handles tiny places. | `model/baseline.py`, `config/params/baseline.yaml`; D-002, D-007, D-011 |
| A4 | **The baseline is "spec B".** A place's year-to-year noise is at least what its own history shows, so one subdivision year in a small township is read as noise, not as its normal pace. Demand signals (household growth, price growth) are not used. | Spec C (demand signals) gained little, was worse for 5+ units and had unstable coefficients. | `use_direct_variance` = 1; D-002, D-006, D-007 |
| A5 | **Count a project once.** When 3 or more new-construction permits on one parcel in one year all report the same count of 50+ units, that count is the project's total and is counted once. | City files repeat a project's total on each building's permit; summing it overstates apartments. | `build/permits.py`, `config/params/permits.yaml`; D-008 |
| A6 | **Not every permitted home is finished.** 97% of single-family and ADU permits and 80% of units in 2+ unit buildings are completed (93% for all housing). | Long-run national Census ratios of completions to permits. | `config/params/aggregate.yaml`; `model/completion.py` |
| A7 | **All money is in real 2025 dollars.** Prices and rents are adjusted with the consumer price index (CPI-U); construction costs with the producer price index for residential construction inputs. | Results across years are comparable; a missing index year gives a missing value, never an unadjusted one. | `model/money.py`, `config/params/money.yaml` |
| A8 | **Builders need a profit measured on the finished value** (15% for developers, 10% for a homeowner building an ADU). A project is feasible if what it can pay for land beats the lot's current-use value plus a margin. | Profit on value makes a fee cut move the land budget dollar for dollar, which is easy to check. | `model/proforma.py`, `config/params/proforma.yaml`; D-009 |
| A9 | **Buildings of 3+ attached units cost more to build** (+10% per sq ft) because they fall under the commercial building code; townhouses and duplexes do not. A switch lets triplexes use the residential code where a city allows it. | The commercial code adds sprinklers, accessibility and licensed design. No solid public source gives the size of the step, so the range is wide (3–25%). | `code_step_premium`, `triplex_under_irc`; D-009 |
| A10 | **Half of a fee cut ends up in land prices** (range 25–75%). | Fee incidence research: landowners capture part of any cost cut, more in strong markets. | `fees.yaml` `land_capture_share` |
| A11 | **Building responds weakly to cost cuts**: a fee elasticity of 0.3, range 0 (no effect) to 1.75. | Quantity studies of fees are mostly null; 0.3 is a tract-level supply elasticity, 1.75 a metro-wide one. | `fees.yaml` `fee_permit_elasticity`; D-010 |
| A12 | **Some new ADUs are not new homes** (65% are; range 45–80%; and 10% of ADU permits, 0–30%, legalize an existing unit), and **some of a place's gain is pulled from its neighbours** (25%; range 0–50%). | ADUs are also used as offices, guest rooms or short-term rentals; reforms partly shift building between places. | `aggregate.yaml` (net-new and formalization used in the ADU scenario; displacement **planned**) |
| A13 | **Held-out outcomes stay hidden.** St. Paul from 2024 and Charlotte from June 2023 (with Mecklenburg County's BPS rows) are removed from every table until a frozen prediction is committed on `main`. | Keeps the forward tests (V5) honest. Two exposures are disclosed. | `config/states/*.yaml`, `validation/holdout.py`; D-012, D-013 |

Rationale for the less obvious choices:

- **Why a rate per eligible parcel?** It separates "how many lots could change" from "how often they do". A
  reform can change both: more lots become eligible, and more of them pencil. Numerator and denominator are
  stored separately and combined only when the model needs a rate (`build/panels.py`), so a denominator fix
  never silently rewrites history.
- **Why spec B and not a richer model?** Decisions D-002 to D-007 record each alternative that was tried and
  why it was kept or rejected, including ones that scored better on some cells. A baseline that a reader can
  check by hand is worth more here than a small gain in accuracy.
- **Why profit on value (D-009)?** The research documents give the feasibility test but not what profit is
  measured on. With profit on value, a $25,000 fee cut raises the land budget by exactly $25,000 per unit,
  plus interest saved when fees are paid at permit. Developer hurdles quoted as 17–25% on cost convert to
  about 15–20% of value (h / (1 + h)).
- **Why a low fee elasticity (D-010)?** The earlier central value of 1.5 had no study behind it, and its high
  case fell outside the range the validation plan treats as plausible. The new central value comes from a
  cited study; the low end is zero because most fee studies find no significant effect on quantity.

## Data sources and cleaning steps

Lotline downloads every dataset with a script (`lotline fetch`) into a folder outside the repository; nothing
is committed. Each download is logged with a checksum, and `docs/data_provenance.md` is generated from that
log: it gives each source's URL, version, access date, license, numbered cleaning steps and known limitations.
This section summarizes it; the provenance document has the detail, under the section names used below.

### Sources and what they feed

| Source | What it feeds | States | Key cleaning step | Section in [data_provenance.md](data_provenance.md) |
|---|---|---|---|---|
| Census Building Permits Survey, annual place files | Baseline numerator: units by building size (1, 2, 3–4, 5+), reported and with Census imputation | All | Places joined by GEOID; IDs filed twice in a year summed; held-out rows removed | "Census Building Permits Survey (BPS), annual place-level files" |
| Census BPS state totals | V0 check only: do our place sums match Census? | All | Held-out years not compared (subtraction would reveal them) | "…annual state totals (reconciliation only)" |
| ACS 5-year estimates (B25024, B25003, B25064, B25077, B25034) | Fallback denominator (one-unit detached homes); household growth for spec C | All | A 5-year estimate counts for its last year and is carried forward; homes split between places, townships and county remainders without double counting | "Census American Community Survey 5-year estimates…" |
| Census 2020 geography files and DHC housing-unit counts | Splitting places that cross county or township lines | All | 2020 housing-unit shares, fixed for every year | "Census 2020 geography…" |
| Census 2020 redistricting data (P.L. 94-171) | Jurisdiction names and population | All | Matched by GEOID | "Census 2020 redistricting data…" |
| Census TIGERweb boundaries (ACS 2025 vintage) | Placing parcels in jurisdictions | OH (TX uses the taxing entity instead) | Parcel centroid point-in-polygon | "Census TIGERweb boundaries…" |
| FHFA House Price Index | Price change for spec C; market context for the pro forma | All | County → metro area → state non-metro → state fallback chain | "FHFA House Price Index…" |
| FRED: mortgage rate, PPI for residential construction inputs, CPI-U | Real dollars; financing context | National | Annual series | "FRED: 30-year mortgage rate…" |
| OMB CBSA delineation, July 2023 | County → metro area for the price fallback | All | Crosswalk only | "OMB core-based statistical area…" |
| City permit files: Minneapolis, St. Paul, Met Council (MN); Raleigh, Durham (NC); Columbus, Cincinnati (OH); Austin (TX) | Local checks of BPS; building types BPS hides (ADUs); reform-era outcomes | MN, NC, OH, TX | Repeated project totals counted once (D-008); holdout filter; no personal fields requested | One section per city |
| Ohio Statewide Parcels (OGRIP) | Eligible parcels (Franklin and Hamilton counties so far) | OH | Land use from state codes via a crosswalk; lot size from land area or polygon area | "Ohio Statewide Parcels…" |
| Travis Central Appraisal District roll (2026) | Eligible parcels for Austin (Travis County part) | TX | Real property only; land use from state codes; owner names and addresses never read | "Travis Central Appraisal District…" |

### What each state has and what is used

- **Minnesota.** BPS reports townships as their own permit issuers, so Minnesota has the most places (1,030
  jurisdictions in the eligible-parcel table, `reports/mn/V0-national.md`). Local permit files are loaded for
  Minneapolis, St. Paul and the seven-county Metropolitan Council area. No parcel data are loaded yet, so
  every eligible-parcel count is the ACS fallback, quality `low`. St. Paul's outcomes from 2024 are held out.
- **North Carolina.** BPS plus Raleigh and Durham permit files, and 14 coded reform rows
  (`config/reforms/nc.csv`). Parcel data are being built by the NC workstream and are not yet in the
  denominator, so NC also uses the ACS fallback (257 jurisdictions). Charlotte is held out from June 2023,
  including the Mecklenburg County BPS rows its permits are filed under (D-012).
- **Ohio.** BPS (townships included) plus Columbus and Cincinnati permit files. The statewide parcel layer is
  loaded for Franklin and Hamilton counties. It has land use and lot size but no unit counts, building size or
  values, so the pro forma there will need county auditor data. The build uses parcels where a state has them
  and the ACS fallback elsewhere (`build/eligible.py`, `combine`). The committed V0 report (2026-10-14)
  predates the parcel load and shows the ACS fallback for all 953 jurisdictions.
- **Texas.** BPS plus Austin's permit file and the Travis Central Appraisal District roll: 239,626 Austin
  parcels, Travis County part only (`config/states/tx.yaml`). Single-family plus condominium parcels equal 0.95
  of ACS one-unit detached homes for Austin (`reports/tx/V0.md` §4); the Williamson and Hays County parts of
  Austin are missing until those rolls are added. Texas does not disclose sale prices, so values are
  appraisals.
- **Data tiers.** Every output will carry the tier it came from: 1 = parcel data, 2 = jurisdiction totals
  only, 3 = national data only. Today no state configuration raises any jurisdiction above the default tier 3
  (`build/jurisdictions.py`, `DEFAULT_TIER`); tiers will be set as parcel data are wired in.

### Cleaning rules that apply everywhere

- **Holdout filter.** Every adapter applies the holdout filter, and the panel loader checks again; a year is
  held out if any day of it falls in the outcome window (`validation/holdout.py`).
- **Unknown is never zero.** A missing denominator year stays missing. An unknown zoning or lot size is counted
  as eligible but flagged as an assumption, and the share of such parcels sets the denominator's quality:
  `high` up to 5%, `medium` above that, `low` at 50% or more (`eligibility.yaml`).
- **As reported versus as counted.** Adapters keep each source's numbers as published; counting rules such as
  D-008 are applied in a separate build step and can be switched off for comparison.
- **Privacy.** Adapters request no owner names, mailing or site addresses, contractors or loan data (each
  provenance entry lists the fields left out). Outputs are published at jurisdiction level or above. A
  minimum-size rule for publishing small places is **planned** and not yet set.

## Methodological approach

Lotline answers one question per scenario: how many more homes would be permitted over five years with the
reform than without it? The flow below shows each step and whether it is built.

```
data adapters ──► eligible parcels (denominator) ─┐
              └─► permits by size (numerator) ────┴─► place × year panel ──► BASELINE forecast (built)
                                                                          │
pro forma: does each building type pay on a lot? (built) ─────────────────┤
evidence: what happened in comparable reformed places? (planned) ─────────┤
                                                                          ▼
     scenario modules: extra units = eligible lots × share that pencils × uptake over time (planned)
                                                                          ▼
     combine (no lot counted twice) ► net new and displacement ► state total, P10/P50/P90 (planned)
```

### The outcome and the eligible-parcel rule

The outcome is units in permits per year, by place and building size. The *rate* is units per 1,000 eligible
parcels. Eligibility follows one versioned rule, applied the same way in every state (`build/eligible.py`,
`RULE_VERSION` = "1.1"):

- **ADU:** land use is single-family detached, at most one unit where the roll records units, the lot meets
  the minimum size (0 sq ft today: the Handbook sets none), and the lot is not excluded (HOA, floodplain,
  historic district) where those are known.
- **Missing middle:** zoned single-family-only **and** either a single-family house (at most one unit) or
  vacant residential land, lot at least the minimum (0 today), not excluded (D-014).
- **Unknowns:** unknown zoning counts as single-family-only; an unknown lot size passes while the minimum is 0;
  an unknown exclusion keeps the parcel. Each is flagged as an assumption.
- **Fallback:** where there are no parcels, ACS one-unit detached homes stand in. That count has no vacant land
  and no zoning, so the missing-middle fallback denominator excludes vacant lots.

### The baseline: what gets built with no change

**In plain words:** each place keeps building at its own recent pace, pulled toward its neighbours' pace when
its own record is too short or too small to trust. The range around that reflects lumpy years and the
regional building cycle. This is spec B (D-002, D-007), with the cycle fixed by D-011. The full specification
is in the header of `src/lotline/model/baseline.py`; every step has a hand-worked test in
`tests/model/test_baseline_model.py`.

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
5. **Range, by simulation.** For each of 4,000 draws (`simulation_draws`, fixed `simulation_seed`): the true
   level is drawn from a gamma distribution with mean μ_i and the variance above; it is multiplied by a
   regional cycle factor; and each year's count is drawn from a negative binomial around the result. The cycle
   factor is exp(sum of *h* resampled year-to-year log changes in the state's total permits over the 25 years
   before the origin, `cycle_history_years`), so the band widens with the horizon *h*. The changes are centred
   by subtracting log(mean(exp(x))), so each year's factor averages 1 and the mean stays flat when nothing
   changes (D-011). The same resampled calendar years are used for every size class and scenario in a given
   state, origin and draw, so draw *j* is the same run of boom and bust years for single-family and 5+ units.
6. **Outputs.** P10, P50 and P90 of the draws, and the mean. P50 is the point forecast because it minimizes
   absolute error; the mean is reported because means add up to state totals and medians do not.

Two optional terms exist and are **off**: a state momentum factor (`use_state_momentum` = 0; the backtest
showed mixed results) and the spec C demand multiplier (D-006, D-007; available as `--spec C`).

### Worked example: two places

This is the hand-worked case tested in `tests/model/test_baseline_model.py` (`test_level_estimates_by_hand`).
It uses a 2-year window ending in 2020 so the arithmetic stays short; the real window is 5 years.

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
| Implied mean units per year (μ × parcels / 1000) | 8.8 | 0.66 |

Place A has a steady record on many lots, so it keeps almost all of its own rate. Place B built nothing in two
years on only 100 lots; that is weak evidence that its true rate is zero, so the model moves it 74% of the way
to the group's rate. The simulation then puts a range around each level.

### Benchmarks the baseline must beat

The validation plan (V1) requires the baseline to beat two simple forecasts on mean absolute error: the
average of the last 3 years (`benchmark_mean_years`), and a straight-line trend fitted by least squares over
the last 10 years and floored at 0 (`benchmark_trend_years`). Both are in `model/baseline.py`, with formulas in
its header.

### The pro forma: does a building pay on a lot?

**In plain words:** a builder can pay for a lot only what is left after building. Lotline works out that
leftover, the *residual land value*, for seven building types (ADU, single-family house, duplex, triplex,
fourplex, 4-unit townhouse row, 6-unit building), for sale or for rent (`model/proforma.py`):

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

### From feasibility to permits: the two prongs (planned)

The design (`docs/research/lotline-two-prong-design.md`, followed by `docs/build/BUILD_PLAN.md`) gives each
scenario two answers that inform each other:

1. **Mechanism prong, "what do your own economics say?"** Eligible parcels → pro forma feasibility → an annual
   *redevelopment hazard* (the share of feasible lots actually built on each year) → permits. Built: the
   eligible-parcel rule, the pro forma, and the ADU hazard with its ramp-up (next section). **Planned:** the
   hazard for missing middle.
2. **Evidence prong, "what happened in places like you?"** Measured effects from places that already reformed
   (Portland, Seattle, California, Spokane and Auckland in the design; Raleigh and Durham in state), per 1,000
   eligible lots and by year since the reform. **Planned:** the comparables table, an original ADU
   natural-experiment estimate (`docs/research/adu-study-design.md`), and the *transport* step that reweights
   comparables on similarity (price-to-cost ratio, rents, lot sizes, recent permit trend, regulatory
   stringency) and flags low confidence when no comparable is close.

The evidence prong calibrates the mechanism prong's free parameters (the hazard and the ramp shape); the
mechanism prong translates the evidence to local prices and costs. Where the two disagree, the tool will show
why. With roughly 10–15 reformed places with usable data, mostly high-cost West Coast cities, the evidence pool
is thin; places far from any comparable will lean on the mechanism prong and say so.

### The ADU hazard: how many eligible lots add an ADU each year

`model/hazard.py`, parameters in `config/params/hazard.yaml` (D-018). The hazard has one anchor: the mature
ADU permits per eligible lot a year at the reference place's rent, home value and rates (Portland 2015–19).
The research band puts Portland at about 4 per 1,000 (`docs/research/adu-study-design.md`); Lotline now
**estimates the anchor from its own post-reform places: 1.04 per 1,000 (90% interval 0.45–3.17)** for a
typical place, with large place-to-place differences, see
"Estimating the anchor" below and D-019. The hazard carries that anchor to another place through what makes an ADU worth building there,
and phases it in after adoption:

    hazard in year t = ramp(t) × mature hazard
    mature hazard     = u × F(PCR) × (V / V_ref)^β_equity × exp(−β_rate × (r − r_ref)),  u = h_ref / F(PCR_ref)

| Piece | Plain words | Value (range) |
|---|---|---|
| PCR | ADU price-to-cost ratio from the pro forma (rented out): value (a year's rent after vacancy and operating costs ÷ cap rate) over cost (hard + soft + fees + interest while building). Rent = the place's median gross rent (ACS) × `adu_rent_to_median_ratio`. | e.g. 1.13 Portland 2015–19, 0.79 at $1,100 a month |
| F(PCR) | Share of lots where an ADU pencils. Lots differ (a garage to convert, slope, the owner's plans), so each lot's ratio is lognormal around the place's PCR; a lot pencils above 1 + the owner's margin. F = Φ((ln PCR − ln(1 + margin)) / σ). | σ 0.5 (0.25–0.8), judgment; margin 10% (0–20%) |
| u | Uptake among lots that pencil, set so the reference place gets the anchor exactly. Reference and target use the same costs, so only local rent, home value and rates transport. | h_ref 0.001038 (0.000453–0.003173), estimated (D-019 fit 3) |
| Home equity (C22) | Owners pay for most ADUs (Portland 62% cash; ~40% used home equity, E045): median home value relative to Portland's. | β_equity 0.25 (0–0.5), judgment |
| Rates (C01, C22) | 30-year mortgage rate relative to the 2015–19 mean (3.99%), beyond the construction loan already in the pro forma. | β_rate 0.07 per point (0–0.15), judgment |
| ramp(t) | Logistic over years since adoption: 1 / (1 + exp(−(t − half) / slope)). | half 2 years (1–3.5), slope 0.75 (0.5–1.5) |

The reference values (Portland's rent $1,573 and home value $519,222 in 2025 dollars, ACS 2015–19; the 2015–19
mortgage rate) and the **calibration range** (rent $1,573–2,034 and home value $519k–836k across Portland,
Seattle and Los Angeles; rates 2.96–6.81% over 2015–23) are recomputed by `scripts/dev/adu_reference.py`.

**Worked example** (the test `test_mature_hazard_one_place_by_hand`, with the earlier anchor 0.004 for round
arithmetic; the hazard scales in proportion to the anchor): rent $1,100, home value half Portland's,
mortgage rate 2 points above 2015–19. PCR = 148,200 / 187,966 = 0.788; F = Φ((ln 0.788 − ln 1.1) / 0.5) =
Φ(−0.666) = 0.253. Portland: PCR 1.127, F_ref = 0.520, so u = 0.004 / 0.520 = 0.0077. Equity 0.5^0.25 = 0.841;
rates e^(−0.07 × 2) = 0.869. Mature hazard = 0.0077 × 0.253 × 0.841 × 0.869 = **0.00142**, 1.4 ADUs per 1,000
eligible lots a year; in year 1 after adoption the ramp gives 21% of that.

**Outside the calibration range.** Most places Lotline covers have lower rents and home values than the
reference cities. The formula still applies there, but it is extrapolation, so the tool says so: each place
gets its log distance outside the range (rent, home value and rate added up; 0 inside), a flag, and a wider
interval. Each simulation draw multiplies the hazard by exp(s·z − s²/2), s = `adu_extrapolation_widening`
(1.0, range 0.5–2) × distance, z standard normal; the mean stays put and P10–P90 widens with distance.

**Properties the tests check:** the hazard equals the anchor at the reference place; higher price-to-cost never
lowers it (any parameter draw in range); it never leaves [0, 1]; widening keeps the mean.

### The ADU scenario: extra homes over current local rules

`model/scenarios/adu.py`, parameters in `config/params/adu.yaml`, `market.yaml` and the ADU shares in
`aggregate.yaml` (D-019). The Handbook scenario allows one ADU on every eligible single-family parcel, at least
600 sq ft, by right, with no parking requirement. It is applied **only above the rules a place already has**.
For each place and each year t = 1 … 5 after the origin:

    current rules   h_cur(t) = max(c × h_m × ramp(a + t), observed ADU rate)
    Handbook rules  h_hb(t)  = max(c × h_m × ramp(a + t) + (1 − c) × h_m × ramp(t), observed ADU rate)
    gross ADUs(t)   = parcels still without an ADU × h(t)            (each set of rules keeps its own pool)
    ADU permits added(t) = Handbook gross ADUs(t) − current-rules gross ADUs(t)
    additional homes(t)  = ADU permits added(t) × net-new share (0.65; 0.45–0.80) × (1 − formalization share (0.10; 0–0.30))

| Piece | Plain words |
|---|---|
| h_m | The place's mature ADU hazard (previous section). |
| c | How close current local rules are to the Handbook, from the coded reforms (`config/reforms/<st>.csv`) in force on 31 December of the origin year: 1 if a detached ADU of 600+ sq ft is allowed by right with no owner-occupancy or parking rule; `adu_partial_rule_share` (0.3; 0.1–0.6, judgment) if any of those restrictions applies; 0 for an explicit "no ADUs" row. **Anything not coded is unknown (D-022):** a blank rubric field restricts, in each draw, with the probability that coded rules restrict it (state share if 5+ coded values, else pooled); a place with no ADU row draws its class from the coded places of its state and size band (<10k, 10–50k, 50k+ people; state, then all-state pooling below 5 coded places). A citywide parking reform with no minimum settles a blank parking field. The central path uses the expected c. Outputs report each place's class probabilities, whether its class was drawn, and the drawn shares. |
| a | Years since that rule took effect: a recent reform (Columbus, December 2025) is still ramping up under current rules, and the Handbook adds nothing to it. |
| Observed ADU rate | Where local permits flag ADUs (Met Council, Minneapolis, Raleigh, Durham, Cincinnati, Austin), ADU permits per eligible parcel a year over 2019–2022. ADUs a place already builds are in its baseline, so they are never counted as added (additionality, judging finding MS-10). |
| Pool | Each year's ADUs use up parcels, so a parcel gets at most one ADU. |

**Additionality and the baseline.** Census BPS counts a detached ADU as a 1-unit permit, so the baseline's
single-family forecast already holds some ADUs: 0.47% of 1-unit permits in the Twin Cities metro (Met Council
2019–22) and 7.65% in Austin (`baseline_adu_share_of_one_unit`, 3.3% pooled, from
`scripts/dev/adu_baseline_share.py`). The scenario adds only the difference between Handbook and current rules,
so its units go on top of the baseline without counting those ADUs twice.

**Mortgage rates.** A forward run draws one 30-year rate per simulation draw from `mortgage_rate_forecast`
(`market.yaml`): central 6.60% (FRED annual mean for 2025), range 2.96–6.81% (the 2015–2025 annual low and high,
a stress range, not a forecast), flat over 2026–2030. Backtests and validation checks never use it: they use
each year's actual rate from `market_geo_year`.

**Worked example** (`test_one_jurisdiction_year_by_hand`): 2,000 eligible parcels, mature hazard 0.0014219 (the
hazard example), no ADU rule today. Year 1: ramp 0.2086, so 2,000 × 0.0014219 × 0.2086 = **0.593 ADU permits
added**, all of them extra because current rules give none; additional homes = 0.593 × 0.65 × 0.90 = **0.347**.
Year 2: (2,000 − 0.593) × 0.0014219 × 0.5 = 1.42 permits added.

**Output.** Per place and year, and as five-year totals: P10/P50/P90 and mean (over 1,000 draws of every
uncertain parameter) of Handbook ADU permits, current-rules ADU permits, permits added and additional homes,
beside the eligible parcels (numerator and denominator kept apart), the central price-to-cost and hazard, the
rule class and note, and the calibration distance with an outside-the-range flag. Five-year ranges are
percentiles of each draw's sum. Places below 20 eligible parcels are not shown alone (D-015).

**Estimating the anchor** (`model/calibrate_adu.py`, `scripts/dev/calibrate_adu.py`; each specification
pre-registered in D-019 before it was run). Fit 3, the current one: ADU permit counts in place-years with a
coded ADU rule in force and permits that flag ADUs, modelled as Poisson around the scenario's current-rules
path (eligible parcels × anchor × hazard modifiers × the rule's c × coverage × ramp), with each year's actual
rent, home value and mortgage rate; each place has its own multiplier u (gamma, mean 1, variance α) shared over
its years; blank rule fields are integrated over per place (D-022). Fit set: Minneapolis, Austin (2016–23) and
14 Twin Cities suburbs, 115 place-years, 2,799 ADU permits. Test set: Raleigh and Durham, 2021–25.

| Parameter | Estimate | 90% interval | Note |
|---|---|---|---|
| Anchor (typical place, Portland's rent/value/rate) | 1.04 per 1,000 parcels a year | 0.45–3.17 | 0.26 of Portland's 4 per 1,000 (research band) |
| Place-effect variance α | 4.7 | — | multipliers from ~0 (Eagan, Lakeville) to ~11 (Austin) |
| Owner-occupancy share m_o | 1.0 | 0.9–1.0 | estimated: an owner-occupancy rule shows no measurable effect |
| Other-restriction share m_x | 0.3 (judgment) | 0.1–1.0 (not identified) | kept at its judgment value |

**Test (not used in the fit):** Raleigh 230 ADU permits over 2021–25 against a predicted mean of 141 (median
11, 90% interval 0–687); Durham 239 against 172 (median 15, 0–865). Both are inside their intervals, but the
intervals are very wide because a new place's own multiplier is unknown. **Minneapolis**, observed vs fitted
for a typical place (before its own multiplier, which is 0.50): 2016 28 vs 15; 2017 30 vs 30; 2018 25 vs 39;
2019 35 vs 47; 2020 28 vs 56; 2021 16 vs 60; 2022 17 vs 53; 2023 14 vs 49; 2024 16 vs 49; 2025 13 vs 50. The
model rises with the ramp and rents while Minneapolis's ADU permits fell after 2020.

**What this means:** rent, home value and rates explain little of why places differ; a typical-place
estimate is 2.4x Minneapolis's ADU permits, 0.4x Raleigh's and 0.1x Austin's over 2016–22. Place ranges are
therefore very wide (a place's median is far below its mean). State totals, which add many independent
places, are much tighter (below).

**Statewide totals, development run** (origin 2025, P10 / P50 / P90 of draws summed over non-overlapping
places, D-020; ADU permits added over current rules, and additional homes after the net-new and formalization
shares), 2026–2030:

| State | ADU permits added | Additional homes |
|---|---|---|
| Minnesota | 1,457 / 2,719 / 5,065 | 762 / 1,516 / 2,814 |
| North Carolina | 1,727 / 3,850 / 8,101 | 950 / 2,117 / 4,540 |
| Ohio | 1,046 / 2,276 / 5,233 | 574 / 1,262 / 2,920 |
| Texas | 7,731 / 14,972 / 29,445 | 4,074 / 8,211 / 16,607 |

Places whose ADU rule is not coded (most of them) draw their rule from coded places like them (D-022), so
these totals will move as more rules are coded.

- **Missing middle:** for each eligible lot, compare the best 2–6 unit prototype's residual land value with
  the lot's existing-use value; lots that newly pencil enter the hazard. Proposed (judging panel): apply the
  benchmark only to the increment above what local rules already allow.
- **Fees:** the primary route is the pro forma threshold (validation test V6b): count lots that cross
  feasibility when fees fall by the builder's share of the cut, (1 − λ) × $25,000. Where parcel data are
  missing, the fallback is the elasticity form (D-010):
  %Δ permits = ε × (1 − λ) × Δfee / TDC × ramp(t), with TDC the total development cost. At an illustrative TDC
  of $350,000 (the $25,000 cut is about 7%): central 0.3 × 0.5 × 7% ≈ +1%; high 1.75 × 0.75 × 7% ≈ +9%
  single-family permits over five years (`fees.yaml` notes). Real local fees will be shown next to the
  Handbook's $50,000, because real fees are far lower in most places checked.
- **Combined runs:** one allocation step so the same lot is never counted for both ADU and missing middle; the
  combined result is at most the sum of the parts.

### Adding up to a state total (planned)

Place results will be summed to the state. Before summing, the planned aggregation step (`aggregate.yaml`,
statistical protocol §5.10) applies the ADU net-new share and a displacement share (0.25, range 0–50%), so the
tool can show both "in this place" and "net statewide"; completion factors are shown alongside permits (the
outcome stays permits). The design sums simulation draws, not medians, so the state P10–P90 reflects shocks
that places share, such as the common regional cycle.

### Validation ladder and results so far

The validation plan (`docs/research/lotline-validation-plan.md` §3) has eight steps. Thresholds marked
proposed there are confirmed at pre-registration (tag `prereg-v1`, **not yet made**; `docs/analysis_plan.md`).

| Step | Question | Status and result (2026-10-19) |
|---|---|---|
| V0 Data reproduction | Do our adapters count what the publishers count? | **Run.** BPS place sums within 1% of Census state totals (D-001) in MN 30/32 years, NC 29/31, OH 34/34, TX 21/34 (`reports/*/V0-national.md`; TX 2003–2014 runs 1–2% high, open). Austin local permits / BPS for homes in 1–2 unit buildings = **0.98** pooled 2010–2025, every year within 10%; 5+ units 1.04 with D-008 (`reports/tx/V0.md`). |
| V1 Baseline accuracy | Does the baseline beat the benchmarks out of sample? | **Run** (fits ending 2016, 2018, 2020; 4 states × 3 windows × 4 size classes = 48 cells). After D-011: **13 of 48 cells pass** all three tests; the model beats both benchmarks in 41, coverage is in range in 32, bias in range in 21. Mean absolute error per 1,000 parcels: single-family 10.13, 2 units 0.367, 3–4 units 0.193, 5+ units 2.77 (D-011). NC results must be re-run on the rebuilt table (D-012). |
| V2 Mechanism | Do the pro forma and hazard predict which parcels redevelop? | Pro forma and ADU hazard built; ADU anchor estimated on Minneapolis, Austin and 14 Twin Cities suburbs, tested on Raleigh and Durham (D-019 fit 3): Raleigh 230 observed vs mean 141 (90% 0–687), Durham 239 vs 172 (0–865): inside, but very wide. Parcel-level V2 **not run**. |
| V3 In-state causal estimates | What did Raleigh's and Durham's reforms do? | **Planned.** |
| V4 Backtests of known reforms | Would the range have contained what happened? | **Planned.** |
| V5 Blind forward tests | St. Paul and Charlotte, predicted before outcomes are seen | **Planned**; predictions to be frozen by Nov 17. Exposures disclosed (D-012, D-013). |
| V6 Fee tests | Natural experiment; pro forma threshold; bunching | **Planned**; ε set (D-010). |
| V7 Transport and second state | Does the method carry to other states? | Partly: V0 and V1 already run in all four states with the same code. |

A V1 cell passes when the model's error is below both benchmarks', its randomized P10–P90 coverage is 70–90%
(D-003), and the post-2022 bias of its mean is within 25% of its error (D-004). Places with fewer than 20
eligible parcels are forecast but not scored (D-005); known reforming places are excluded
(`config/params/v1_excluded_places.csv`).

## Limitations and edge cases

These limits apply today. Each will be restated next to results in the tool and in the Policy Scenario
Comparison, so a reader sees them where the numbers are.

- **No policy mechanism yet.** The scenario modules, hazard, evidence prong, combination and aggregation are
  planned, not built. Today Lotline can forecast the baseline and price a building on a lot; it cannot yet say
  how many units a reform adds.
- **The baseline under-forecasts recent building.** Every method under-forecasts NC and TX single-family
  permits in 2023–25 (model mean 70–87% of observed, D-006). Correcting the cycle so the mean no longer drifts
  up (D-011) made this visible: V1 passes fell from 17 to 13 of 48 cells, all on the bias test. For
  single-family homes the model's error was slightly worse than the 3-year average's (10.08 vs 9.66 per 1,000
  parcels, D-005, before D-011). A pre-declared fix is still open (D-007). How much this bias carries into
  scenario effects depends on the scenario modules and will be reported with them.
- **BPS hides building types.** BPS counts buildings of 1, 2, 3–4 and 5+ units. It does not flag ADUs (most are
  filed as 1-unit homes) and it puts 5–6 unit buildings in with large apartments. ADU and 5–6 unit effects
  therefore need city permit files, which only some places have.
- **Denominators are weak in most places.** Every MN and NC jurisdiction, and most of OH and TX, uses the ACS
  fallback (homes, not lots; no zoning; no vacant land), quality `low`. Austin's parcels cover the Travis part
  only (0.95 of ACS detached homes). No jurisdiction is yet labelled above data tier 3.
- **One boundary vintage.** Parcels are placed with 2025 boundaries and places are split with 2020 housing
  shares; annexations and older boundaries are not modelled.
- **Fee evidence is weak.** Quantity studies of fees are mostly null, and the land-capture share is wide. The
  Handbook's $50,000 fee is far above real fees in most places checked, so the benchmark fee result is not a
  forecast of a realistic local fee cut.
- **Pro forma numbers are approximate.** Several `proforma.yaml` values are marked "approx." (taken from a
  public source without re-checking) or rest on judgment (no public source found: code step, ADU premium,
  operating costs, owner margin, existing-use margin). They are to be checked against sources before V2 uses
  them (D-009). Ohio parcels lack values and units; Texas has no sale prices.
- **Holdout exposures.** Charlotte's 2023–25 outcomes entered the NC backtests in aggregate through Mecklenburg
  County rows before the fix (D-012). St. Paul post-reform counts were quoted in a research document that the
  builders may have read (D-013). Both are disclosed, and both forward tests proceed with the note.
- **Reform registry incomplete.** Places that already reformed are excluded from V1 by a placeholder list of
  known places until `config/reforms/*.csv` covers every state.
- **Small places.** Places with under 20 eligible parcels are too noisy to score; they are forecast with wide
  ranges and should be read rolled up to their county.
- **Not yet pre-registered.** The V1–V5 thresholds are proposals until the `prereg-v1` tag is made, and V1 has
  been used during development.

## Sensitivity notes

Lotline shows uncertainty two ways: ranges on every result (from simulation), and sensitivity tables that show
how results move when a key assumption changes. Every parameter not fixed by the Handbook or a definition has
a low–high range for this purpose.

### How ranges are shown

- **P10/P50/P90** of the simulated draws, for every place, year and (planned) scenario
  (`interval_low_quantile` = 0.10, `interval_high_quantile` = 0.90). The baseline's range combines three
  sources: uncertainty about a place's true rate, the regional cycle, and year-to-year lumpiness.
- The pro forma's range draws every parameter from its low–central–high triangle (`rlv_range`).
- Ranges are reproducible: the seed is a parameter. With 4,000 draws, summed P10 and P90 moved by less than 1%
  between two seeds (`baseline.yaml`, `simulation_draws` source).

### What matters most

Specification choices already compared both ways (sources in `docs/analysis_plan.md`):

| Choice | Setting 1 | Setting 2 | Effect |
|---|---|---|---|
| Variance floor from own history (D-002) | Off (spec A) | On (spec B, adopted) | V1 cells passed 19 vs 17 (before D-011); B has 13% lower error for 5+ units |
| Demand signals (D-007) | Spec B (adopted) | Spec C | 17 vs 17 cells; single-family error 10.08 vs 10.01; 5+ units 2.82 vs 2.92; C's coefficients unstable |
| Cycle centring (D-011) | Old (mean drifts up about 6% by year 5) | New (mean flat, adopted) | 17 → 13 cells pass; 5+ unit error 2.82 → 2.77 |
| Repeated totals counted once (D-008) | As reported | Rule on (adopted) | Columbus 2023 5+ units 1.41 → 1.02 of BPS; Austin 2022 1.42 → 1.25 |
| BPS reported only vs with imputation (`use_reported_only`) | Reported only (adopted) | With imputation | Run in the backtest as a sensitivity; numbers to be added here |

Parameters expected to drive scenario results (to be confirmed by the planned global sensitivity run):

- **Fees:** land-capture share λ (0.25–0.75) and fee elasticity ε (0–1.75). At the illustrative cost above, the
  5-year single-family effect runs from 0 (ε = 0) to about +9% (ε = 1.75, λ = 0.25).
- **Missing middle:** hard cost per sq ft ($120–260), the commercial-code step (3–25%), the developer margin
  (10–20% of value), the cap rate (4.5–7.5%) and the existing-use margin (0–25%), each through how many lots
  pencil; then the hazard (planned).
- **ADU:** the place-to-place variation in uptake (place-effect variance 4.7), the anchor hazard (0.45–3.17
  per 1,000 lots a year, estimated), how sharply uptake falls with price-to-cost (σ
  0.25–0.8), the partial-rule share (0.1–0.6), the mortgage rate path (2.96–6.81%), the net-new share
  (45–80%) and the formalization share (0–30%); for most places, also the widening outside the calibration
  range.
- **All scenarios:** the displacement share (0–50%) decides how much of a place's gain is new statewide.

### Planned tornado chart

For each scenario, the tool will vary one parameter at a time from its low to its high value, holding the rest
at central values, and draw the change in the statewide 5-year result as a horizontal bar. Bars are sorted
longest first, so the chart reads as "what this result depends on most". A global method (Sobol or Morris)
will check that the ranking holds when parameters move together. Two scenarios will be ranked only if one's
P10 is above the other's P90, or most paired draws favour one (rule proposed by the judging panel); otherwise
they are reported as indistinguishable.

### Parameter table

Generated from `config/params/*.yaml`; regenerate with `uv run python scripts/dev/params_table.py` and check
with `--check`. Sources are shortened; the YAML files hold the full citation and notes. Evidence codes such as
E081 refer to rows of `docs/research/lotline-evidence-register.csv`; C-codes refer to
`docs/research/lotline-confounder-register.csv`.

<!-- params-table:start -->
<!-- GENERATED by `uv run python scripts/dev/params_table.py` from config/params/*.yaml. Do not edit by hand. -->

117 parameters in 12 files. "Fixed" means the value is set by the Handbook, the validation plan or a definition and is not varied.

**`config/params/adu.yaml`** (19 parameters)

| Parameter | Value | Range (low–high) | Unit | Source (short; full text in the file) |
|---|---|---|---|---|
| `adu_handbook_min_sqft` | 600 | fixed | sq ft | Handbook benchmark ADU scenario: one ADU per eligible single-family parcel, at least 600 sq ft, no parking re… |
| `adu_partial_rule_share` | 0.3 | 0.1–0.6 | share of Handbook uptake reached under current local rules (m_x) | Judgment |
| `adu_owner_occupancy_share` | 1 | 0.9–1 | share of Handbook uptake reached when owner occupancy is the only restriction (m_o) | Estimated, D-019 fit 3 (pre-registered): profile maximum 1.0, 90% profile interval 0.9-1.0 (grid 0.1-1.0), na… |
| `adu_observed_first_year` | 2019 | fixed | calendar year | Choice (D-019): observed ADU permits from 2019, after the main Twin Cities and Austin ADU rules took effect |
| `adu_observed_last_year` | 2022 | fixed | calendar year | Choice (D-019): observed ADU permits to 2022, before the 2023 rate shock and outside every holdout window (St |
| `adu_simulation_draws` | 1,000 | 500–5,000 | draws | Choice: P10/P90 of 1,000 draws move by under 2% between seeds on the development run |
| `adu_simulation_seed` | 20261020 | 0–4294967295 | random seed | Choice: a fixed seed makes every run reproducible |
| `adu_rule_band_small_max_pop` | 10,000 | fixed | 2020 population (upper edge of the small-place band) | Choice (D-022, Ben 2026-10-20): place-size bands <10k, 10-50k, 50k+ for the rule priors of places with no cod… |
| `adu_rule_band_mid_max_pop` | 50,000 | fixed | 2020 population (upper edge of the middle band) | Choice (D-022, Ben 2026-10-20): place-size bands <10k, 10-50k, 50k+ |
| `adu_rule_min_coded` | 5 | fixed | coded places (or coded field values) | Choice (D-022): a state-and-band rule prior, or a state's field probability, needs at least 5 coded places (v… |
| `adu_unknown_rule_age_years` | 10 | fixed | years | Choice (D-022): a sampled rule with no known date is treated as long in force (ramp ~1), so current-rules upt… |
| `adu_rule_zoned_coverage_share` | 0.75 | fixed | share of eligible single-family lots covered | Judgment (D-021): a rule limited to listed zoning districts or a lot-size minimum, where the parcel roll has… |
| `adu_rule_limited_coverage_share` | 0.2 | fixed | share of eligible single-family lots covered | Judgment (D-021): a rule whose coverage text names a limited area (an overlay, a half-mile corridor, new subd… |
| `adu_dose_grade_permit` | 0.3333 | fixed | dose (share of a by-right rule without owner occupancy) | Choice, flagged for Ben (D-023 orders the grades none < permit or conditional use < by right with owner occup… |
| `adu_dose_grade_owner` | 0.6667 | fixed | dose | Choice, flagged for Ben (D-023 grade order |
| `adu_dose_grade_by_right` | 1 | fixed | dose | D-023: by right without owner occupancy is the full dose |
| `adu_estimation_bootstrap_draws` | 999 | fixed | draws | D-023: wild cluster bootstrap by place, 999 draws |
| `adu_estimation_permutations` | 999 | fixed | permutations | Choice: randomization inference permuting adoption years among treated places (D-023 asks for it, not its siz… |
| `adu_transport_widening` | 1 | fixed | standard deviation of log(predicted mean) per unit distance outside the Minnesota modifier range | D-023: places outside the Minnesota modifier range are flagged and their intervals widened as in hazard.widen |

**`config/params/aggregate.yaml`** (8 parameters)

| Parameter | Value | Range (low–high) | Unit | Source (short; full text in the file) |
|---|---|---|---|---|
| `adu_net_new_share` | 0.65 | 0.45–0.8 | share of permitted ADUs | Statistical protocol §5.10 |
| `adu_formalization_share` | 0.1 | 0–0.3 | share of ADU permits that legalize an existing unpermitted unit | Judgment, from E049 (San Jose 2016-20: ~78% of detached ADU construction unpermitted, 3-4 informal per formal… |
| `baseline_adu_share_of_one_unit` | 0.033 | 0.0047–0.0765 | ADU permits / (ADU + detached single-family permits) | scripts/dev/adu_baseline_share.py: Met Council residential permits and Austin permits, 2019-2022 (MS-10): Twi… |
| `displacement_share` | 0.25 | 0–0.5 | share of local gain | Statistical protocol §6 (decision table: '0-50% range parameter') |
| `completion_factor_single_family` | 0.97 | 0.95–1 | completions per permitted unit | Census New Residential Construction via FRED, long-run completions per permitted unit, recomputed by scripts/… |
| `completion_factor_multifamily` | 0.8 | 0.74–0.88 | completions per permitted unit | Census New Residential Construction via FRED, long-run completions per permitted unit, recomputed by scripts/… |
| `completion_factor_all` | 0.93 | 0.89–0.96 | completions per permitted unit | Census New Residential Construction via FRED, long-run completions per permitted unit, recomputed by scripts/… |
| `min_eligible_parcels_publish` | 20 | 10–50 | eligible parcels | Analysis plan D-015 (Ben, 2026-10-19), matching the V1 scoring floor (D-005, config/params/baseline.yaml v1_m… |

**`config/params/baseline.yaml`** (27 parameters)

| Parameter | Value | Range (low–high) | Unit | Source (short; full text in the file) |
|---|---|---|---|---|
| `forecast_horizon_years` | 5 | fixed | years | Challenge brief (CLAUDE.md): housing production over 5 years compared with a baseline |
| `benchmark_mean_years` | 3 | fixed | years | Validation plan V1: benchmark (a) 'last-3-year average' |
| `benchmark_trend_years` | 10 | 5–10 | years | Validation plan V1: benchmark (b) 'a simple trend' |
| `level_years` | 5 | 3–7 | years | Chosen a priori (WS-ENGINE round 2, 2026-10-14), not tuned on the V1 windows: one more cycle-length than the… |
| `min_group_places` | 5 | 2–10 | places | Statistical protocol §5.7 (Fay-Herriot shrinkage toward a group rate) |
| `use_reported_only` | 1 | 0–1 | flag (1 = yes) | Validation plan §1 (non-reforming places: 'BPS (reported-only, not imputed)') |
| `simulation_draws` | 4,000 | 1,000–20,000 | draws | Monte Carlo size: summed P10 and P90 moved by less than 1% between two seeds (MN, 2018 origin, 1-unit and 5+… |
| `simulation_seed` | 20261014 | 0–4294967295 | integer seed | Fixed so every run is reproducible from config alone (WS-ENGINE acceptance) |
| `interval_low_quantile` | 0.1 | fixed | quantile | CLAUDE.md 'show uncertainty' |
| `interval_high_quantile` | 0.9 | fixed | quantile | CLAUDE.md 'show uncertainty' |
| `cycle_history_years` | 25 | 10–33 | years | Census BPS place files start in 1992 |
| `v1_fit_end_years_first` | 2016 | fixed | year | Validation plan V1: 'Fit on data through 2018 ... Repeat with fits ending 2016 and 2020' |
| `v1_fit_end_years_last` | 2020 | fixed | year | Validation plan V1 |
| `v1_fit_end_step` | 2 | fixed | years | Validation plan V1 (2016, 2018, 2020) |
| `v1_last_outcome_year` | 2025 | fixed | year | Validation plan V1: 'Forecast 2019-2025' |
| `v1_bias_first_year` | 2023 | fixed | year | Validation plan V1: 'no systematic bias in the post-2022 window' |
| `v1_bias_tolerance` | 0.25 | 0.1–0.5 | share of MAE | Proposed (WS-ENGINE round 2, 2026-10-14) to make V1's 'no systematic bias' testable |
| `v1_coverage_low` | 0.7 | fixed | share | Validation plan V1 pass (proposed): coverage 70-90% |
| `v1_coverage_high` | 0.9 | fixed | share | Validation plan V1 pass (proposed): coverage 70-90% |
| `use_direct_variance` | 1 | 0–1 | flag (1 = yes) | Deviation (WS-ENGINE round 2, 2026-10-14), after the first V1 run: one-off subdivision years in tiny places w… |
| `use_state_momentum` | 0 | 0–1 | flag (1 = yes) | Validation plan V1 ('If it fails: add rates or regional demand to the baseline explicitly') |
| `momentum_recent_years` | 3 | 1–5 | years | Chosen a priori to match the 3-year benchmark window (validation plan V1), not tuned |
| `v1_min_eligible_parcels` | 20 | 0–50 | eligible parcels at the forecast origin | Ben's decision 5, 2026-10-14 (WS-ENGINE V1 report, PR #93): places with fewer than 20 eligible parcels domina… |
| `household_growth_years` | 5 | fixed | years | Analysis plan D-006: ACS B25003_001 5-year window ending at the origin vs the non-overlapping window ending 5… |
| `hpi_change_years` | 3 | fixed | years | Analysis plan D-006: FHFA house-price change over the 3 years to the origin, annualized |
| `irls_tolerance` | 1e-08 | 1e-12–1e-06 | relative change in Poisson deviance between iterations | R glm.control default (epsilon = 1e-8): converged when \|dev - dev_old\| / (\|dev\| + 0.1) < epsilon |
| `irls_max_iterations` | 100 | 25–1,000 | iterations | Numerical setting for the Poisson IRLS fit, chosen a priori: Poisson log-link IRLS usually converges in under… |

**`config/params/eligibility.yaml`** (7 parameters)

| Parameter | Value | Range (low–high) | Unit | Source (short; full text in the file) |
|---|---|---|---|---|
| `min_lot_sqft_adu` | 0 | fixed | sq ft | Handbook benchmark ADU definition: one ADU per parcel with an existing single-family building |
| `min_lot_sqft_missing_middle` | 0 | fixed | sq ft | Handbook benchmark missing-middle definition: setbacks and lot coverage assumed not to constrain |
| `exclude_hoa` | 1 | 0–1 | toggle | Statistical protocol §5.2: exclusions (HOA, floodplain, historic districts) where the data allow |
| `exclude_floodplain` | 1 | 0–1 | toggle | Statistical protocol §5.2 |
| `exclude_historic_district` | 1 | 0–1 | toggle | Statistical protocol §5.2 |
| `quality_medium_max_unknown_share` | 0.05 | 0–0.25 | share of eligible parcels | Lotline convention (proposed, to confirm at pre-registration): denominator quality bands |
| `quality_low_min_unknown_share` | 0.5 | 0.25–0.75 | share of eligible parcels | Lotline convention (proposed, to confirm at pre-registration): denominator quality bands |

**`config/params/fees.yaml`** (4 parameters)

| Parameter | Value | Range (low–high) | Unit | Source (short; full text in the file) |
|---|---|---|---|---|
| `handbook_fee_per_unit_usd` | 50,000 | fixed | USD per unit | Handbook benchmark fees scenario: total development fees assumed $50,000 per unit (fees causal diagram, scena… |
| `handbook_fee_cut_share` | 0.5 | fixed | share of fees | Handbook benchmark fees scenario: cut total development fees by 50% (i.e. -$25,000 per unit) |
| `land_capture_share` | 0.5 | 0.25–0.75 | share of fee change | Methods review §3c (lambda_land 0.25-0.75+, central 0.5) |
| `fee_permit_elasticity` | 0.3 | 0–1.75 | % change in permits per % change in price received by builders (applied to a cost change as a share of total development cost) | Central: E081 Baum-Snow & Han 2024, tract-level unit supply elasticity ~0.3 |

**`config/params/hazard.yaml`** (19 parameters)

| Parameter | Value | Range (low–high) | Unit | Source (short; full text in the file) |
|---|---|---|---|---|
| `adu_mature_hazard_ref` | 0.001038 | 0.000453–0.003173 | ADU permits per eligible single-family parcel per year, at the reference place's rent, home value and rate | Estimated, D-019 fit 3 (pre-registered: graded rule shares, gamma place effects, blank fields integrated per… |
| `adu_ref_rent_usd` | 1,573 | fixed | USD per month (2025) | scripts/dev/adu_reference.py: ACS 2015-2019 B25064 median gross rent, Portland city OR (place 4159000), CPI-U… |
| `adu_ref_home_value_usd` | 519,222 | fixed | USD (2025) | scripts/dev/adu_reference.py: ACS 2015-2019 B25077 median home value, Portland city OR, CPI-U to 2025 dollars |
| `adu_ref_mortgage_rate` | 3.99 | fixed | percent (30-year fixed) | scripts/dev/adu_reference.py: FRED MORTGAGE30US annual means (market_geo_year.mortgage_rate), mean of 2015-20… |
| `adu_calibration_rent_low_usd` | 1,573 | fixed | USD per month (2025) | scripts/dev/adu_reference.py: lowest ACS 2015-2019 median gross rent of Portland, Seattle and Los Angeles (20… |
| `adu_calibration_rent_high_usd` | 2,034 | fixed | USD per month (2025) | scripts/dev/adu_reference.py: highest ACS 2015-2019 median gross rent of Portland, Seattle and Los Angeles (2… |
| `adu_calibration_value_low_usd` | 519,222 | fixed | USD (2025) | scripts/dev/adu_reference.py: lowest ACS 2015-2019 median home value of Portland, Seattle and Los Angeles (20… |
| `adu_calibration_value_high_usd` | 835,671 | fixed | USD (2025) | scripts/dev/adu_reference.py: highest ACS 2015-2019 median home value of Portland, Seattle and Los Angeles (2… |
| `adu_calibration_rate_low` | 2.96 | fixed | percent (30-year fixed) | scripts/dev/adu_reference.py: lowest annual mean of FRED MORTGAGE30US over 2015-2023, the years the comparabl… |
| `adu_calibration_rate_high` | 6.81 | fixed | percent (30-year fixed) | scripts/dev/adu_reference.py: highest annual mean of FRED MORTGAGE30US over 2015-2023 |
| `adu_rent_to_median_ratio` | 1 | 0.8–1.2 | ADU rent / place median gross rent | Judgment |
| `adu_feasibility_dispersion` | 0.5 | 0.25–0.8 | standard deviation of log(lot's own price-to-cost) | Judgment |
| `adu_equity_elasticity` | 0.25 | 0–0.5 | % change in hazard per % change in median home value | Judgment |
| `adu_rate_semi_elasticity` | 0.07 | 0–0.15 | share change in hazard per percentage point of mortgage rate | Judgment |
| `adu_fee_per_unit_usd` | 0 | fixed | USD per ADU (2025) | E073 (Terner 2019): many California cities waive ADU fees, others charge up to $50k |
| `adu_ramp_half_years` | 2 | 1–3.5 | years after adoption to reach half the mature hazard | adu-study-design.md: immediate where conversions and pent-up demand exist (LA garages, E038) |
| `adu_ramp_slope_years` | 0.75 | 0.5–1.5 | years (logistic scale) | Judgment, set so the ramp goes from ~20% to ~80% of mature uptake in about 2 years (Seattle's ~3 years to pla… |
| `adu_extrapolation_widening` | 1 | 0.5–2 | standard deviation of log(hazard) per unit of log distance outside the calibration range | Judgment |
| `adu_place_effect_variance` | 4.735 | fixed | variance of a place's multiplier on the ADU hazard (gamma, mean 1) | Estimated, D-019 fit 3 (alpha): fitted place multipliers range from ~0 (Eagan, Lakeville, St |

**`config/params/market.yaml`** (1 parameter)

| Parameter | Value | Range (low–high) | Unit | Source (short; full text in the file) |
|---|---|---|---|---|
| `mortgage_rate_forecast` | 6.6 | 2.96–6.81 | percent (30-year fixed), held flat over the 5-year forecast (2026-2030) | Central: FRED MORTGAGE30US annual mean for 2025, 6.595% (market_geo_year.mortgage_rate, national:US) |

**`config/params/mm.yaml`** (4 parameters)

| Parameter | Value | Range (low–high) | Unit | Source (short; full text in the file) |
|---|---|---|---|---|
| `mm_panel_first_year` | 2010 | fixed | calendar year | Choice (D-024): the first year with missing-middle eligible-parcel rolls (rule 1.1) and ACS 5-year estimates… |
| `mm_panel_last_year` | 2025 | fixed | calendar year | Choice (D-024): the last full year of Census BPS place permits |
| `mm_estimation_min_population` | 10,000 | 10,000–50,000 | people (2020 Census) | Choice, flagged for Ben (D-024): comparison places of at least 10,000 people, the lower edge of D-022's middl… |
| `mm_dose_grade_permit` | 0.3333 | fixed | share of the by-right dose | Choice, flagged for Ben (D-024), mirroring D-023's equal steps: a rule that allows 2-4 units only by permit o… |

**`config/params/money.yaml`** (1 parameter)

| Parameter | Value | Range (low–high) | Unit | Source (short; full text in the file) |
|---|---|---|---|---|
| `real_dollar_year` | 2025 | fixed | calendar year | Statistical protocol §5.9: 'Real 2025 dollars' |

**`config/params/permits.yaml`** (2 parameters)

| Parameter | Value | Range (low–high) | Unit | Source (short; full text in the file) |
|---|---|---|---|---|
| `repeated_total_min_units` | 50 | 20–100 | units per permit | Ben, 2026-10-19 (decision D-008) |
| `repeated_total_min_permits` | 3 | 2–5 | permits | Ben, 2026-10-19 (decision D-008) |

**`config/params/proforma.yaml`** (23 parameters)

| Parameter | Value | Range (low–high) | Unit | Source (short; full text in the file) |
|---|---|---|---|---|
| `adu_sqft` | 800 | 600–1,000 | sq ft per unit | WS-ENGINE brief: 'ADU 600-1,000 sq ft' |
| `single_family_sqft` | 2,150 | 1,600–2,700 | sq ft per unit | Census Characteristics of New Housing: median new single-family home ~2,150-2,300 sq ft in 2023-24 (approx.) |
| `townhouse_sqft` | 1,700 | 1,400–2,000 | sq ft per unit | No solid public source found for new townhouse size alone (Census CNH reports single-family attached with det… |
| `plex_unit_sqft` | 1,000 | 750–1,300 | sq ft per unit | Census Characteristics of New Housing: median new multifamily unit ~1,050-1,100 sq ft (approx.) |
| `townhouse_units` | 4 | 2–6 | units per project | Handbook Missing Middle scenario: 2-6 units |
| `small_multifamily_units` | 6 | 5–6 | units per building | WS-ENGINE brief: '5-6 unit' prototype |
| `hard_cost_per_sqft_usd` | 165 | 120–260 | USD per sq ft (2025) | NAHB Cost of Constructing a Home 2024 (public): construction cost ~$162 per sq ft of finished area (approx.),… |
| `code_step_premium` | 0.1 | 0.03–0.25 | share added to hard cost per sq ft | No solid public source found (confounder register C43: 'to source') |
| `triplex_under_irc` | 0 | 0–1 | switch (0 = commercial code, 1 = residential code) | ICC IRC R101.2 scope (detached one- and two-family dwellings and townhouses) |
| `adu_hard_cost_premium` | 0.15 | 0–0.4 | share added to hard cost per sq ft | No solid public source found |
| `soft_cost_share` | 0.2 | 0.1–0.3 | share of hard cost | Conventional pro forma range (design, engineering, permits other than fees, insurance, legal) |
| `construction_loan_rate` | 0.085 | 0.065–0.11 | annual interest rate | FRED DPRIME (bank prime rate ~7.25-7.5% in 2025) plus a typical 0.5-1.5 point spread for small construction l… |
| `average_draw_share` | 0.5 | 0.4–0.65 | share of hard + soft cost outstanding on average | Standard construction-loan approximation: money is drawn as work proceeds, so on average about half the cost… |
| `construction_years_irc` | 0.75 | 0.5–1.25 | years | Census Survey of Construction, average months from start to completion: single-family ~7-9 months in 2023-24… |
| `construction_years_ibc` | 1.25 | 0.75–2 | years | Census Survey of Construction, average months from start to completion for multifamily buildings (approx. 12-… |
| `fee_paid_at_permit` | 1 | 0–1 | share of fees paid at permit (carried through construction) | Confounder register C54: fees paid at permit add financing carry |
| `sale_cost_share` | 0.05 | 0.03–0.08 | share of sale price | NAHB Cost of Constructing a Home 2024: sales commission plus marketing ~4-5% of price (approx.) |
| `rental_vacancy_rate` | 0.05 | 0.03–0.08 | share of potential rent | Underwriting convention for stabilized new rentals |
| `operating_expense_share` | 0.35 | 0.25–0.45 | share of collected rent | No public source found (income-and-expense surveys such as IREM are proprietary) |
| `cap_rate` | 0.055 | 0.045–0.075 | annual net operating income / value | Published summaries of national multifamily cap-rate surveys, ~5-5.5% in 2025 (approx.) |
| `developer_margin` | 0.15 | 0.1–0.2 | share of finished value | Confounder register C48 and E030 (Wellington): hurdles of 17-20% on cost for infill, 20-23% for redevelopment |
| `adu_margin` | 0.1 | 0–0.2 | share of finished value | No solid public source found |
| `existing_use_margin` | 0.1 | 0–0.25 | share above existing-use value | Methods review §2a and register C46: feasible when residual land value >= existing-use value x (1 + margin) |

**`config/params/tiers.yaml`** (2 parameters)

| Parameter | Value | Range (low–high) | Unit | Source (short; full text in the file) |
|---|---|---|---|---|
| `tier2_min_land_use_share` | 0.9 | 0.7–0.98 | share of parcels with a known land use (latest roll) | Tier definitions in docs/build/workstreams/WS-NC.md ('tier 1 ... year built and use codes, tier 2 ... use cod… |
| `tier1_min_year_built_share` | 0.8 | 0.5–0.95 | share of built parcels with a known year built (latest roll) | Same tier definitions (WS-NC brief, BUILD_PLAN §5) |
<!-- params-table:end -->

## Intended users and use cases

Lotline is built for people who write, analyse or advocate for state housing law and need a transparent,
checkable estimate rather than a black box. This section says who they are, which questions the tool is meant
to answer, and where its answers stop.

### Who it is for

- **State legislators and their staff**, including fiscal and policy analysts who must explain a bill's likely
  effect.
- **State housing and planning agencies** that will implement a reform and want to know where it bites.
- **Advocates, researchers and local governments** who want to test assumptions, supply their own data (a
  jurisdiction's parcels, permits or fees enter through an adapter), and see what drives the answer.

### Questions it is meant to answer

1. "If we pass a statewide missing-middle bill, roughly how many more homes would be permitted over five
   years, and how sure are we?" Answer: a statewide range, with the share in each region.
2. "Which of these reforms adds the most housing in our state, and is the difference real?" Answer: scenarios
   side by side on one scale, ranked only when their ranges separate.
3. "Why does the fee cut add so little here?" Answer: the drivers (land capture, how close projects are to
   feasibility, real fee levels versus the Handbook's $50,000) and the tornado chart.
4. "How much does the answer depend on data we don't have?" Answer: the data tier and denominator quality
   behind each result, and how much wider the range is because of them.

### What it should not be used for

- **Not lot-level predictions.** Parcels are used to count where a reform could apply; no result says what
  will happen on a given lot, and the tool will not map predicted units by parcel.
- **Not small-place precision.** Results for places with few eligible lots are wide and are best read at
  county or regional level.
- **Not prices or affordability.** Lotline estimates permits, not rents, prices or who benefits.
- **Not a substitute for local review.** Local rules (owner occupancy, lot splits, utility capacity, local
  fees) can make the real effect smaller or larger than the benchmark scenario.
- **Not yet for decisions.** Until the scenario modules are built and validated, Lotline's numbers cover the
  baseline and building-level economics only.
