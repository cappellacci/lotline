# Lotline: Similarity, standardization and statistical protocol (v0.1, 2026-09-30)

**Status:** working protocol. It will change once we see the chosen state's data (§6 lists the decision points).

**Evidence behind it:** `research/lotline-methods-extraction.csv` records the methods sections of 42 studies plus 4 methods-guidance papers, field by field:

- comparison group
- similarity covariates
- how similarity enters the estimate
- units
- zeros
- dose
- diagnostics
- data cleaning

IDs refer to `research/lotline-evidence-register.csv`. How well each row is sourced:

| Source read | Rows |
|---|---|
| Full text | 26 |
| Working-paper version | 11 |
| Abstract or secondary sources only | 9 (E020, E043, E048, E059, E060, E061, E063, E068, E081) |

---

## 0. Headline findings

1. **No housing study we found transfers an effect from reformed places to a new target place.** Every study estimates the effect *where the reform happened*.
   - Our evidence prong asks a different question: what would happen *here*. That is a transportability problem.
   - The standard tool for it comes from epidemiology: inverse-odds weighting (Westreich et al. 2017, G04). We would be applying it in a new setting, so we have to justify and test it ourselves.
2. **Comparison-group quality varies widely.**
   - **Strongest:** synthetic control with explicit donor-pool rules (E002, E004, E021) and boundary or buffer designs (E006, E008, E009).
   - **Weaker:** panels with fixed effects plus unit trends and no overlap check.
     - Stacy et al.'s comparison cities averaged about 19.7k people against about 200k for reformers (E012).
     - The fee panels use FE only, with fee dummies and raw counts (E058–E062).
   - **Weakest:** before/after comparisons within one city (E022, E038, E044).
3. **Denominators are the most neglected detail.**
   - Portland's "per 1,000 lots" never defines a lot and doesn't say whether the rate is annual (E022).
   - New Hampshire's single-family house counts have no stated source (E056).
   - SB 9's 6.1M "eligible parcels" is a simulated number that later reports reuse as if it were observed (E026 → E028).
   - Almost no study explains how it handled zero counts. São Paulo's Poisson model (E006) is the exception.
4. **Reform coding can drive the result by itself.** The Stacy vs. AEI dispute (E012/E013) is entirely about which reforms count and when they started.

---

## 1. How the literature defines "similar"

| # | Technique | How similarity is set | Examples | Strength | Main weakness |
|---|---|---|---|---|---|
| a | Own pre-period only | The place before the reform | Portland RIP (E022), Seattle ADU (E044), CA ADU (E038) | Weak | Any market cycle or concurrent reform looks like an effect |
| b | Panel with fixed effects (+ unit trends) | Assumed: FE remove level differences, trends remove linear drift | Stacy (E012); fee panels E058–E062 | Weak–moderate | No overlap or balance check. TWFE with staggered timing and unit trends is biased (G03). Trends can absorb the dynamic effect itself. |
| c | Stratify into similar submarkets | Estimate separately by tier | Dresch & Sheffrin east/west (E066); Burge & Ihlanfeldt suburb type (E059/60); Mathur quality tiers (E068) | Moderate | Tiers chosen ad hoc; small cells |
| d | Geographic proximity | Buffers or rings (E009 1,000 ft; E017 0.5–2 mi; E018 1–3 km); boundary RD (E006 blocks; E008 0.3 mi within town and school zone); same-zone FE (E001 suburb × zone) | Strong for the local effect | Spillovers contaminate nearby controls. Boundaries may follow expected development. Estimates a *local* effect only. |
| e | Matching | Generalized full matching with exact match on 6 pre-years of unit counts; balance target SMD ≤ 0.1 (E010) | Strong | Needs many candidate units |
| f | Synthetic control | Weighted donors chosen to fit the pre-period outcome path | Auckland on Functional Urban Areas (E002); Lower Hutt (E004); Minneapolis Fed 126 donors (E021); Gu & Munro 83 donors (E020) | Strong for single places | Needs a long pre-period and a clean donor pool. Poor fit means bias (augmented SCM fixes this). |
| g | Timing-based controls | Not-yet- or last-treated units | Zurich last-treated rasters (E007); Chicago later-treated parcels (E011) | Strong | Only works where reforms roll out in stages |
| h | Transport reweighting | Weight the study sample to match the target's effect modifiers | Westreich et al. (G04); **no housing application found** | — | Needs overlap (positivity) and the right effect modifiers |

