# Lotline: Target-state reassessment against the model design (v0.1, 2026-10-04)

**Status:** decision input. **Update (later on 2026-10-04):**
- The Minnesota scouting pass is done; see `research/lotline-mn-scouting.md`.
- 4 of 5 deciding facts check out, two of them only partially. MN re-scores to **37**.
- Ben chose to develop and test on the **top four states (MN, TX, NC, OH)**, starting with MN. Roles are in the scouting doc §5.
- Still open: which state is the official benchmark. Re-scores candidate states against what the causal diagrams and validation plan now require, instead of the general data-readiness criteria used in the Housing Data Readiness Ranking (v3) and `research/lotline-data-availability.md`.
**Why:** NC became the working assumption because it ranked #2 and we discussed it most. The model design has since changed what matters (in-state reforms with type-flagged permits, within-city comparisons, a blind forward test, parcel history for the mechanism test).

---

## 1. What the model now needs from the target state

| # | Requirement | Why (validation plan step) | Weight |
|---|---|---|---|
| 1 | **Headroom** in all three scenarios over 2027–31 | Baseline must not already contain the reform, or scenario effects are ~0 | 3 |
| 2 | **In-state reforms ≥3 years old** with permit data that identify ADUs / 2–6 unit buildings | V3 causal estimates, V4 backtests | 3 |
| 3 | **Within-city contrast** (zoning map + parcels in a reformed city) | Strongest design: removes rates, demand, politics | 2 |
| 4 | **A 2–3 year-old reform** for a blind forward test | V5 | 1 |
| 5 | **Statewide parcel attributes** for the eligible-parcel denominator | Statewide run, tier 1 coverage | 2 |
| 6 | **Parcel history + sale prices** in-state | V2 mechanism test (can fall back to Portland Metro) | 2 |
| 7 | **Fee evidence**: real fee data and/or an exogenous fee shock | V6 | 1 |
| 8 | **Spread of data tiers** (rich metros, sparse rural areas) | Sparse-data bonus (Rules §8) | 1 |

Gate (not scored): open licensing (R10). All candidates below pass with runtime fetching.

---

## 2. Scores (0–3, weighted; maximum 45)

| State | 1 Headroom | 2 Reforms | 3 Contrast | 4 Forward | 5 Parcels | 6 History+prices | 7 Fees | 8 Tiers | **Weighted** | Verified? |
|---|---|---|---|---|---|---|---|---|---|---|
| **MN** | 3 | 2 | 2 | 3 | 2 | 2 | 2 | 3 | **35** | **No** (desk + 2026-10-04 spot checks) |
| **TX** | 3 | 2 | 3 | 2 | 2 | 1 | 2 | 3 | **34** | Yes (LB-013) |
| **NC** | 2 | 2 | 3 | 3 | 2 | 1 | 2 | 3 | **32** | Yes |
| OH | 3 | 1 | 2 | 2 | 2 | 2 | 1 | 3 | 30 | Yes |
| WI | 3 | 1 | 1 | 1 | 2 | 2 | 3 | 3 | 29 | Yes |
| UT | 3 | 1 | 1 | 1 | 3 | 2 | 1 | 2 | 28 | Yes |
| FL | 3 | 0 | 0 | 0 | 3 | 3 | 3 | 3 | 27 | No |
| CT | 2 | 1 | 1 | 1 | 3 | 2 | 1 | 1 | 24 | Yes |

Out as targets (no headroom; use as evidence sources): **CA, OR, WA, VT**. Also out: **MA** (statewide ADUs since Feb 2025; reforms too recent), **CO** (no MM reform; recent ADU law), **MD, VA, NJ** (reforms too recent, litigated or absent).

**The top three are within 3 points, and the scores are judgment calls.** No state is clearly better than NC on paper. The difference is in what kind of risk each carries.

---

## 3. The three contenders

### North Carolina (32): known gaps, strong design fit
- **For:**
  - three reforms of different vintages (Durham 2019, Raleigh 2020/2021, Charlotte 2023);
  - two clean within-city contrasts (Raleigh R-1, Durham tiers);
  - the *Carthage* fee shock;
  - 100 counties;
  - disclosure state.
- **Against (all verified):**
  - OneMap parcels are current-only with county-native codes;
  - Raleigh's unit field is empty from 2024;
  - Durham permits may be stale since Nov 2024;
  - Mecklenburg permits have no unit counts;
  - no open statewide zoning.
- **Newly weighed:** S.L. 2026-59 requires ADUs in non-coastal cities over 50,000 from Jan 2027. The ADU scenario's headroom in NC's biggest cities largely disappears inside our 5-year window, so the statewide ADU effect will come mostly from smaller places.

### Texas (34): best permit data, no sale prices
- **For:**
  - Austin permits 1970–2026 with an ADU class, units, completions and demolitions, plus Travis appraisal exports 2022–26;
  - Austin HOME (Dec 2023 / May 2024) as the MM test;
  - Houston's lot-size reforms (1998, 2013) as a long-run townhouse case with a published inside/outside-loop design (E017);
  - San Antonio ADUs (2023) as a forward test;
  - 254 counties;
  - no statewide MM or ADU mandate on single-family lots.
