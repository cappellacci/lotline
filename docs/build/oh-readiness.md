# Ohio data readiness (thread 11, step 3)

*WS-OH, draft of 2026-10-26. Plan: `docs/build/oh-data-plan.md` (#217). No model runs: these are counts of the
processed input tables in `~/lotline-data/processed/oh`, built with the open Ohio PRs **#224** (Franklin ADU
flags), **#226** (Gahanna rule) and **#232** (county land use, Franklin year built). On `main` alone the
numbers are lower; each row says which PR it depends on.*

**Bottom line.** Ohio can run end to end today: every one of its 952 jurisdictions has a denominator, a data
tier, BPS permits, market inputs and a rule (coded or drawn, D-022). For **93% of Ohio's population the
eligible-lot count now comes from real parcels**, not the ACS estimate. What Ohio still lacks is **evidence
for the estimation panels**: 4 places for the ADU panel and 1 treated place for missing middle.

## 1. Coverage of each model input (952 jurisdictions: 567 places, 297 townships, 88 county remainders)

| Input | Real | Fallback | Unknown / missing | Depends on |
|---|---|---|---|---|
| **Eligible lots (denominator)** | 874 jurisdictions counted from parcels, with D-035's scaled 2010–2024 history: **92.5% of population** | 72 on the ACS fallback (D-017): 6.8% of population. Among the 40 largest places only **Dayton** (18.6% unknown land use), **Hamilton** (10.4%) and **Middletown** (15.2%) | 6 jurisdictions lack a full 2010–2024 window (Violet, Greenfield and Pleasant townships; Henry and Lorain county remainders; Smithfield and Waverly villages: no ACS anchor within 3 years) | #232 |
| Denominator quality | 2 rows `high` | 944 `low` | — | Quality is `low` because zoning is unknown everywhere: unknown zoning counts as single-family-only (the same in NC). Zoning layers would raise it (Columbus base zoning, CC0, in the catalog; Montgomery's `MC_ZONING.gdb` is on disk) |
| **Data tier** | **Tier 1: 72** (land use + year built; 28.5% of population; Columbus, Parma, Cuyahoga Falls, Lakewood, Euclid …). Tier 2: 807 (64.7%) | Tier 3: 73 (6.8%) | — | #232 (on `main`: 0 / 826 / 126) |
| Permits, all places | Census BPS for every permit-issuing place and township | — | — | `main` |
| **Permits with an ADU flag** | Cincinnati (`cincy_permits`, 26 ADUs), Columbus (`columbus_permits`, 20 ADUs read from the Auditor's descriptions), 8 Franklin suburbs (`franklin_permits`) | — | Columbus finds about 1 in 4 of its ADUs (14 vs the city's 57 for 2019 to Sep 2025). No ADU permit data for Cleveland, Toledo, Akron, Dayton or any other city | #224 |
| Permits with 2–4 unit flags | Columbus, Cincinnati (city records); BPS everywhere | — | — | `main` |
| **ADU rules** | 16 places with dated rows (32.8% of population) | The rest draw a rule type (D-022) | Uncoded among the 40 largest: Akron, Parma, Canton, Lorain, Cuyahoga Falls (code host blocks scripts) and places 21–40; in Ben's fill-in table | #226 |
| **Missing-middle rules** | 1 place (Cincinnati, 2024-07-01) | The rest draw a rule type (D-022) | Euclid's Ord. 120-2024 (two-family in U1) unconfirmed; 46 other places in Ben's table | `main`, #226 |
| Fees | none (`config/fees/oh.csv` does not exist) | The Handbook $50,000 prior (D-034) everywhere | Columbus capacity charges are in the catalog (S8, not started) | — |
| Market (rent, value, rates, costs) | ACS, FHFA, FRED: statewide | — | — | `main` |
| Demand index | processed (`market_geo_year/demand.parquet`) | — | — | `main` |
| Holdouts | none in Ohio | — | — | — |

## 2. What Ohio adds to the estimation panels

| Panel | What a place needs | Ohio places today | What would add more |
|---|---|---|---|
| **ADU (D-025)** | A permit source that flags ADUs, a dated ADU rule (a "no ADUs" row counts) and eligible lots | **4**: Cincinnati (adopted 2023-10-02), Columbus (2025-12-25; pre-period counts about 1 in 4 of the true count), Dublin (Historic Districts 2021), Gahanna (conditional use 2024-05-01). Before this thread: 1 (Cincinnati) | (1) **Rule rows for the 15 Franklin places without one** (Westerville, Grove City, Hilliard, Upper Arlington, Reynoldsburg …): their ADU counts already exist in `franklin_permits`; the panel's caller must list them, because a place with no ADU has no row. (2) Columbus's own yearly ADU counts. (3) Any ADU permit data for Cleveland, Toledo, Akron, Dayton. All in Ben's list (#217 §8) |
| **Missing middle (D-024)** | BPS 2–4 unit permits (every Ohio place ≥ 10,000 with a BPS row: **156 places**) and, to be treated, a dated rule | **1 treated** (Cincinnati) | Euclid (Ord. 120-2024) if confirmed; any of the 46 places in `oh-mm-lookups-todo.csv` |

## 3. Remaining gaps and what closes each

| Gap | Effect | What closes it | Owner |
|---|---|---|---|
| Dayton land use (Montgomery County) | Dayton's denominator is the ACS estimate | The Auditor's real-estate (CAMA) extract, downloaded in a browser (the Auditor's weekly geodatabase has no parcel land-use code); or a stated proxy from the building tax class (a D-017 method choice) | Ben (#217 §8 item 4) |
| Hamilton (10.4% unknown) | ACS estimate, 0.4 points over the D-017 gate | Keep the gate, or a stated tolerance; the remaining parcels have no appraisal record in Butler's own layer | Ben (item 3) |
| Middletown, Mason (Warren County, 44% unknown) | ACS estimate for Middletown; Warren parcels unknown | A Warren County Auditor parcel download with land-use codes | Ben (item 12) |
| ADU rules for Franklin places and the 40 largest | Fewer ADU-panel places; more D-022 draws | `oh-adu-lookups-todo.csv` | Ben (item 8) |
| Columbus ADU undercount | Columbus's pre-adoption ADU counts are about a quarter of the true count | The city's yearly ADU counts; meanwhile a measurement note or exclusion in D-025 | Ben (items 5, 10), WS-ENGINE |
| Missing-middle events | Ohio adds 1 treated place | `oh-mm-lookups-todo.csv` (Euclid first) | Ben (item 9) |
| Fees | Handbook prior everywhere | S8: Columbus, Cincinnati, Cleveland water and sewer fees from official PDFs | WS-OH (not started) |
| Second roll year | D-035 scales ACS to one roll | Lucas yearly cadastres (2013–2025, shapes only) as a check; the 2022 statewide vintage (OGRIP email) | WS-OH, Ben (item 13) |
| Zoning | Denominator quality stays `low` | Columbus base zoning (CC0); Montgomery `MC_ZONING.gdb` (on disk) | WS-OH (not planned yet) |
| Cleveland permits (S7) | Cleveland not in the ADU panel as an untreated place | `cle_permits` adapter, ODbL runtime fetch (approved) | WS-OH (not started) |

## 4. How these numbers were made

`readiness` counts come from the processed `jurisdictions`, `eligible_parcels`, `permits` and `bps_place_year`
tables on 2026-10-26 after the rebuilds in #232, and `config/reforms/oh.csv` from #226. The ADU-panel
count applies D-025's inclusion rule (a flagging permit source, a dated rule, eligible lots) without running
the estimator. Population shares use the 2020 census counts in `jurisdictions`.
