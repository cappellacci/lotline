# Lotline: Two-pronged design, statewide and local (proposal, 2026-09-30)

**Status:** proposal for discussion. Not yet in the HANDOFF decisions log.
**Evidence:** `research/lotline-evidence-register.csv` (E-numbers below) and `research/lotline-methods-review.md`.

## The idea

A state or city enters its data and gets two answers side by side for each scenario:

1. **Evidence prong: "What happened in places like you?"**
   - Measured effects from comparable places that already reformed, such as Portland, Seattle, California, Spokane and Auckland.
   - Expressed per 1,000 eligible lots, by year since the reform.
2. **Mechanism prong: "What do your own economics say?"**
   - Parcel funnel: eligible parcels → pro forma feasibility → annual redevelopment hazard → permits.
   - The fee cut enters as a cost shock, adjusted for how much of it landowners capture, and converted to units with a supply elasticity.

The same engine runs **statewide** (the benchmark output the Rules require) and **locally**, because cities and counties control most of these levers.

## Verdict: strong design, with three refinements

### 1. The prongs should inform each other, not just sit side by side
- **Calibration:** the evidence prong sets the mechanism prong's free parameters, meaning the realization hazard and the ramp-up shape (E022, E028, E044, E038).
- **Local translation:** the mechanism prong translates that evidence to the local market.
  - Example: "Your price-to-cost ratio is 30% below Portland's, so fewer lots pencil."
- **Reconciliation panel:** where the two answers differ, show why. That explanation is the "what drives the differences" content scored under Policy Insight.
- **Uncertainty:** show both ranges and a combined range. Never a single number (S6).

### 2. "Comparable places" needs a stated similarity rule, and honesty that the pool is thin
- **Pool size:** only about 10–15 reformed places have usable production data. Most are on the West Coast and high-cost.
- **Similarity covariates:**
  - Price-to-construction-cost ratio, i.e. the Glaeser–Gyourko regime (E083)
  - Rent level
  - Lot-size distribution
  - Share of parcels that are single-family
  - Recent permit trend
  - Regulatory stringency (WRLURI, E085)
  - Reform design details (owner occupancy, floor-area/unit caps, lot splits)
- **Transfer method:** reweight on these covariates, following transportability theory (Pearl & Bareinboim, E102).
- **Confidence flag:** show a similarity score. When the nearest comparable is far away, as it will be for most of Ohio or rural North Carolina, flag the evidence prong as low-confidence and lean on the mechanism prong.
- **Fees have no clean comparables.** Only Portland's ADU fee waiver (E047) comes close, and it is confounded. For fees, the evidence prong should instead show:
  - the literature's range of estimates (mostly near zero: E058, E059, E062);
  - incidence estimates (E064, E066).

### 3. One engine, with the jurisdiction as the basic unit
- **Statewide is a sum of jurisdictions.** The local view is the same run, filtered. This keeps the local mode cheap to build.
- **Data tiers:** label every output with the tier it came from. This directly serves the sparse-data bonus.

  | Tier | Data available | Used for |
  |---|---|---|
  | 1 | Parcel data | Full parcel pro forma |
  | 2 | Jurisdiction aggregates only (BPS, ACS, estimated lot-size distribution) | Aggregate funnel |
  | 3 | Nothing local | State/county defaults, with partial pooling (Fay–Herriot, E103) |

## Local-mode caveats to design in from the start
- **Local results are not additive.**
  - A city's gain partly comes from its neighbors (displacement: E001; Lower Hutt shows the regional net can still be positive, E004).
  - Show two figures: "in this city" and "net statewide contribution".
  - Make the displacement share a visible parameter.
- **Small places are noisy.** Use wider bands and shrinkage toward similar places.
- **Local levers differ from benchmark definitions.** The evidence says design details drive most of the uptake:
  - owner-occupancy rules
  - floor-area/unit caps (Minneapolis vs Portland, E019, E024)
  - lot-split rules and utility fees (SB 9, E028)
  - SDC scaling
  - pre-approved plans
  
  Offer these as optional, clearly labeled local toggles. Keep the benchmark scenarios on the Handbook's exact definitions (S1, S7).
- **Measurement:** the Census Building Permits Survey does not flag ADUs. Local ADU backtests need city or state data, such as CA HCD APR, Portland and Seattle open data (see `adu-study-design.md`).

## Build order (coding opens Oct 14; due Dec 16, about 9 weeks)
1. **Weeks 1–3:** Data adapters and baseline forecast, per jurisdiction, for the chosen state. Jurisdiction is the unit from day one.
2. **Weeks 3–5:** Mechanism prong: parcel/aggregate funnel, fee cost-shock module, Monte Carlo.
3. **Weeks 4–6:** Evidence prong:
   - curated comparables table (uptake curves with ranges) drawn from the register;
   - one original estimate, the ADU natural experiment in `adu-study-design.md`.
   
   Do not attempt new causal estimates for every comparable.
4. **Weeks 6–7:** Backtest: predict Portland 2021–24, Seattle 2019+, California ADUs and SB 9 from pre-reform data, and report coverage.
5. **Weeks 7–9:** Interface with a state/local toggle, reconciliation panel, tornado chart, documentation.

## Open questions
- Which state? The local mode favors a state with good open parcel data and several active jurisdictions (NC and OR both qualify).
- Combined-scenario runs need one parcel-allocation step so that ADUs and Missing Middle do not double-count the same lots.