- **Against:**
  - non-disclosure state (pro forma must use appraisal values);
  - StratMap parcels unstandardized, with sparse year built;
  - Houston has no zoning (deed restrictions instead), so "parcels restricted to single-family use" needs a definition there;
  - Austin HOME is only ~2.5 years old.

### Minnesota (35): the one new candidate, not yet verified
Minnesota was outside the 13-state verification pass.

- **For:**
  - **Statewide MM and ADU bills failed in 2024, 2025 and 2026**, so headroom is high outside Minneapolis and St. Paul.
  - **Minneapolis 2040** (2020, ~6 years) is the best-known *low-uptake* missing-middle case (floor-area limits bound; E019–E021). Predicting a small effect correctly is a stronger test than predicting a big one.
  - **The 2040 plan was enjoined** on 2022-06-17 and reinstated 2024-05-13. The city had to revert to pre-2040 zoning in between, giving an on–off–on natural experiment. *Exactly which rules reverted for 2–3 unit buildings needs checking.*
  - **St. Paul** ADUs (2016/2018, ~8 years) for ADU backtests; St. Paul 1–6 units (Nov 2023) as a blind forward test; Rochester ADUs (2023).
  - **Twin Cities 7-county parcels** are free (counties' policy: "without fee or licensage"), published quarterly, with archives back to at least 2003 (BTAA geoportal).
  - **Fee shock:** *Harstad v. Woodbury* (Minn. Sup. Ct. 2018) barred statutory cities from charging fees for future road improvements, a court-driven fee cut like NC's *Carthage*. It applies to statutory cities, not charter cities, which gives a built-in comparison.
  - **Clear data tiers:** a rich metro next to sparse Greater Minnesota (statewide parcels are opt-in by county).
- **Against / unknown:**
  - **Sale prices:** eCRV bulk download is restricted to local government agencies, so prices depend on what the metro parcel layer carries.
  - **Parcel fields:** whether the regional parcels include year built, sale value and units is to confirm.
  - **Permits:** Minneapolis and St. Paul permit fields (unit counts, ADU identification) are unverified. The Met Council permit survey is city-level with demolitions, but an ADU breakdown was not confirmed.
  - **No in-city ineligible group in Minneapolis:** 2040 rezoned every residential lot. The contrast has to come from the city border (Kuhlmann E018 did this for prices) or from the injunction timing.
  - **Greater Minnesota parcel coverage** outside opt-in counties is unknown.

---

## 4. Recommendation

1. **Don't switch on paper.** Minnesota's lead is three points of judgment on unverified data. NC's desk scores dropped noticeably once datasets were opened (data-availability §0), and Minnesota could too.
2. **Run a one-day Minnesota scouting pass** on the five facts that decide it:
   - regional parcel fields and archive years;
   - Minneapolis and St. Paul permit fields (units, ADU flag, dates, parcel ID);
   - what reverted during the 2040 injunction;
   - whether county parcel layers carry sale prices;
   - Greater Minnesota parcel coverage.
3. **Decision rule:**
   - If ≥4 of the 5 check out, Minnesota becomes the target. Its headroom and the Minneapolis low-uptake test make for a stronger story.
   - Otherwise stay with NC, which has the better within-city designs, and take Texas as the second-state stress test (V7). Austin's permit data is the best for that.
4. **Whatever the target, run the V2 mechanism test in a parcel-rich metro** (Portland Metro or the Twin Cities). Neither NC nor TX has in-state parcel history with prices.

---

## Sources (spot checks, 2026-10-04)
- [Housing Data Readiness Ranking v3](https://claude.ai/artifact/PUQszFy2CYHvr2uNHTGRna) (all 50 states, desk scores and policy notes)
- `research/lotline-data-availability.md`, `research/lotline-data-summary.csv`, `research/lotline-data-catalog.csv` (13 verified states)
- [MetroGIS parcel data](https://metrogis.org/how-do-i-get/parcel-data/) · [MetroGIS Regional Parcel Dataset, Year End 2003 (BTAA Geoportal)](https://geo.btaa.org/resources/621f9c48-d30f-4e03-a484-8ced8d66ebce) · [Metropolitan 7-County Parcel Polygons](https://gis.data.mn.gov/content/136b28bd0d874076b702ca55b9aafffc)
- [Met Council residential development data](https://metrocouncil.org/Data-and-Maps/Community-Development-Research/Housing/Residential-Development.aspx)
- [MN Revenue eCRV Download Service](https://www.revenue.state.mn.us/guide/download-service)
- [Judge axes Minneapolis 2040 Plan (Minnesota Lawyer, 2022-06-17)](https://minnlawyer.com/2022/06/17/judge-axes-minneapolis-2040-plan/) · [CNU: Minneapolis zoning reform put on ice](https://www.cnu.org/publicsquare/2022/06/30/minneapolis-zoning-reform-put-ice) · [MPR: Appeals court lifts injunction (2024-05-13)](https://www.mprnews.org/story/2024/05/13/appeals-court-lifts-injunction-on-minneapolis-2040-plan)
- [League of Minnesota Cities: Harstad v. Woodbury](https://www.lmc.org/page/1/Harstad-Woodbury.jsp?ssl=true) · [Harstad v. City of Woodbury (2018)](https://caselaw.findlaw.com/court/mn-supreme-court/1947518.html)
