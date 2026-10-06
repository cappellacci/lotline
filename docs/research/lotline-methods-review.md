# Lotline: Methods Review — How researchers estimate the effects of ADUs, Missing Middle and fee cuts

*Study-by-study details (data, method, counterfactual, finding, link) are in `research/lotline-evidence-register.csv` (104 studies, citations checked 2026-09-30).*

*Research pass: 2026-09-30. Four parallel literature sweeps (~140 searches/fetches) plus spot checks. Tags: **[v]** = checked against the publisher, NBER, RePEc or the author's page; **[d]** = our own arithmetic on published counts; **[?]** = unverified, disputed or depends on definitions. Verify every [?] item before it goes into a config file.*

---

## 0. Summary

1. **There are two families of methods, and a good simulator uses both.**
   - **Ex-post causal inference** looks at reforms that have already happened and asks what they did, compared with an estimated counterfactual. Tools: DiD, event studies, synthetic control, spatial RD, IV.
   - **Ex-ante simulation** asks what would happen under a hypothetical rule. Tools: pro formas, parcel microsimulation, supply elasticities, structural equilibrium models.
   - The standard hybrid is to **build the ex-ante mechanism and calibrate its free parameters to ex-post estimates**, then **backtest** it on reforms whose outcomes are known.

2. **The rules create a large capacity; the realized share is small.** Pro-forma capacity overstates realized production by one to two orders of magnitude.
   - California SB 9: about 700k units were judged "feasible", but only 266 projects were built in two years.
   - Auckland: about 111k units were judged "commercially feasible", and about 22k extra were consented in five years.
   - The parameter that drives Lotline's results is the **annual realization (hazard) rate**, not the capacity count.

3. **Evidence quality differs a lot across our three scenarios:**

   | Scenario | Best evidence | Strength |
   |---|---|---|
   | Missing Middle | Auckland (DiD + synthetic control), São Paulo (spatial RD), Zurich (staggered DiD), NYC | **Strong abroad**; thin and mostly descriptive in the US (Portland, Spokane, Minneapolis, Houston, SB 9) |
   | ADUs | Before/after permit series (California, Seattle, Portland, Vancouver), parcel location models, owner surveys | **Medium**: large, consistent jumps, but almost no formal causal designs |
   | Fees | 1990s–2000s Florida/IL/TX panels, incidence studies | **Weak for quantity** (mostly nulls); **strong that fees capitalize** into prices and land |

4. **Implication for Lotline:** a parcel funnel model for Missing Middle and ADUs (eligible → feasible → realized, via a hazard). Fees act as a cost shock that moves parcels across the feasibility threshold, plus an elasticity fallback for places without parcel data. Monte Carlo with Sobol or tornado ranking for uncertainty, and hierarchical pooling for places with sparse data.

---

## 1. Ex-post causal methods: how the counterfactual is built

In every one of these designs the counterfactual is *estimated from untreated units or periods*. The methods differ in what they assume makes those units comparable.

| Method | Counterfactual comes from | Key assumption | Housing applications |
|---|---|---|---|
| **DiD / event study** | Change over time in untreated places | Parallel trends | Auckland upzoning (Greenaway-McGrevy & Phillips 2023, *JUE* 136) **[v]**; NYC rezonings (Liao; Su, Curran-Groome & Freemark, Urban Inst. 2026); Chicago (Freemark 2020, *UAR*) |
| **Staggered DiD** (Callaway–Sant'Anna 2021; Sun–Abraham 2021; Borusyak–Jaravel–Spiess 2024 *REStud* **[v]**; de Chaisemartin–D'Haultfœuille 2020 *AER* **[v]**) | Not-yet- and never-treated units, with separate estimates for each adoption cohort | Parallel trends; no bias from comparing early adopters against late adopters | Zurich upzonings, 168 municipalities (Büchler & Lutz 2024, *JUE* 143) **[v]**. Plain TWFE is biased when effects differ across cohorts (Goodman-Bacon 2021). |
| **Imputation DiD** (Borusyak et al.) | Fit a model of untreated outcomes, then *predict* the baseline for treated units | Correct untreated model | Conceptually the same as Lotline's "forecast baseline, subtract" |
| **Synthetic control / augmented SCM / synthetic DiD** (Abadie et al. 2010; Ben-Michael et al. 2021 **[v]**; Arkhangelsky et al. 2021 *AER* **[v]**) | A weighted mix of donor places that tracks the treated place before the reform | Pre-reform fit carries over after the reform | Auckland vs other NZ regions: permits roughly doubled; ~52k extra over 7 years (Greenaway-McGrevy 2026, *Econ. Modelling* 160) **[v]**; Lower Hutt, consents roughly tripled (Maltman & Greenaway-McGrevy 2025, *JHE*); Minneapolis prices/rents (Gu, H. & Munro, D. 2025) |
| **Spatial regression discontinuity** | Parcels just across a zoning boundary | Nothing else changes at the boundary | São Paulo: +1 in allowed floor-area ratio roughly doubles multifamily permits (Anagol, Ferreira & Rexer 2026, *AEJ: Policy* 18(3):235–74) **[v]**; Boston: relaxing *density*, not just *use*, is what matters (Kulka, Sood & Chiumenti 2022); Turner, Haughwout & van der Klaauw 2014, *Econometrica* **[v]** |
| **Instrumental variables** | Variation from an instrument (geography, labor-demand shocks, law × eligibility) | Exclusion restriction | Saiz 2010 (land unavailability); Baum-Snow & Han 2024 (Bartik-style demand shocks); ADU spillovers in LA (Tanrisever 2025, *RSUE*) |
| **Bayesian structural time series (CausalImpact)** | Forecast of the treated series from control series | Stable relationship with the controls | Suits a single city's monthly BPS series. No peer-reviewed zoning application found **[?]** |