**Synthetic-control donor-pool rules** (Abadie G01, applied in E002/E004/E021). Exclude:

- units that received the same or a similar reform;
- units hit by a large idiosyncratic shock (Christchurch earthquake);
- tiny or remote units;
- neighbors that could receive spillovers (Wellington-region councils; St. Paul).

On predictors:

- The main predictors are **pre-period outcomes, demeaned**, so the match is on trends rather than levels.
- Covariates such as population growth, income and dwellings per capita appear in robustness runs. The authors report that adding them worsens the fit on outcomes.
- Monthly data are too noisy; they use annual data or a 3-year moving average.

---

## 2. How similarity enters the estimate

| Mechanism | Used in |
|---|---|
| Unit FE + period FE | Nearly all panels |
| Unit-specific linear trends | E012, E059/60 (random trends) |
| Finer FE (tract × year, block, zip-year, parcel) | E040, E042, E048, E076 |
| Synthetic-control weights (predictor weights V, unit weights W) | E002, E004, E020, E021 |
| Matching weights, with a balance check | E010 |
| RD bandwidth / distance to boundary | E006, E008 |
| Instrumental variables (for endogenous treatment) | Eligibility × post (E042, E040); political instruments for regulation (E058); land and politics (E080); Bartik demand shocks (E081) |
| Stratified estimation | E059/60, E066, E068 |

**Diagnostics the stronger studies report:**

- event-study leads or pre-trend plots (E001, E007, E009, E012, E041, E042);
- placebo treatment dates, and backdating treatment to "the first period the outcome could react" (E001 → 2015, E004 → 2018);
- placebo-in-space permutation p-values, 1/(J+1), using the post/pre RMSE ratio (E002, E004, E021);
- leave-one-out donors and alternative donor pools;
- bandwidth sweeps and covariate balance at the boundary (E006, E008);
- falsification on buildings built before the rule existed (E008);
- first-stage F statistics (E040 is very high but R² is only 0.006, a warning sign; E042 ~100; E080 ~48).

**The fee panels report almost none of these diagnostics.**

---

## 3. Standardized units observed

**Outcome scales and when each appears:**

| Scale | Where used | Note |
|---|---|---|
| Permits per 1,000 residents | SC studies (E002, E004) | Robust to raw counts, pre-mean-normalized counts and logs (E004) |
| Units per 1,000 lots | E022 | Lot not defined |
| Permits per 1,000 SF houses | E056 | House-count source not stated |
| Permits per 10,000 residents | E038 | |
| % of dwelling stock / % of total permits / % of control mean | E001, E006, Oregon/Spokane shares | |
| Logs | E007, E009, E058 | Where cells are large. Zero handling unstated. |
| Levels | E001, E010 | Chosen so bounds or aggregation stay additive. E001 uses levels deliberately. |
| Counts with Poisson | E006 (block-quarter) | The only explicit zero-handling approach |
| Raw counts | E062 | Coefficients don't transfer to other places. **Avoid.** |

**Treatment dose.** The best studies measure the change in allowed FAR or capacity (lot area × FAR), then either keep it continuous (E006, with IV scaling per unit of FAR) or apply thresholds:

- any increase (E001);
- ≥20% capacity (E009);
- >0.25 FAR (E010);
- a median split (E007).

"Bindingness" (current vs. allowed floor area) and market strength are the main effect modifiers.

**Fee measurement varies:**

- a yes/no dummy (E058, E061);
- summed real dollars, averaged across zones and priced at a 2,500 sq ft reference house (E062);
- priced at the average home size (E064);
- water/sewer fees separated from other fees, because the sign of the effect differs (E059/60).

**Money:** stated in real dollars (CPI) where stated at all.

**Gross vs net.** Almost all studies count gross units. NZ has no demolition data (E001). Portland reports units per demolition (E022).

---

## 4. Pitfalls the authors themselves flag

