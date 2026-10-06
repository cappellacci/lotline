# Lotline: Minnesota data scouting (v1, 2026-10-04)

**Status:** scouting pass complete. It answers the five deciding facts in `research/lotline-state-reassessment.md` §4 and feeds the four-state plan (§5 below).
**Method:**
- Two parallel research agents opened live dataset pages, ArcGIS REST metadata, court opinions and statutes.
- Claude re-checked the two claims that matter most: the Met Council permit metadata (ADU and DTQ categories, public domain) and the MnGeo opt-in parcel item (59 counties, licence "None").
- Dataset rows are in `research/lotline-data-catalog-mn.csv`, same columns as the main catalog.

---

## 0. Bottom line

- **4 of the 5 deciding facts check out**, two of them only partially. The court freeze of the 2040 plan is the one that doesn't hold up as a test.
- **Minnesota passes the decision rule**, re-scored **37 of 45**, up from 35 (§3).
- **The biggest find wasn't on the list.** The Metropolitan Council publishes a **permit-level residential dataset for the 7-county metro, 2009–2024**, public domain. Each record has PIN, units, removals, and a housing type of **SFD / ADU / TH / DTQ (duplex–quad) / MF5**.
  - Outside California's APR data, it is the only multi-jurisdiction source we have found that flags ADUs and small multifamily permit by permit.
  - It covers ~180 cities, which adopted ADU ordinances at different times. That makes a **staggered ADU study across many suburbs** possible, a design we couldn't do anywhere else.
- **Headroom confirmed:**
  - No statewide ADU or middle-housing mandate through the 2026 session.
  - 2024 missing-middle bill died. 2025 "Yes to Homes" bills died. The 2026 Starter Homes Act failed 5–7 in committee.
  - Only an HOA-requirement ban passed (2026).

---

## 1. The five deciding facts

| # | Fact | Finding | Verdict |
|---|---|---|---|
| 1 | **Regional parcel fields and archives** | Met Council 7-county parcels: YEAR_BUILT, NUM_UNITS, DWELL_TYPE, USECLASS1–4, EMV land/building, HOMESTEAD, SALE_DATE, SALE_VALUE. Public domain. Quarterly. **Open year-end archives 2021–2025** via REST. Services for 2002–2020 exist but are token-locked or not running. Schema changed 1 Jan 2019. **Hennepin leaves units and dwelling type blank** in the regional layer; Hennepin's own layer has build year and property type. | **Pass (partial):** pre-2021 history needs a request to Met Council or BTAA download |
| 2 | **Permits identify ADUs and 2–6 unit buildings** | **Met Council permits 2009–2024 flag ADU and DTQ by PIN** across the metro (fully passes). Minneapolis CCS permits (CC0): unit counts new/removed, parcel ID, issue and completion dates, but no ADU flag and a rolling window from Dec 2016. St. Paul permits: no unit counts, no ADU flag, rolling 10-year window, looks stale since mid-2025. | **Pass** (via Met Council). 5–6 unit buildings fall in MF5, same limit as BPS. |
| 3 | **What reverted during the 2040 injunction** | June 2022 injunction, vacated Dec 2022. **Amended injunction Sept 2023:** the city had to restore the status quo of 4 Dec 2018 (2030 Plan) within 60 days, effective about **4 Nov 2023**. **Reversed 13 May 2024.** 2024 law (HF 5247) exempted comp plans from environmental-review suits. Whether the 2020 triplex rule was suspended for new applications is **not confirmed**. | **Fail as a test:** the effective window is ~6 months with unclear scope |
| 4 | **Sale prices** | Last sale price and date per parcel are open in the regional layer (Hennepin: 390k of 447k parcels; Ramsey: 124k of 172k) and in Hennepin's and Ramsey's own layers. **No open transaction history:** eCRV bulk download is limited to local government agencies, and Revenue's sales-ratio reports are aggregate. Stacking 2021–25 year-end vintages gives partial history. | **Pass (partial)**, better than NC (no price in statewide parcels) and TX (non-disclosure) |
| 5 | **Greater Minnesota parcel coverage** | MnGeo opt-in compilation: **59 of 87 counties**, same standard schema, licence "None", quarterly, ~2.7M records, CSV/GDB/GeoJSON export. Attributes are sparse outside the metro (year built on ~43% of records, sale value on ~36%), and there are no historical vintages. Missing counties include Blue Earth, Kandiyohi, Goodhue, Freeborn, Nicollet, Beltrami, Pine. | **Pass (partial).** It also gives three data tiers in one state: rich metro (tier 1), thin opt-in counties (tier 2), no parcels (tier 3). |