**Inference with few treated units.** When only one city or region is treated (Minneapolis, Auckland), conventional standard errors are invalid. Researchers use:

- placebo/permutation tests (Gu & Munro: p = 0.012 from 83 placebo cities);
- conformal intervals (Chernozhukov, Wüthrich & Zhu 2021, *JASA*) **[v]**;
- bounds on violations of parallel trends (Rambachan & Roth 2023, *REStud*, "HonestDiD") **[v]**. The Auckland paper uses these to bound displacement.

**Two cautions from recent debates:**

- **Reform coding drives the result.** Stacy et al. (2023, *Urban Studies*) coded 180 reforms in 1,136 cities and found +0.8% supply after 3–9 years. AEI (Peter et al., *Econ Journal Watch*, 2026) argues many of those reforms were duplicates, minor, or carried "poison pills". Lotline should publish its reform-coding rules.
- **Aggregation weights matter.** Deb, Norton, Wooldridge & Zabel (NBER w34331, 2025) **[v]** show that common Callaway–Sant'Anna software weights can move the overall effect by about 16%.

---

## 2. Ex-ante (counterfactual simulation) methods

### 2a. Pro forma / residual land value (RLV)
- **Feasibility test:** a parcel is feasible if `value − (hard + soft + fees + financing + target profit) ≥ existing-use value × (1 + margin)`.
- **Examples:**
  - Terner Center's SB 9 model (2021): 652 prototypes per parcel across 6.1M eligible parcels found ~700k feasible units. It stated plainly that this was "not a forecast."
  - Terner "Making It Pencil" (2023), with an open calculator.
  - New Zealand's capacity assessments (NPS-UD).
- **Sensitivity:** SB 9 capacity moved +36k units with costs −10% and +57k with prices +10%. Wellington's stress test (prices −10%, costs +10%) cut realizable capacity by 42%.
- **NZ four-tier funnel:** plan-enabled → infrastructure-ready → commercially feasible → "reasonably expected to be realised."
  - Auckland 2017: 906k plan-enabled, of which 111k (12%) were commercially feasible (secondary source) **[?]**.
  - Profit hurdles used: 17–20% for infill, 20–23% for redevelopment.
  - **This is the structure to copy.**

### 2b. Parcel microsimulation and redevelopment hazard
- **UrbanSim developer model** (Waddell 2002, *JAPA*): runs a pro forma on each parcel. Demand (a target vacancy rate) sets *how much* gets built; profit-weighted draws set *where*. Borrow the architecture, not the code (originality rule).
- **Redevelopment and teardown models:**
  - Rosenthal & Helsley (1994): redevelop when vacant-land value exceeds value in current use.
  - Dye & McMillen (2007): a probit model of teardowns. Rates were ~0.4%/yr in Chicago city and ~1.3%/yr in hot suburbs **[d]**.
  - Murphy (2018, *AEJ: Policy*): a dynamic optimal-stopping model. Timing and cycles make supply less elastic, which is **why "feasible" does not mean "built"**.