- **Contaminated controls:**
  - displacement into or out of nearby areas (E001 bounds it; E004 runs a synthetic control for each neighbor);
  - controls that reform later (a third of E021's donors have since reformed);
  - unobserved reforms among controls (E012/E013).
- **Anticipation.** Prices move about 2 years before approval (E076). The Auckland plan was notified 3 years before it took effect.
- **Concurrent reforms and shocks.** Examples: Portland's size limit plus fee waiver; COVID in Minneapolis; the 2022 rate shock.
- **Measurement:**
  - permits are not completions (NZ completes about 90–95%);
  - USPS address counts miss ADUs that share an address (one dataset caught 58% of verified LA ADUs);
  - state annual progress report (APR) data are self-reported;
  - unpermitted ADUs (E049);
  - water/sewer fees are often missed because utilities levy them.
- **Estimates change between versions of a paper.** For example, E040's IV premium was 40–60% in the working paper and 7–9% when published. Pin every parameter to a specific version.

---

## 5. Lotline protocol (recommendations)

### 5.1 Canonical unit
- **Primary unit:** net new units permitted per 1,000 eligible parcels per year, indexed by years since the reform. This is what the mechanism prong produces (hazard × units per project), and it transfers across places of different sizes.
- **Cross-check scales:** per 1,000 residents and % of dwelling stock, so results can be compared with E001, E002 and E004.
- **Always store the numerator and denominator separately.** Never store only the rate.
  - This lets us re-aggregate from city to county to state.
  - It lets us pool counts properly in a count model with an offset, log(eligible parcels), instead of averaging rates.

### 5.2 Eligible-parcel definition as versioned code
- Apply one rule to the target and to every comparable place: land-use code, lot size floor, existing single-family structure, and exclusions (e.g., HOA, floodplain, historic districts where the data allow).
- Where a comparable place's published denominator is undefined (E022, E056), rebuild it from parcel data or mark it `denominator_quality = low`.
- Don't reuse simulated denominators as if they were observed (the SB 9 lesson).

### 5.3 Time
- Use event time. Treatment date = the first period the outcome could react (adoption vs. effective date, as in Abadie).
- Test an anticipation window of 1–2 years.
- Use annual data. Smooth anything finer.

### 5.4 Reform coding rubric (published in the repo)
- Each reform is a vector, not a yes/no:
  - by-right or discretionary;
  - owner-occupancy rule;
  - unit cap and FAR/size cap;
  - lot splits allowed;
  - parking requirement;
  - fee change ($/unit);
  - effective date;
  - geographic coverage.
- Two coders, with disagreements logged. This answers the Stacy/AEI problem directly.

### 5.5 Similarity: three steps
1. **Eligibility filter for comparable places:**
   - same reform type, with rubric scores within a set tolerance;
   - at least 3 post-reform years;
   - the denominator can be rebuilt;
   - no major concurrent shock.
2. **Distance on effect modifiers.** Standardize each covariate (z-scores or ranks) and use Mahalanobis distance. Covariates:
   - price-to-construction-cost ratio (Glaeser–Gyourko regime);
   - rent;
   - median lot size;
   - share of single-family parcels;
   - pre-reform permits per 1,000 parcels;
   - growth;
   - WRLURI (regulation index).
   
   Report the similarity score in the interface.
3. **Overlap check.** If the target falls outside the range of the comparable places on any key modifier, don't extrapolate:
   - flag the evidence prong as low-confidence;
   - weight the mechanism prong more.
   
   If overlap holds, apply inverse-odds (G04) or kernel weights. With so few comparables, keep the weights simple and always show leave-one-out results.

### 5.6 Our own estimates (the ADU natural experiment, backtests)
- **Staggered designs:** Callaway–Sant'Anna or the Borusyak imputation estimator with not-yet-treated controls. **No TWFE with unit trends** (G03).
- **Single cities:** synthetic control with Abadie's donor rules, demeaned pre-period outcomes, and augmented SCM when the pre-period fit is poor.
- **Counts with zeros:** Poisson (PPML) or negative binomial with the eligible-parcel offset.
- **Inference:**
  - wild bootstrap, or randomization/permutation inference when few units are treated;
  - conformal intervals for single-place SC;
  - HonestDiD bounds for violations of parallel trends.
- **Pre-register the choices** (§6) before looking at post-reform outcomes, and log any deviations.

### 5.7 Pooling to form the evidence prong
- A hierarchical negative-binomial model of uptake curves:
  - counts with the log(eligible parcels) offset;
  - random effects by place;
  - effect modifiers from 5.5 as covariates;
  - a ramp shape over event time.
- The target's posterior predictive distribution is the evidence-prong range.
- Use Fay–Herriot shrinkage for noisy small-place baselines.

### 5.8 Linking to the mechanism prong
- Calibrate the redevelopment hazard to the same pooled comparable data.
- Validate with leave-one-place-out backtests: predict Portland from the others, then Seattle, and so on.
- Report how often the P10–P90 band contains the observed value.

### 5.9 Money and fees
- Real 2025 dollars. Deflate costs with the BLS PPI for residential construction inputs, and prices and rents with CPI.
- Express fees both per unit and as % of total development cost.
- Keep water/sewer fees as a separate component.

### 5.10 Gross to net
- Subtract demolitions where the data have them.
- Apply the ADU net-new share (about 50–80%, E039/E051/E052) and a formalization adjustment (E049) as explicit, adjustable parameters.
- Show a permits-to-completions factor separately.

---

## 6. What will change once we see the data (decision points)

| Decision | Depends on | Default until we know |
|---|---|---|
| Denominator: eligible parcels vs. SF houses vs. residents | Whether the state's parcel data carry land use, lot area and year built | Eligible parcels; fall back to ACS SF units |
| Count model: Poisson vs. NB vs. zero-inflated | Share of zeros and overdispersion in place-year permit counts | NB with offset |
| Levels vs. logs | Pre-trend diagnostics and whether results must add up (state totals must) | Levels for aggregation, logs as robustness |
| SC vs. pooled DiD for each comparable | Number of donors and length of pre-period in each place's series | SC for single cities with ≥8 pre-years; otherwise pooled |
| Which effect modifiers to use | Coverage and correlation in the comparables set (with about 15 places, 3–4 modifiers at most) | Price/cost ratio, lot size, pre-reform rate |
| Overlap threshold | How far the chosen state sits from the comparables | Flag when outside the convex hull on price/cost or lot size |
| Anticipation window | Event-study leads in the comparables | 1 year |
| BPS vs. local permit data | Place-level BPS imputation rates; ADU flags in local data | BPS for baseline; local data for ADU calibration |
| Displacement share | Whether neighbor-place data show pull-in | 0–50% range parameter |
| Completion factor | Census Survey of Construction lags; local completion data | 0.85–0.95 |

**Rule:** once the state's data are in hand, write these choices into `docs/analysis_plan.md` and commit it *before* running outcome models. Any later change gets a dated entry explaining why. This is cheap to do and counts toward Transparency (30%).

---

## 7. The fee scenario: keep it or swap it?

**The evidence gap is real, but narrower than "no evidence":**

- There is no clean study of what a fee **cut** does to production. The closest analogs are Florida's 2009–10 suspensions (E063, a weak consultant study) and Portland's ADU fee waiver (E047, confounded).
- Panels on fee **levels** exist but are the weakest designs in the set (§1b). They mostly find null or mixed effects on quantity (E058, E059, E062).
- The **incidence** evidence is solid: fees are passed into prices or pushed back onto land (E064, E066, E068).

**What the alternatives look like** (the Rules require at least 3 of the 5 benchmark scenarios, so dropping fees means adding one):

| Option | Evidence on housing production | Other evidence | Fit with our design |
|---|---|---|---|
| **Fees (keep)** | Weak, mostly null | Strong on incidence | Parameters fixed by the Handbook ($50k, −50%). It is a pure cost shock in the pro forma we are building anyway. |
| **Parking** | Also thin | Good on *parking still built*, which the Handbook asks us to state. Seattle built 40% fewer spaces than required (868 developments; Gabbe, Pierce & Clowers 2020, *Land Use Policy* 91). Buffalo: 47% of major developments built fewer spaces than previously required (Hess & Rehler 2021, *JAPA* 87(3)). | We must pick a "parking still built" assumption; interacts with ADU and MM |
| **TOD** | Mixed (Chicago null, E011) | — | Needs transit-stop data and our own distance thresholds. Weak for sparse-data states; already set aside. |

**Recommendation: keep fees.**

- **Least risk.** The Handbook fully specifies the scenario, so there are no contestable assumptions about the policy itself.
- **Least cost.** It reuses the pro forma engine we are already building.
- **The weak evidence is itself a finding.** "Fee cuts mostly show up in land prices unless the market sits near the feasibility margin" is exactly the kind of result Policy Insight rewards.
- **Parking has the same core gap** on housing units.
- **We can add some original evidence.** Portland's 2010 ADU fee waiver is already row 1 of `adu-study-design.md`, so our ADU natural experiment can report a fee-waiver contrast.

**Consequences for the tool:**

- For fees, the evidence prong shows literature bounds only and says so.
- The low case includes zero.
- The land-capture share and the market regime become the lead sensitivity parameters.
- Parking stays as a possible 4th scenario if the schedule allows.

**Reasons you might still swap:** if the team wants all three scenarios to have a symmetric two-prong story, or if the chosen state has a high-profile parking reform with good local data.
