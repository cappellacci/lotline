# Lotline: Data Availability Assessment (v1, 2026-09-30)

## Scope and files

**States covered.** The 12 top-ranked states on the "Lot-by-lot study" preset of the [Housing Data Readiness Ranking](https://claude.ai/artifact/PUQszFy2CYHvr2uNHTGRna) (v3), plus OH, which is pinned there.

**Cities covered.** The key cities for each state.

**National sources.** These are sources that every state run would use.

**Files:**
- `research/lotline-data-catalog.csv`: 194 datasets, one row each, covering:
  - fields present and missing
  - vintages and update cadence
  - access and license
  - known quality issues
  - which method uses the dataset
  - a 0–3 score
  
  156 rows were opened and checked this pass (`verified = Y`).
- `research/lotline-data-summary.csv`: state × requirement scores (R1–R10), blockers, and the best local jurisdictions.

**Requirements (R1–R10)** come from the statistical protocol:

| Code | What it covers |
|---|---|
| R1 | Parcel universe |
| R2 | Parcel history |
| R3 | Zoning |
| R4 | Permits |
| R5 | ADU flag |
| R6 | Completions and demolitions |
| R7 | Prices and rents |
| R8 | Fees |
| R9 | In-state reform evidence |
| R10 | Access and license |

---

## 0. Bottom line

1. **The desk ranking overstated how deep the data goes.** Once the actual datasets were opened:
   - No state scores ≥2 on every requirement.
   - Mean scores cluster between 1.5 and 2.1.
   - Parcel layers were the biggest overstatement. Most statewide layers have land use and value, but no year built, building size or unit count.
2. **Three blockers apply to every state:**
   - **National Zoning Atlas license.** Its terms forbid downloading, redistributing or building derivatives without written permission. Bulk data now goes through Land Use Labs under license. We can't bundle it in a public Apache-2.0 repo. Open alternatives:
     - WA Commerce Zoning Atlas (320 jurisdictions; custom license, to verify)
     - VT's UVM atlas (MIT)
     - CA's statewide zoning layer (no license stated)
     - local zoning GIS
     - NZLUD (Eviction Lab, MIT) as a restrictiveness covariate
   - **ADUs are invisible in Census BPS.** Detached ADUs are folded into 1-unit permits, and conversions are excluded. The only statewide record-level ADU source is California's HCD APR Table A2. Elsewhere, ADU calibration has to come from city permit data that flags ADUs:
     - Portland
     - Bend
     - Raleigh
     - Seattle
     - Los Angeles
     - San Francisco
   - **BPS place-level imputation.** About 11,500 of about 19,900 places report annually and are imputed from division/state factors when missing. Small-place models must use the "reported-only" series or flag imputed place-years.
3. **Real fees are far below the Handbook's $50,000 per unit in most places checked.**

   | Place | Fees found |
   |---|---|
   | Raleigh | ~$7.4k plus 0.38% of value |
   | Charlotte | ~$6.8k water and sewer |
   | Austin | ~$7.7k water and wastewater |
   | Beloit, WI | ~$1k per unit |
   | WA (industry survey) | ~$18.4k single-family average |
   | Colorado (16-city study) | ~$51.7k, the only place near $50k |

   The Rules fix $50k, so we model it. But a $25k cut is larger than *total* actual fees in much of NC, TX and WI. That belongs in the limitations and is a genuine policy insight.
4. **The two prongs want different kinds of states:**
   - **Evidence prong** (long post-reform periods and ADU/middle-housing-flagged permits): CA, OR, NC, WA, TX.
   - **Mechanism prong** (rich parcels, sale prices, fees): CT, MA, WI, then UT and MT. But UT and MT are non-disclosure states, so they have no sale prices.
   - **The evidence prong can borrow out-of-state comparables anyway** (Portland, Seattle, LA, Raleigh, Austin). So state choice should weigh what the *target* needs most: parcel universe, zoning eligibility, prices, and policy headroom.
5. **Policy headroom matters as much as data.**
   - The baseline is "current rules". In WA, OR, CA and VT, statewide middle-housing and ADU laws are already in the baseline, so our scenarios would change little in their big cities.
   - These states are better used as **sources of comparable evidence** than as the target. This matches the logged decision "calibrate where reforms are old, apply where they aren't" (LB-005).

---

## 1. State × requirement matrix (verified scores, 0–3)

Prong fit columns:
- **Evidence** = mean of R4, R5, R9
- **Mechanism** = mean of R1, R2, R7, R8
- **Statewide** = mean of R1, R3, R4

| State | Desk rank | R1 Parcels | R2 History | R3 Zoning | R4 Permits | R5 ADU | R6 CO/demo | R7 Prices | R8 Fees | R9 Reforms | R10 Access | Mean | Evidence | Mechanism | Statewide | Headroom (MM / ADU) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| WA | 1 | 2 | 1 | 3 | 3 | 2 | 2 | 2 | 2 | 2 | 2 | 2.1 | 2.3 | 1.8 | 2.7 | Low / Low |
| NC | 2 | 2 | 1 | 1 | 2 | 2 | 2 | 2 | 2 | 3 | 2 | 1.9 | 2.3 | 1.8 | 1.7 | **High** / Med (ADU mandate for cities >50k from 2027) |
| CT | 3 | 3 | 2 | 2 | 2 | 1 | 2 | 3 | 1 | 2 | 3 | 2.1 | 1.7 | 2.2 | 2.3 | **High** / Med (115 of 169 towns opted out) |
| CA | 4 | 1 | 1 | 2 | 3 | 3 | 3 | 1 | 2 | 3 | 2 | 2.1 | **3.0** | 1.2 | 2.0 | Low / Low |
| MA | 5 | 3 | 3 | 2 | 2 | 2 | 1 | 2 | 1 | 1 | 2 | 1.9 | 1.7 | 2.2 | 2.3 | **High** / Low |
| VT | 6 | 2 | 1 | 3 | 1 | 1 | 1 | 3 | 1 | 2 | 2 | 1.7 | 1.3 | 1.8 | 2.0 | Low / Low |
| UT | 7 | 3 | 2 | 1 | 2 | 2 | 2 | 1 | 1 | 2 | 2 | 1.8 | 2.0 | 1.8 | 2.0 | **High** / Med (internal ADUs only) |
| MT | 8 | 3 | 3 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 1.6 | 1.0 | 2.0 | 2.0 | Med (duplex only) / Low |
| WI | 9 | 2 | 3 | 0 | 2 | 1 | 1 | 2 | 2 | 1 | 2 | 1.6 | 1.3 | 2.2 | 1.3 | **High** / **High** |
| OR | 10 | 1 | 1 | 2 | 3 | 2 | 2 | 2 | 2 | 3 | 2 | 2.0 | 2.7 | 1.5 | 2.0 | Low / Low |
| CO | 11 | 2 | 1 | 2 | 2 | 1 | 2 | 2 | 2 | 1 | 2 | 1.7 | 1.3 | 1.8 | 2.0 | **High** / Low–Med |
| TX | 12 | 2 | 2 | 1 | 2 | 1 | 2 | 1 | 2 | 3 | 2 | 1.8 | 2.0 | 1.8 | 1.7 | **High** / **High** |
| OH | 18 | 2 | 1 | 1 | 2 | 1 | 2 | 2 | 1 | 1 | 2 | 1.5 | 1.3 | 1.5 | 1.7 | **High** / **High** |

**Headroom** is how much of each benchmark scenario is *not* already in current law statewide. Fees headroom is always present because of the Handbook assumption.

---

## 2. What the methods need vs. what exists

### R1–R2: parcel universe and history (the eligible-parcel denominator)

**Statewide layers with building attributes:**

| State | Layer | Building fields | License / vintages |
|---|---|---|---|
| UT | LIR | property class, house count, year built, building sq ft, acres, values | "No constraints" with attribution |
| CT | CAMA | use code, zone, acres, living area, year built, values, sale price | CC0; editions from 2023 only |
| MA | MassGIS L3 | units, year built, building area, last sale | All years in one download; no license stated |
| MT | Cadastral + ORION CAMA | CAMA building data | Monthly; archives Dec 2002–Dec 2025 |

**Statewide layers without building attributes:**

| State | Layer | Limitation |
|---|---|---|
| WA | Current Parcels | Some counties restrict use to state business |
| NC | OneMap | Current only; each county has its own land-use codes, which need a crosswalk |
| OH | Statewide parcels | Land-use code and lot area only |
| TX | StratMap | Schema not standardized; year built sparse |
| CO | Parcel composite | County gaps |
| WI | Statewide parcels | 12 annual vintages, but PROPCLASS 1 is all residential |
| VT | Statewide parcels | No statewide building data exists |

**No statewide layer:** CA (LA County and SF are free and multi-year) and OR (Metro RLIS is rich; elsewhere county by county).

**Implications for the methods:**
- The "eligible single-family parcel" rule must work at three data tiers:
  - **Tier 1:** land use + year built + units.
  - **Tier 2:** land use + lot area, with single-family inferred from residential class × ACS 1-unit share.
  - **Tier 3:** ACS 1-unit detached counts plus FEMA/ORNL USA Structures RES1 footprints (CC BY 4.0).
- Parcel-level before/after panels are realistic only in MA, MT, WI, UT (partly) and a few counties (Franklin OH, Travis TX, LA, SF, Metro Portland).

### R3: zoning eligibility
- Without the National Zoning Atlas, only WA (Commerce atlas) and VT (UVM, MIT) have open statewide zoning that identifies single-family-only lots.
- Elsewhere:
  - **Big cities:** local zoning GIS layers (Raleigh, Charlotte, Durham, Columbus CC0, Austin, Seattle, Portland, Denver).
  - **Rest of the state:** default to "single-family-only unless known otherwise", which is conservative and states its assumption.
- **Action:** ask Land Use Labs for written permission. Even a "use for validation only" answer would help.

### R4–R6: outcomes

**Census BPS (all states):**
- Use it for the statewide baseline.
- Flag imputed place-years.
- It has no ADU flag. We need an explicit assumption for the share of ADUs inside the 1-unit count, calibrated from CA APR and city ratios.

**Best record-level city data:**

| City | Coverage | Key fields |
|---|---|---|
| Portland | 1995–2026 | ADU flag, new units, parcel ID; separate demolition layer |
| Bend | from 1934 | HB 2001/ADU flag, date finaled, taxlot |
| Seattle | — | units added/removed, dwelling type, completed date |
| Austin | 1970–2026 | units, completion, demolitions, appraisal ID |
| Raleigh | 2000–2026 | ADU and missing-middle flags, CO date |
| Boulder | 1987+, CC0 | new and removed units, completed date |
| Denver | 2015+ | units, parcel, CO date |
| LA | — | ADU, JADU and CO fields |
| SF | — | net units and ADU units |
| Columbus, Cincinnati | 2010+ | units |

**Quality traps found:**
- Raleigh's units field is nearly empty after 2023, and 2013 is implausible.
- Mecklenburg (Charlotte) has no unit counts.
- Dallas stopped publishing in 2020.
- Salt Lake City's datasets appear retired.
- Houston publishes aggregates only.
- Boston, Cambridge and Somerville have no unit column.
- Several cities show only rolling windows (Bozeman 6 months, Spokane ~3 years).

**State production reporting:**
- CA APR is the gold standard.
- Useful but secondary: WA OFM units by city (1990–2026), CT DECD permits and demolitions by town, CO State Demography Office, UT Moderate Income Housing reports (ADU permits by city, PDF), WI Act 243 reports (PDFs across about 70 city websites).
- Not yet published: OR HB 4006 data (request it from DLCD) and NC's new fee reporting (first report date not yet set).

### R7: prices and rents
- **Non-disclosure states** (no sale prices): TX, UT, MT (confirmed statewide by MCA 15-7-308). In CA, prices aren't free in bulk.
- **Workaround:** the pro forma uses assessed values and ACS values/rents moved forward with FHFA HPI, with a stated caveat.
- **Strong price data:** CT (CC0 parcels plus a 2001–2024 sales file), VT (weekly transfer extract), MA, NC (Wake County), OH (Franklin County Auditor).
- **Zillow and Redfin can't be bundled.** Zillow requires attribution with no redistribution; Redfin is non-commercial only.

### R8: fees
- **No state has a machine-readable per-unit fee database.** The best available:
  - WI Act 243 fee reports (standardized per unit, but scattered PDFs)
  - city schedules (Raleigh, Charlotte, Austin, Portland SDCs, Tacoma permits with fees paid)
  - Boston `total_fees` per permit
  - NC's new disclosure law, once reports start
- **What this means for Lotline:** fees enter as the Handbook's $50k. We collect real local fees for 5–10 jurisdictions as a sanity check and for the "gap to reality" insight.

### R9: in-state reform evidence
- **Strongest:** CA, OR, NC, TX.
  - NC: Durham 2019, Raleigh ADU 2020 and middle housing 2021, Charlotte 2023.
  - TX: Houston 1998/2013, Austin HOME 2023–24.
- **Recent statewide reforms (about 1 year of data):** WA HB 1110/1337, CO, MA, UT, MT, and CT's middle-housing provisions.

### R10: access and license risks
- **Share-alike (ODbL):** Cleveland and Somerville.
- **Restricted:** some WA counties limit parcel use to state business; Vancouver WA is personal-use only; Salem is non-commercial; the BIAW fee survey is copyrighted.
- **Paywalls:** PPRBD (Colorado Springs) and Utah's statewide permit feed ($4,000).
- **No stated license:** CA HCD APR, CA zoning, MassGIS, WRLURI, Saiz data.
  - **Policy:** fetch these at runtime from the official source, never vendor them into the repo, and record the terms in `docs/data_provenance.md`.

---

## 3. What this means for choosing the state (recommendation, for discussion)

**Target-state criteria, in order:**
1. Policy headroom
2. Statewide parcel universe (R1)
3. Prices (R7)
4. In-state local reforms for calibrating and testing local mode (R9)
5. Everything else

The evidence prong draws on out-of-state comparables in any case.

- **NC: best overall fit as the target.**
  - High middle-housing headroom statewide.
  - Several in-state local reforms old enough to calibrate and backtest: Raleigh, Durham, Charlotte.
  - Disclosure state.
  - Statewide parcels include year built and values.
  - 100 counties, many of them sparse, which suits the sparse-data bonus.
  - **Costs:**
    - a land-use-code crosswalk across 100 counties
    - Raleigh's post-2023 unit-count gap
    - no statewide zoning
    - the 2027 ADU mandate for cities over 50k must be written into the baseline
- **Alternates:**
  - **TX:** great headroom and evidence (Austin, Houston), but non-disclosure and an unstandardized parcel schema.
  - **OH:** great headroom and good Columbus/Cincinnati data, but thin statewide parcels and only one reform with about 2 years of data.
  - **CT:** rich CC0 parcels and prices, and the ADU opt-out is a natural experiment, but city permit data is thin.
- **Evidence and backtest sources, not targets:** OR, WA, CA. Their reforms are already in the baseline, and their data is best for calibration: Portland, Bend, Seattle, CA APR, LA, SF.

---

## 4. Do we need to enumerate in more detail?

**Yes, but targeted, not for all 13 states.** This pass confirmed which datasets exist and what fields they document. It did not download samples. The protocol's decision points (§6 of the statistical protocol) depend on facts we can only get from the files themselves:
- null rates
- code lists
- how far back usable history goes
- whether parcel IDs stay stable across vintages

Recommended next pass (the "data scouting" phase, before Oct 14):

1. **Target state (NC first; one alternate):**
   - Download NC OneMap parcels and profile `parusecode`/`structyear` completeness by county.
   - Build the land-use crosswalk for the 10 largest counties.
   - Profile the permit files for Raleigh, Durham and Mecklenburg (date ranges, unit fields, ADU and middle-housing flags, 2013/2024 anomalies).
   - Pull Wake County sales.
   - Check BPS reported-only vs. imputed status for all NC places.
2. **Comparable-evidence cities:** a field-level data dictionary and a year-by-year count check for:
   - Portland
   - Bend
   - Seattle
   - Austin
   - Raleigh
   - Los Angeles and San Francisco
   - CA APR Table A2 (get the CSV header; the data dictionary is a .docx)
3. **Licenses:** email Land Use Labs (NZA) and WA Commerce, and confirm the terms of MassGIS, CA HCD APR, Metro RLIS and Bend's "custom" license.
4. **Records requests:** OR DLCD HB 4006 production data; WA OFM Form A submissions (ADUs, demolitions).
5. **Fees:** gather actual fee schedules for 5–10 jurisdictions (NC ×4, Austin, Portland, Seattle, Denver) to document the gap between real fees and $50k.

**Output of that pass:** `docs/data_provenance.md` rows with field lists, null rates and license text, plus a filled-in version of protocol §6 (the data-dependent decisions).