- **ADU location models:**
  - Brueckner & Thomaz 2024 (*REE*): LA County parcel panel.
  - Kim et al. 2023: multilevel logit.
  - After a reform, parcel characteristics predicted *less* (Kim et al.). That supports a simple rate × eligible parcels structure with modest multipliers.

### 2c. Supply elasticities (the fee channel and the sparse-data fallback)
- **Saiz (2010, *QJE*):** metro elasticities from about 0.6 (coastal) to above 3 (inland). The ~1.75 average is from memory **[?]**.
- **Baum-Snow & Han (2024, *JPE*) [v]:** tract-level elasticities of **~0.3 for units** and ~0.5 for floor space. Most of the variation is within metros. Replication data are on Harvard Dataverse.
- **Aastveit et al. (2020):** the median metro elasticity fell from 2.63 to 1.75 after 2006.
- **Glaeser & Gyourko (2018, *JEP*), minimum profitable production cost (MPPC):** splits places into regimes.
  - Where price ≤ MPPC, a cost cut tips projects into feasibility (large quantity response).
  - Where price ≫ MPPC, the cut mostly goes into land value.

### 2d. Structural equilibrium models
- Anagol, Ferreira & Rexer (São Paulo): stock +1.6%, prices −0.4%, welfare +0.65% of city GDP **[v]**.
- Favilukis, Mabille & Van Nieuwerburgh (2023, *REStud*).
- Hsieh & Moretti (2019). **[?]** A published Comment reports a computational error that shrinks the headline gains.
- These models are powerful, but too opaque for a 30%-transparency rubric. Use them for context, not as Lotline's engine.

---

## 3. Scenario-by-scenario evidence

### 3a. Missing Middle (2–6 units on single-family parcels, 3 stories)

| Case | Design | Result |
|---|---|---|
| Auckland 2016 (~75% of residential land upzoned, mostly 2–3 storeys) | DiD, 479 areas + synthetic control | +21,808 dwellings in 5 yrs ≈ **+4.1% of stock** **[v]**. All of it attached housing; detached unchanged. Robust to a 4× control-area trend. |
| São Paulo 2016 | Spatial RD at block boundaries | Multifamily permits ~2× per +1 FAR; effect begins after ~1 yr and doubles by yr 3; **no single-family effect**; little displacement |
| Zurich | Staggered DiD (Sun–Abraham) | +7–9% units within 5–10 yrs; only where zoning bound and rents were high |
| NYC | DiD with a 1,000-ft boundary buffer | +4% units after 7 yrs; significant after 2–3 yrs **[?]** venue |
| Portland RIP (2021) | Descriptive monitoring | 1,400+ ADU and middle-housing units, Aug 2021–Jun 2024; ~4 middle units per 1,000 lots/yr (R2.5), ~2 (R5), across ~148k single-dwelling lots **[v]** |
| Oregon HB 2001 (45 cities) | Descriptive | Middle housing 8% → 11% of permits; Portland 26% by year 3; many cities ≈ 0 |
| Spokane (2022–23) | Descriptive | Middle housing incl. ADUs 3–4% → ~20% of units |
| Minneapolis 2040 | Descriptive + synthetic control on prices | **~1% of 2017–22 units were in 2–4-unit buildings**. Floor-area limits bound, and price effects are attributed to demand, not supply. |
| Houston lot-size reform | Descriptive + DiD on land values | ~0.5% of SF parcels converted over ~14 yrs (≈0.04%/yr **[d]**); land values ~−9% |
| California SB 9 | Descriptive | 266 projects out of 6.1M eligible parcels by end-2023 (≈0.002%/yr **[d]**) |

**Lessons:**

- Density and floor-area limits are the binding lever, not "use" alone (Kulka et al.; Portland vs Minneapolis).
- Ownership frictions kill uptake: lot splits, owner-occupancy rules, and utility/lot-split fees of $30–100k (SB 9).
- The Handbook's "setbacks and coverage don't constrain" assumption removes one binding constraint. Lotline should therefore land above SB 9 and Minneapolis but well below pro-forma capacity.

**Calibration range (US):** ~**0.02%–0.2%** of eligible SF lots redevelop per year, with ~3–4 units per project. Treat Auckland as the upper bound.

### 3b. ADUs (one ADU per SF parcel, ≥600 sq ft, no parking)