**A quick look at the injunction window** (Minneapolis CCS permits; summary counts from a web fetch, **to recompute in code**): new duplex and 3–4 unit permits run at roughly 15–30 a year throughout 2016–2025. There is no visible collapse in the injunction window. This matches the Minneapolis Fed's count of 362 units in 2–4 unit buildings for 2019–2025. **Minneapolis's missing-middle response was small before, during and after.** That is the low-uptake case the model needs to predict.

---

## 2. Other findings

- **Zoning:**
  - Minneapolis primary zoning and Built Form layers are **CC0**. St. Paul principal zoning is public domain, but the canonical service is unclear.
  - No regional zoning layer. Met Council's Planned Land Use (comp-plan designations with min/max density, public domain) can stand in for SF-only identification outside the two cities.
  - National Zoning Atlas Minnesota is in progress (unusable anyway because of its licence).
- **Fees:**
  - **Weaker than hoped.** *Harstad v. Woodbury* (2018) barred statutory cities from charging fees for future roads at subdivision approval (Woodbury: $20,230/acre). Street-impact-fee bills in 2023 and 2025 failed. We found no list of other cities that charged such fees, so the natural experiment is thin.
  - **Real fee levels exist.** Minn. Stat. §326B.145 requires cities to report construction and development fees and unit counts every year. Reports are archived as PDFs at the Legislative Reference Library (e.g., Plymouth 2016: ~$7,000 in permit fees per new single-family home).
  - Regional sewer availability charge: $2,485 per unit (2026–27).
  - Fee score lowered to 1.
- **Uptake evidence from the data:**
  - Minneapolis ADUs: 232 total through 2022, falling from 47 in 2016 to 13 in 2022 (TCB, 2023).
  - St. Paul's 2023 reform: 76 units in 2–4 unit buildings in 2024 (18% of permits) and 47 in 2025 (Minneapolis Fed, 2026).
  - About 300 metro ADUs in 2016–2024 (Star Tribune, citing Met Council data).
  - **Minnesota is a low-uptake state for both reforms.** That is valuable as a test, and it means the statewide effects we report will probably be small.
- **Do now:** Minneapolis and St. Paul permit layers are rolling windows, so history disappears as they roll. A snapshot script should run as soon as coding opens (14 Oct). Until then, a manual CSV export is a cheap safeguard.

---

## 3. Updated Minnesota score

| Requirement (weight) | Before | After | Why |
|---|---|---|---|
| 1 Headroom (3) | 3 | 3 | Confirmed: no statewide mandate through 2026 |
| 2 In-state reforms with flagged data (3) | 2 | **3** | Met Council ADU/DTQ permits 2009–24, plus Minneapolis 2020, St. Paul ADU 2016/2018 and 2023 |
| 3 Within-city contrast (2) | 2 | 2 | No ineligible lots inside Minneapolis. St. Paul H-districts vs others and the Minneapolis border remain options. |
| 4 Blind forward test (1) | 3 | 3 | St. Paul 2023. 2025 Met Council data due ~mid-2026, so already out or close. |
| 5 Statewide parcels (2) | 2 | 2 | Metro strong; 59/87 counties thin |
| 6 History + prices (2) | 2 | 2 | 2021–25 vintages; last sale only |
| 7 Fees (1) | 2 | **1** | Harstad thin; fee data in PDFs |
| 8 Data tiers (1) | 3 | 3 | All three tiers inside one state |
| **Weighted (max 45)** | 35 | **37** | |

---

## 4. Risks to carry

1. **Low uptake everywhere.** The model must avoid predicting "zero" just because the calibration data are near zero. Out-of-state comparables (Portland, Seattle, Austin) are still needed for the upper range.
2. **Pre-2021 parcel vintages** need a request to Met Council GIS. Without them, the mechanism test (V2) can only use 2021–2025.
3. **Hennepin units blank** in the regional layer. Use Hennepin County's own parcel layer for Minneapolis.
4. **Met Council permits stop at 2024**, with 2025 due mid-2026. Check whether 2025 is already posted.
5. **Greater Minnesota has no in-state reform evidence.** Duluth and Rochester fall outside the Met Council data and weren't confirmed.

---

## 5. Four-state plan (Ben, 2026-10-04: "test the top 4 states; sparse data is the name of the game")

The Rules ask for results "added up to a statewide total for one chosen state" (HANDOFF S5). So one state is the **official benchmark state** and the other three are **portability runs** using the same code and different data tiers. Proposed roles:

| State | Role | What it proves | Ladder steps |
|---|---|---|---|
| **MN** | Primary development state; leading candidate for official benchmark | Full ladder; staggered ADU design across ~180 metro cities; low-uptake prediction | V0–V7 |
| **NC** | Second full in-state validation | Within-city contrasts (Raleigh R-1, Durham tiers); Charlotte blind test; *Carthage* fee shock | V0–V6 |
| **TX** | Best permit data, no sale prices | Austin HOME test; the "no prices" path (appraisal values only) | V0, V1, V3/V4 (Austin), statewide run |
| **OH** | Sparsest evidence | Pure transport: no mature in-state reform, so the tool must lean on the mechanism and out-of-state evidence | V0, V1, statewide run with low-confidence flags |

- **Budget:** one national Census BPS adapter covers all four. The per-state cost is parcel and local-permit adapters.
- **Phasing:**
  - MN full: weeks 1–5.
  - NC: weeks 3–6.
  - TX and OH, lighter: weeks 6–7.
- **Open decision:** which state is the official benchmark. **Recommendation: MN.** It has the most headroom (NC loses much of its ADU headroom in big cities from Jan 2027), the richest multi-city outcome data, and all three data tiers within one state.

---

## Sources
- Met Council residential building permits (metadata, public domain): https://metrocouncil.org/Data-and-Maps/Research-and-Data/Metadata/Residential-Building-Permits.aspx · download: https://gisdata.mn.gov/dataset/us-mn-state-metc-econ-residential-building-permts
- Met Council parcels: https://arcgis.metc.state.mn.us/data1/rest/services/parcels?f=pjson · item licence: https://www.arcgis.com/sharing/rest/content/items/136b28bd0d874076b702ca55b9aafffc?f=pjson · https://metrogis.org/how-do-i-get/parcel-data/
- MnGeo opt-in parcels (59 counties): https://www.arcgis.com/sharing/rest/content/items/69148d3959194a05a23964cc60f6517b?f=pjson
- Hennepin County parcels metadata: https://www.arcgis.com/sharing/rest/content/items/7975aabf6e1e42998a40a4b085ffefdf/info/metadata/metadata.xml?format=default&output=html · Ramsey parcel points: https://gis.ramseycountymn.gov/server/rest/services/Cadastral/CAD_AttributedParcelPoint_ViewOnly/FeatureServer/0?f=pjson
- eCRV download service (agencies only): https://www.revenue.state.mn.us/guide/download-service · sales ratio reports: https://www.revenue.state.mn.us/sales-ratio-reports
- Minneapolis CCS permits (CC0): https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/CCS_Permits/FeatureServer/0?f=pjson · St. Paul permits: https://services1.arcgis.com/9meaaHE3uiba0zr8/arcgis/rest/services/Building_Permits_/FeatureServer/0?f=pjson
- Minneapolis triplex amendment (eff. 2020-01-01): https://www2.minneapolismn.gov/business-services/planning-zoning/amendments/adopted-proposed/recently-adopted/residential-buildings-3-units-amendment
- 2040 litigation: Court of Appeals 2024 opinion https://law.justia.com/cases/minnesota/court-of-appeals/2024/a23-1382.html · https://bringmethenews.com/minnesota-news/minneapolis-sets-aside-2040-comprehensive-plan-after-judge-ruling-goes-into-effect · https://minnesotareformer.com/briefs/legislature-passes-law-protecting-minneapolis-2040-plan/
- Statewide bills: https://tcbmag.com/missing-middle-housing-bill-off-the-table-for-now/ · https://minnesotareformer.com/2025/05/05/a-last-ditch-effort-to-reform-minnesota-zoning-fails-in-senate-committee/ · https://www.moreneighbors.org/news-stories/2026-legislative-session-recap
- Fees: https://caselaw.findlaw.com/court/mn-supreme-court/1947518.html · https://www.revisor.mn.gov/statutes/cite/462.358 · §326B.145 reports, e.g. https://www.lrl.mn.gov/docs/2017/mandated/171039.pdf · SAC: https://metrocouncil.org/Wastewater-Water/Funding-Finance/Rates-Charges.aspx
- Uptake: https://www.minneapolisfed.org/article/2026/housing-policies-in-saint-paul-yield-mixed-results-data-and-developers-say · https://tcbmag.com/what-happened-to-the-push-for-accessory-dwelling-units/ · https://www.startribune.com/twin-cities-suburbs-accessory-dwelling-units/601438149
