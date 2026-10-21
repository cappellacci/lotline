# North Carolina data plan (thread 10, step 1)

*WS-NC, 2026-10-21. Status: **draft for Ben's approval.** Nothing heavy (large downloads, research beyond
targeted lookups) starts until Ben approves. Brief: `docs/build/handoffs/10-north-carolina-data-complete.md`.*

**Goal:** North Carolina can run end to end through the baseline forecast, the ADU scenario (D-025), the
missing-middle scenario (D-024), the fee scenario and the county and state totals (thread 9), for all 322 NC
jurisdictions. Every input is either real or a labelled fallback.

## 1. What exists today (checked 2026-10-21)

I checked `main` at `b0777eb` and the shared data directory (`~/lotline-data`). The brief's snapshot is right,
with the corrections and additions in bold.

| Input | What is there | Gap |
|---|---|---|
| Jurisdictions | 322 (222 places, 100 county remainders); tiers 54 / 32 / 236 (tier 1 / 2 / 3) | Wilmington, Hickory, Salisbury and Statesville are filed under their counties by BPS (D-020, D-021 `county_mix`). **Charlotte, Concord and Kannapolis are tier 3**: Charlotte because its pre-UDO layer has no land use, Concord and Kannapolis because Cabarrus sends no land-use code (100% unknown). |
| Parcels, OneMap | **1,633,685 parcels from the 10 largest counties** (vintage 2026); crosswalks for those 10 in `config/crosswalks/` | 90 counties have no crosswalk, so the adapter refuses them (`build()` raises on a county without one). |
| Parcels, Wake | Dec 2023 roll processed (427,566 parcels, 16 jurisdictions) | The copy in the data folder came from an automated download on 2026-10-19 (`services.wake.gov/realdata_extracts/…`). `services.wake.gov/robots.txt` disallows automated access, so **Ben's browser download and `lotline manifest register` are still needed** to replace it. |
| Parcels, Charlotte | Pre-UDO zoning layer (324,129 parcels, dated 2023-05-31) | No land use, year built or units. Ben's request to Mecklenburg for a pre-June-2023 roll is pending. |
| Eligible parcels | Rule 1.1. **79 jurisdictions counted from parcels, each for one year only** (13 Wake places: 2023; 66 OneMap places: 2026); **243 on the ACS fallback, 2010–2024.** 13 of 7,448 rows are rated `high` quality (unknown zoning counts as single-family only, which rates the rest `low`). | Rebuild after new counties load; check non-overlap again (D-020). **Parcel-counted places have no denominator history** (S13). |
| Permits | Raleigh 2000–2026 (177,473; 291 ADU, 972 two-unit, 246 three-or-four-unit) and Durham 2007–2026 (77,479; 392 ADU, 783 / 198) | Mecklenburg blocked (Cloudflare 403). **New: Greensboro has an open permit layer** (see S3). |
| ADU rules | 37 rows: 19 S.L. 2026-59 rows (2027-01-15) and 18 local rows for Raleigh, Durham (city and county), Charlotte, Greensboro and Wilmington | No dated history for most of the 40 largest places. |
| Missing-middle rules | 5 rows (Durham EHC, city and county 2019; Raleigh 2021 and 2022; Charlotte UDO 2023) | Other places: unknown. |
| Fees | `config/fees/nc.csv`: 11 rows, **all Raleigh, FY2026** | No other city; no history before FY2026. |
| Market, rates, costs | ACS, FHFA, FRED statewide; processed | — |
| Demand index | Processed `demand.parquet` exists locally | PR #187 not merged yet |
| Engines on `main` | Baseline, ADU scenario | Missing-middle (#188, #196), fee scenario (#189) and combine/aggregate (thread 9) are still in open PRs. |
| Holdout | Charlotte V5 (3712000; 37119 from 2023-06-01) | **Prediction frozen by Nov 17** (#45). |

`docs/data_availability.md`'s NC table is out of date: it still says NC is all on the ACS fallback. S11 fixes it.

## 2. What "end to end" needs

An end-to-end run already works with fallbacks: places with no parcels use the ACS denominator (D-017), places
with no rule rows draw a rule type (D-022), and in the fee scenario (#189, open) places with no coded water/sewer fee take the $50k national prior (D-034). So few
subtasks are *strictly* needed. A subtask is marked **E2E** if the run would break, or would print a result we
could not defend, without it; everything else is **accuracy**.

## 3. Subtasks

Costs are wall-clock time for me plus whether the work is token-heavy. "Automatable" means no broad web
searching: public APIs, data already in the repo, or official pages I can open directly.

| # | Subtask | Feeds | Source | Automatable? | Cost | Priority | Owner |
|---|---|---|---|---|---|---|---|
| S1 | **OneMap parcels for all 100 counties.** Pull each remaining county's distinct land-use codes and labels with ArcGIS statistics queries (no parcel download); write one shared keyword crosswalk for common labels plus a short per-county file for odd codes; set each county's tier and vacant rule in `nc_land_use_counties.csv`; then download the remaining ~4.0M parcels (OneMap holds 5,926,051 on 2026-10-21; ~1.5 GB raw, est. 3–5 h unattended). Add the counties to `parcel_sources` (default `onemap_parcels` already covers them). Apply the D-017 gate: counties with < 90% known land use stay on ACS. | Eligible parcels (ADU, MM), data tiers, D-021 zone/lot coverage, ranges | `onemap_parcels` adapter (exists) | Yes | Code lists: 2–3 h, moderate tokens (90 counties of labels). Download: 3–5 h unattended, low tokens. | Accuracy (high): moves about two-thirds of NC parcels from ACS to parcel counts | Me; **needs approval (large download)** |
| S2 | **Rebuild statewide eligible parcels** with non-overlap checks: each parcel in one jurisdiction; Wake roll and OneMap never both used for a place (`single_source`); local-only places (Charlotte, Concord, Huntersville …) subtracted from county remainders (D-020); totals vs ACS one-unit homes by county within a stated band; report what moved. | Every scenario's denominator | `lotline` build (exists) | Yes | 1–2 h, low tokens | **E2E** (after S1; also now, to confirm the current table) | Me |
| S3 | **Permits beyond Raleigh and Durham.** Catalog first: Greensboro (marked "no open dataset") does have one: `gis.greensboro-nc.gov/…/OpenData_HRES_DS/MapServer/2`, 125,092 permits, issued 1990-07-30 to 2026-10-20, with `NumUnits`, `Zoning`, `OccupancyDesc`, `Description` (1,706 mention "accessory" or "ADU", which includes sheds). Adapter with ADU and 2–4 unit flags, leaving out owner names and addresses (it has `OwnerName`, `FullAddress`: excluded by field list). Fayetteville's layer is a dashboard of case types, not units; Asheville's 2018 service did not answer; Chapel Hill only 2013–2016. Others: one ArcGIS search each, then stop. | ADU effect estimation (D-025: Greensboro adopted 2024-04-16, a third NC event), baseline V0/V1, optional V5 Greensboro | ArcGIS REST | Yes (robots.txt on the host returns 404, i.e. no rules) | Greensboro adapter + tests: 3–4 h, moderate tokens; probes of 6 more cities: 30 min | Accuracy (high for D-025) | Me |
| S4 | **ADU rule histories, 40 largest places**: dated changes since 2010 (allowed, by right, owner occupancy, size cap, parking, detached). From batch-1 records and official city pages I can open directly; one fetch per place, no search sweeps. Everything else goes to `docs/research/ordinances/nc-adu-lookups-todo.csv` (Minnesota format), largest first. Confirmed rows go into `config/reforms/nc.csv` with the 1.7 citation fields; unread stays blank (D-022). | ADU scenario current rules (c), D-025 adoption dates, S.L. 2026-59 baseline | Batch-1 JSON, city code pages (Municode / American Legal often block bots) | Partly | 3–5 h, token-heavy if pages are long; capped at ~1 fetch per place | Accuracy (E2E runs on D-022 draws) | Me, then **Ben** for the todo CSV |
| S5 | **Missing-middle rule dates**, same 40 places: when 2–4 units became legal by right on single-family lots, if ever. Same method; `nc-mm-lookups-todo.csv` for the rest. Confirm Raleigh TC-5-20 effective date (the CSV has 2021-08-05, batch-1 says adopted 2021-07-06) and Durham EHC (2019-09-03 vs batch-1 "2019-10"). | MM scenario current rules, D-024 panel events | Same | Partly | 2–3 h (shared fetches with S4) | Accuracy | Me, then **Ben** |
| S6 | **Fees by city and year.** Raleigh fee guide history (FY2019–FY2026 PDFs on the city blob store, linked from batch-1 TC-3-19); Charlotte Water system development fees (input only, not an outcome, so the holdout does not apply); Durham fee schedule from batch-1; check whether any S.L. 2026-59 §49 disclosures are posted (the UNC SOG blog in the catalog). Thread 2's `config/fees` format. | Fee scenario (#189): local fee levels instead of the Handbook $50k for coded places | City PDFs | Partly (PDFs on official hosts) | 3–4 h, token-heavy (PDF tables) | Accuracy; **E2E only for the fee scenario's "real fees" variant** | Me |
| S7 | **Ben's manual items** (exact steps in §4): Wake browser download + register; the Mecklenburg request (pre-UDO roll and the blocked permit service). | V2 baseline (Raleigh), V5 | Ben | No | Ben: 15 min (Wake), one email (Mecklenburg) | Wake: **E2E** for a clean provenance record; Mecklenburg: V5 | **Ben** |
| S8 | **V5 Charlotte, what it needs before Nov 17** (see §5). | V5 frozen prediction | — | Partly | 2–3 h for data prep (the prediction itself belongs to WS-ENGINE) | **E2E for V5** | Me (data) + WS-ENGINE + **Ben's decision** |
| S9 | **County rows with cities inside** (Wilmington, Hickory, Salisbury, Statesville): make sure each county row's rule mix (D-021 `county_mix`) has rule rows for the city it contains. Wilmington has one; Hickory, Salisbury and Statesville go into S4. | ADU and MM scenarios for 4 county rows | S4 | Yes | 30 min | Accuracy | Me |
| S10 | **Readiness report** `docs/build/nc-readiness.md` and a statewide integration run of what's on `main` (baseline + ADU as a development run, with the D-025 fragility warning), confirming it finishes for all 322 jurisdictions. Missing-middle, fee and combine added if their PRs merge first. | — | — | Yes | 2–3 h, moderate tokens | **E2E** | Me |
| S13 | **Denominator history for parcel-counted places.** Today Raleigh, Greensboro, Durham and the other 76 parcel-counted places have one eligible-parcel year (2023 or 2026), so any engine that needs the level window (2010–2024) has no denominator there: #189's development run already reports "no baseline" for Raleigh for this reason. Options: (a) backcast each roll with year built (a parcel counts in year t if built by t; tier 1 only), (b) scale the place's ACS series to the roll's level in the roll year, (c) use the ACS series for history and the roll only for the share of lots by type. **This is a method choice in `build/eligible` (WS-CORE's code), so I'd open a `contract-change` issue with the options and a recommendation (b, with a as a check where tier 1), and Ben decides.** | Baseline, every scenario, V1 backtests for NC's largest places | Existing tables | Yes | Issue: 30 min; build: WS-CORE | **E2E** | WS-CORE + **Ben's decision** |
| S11 | Refresh the NC rows of `docs/data_availability.md` and the catalog's Greensboro row. | Transparency | — | Yes | 30 min | Accuracy | Me |
| S12 | *Carthage* town list (V6a), #11 and #46. | V6a only | UNC SOG research | No | — | Out of scope here | Ben / later |

**Order I'd work it:** S13 issue and S2 now (on today's table, to catch problems early) → S1 (after approval) → S2 again →
S3 Greensboro → S8 data prep → S4/S5/S9 together (shared fetches) → S6 → S10 → S11. One small PR each.

## 4. Ben's manual items (exact steps)

**Wake roll (S7a), about 15 minutes:**

1. In a browser, open
   https://www.wake.gov/departments-government/tax-administration/data-files-statistics-and-reports/real-estate-property-data-files.
2. Download **Real_Est_Data_Final_Dec2023.xlsx** (about 162 MB) and **Qualified_Sales_Past_24Months.xlsx**.
3. Register each (this records them as browser downloads; paths are examples):

```bash
uv run lotline manifest register ~/Downloads/Real_Est_Data_Final_Dec2023.xlsx --source wake_realestate --vintage 2023-12 --url "https://www.wake.gov/departments-government/tax-administration/data-files-statistics-and-reports/real-estate-property-data-files" --license "Wake County public records (no license stated)"
```

```bash
uv run lotline manifest register ~/Downloads/Qualified_Sales_Past_24Months.xlsx --source wake_realestate --url "https://www.wake.gov/departments-government/tax-administration/data-files-statistics-and-reports/real-estate-property-data-files" --license "Wake County public records (no license stated)"
```

4. Tell me the sha256 it prints. If the Dec 2023 file matches the automated copy (`7762d75a…`), the processed
   parcels don't change; if not, I rebuild the Wake parcels.

**Mecklenburg (S7b), one email:** to Mecklenburg County GIS (the contact on the BuildingPermits item page,
`maps.mecknc.gov/opendata/metadata/BuildingPermits.html`):

> We are building an open, public-interest housing model. Could you provide (1) an archived parcel/CAMA extract
> (land use, year built, units, parcel ID) dated between January 2022 and May 31, 2023, and (2) bulk access to the
> BuildingPermits feature service, which currently returns a Cloudflare challenge to scripted requests? We only
> need non-personal fields (no owner names).

If (1) never arrives, V5 still runs with §5's fallback.

## 5. V5 Charlotte before Nov 17

The prediction is "duplex and triplex units on lots that became N1 under the UDO, June 2023–2025".

| Need | Status | What closes it |
|---|---|---|
| Pre-UDO zoning per parcel | Done (`clt_udo_translation`, 2023-05-31) | — |
| N1 translation rule (R-3 → N1-A … UR-1 → N1-E) | In the research note, not in config | Add `config/crosswalks/nc_clt_udo_n1.csv` with its UDO §3.2 Table 3-1 source (S8, me) |
| Which N1 lots held a single-family house or were vacant before June 2023 | Missing | **Ben decides:** (a) wait for Mecklenburg's archive; (b) use the share of single-family and vacant parcels in the six Mecklenburg towns (current roll, not held out) as a prior with a range; (c) is ruled out: reading Charlotte's current roll breaks the snapshot rule. **I recommend (b) now, swapping in (a) if it arrives before Nov 10.** |
| Missing-middle effect to apply | D-024 estimator (#196) found no credible estimate | WS-ENGINE: the frozen prediction uses whatever D-024 prior/range is on `main` by then, stated as such |
| Charlotte's other inputs (market, demand, rates) | ACS, FHFA, FRED, demand index: all dated before the window or not outcomes | Check the demand index uses no Mecklenburg employment from after 2023-06 as an *outcome* (it's an input; fine either way, but say so) |
| Outcome data for unblinding (after freezing) | Mecklenburg permits blocked; BPS 37119 held out | S7b; otherwise unblind on BPS 37119 (county level, disclosed) |
| Freeze file | `results/frozen/V5-NC-CHARLOTTE.json` | WS-ENGINE, by Nov 17 |

Nothing in this plan opens Charlotte or Mecklenburg outcomes from 2023-06-01.

## 6. Decisions I need from Ben

1. **Approve S1's download** (~4.0M parcels, ~1.5 GB in `~/lotline-data`, 3–5 h unattended).
2. **Approve S3** (a Greensboro permit adapter; no new dependency).
3. **Approve S4–S6 research** at about one direct fetch per place (no search sweeps).
4. **V5 roll choice:** (b) now, (a) if Mecklenburg answers by Nov 10?
5. Do the Wake download and the Mecklenburg email (§4).
6. **S13:** OK to open the `contract-change` issue for WS-CORE, recommending option (b)?