| Place | Change | Implied annual rate on SF parcels **[d]** |
|---|---|---|
| California (2016 → 2019 → 2022) | ~1k → 15.6k → ~24k permits/yr (~19% of all permits by 2022) | ~0.01% → ~0.2% → ~0.3% (on ~8M SF homes **[?]**) |
| LA County 2013–19 | 1.5% of parcels added an ADU over 7 yrs; 117 → 2,316 permits in 2016→17 (from the Thomaz working paper; not in the published abstract **[?]**) | ~0.4%/yr post-law |
| Seattle 2019 reform (parking and owner-occupancy rules removed) | ~263/yr → ~1,000/yr (2022–23) | ~0.7% (~135k lots) |
| Portland 2010 SDC waiver ($7–12k) | 25 (2009) → 472 (2018) → 636 (2019) | ~0.3–0.4% at peak |

- **Suggested parameters:** baseline 0.01–0.05%/yr. Post-reform steady state **0.2% low / 0.4% central / 0.8% high** per year. Logistic ramp reaching steady state by years 3–4.
- **Net-new haircut:** owner surveys find a wide range. Portland DEQ 2014: ~80% long-term residences. UCLA 2020 (LA): 76% residences. CCI 2021 (California, n=694): 32% rented to non-family plus 16% housing family for free (~48%), with 8% short-term rental, 16% office/guest and 28% vacant/other. Use **~50–80%** as the net-new-housing share (corrected 2026-09-30 after checking the CCI report).
- **Formalization vs new construction:** San Jose satellite imagery found ~78% of detached ADU construction was *unpermitted* (Jo et al. 2024, JAPA). Part of any post-reform permit jump is legalization of existing units.
- **BPS measurement:** form C-404 asks only for *new-structure* ADUs, so garage and interior conversions may never appear. This matters directly if permits are our outcome metric.
- **Gap:** there is no peer-reviewed DiD or synthetic-control study of recent statewide ADU laws (OR, WA, MT, etc.). This is an opening for Lotline's backtest.

### 3c. Development fees (−50% of $50k/unit)

- **Effect on quantity (mostly null):**
  - Mayer & Somerville (2000, 44 metros): fees had little effect; **delay** mattered (a 1-SD longer approval delay, ~2–3 months ≈ −20–25% permits).
  - Campbell & Alm (2006, FL): not significant.
  - Burge & Ihlanfeldt (2006, FL, two papers): non-water/sewer fees *increased* some construction (fees buy approvals and infrastructure); water/sewer fees reduced it.
  - Florida's 2009–10 fee suspensions: no permit difference (consultant study, during the bust).
  - Skidmore & Peddle (1998): −25–30% from imposing a fee. This is an outlier upper bound **[?]**.
- **Incidence (who benefits) is well estimated:**
  - Ihlanfeldt & Shaughnessy (2004): $1 of fee → +$1.60 home price and −$1.00 land price.
  - Dresch & Sheffrin (1997): passed forward ~$1.88 per $1 in strong submarkets; ~75% absorbed in weak ones.
  - Yinger (1998): about ¼ of the burden falls on landowners (theory).
- **Recent work:**
  - Soltas & Gruber (2026): in LA, permit fees are ~1.2% of land value, while process costs dominate.
  - Terner "Making It Pencil" (2023): in LA, only a combined package ($10k fees + 0.25 parking + 25% density bonus) made the prototype viable (return on cost 5.12% → 5.71%). The report does not isolate a fee-only effect.
- **The $50k benchmark is high:** typical US single-family fees are ~$15–30k (NAHB 2021; FL TaxWatch 2023). Coastal California runs $12k–157k (Terner 2018). A $25k cut is outside the range most studies observed.
- **Transparent conversion (fee agent's proposal; treat parameters as priors):**

  `%ΔPermits = ε × (1 − λ_land) × (ΔFee / TDC) × ramp(t)`

  | Parameter | Range | Central |
  |---|---|---|
  | ε (elasticity) | 0.5–3 | 1.5 |
  | λ_land (share captured by landowners) | 0.25–0.75+ | 0.5 |
  | ΔFee / TDC | ≈5–7% SF, 7–12% small MF, 10–15% ADU | — |

  - Rough 5-year ranges: SF **0 to +12%**, 2–6 units **0 to +18%**, ADUs **+5 to +40%**.
  - **Show the zero low case explicitly.**
  - Better where parcel data exist: apply the $25k to each parcel's RLV and count threshold crossings.
- **Revenue toggle:** fees fund infrastructure. Add a switch for "revenue replaced" vs "not replaced". Without replacement, sewer and water capacity or anti-growth backlash can offset the gain.

---

## 4. Handling uncertainty and sparse data

- **Monte Carlo** over documented parameter distributions (hazard, elasticity, land capture, ramp, completion lag, net-new share). Report P10/P50/P90. This satisfies the "never a single number" rule (S6).
- **Global sensitivity:** Sobol indices, Morris screening, or tornado charts for the plain-language view. SALib implements Sobol and Morris (MIT license **[?]**, verify for T8). This feeds the Policy Insight criterion: "which assumptions matter most".
- **Hierarchical Bayes / partial pooling:** place → county → state → national prior. Small or sparse jurisdictions borrow strength from similar ones, which directly serves the sparse-data bonus.
  - For noisy place-level permit baselines: Fay–Herriot small-area estimation (1979, *JASA*).
  - PyMC is Apache-2.0.
- **Transportability:** Pearl & Bareinboim (2014). Transfer effects from Portland, Seattle or Auckland to our state by reweighting on covariates that change the effect: price-to-cost ratio (MPPC regime), lot-size distribution, SF parcel share, and whether density limits bind.
- **Backtesting:** predict known reforms from pre-reform data and report how often the P10–P90 band contained the observed value.
  - Portland 2021–24
  - Oregon HB 2001 cities
  - SB 9
  - California ADUs 2017–21
  - Seattle 2019
  - Minneapolis 2–4-unit share
  - Auckland

  This is the strongest possible evidence for "Methodological Soundness" and "Tests prove the method".

---

## 5. Pitfalls to design around

1. **Displacement and spillovers (SUTVA).** Upzoning shifts construction between places, so statewide totals must not simply add up local effects. Make within-state reallocation a parameter (e.g. 0–50%).
2. **Scenario overlap.** ADU and Missing Middle compete for the same parcels (SB 9 applications lost out to ADUs). Combined runs need one parcel allocation step, not additive effects.
3. **Anticipation.** Auckland's plan was notified 3 years before it took effect. Use anticipation windows in any backtest.
4. **Market cycles.** Don't anchor the baseline on the 2021–22 boom or the 2023 rate shock. Use multi-year averages or detrend with metro series.
5. **Measurement.** Permits are not completions: multifamily takes ~18–22 months to complete, and ~84–90% of consents get built. BPS undercounts ADUs. Stacy et al. used USPS addresses. State the outcome definition exactly (S4).
6. **Supply vs demand.** Falling rents don't prove new supply (Minneapolis). Model production directly.
7. **Data licensing.** Regrid's academic terms are non-commercial, which may conflict with T8/T11. Prefer open state parcel layers behind an adapter. The National Zoning Atlas license is unclear **[?]**.

---

## 6. Data sources used in this literature

| Need | Source | Notes |
|---|---|---|
| Outcome (permits) | Census Building Permits Survey | Place/county/state, 1/2/3–4/5+ units; annual counts are complete (with imputation); no ADU flag |
| Lags | Census Survey of Construction | Permit → start → completion times |
| Stock / context | ACS | Units in structure, tenure, rents |
| Parcels | State open parcel layers; county assessor rolls | Land use, lot area, building sq ft, year built, assessed value |
| Zoning | National Zoning Atlas; local GIS | Which districts allow 2/3/4+ units and ADUs; minimum lot size |
| Regulation covariate | Wharton WRLURI 2018 | For reweighting and pooling |
| Prices / costs | FHFA HPI (public), Zillow ZHVI/ZORI (terms), BLS PPI | CoStar and RSMeans are proprietary: cite them only as parameter sources |
| Elasticities | Saiz (MIT), Baum-Snow & Han (Dataverse) | Tract and metro level |
| ADU counts | CA HCD Annual Progress Reports; city open data (Portland BDS, Seattle OPCD, LADBS) | Backtest targets |

---

## 7. Open verification list
- Saiz average elasticity (1.75); Green–Malpezzi–Mayo range; Topel–Rosen flow elasticities.
- Skidmore & Peddle magnitude (secondary source only); Burge–Ihlanfeldt price-tier numbers.
- Magnitudes in Kulka–Sood–Chiumenti and Kuhlmann (2021); Stacy et al. subgroup figures.
- Liao NYC paper: publication venue.
- Arlington EHO outcomes (the report could not be fetched).
- Auckland Council's primary capacity report (the 12% feasible figure is from a secondary source).
- Licenses for SALib, UrbanSim and the National Zoning Atlas.
- SF parcel denominators used in the ADU rate calculations (CA ~8M, City of LA ~500k, Vancouver ~70k).
- California SB 13 (2019) is the ADU impact-fee exemption for units under 750 sq ft, not AB 68.

## Key sources (selected)
- Greenaway-McGrevy & Phillips 2023, *JUE*: https://cowles.yale.edu/sites/default/files/2024-02/p1863.pdf
- Greenaway-McGrevy 2026, *Economic Modelling*: https://ideas.repec.org/a/eee/ecmode/v160y2026ics0264999326001215.html
- Anagol, Ferreira & Rexer 2026, *AEJ: Policy*: https://www.aeaweb.org/articles?id=10.1257%2Fpol.20230542
- Büchler & Lutz 2024, *JUE*: https://www.sciencedirect.com/science/article/pii/S0094119024000597
- Kulka, Sood & Chiumenti 2022 (Boston Fed): https://www.bostonfed.org/publications/research-department-working-paper/2022/how-to-increase-housing-affordability-understanding-local-deterrents-to-building-multifamily-housing.aspx
- Stacy et al. 2023: https://www.urban.org/sites/default/files/2023-03/Land-Use%20Reforms%20and%20Housing%20Costs.pdf
- Portland middle housing monitoring report, Jan 2025: https://www.sightline.org/wp-content/uploads/2025/02/Monitoring-reports-Middle-Housing-in-the-Single-Dwelling-Zones-Progress-Report-2018-2024-January-2025.pdf
- Sightline on Oregon HB 2001, 2025: https://www.sightline.org/2025/06/04/oregons-zoning-reforms-are-working-but-they-need-some-upgrades/
- Terner SB 9 feasibility, 2021: https://ternercenter.berkeley.edu/wp-content/uploads/2021/07/SB-9-Brief-July-2021-Final.pdf
- "Missing No Longer?" SB 9 uptake, 2024: https://www.aducalifornia.org/wp-content/uploads/2024/12/Missing-No-Longer.pdf
- Pew on Minneapolis, 2024: https://www.pew.org/en/research-and-analysis/articles/2024/01/04/minneapolis-land-use-reforms-offer-a-blueprint-for-housing-affordability
- Marantz, Elmendorf & Kim 2023, *Cityscape*: https://www.huduser.gov/portal/periodicals/cityscape/vol25num2/ch5.pdf
- Chapple et al. 2020, *Reaching California's ADU Potential*: https://ternercenter.berkeley.edu/wp-content/uploads/pdfs/Reaching_Californias_ADU_Potential_2020.pdf
- Seattle ADU Annual Report 2023: https://www.seattle.gov/documents/Departments/OPCD/OngoingInitiatives/EncouragingBackyardCottages/OPCD-ADU-Report-2023.pdf
- Jo et al. 2024, unpermitted ADUs: https://law.stanford.edu/wp-content/uploads/2024/07/2024-07-16_Not-Officially-in-My-Backyard.pdf
- Mayer & Somerville 2000: https://realestate.wharton.upenn.edu/wp-content/uploads/2017/03/331.pdf
- Ihlanfeldt & Shaughnessy 2004, *RSUE*: https://www.sciencedirect.com/science/article/abs/pii/S0166046204000158
- Burge & Ihlanfeldt 2006, *JUE*: https://www.sciencedirect.com/science/article/abs/pii/S0094119006000222
- Terner "It All Adds Up", 2018: https://ternercenter.berkeley.edu/wp-content/uploads/pdfs/Development_Fees_Report_Final_2.pdf
- Terner "Making It Pencil", 2023: https://ternercenter.berkeley.edu/wp-content/uploads/2023/12/Development-Math-2023.pdf
- Soltas & Gruber 2026: https://evansoltas.com/papers/Permitting_SoltasGruber2026.pdf
- Baum-Snow & Han 2024, *JPE*: https://www.journals.uchicago.edu/doi/abs/10.1086/728110
- Glaeser & Gyourko 2018, *JEP*: https://www.aeaweb.org/articles?id=10.1257%2Fjep.32.1.3
- Borusyak, Jaravel & Spiess 2024: https://academic.oup.com/restud/article/91/6/3253/7601390
- Arkhangelsky et al. 2021, synthetic DiD: https://www.aeaweb.org/articles?id=10.1257%2Faer.20190159
- Rambachan & Roth 2023: https://academic.oup.com/restud/article-abstract/90/5/2555/7039335
- Pearl & Bareinboim 2014: https://projecteuclid.org/journals/statistical-science/volume-29/issue-4/External-Validity-From-Do-Calculus-to-Transportability-Across-Populations/10.1214/14-STS486.full
