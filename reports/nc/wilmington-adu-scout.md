# Wilmington ADU permits: scout and first counts

*Data thread, 2026-11-10 (branch `claude/nc-wilmington-permits-08322e`). Counts below are descriptive tables of
the processed `permits` table in `LOTLINE_DATA_DIR`. No engine, scenario or calibration code was run. The data
is not in the repo.*

**Verdict: a usable open source exists, and it is now loaded.** New Hanover County Building Safety issues
every building permit inside the City of Wilmington. The county publishes those permits, one row each, on its
public ArcGIS server for 2014 to the present. The adapter `src/lotline/adapters/states/nc/wilmington_permits.py`
(source id `wilmington_permits`) loads them. ADUs are not flagged: they are read from the work description, so
the counts below are estimates. A hand check put precision at about 90% and the missed share at a few percent.

- **Wilmington (3774440): 291 ADU permits, 2014 to 2026, on 279 parcels.** That is 0.1 to 0.5 per 1,000 eligible
  lots a year before 2022, and 1.5 to 2.2 a year from 2023. The rise follows the Dec 2021 LDC (no parking
  minimum, no "lot and a half" rule) and the May 2024 amendment.
- **Unincorporated New Hanover County (37129): 64 ADU permits**, 14 to 16 a year from 2024.
- **Coverage gain.** NC jurisdictions with ADU-flagged permits held 8.1% of NC's 2024 eligible lots (theme
  `adu`; Raleigh, Durham city and county, Greensboro, six Mecklenburg towns). Adding Wilmington gives 8.9%, and
  adding unincorporated New Hanover gives 9.9%.

## 1. Sources scouted

| # | Source | URL | Format | Years | One row per permit? | ADU flag | Parcel ID | Units | License / terms | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **New Hanover County `Thematic/BuildingPermits`, layer 0 "Building Permits"** (ArcGIS item b84f1cf36cf440efb66ef14e8d93ea06) | https://gis.nhcgov.com/server/rest/services/Thematic/BuildingPermits/FeatureServer/0 | ArcGIS FeatureServer (JSON query, 10,000 per page; also csv/geojson export) | Issue dates 2014 to 2026 (a handful of 1975–2013 strays, one 2027 typo). Converted OneSolution records 2014–2018 (`WORK_CLASS` "Converted"), Tyler EnerGov from 2019 | Yes, plus sign-off holds and job records (see §2) | **No.** No ADU field or work class; ADUs only in `DESCRIPTION` | `PID` (county tax PID, e.g. R06220-001-027-000); layer 4 of the same service maps PID → NC PIN | **None.** No unit count of any kind | No license stated. Item: "originates from the county's building permitting and inspections records … refreshed on a monthly basis". County open-data site disclaimer (https://opendata.nhcgov.com): provided as is, no warranty, use at your own risk, hold the County harmless. No reuse or redistribution limit. `gis.nhcgov.com/robots.txt` is 404. Same terms as Greensboro's source | **Used** |
| 2 | Same service, layer 4 "Parcels" (PID, PIN, MAPID, acres) | …/FeatureServer/4 | ArcGIS FeatureServer | Current | n/a | n/a | PID and PIN | n/a | As #1 | **Used** for the PID → PIN join only (no owner fields exist in this layer) |
| 3 | Same service, layer 1 "Building Plans" | …/FeatureServer/1 | ArcGIS FeatureServer | 2019 on | One row per plan review | No | PID | No | As #1; it also holds owner names and addresses | Not needed |
| 4 | `Layers/BuildingPermits` and `Layers/TradePermits` MapServers (older geo.nhcgov.com and gis.nhcgov.com) | http://geo.nhcgov.com/gis/rest/services/Layers/BuildingPermits/MapServer | ArcGIS MapServer | Current calendar year only | Yes | No | Yes | No | As #1 | Superseded by #1 |
| 5 | City of Wilmington | https://www.wilmingtonnc.gov/Development-Business/Zoning/Building-Permits | Web pages; online portal is for zoning review | n/a | n/a | n/a | n/a | n/a | n/a | **No city permit data.** The city says the county "issues all building permits in the city"; the city does zoning and address review only |
| 6 | New Hanover County open-data hub (Hub site; site item licensed CC-BY-SA) | https://opendata.nhcgov.com | ArcGIS Hub | — | — | — | — | — | Disclaimer as in #1. The CC-BY-SA tag belongs to the Hub *site* item, not to the permit layer | No permit dataset listed; #1 is reachable only through the REST directory and ArcGIS Online search |
| 7 | COAST (the county's EnerGov citizen portal) | linked from the city's permit page | Interactive search | — | Yes | — | — | — | Portal terms; built for one-off lookups | Not used: it would mean scraping a portal when #1 publishes the same records |
| 8 | Third-party mirrors (openpermitdata.com and others) | — | — | — | — | — | — | — | Secondary, unknown terms | Not used |

Nothing here is personal-use-only or no-redistribution. Lotline does not redistribute the records anyway: they
are fetched into `LOTLINE_DATA_DIR` and only aggregates are published. **No records request is needed.**

## 2. What layer 0 holds, and what the adapter keeps

489,007 rows on 2026-11-10. The adapter downloads 11 building-permit types (65,767 rows) and keeps **48,930
permits**:

- **Not downloaded:** trade permits (electrical, plumbing, mechanical: most of the layer); building
  *applications* ("NHC Residential Building Application", 23,787 rows, nearly all without an issue date); and the
  71,203 "NHC Converted" rows. Those are sign-off holds attached to a permit ("NEEDS CITY ZONING", "CFPUA
  FINAL"), not permits.
- **Dropped:** unissued, void, withdrawn, denied and revoked permits. Also dropped: converted records whose
  description ends "Job master" (17,385 rows). These are the old system's job containers. Each building job
  also has its own structure permit with its own number on the same parcel, so keeping both would count every
  building twice. All 2016 ADUs showed the pairing ("2016-11409 … Job master" and "16-32903 … Structure", same
  parcel).
- **Jurisdiction:** by the permit's point in Census place polygons (`lotline.geo`, TIGERweb ACS 2025). That
  puts 24,450 permits in Wilmington, 23,230 in the unincorporated county, and 1,250 in the beach towns (partial
  coverage, not checked). The county's own `DISTRICT` label is filled only from 2019, so it is the fallback.
- **Parcel:** `parcel_id` = 37129 + PIN through layer 4. It is filled for 97% of permits and for every
  Wilmington ADU, so permits join to the OneMap parcels and to `eligible_parcels`.
- **Units:** no field. New single-family work classes count 1 home (`derived`). Converted permits, other
  dwelling types and multifamily come from the shared description parser (`inferred`). Apartment buildings
  rarely state a count, so they are mostly `UNKNOWN`.

**Sanity check against the Census BPS** (`bps_place_year`, row 37129, which includes Wilmington): this file's
1-unit homes (SFD + TH + ADU, Wilmington and unincorporated county) run at 0.75 to 1.23 of BPS 1-unit units:

| Year | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| This file | 727 | 847 | 903 | 1,181 | 1,066 | 1,110 | 1,300 | 1,383 | 1,623 | 1,106 | 906 | 981 |
| BPS 1-unit | 826 | 1,013 | 1,148 | 1,565 | 1,245 | 1,310 | 1,403 | 1,565 | 1,324 | 1,126 | 1,213 | 1,107 |
| Ratio | 0.88 | 0.84 | 0.79 | 0.75 | 0.86 | 0.85 | 0.93 | 0.88 | 1.23 | 0.98 | 0.75 | 0.89 |

This is good enough for ADU counting. It is not a replacement for BPS home counts: the file has no unit field.

## 3. ADU counts

`building_type_std = "ADU"` (one row per permit). Eligible lots are `eligible_parcels` with theme `adu` and rule
1.1. 2025 has no eligible row in the table, so the 2024 count is used. 2026 runs to 2026-11-05 only.

**Wilmington (3774440)**

| Year | ADU permits | Parcels | Detached | Attached | New SFD permits | Eligible lots | ADUs per 1,000 eligible |
|---|---|---|---|---|---|---|---|
| 2014 | 3 | 3 | 0 | 0 | 200 | 27,150 | 0.11 |
| 2015 | 6 | 6 | 1 | 1 | 207 | 27,072 | 0.22 |
| 2016 | 11 | 10 | 2 | 5 | 261 | 27,834 | 0.40 |
| 2017 | 5 | 5 | 0 | 1 | 387 | 27,611 | 0.18 |
| 2018 | 2 | 2 | 0 | 0 | 370 | 27,943 | 0.07 |
| 2019 | 6 | 6 | 2 | 0 | 302 | 28,285 | 0.21 |
| 2020 | 15 | 15 | 0 | 4 | 358 | 29,106 | 0.52 |
| 2021 | 7 | 7 | 0 | 0 | 534 | 28,186 | 0.25 |
| 2022 | 23 | 22 | 5 | 1 | 804 | 28,190 | 0.82 |
| 2023 | 44 | 43 | 1 | 0 | 490 | 28,717 | 1.53 |
| 2024 | 45 | 43 | 6 | 3 | 505 | 29,808 | 1.51 |
| 2025 | 59 | 59 | 4 | 3 | 467 | (29,808) | 1.98 |
| 2026 (to Nov 5) | 65 | 65 | 20 | 0 | 341 | 29,808 | 2.18 |
| **Total** | **291** | **279** | 41 | 18 | | | |

Most ADUs have kind `unknown` (224 of 291): the descriptions often say just "ADU" or "Accessory Dwelling Unit".

**Unincorporated New Hanover (37129):** 2, 0, 2, 1, 4, 1, 4, 2, 2, 2, 14, 16, 14 ADU permits in 2014 to 2026
(64 in all). Eligible lots: about 32,000 to 37,000. The county's own ADU rules are not coded (see §5).

## 4. Hand check of the description rule

The rule is `is_adu_text` in the adapter. A residential building, accessory or addition permit counts as an
ADU when its description has an ADU term and no veto applies. The term comes from the shared parser's
`permit_text.ADU` or the county's own (`LOCAL_ADU`). The vetoes are: a "Not to be used as an ADU" note, work
on an existing ADU, an ADU on another permit, or a duplex.

How it was checked. Wilmington residential permits, read by hand, five rounds of 30 + 30. Rounds 1 to 4 were
used to build the rule. **Round 5 was drawn only from permits no earlier round had shown, and the rule was
frozen first.** Its numbers are the ones to quote:

| Round 5 sample | Drawn from | Result |
|---|---|---|
| 30 matches | the 191 ADU permits not shown before | **27 real ADUs: precision 90%** (exact 95% CI 73–98%) |
| 30 non-matches, likely-ADU pool | the 128 unseen non-ADU permits that name an ADU-like term ("apartment", "unit A", "guest house", "dwelling unit", "in-law" …; 184 in the pool in all, RiverLights "cottage" homes left out) | **5 missed ADUs** ("new garage with apartment", "detached garage with upstairs apartment", "SFR with attached dwelling unit", "attached 468 sq ft 1 bedroom apartment to newly constructed home", "new detached dwelling apartment"); 1 guest house left out on purpose |
| 30 non-matches, random | all 16,787 non-ADU residential permits | **0 missed** |

**What that means for the totals.** Scaling 5 of 30 to the 184-permit pool gives about 30 missed ADUs (very
roughly 12 to 55). Random permits outside the pool show none. About 10% of the 291 matches are false. So the
true count is near the flagged one: about 262 true matches plus about 30 misses, roughly 290. Recall is about
90%. The errors roughly cancel in the total, but not by year: the misses are spread over 2019–2026 and the
false positives mostly fall in 2025–2026.

**False positives found (all rounds):**
- Notes ruling an ADU out, written in a way the veto misses: "NOT APPROVED FOR SEPARATE LIVING SPACE/ADU".
- Repairs at an existing ADU ("All work to take place at Accessory Dwelling Unit … repairs to existing deck").
- A house permit whose ADU has its own permit, phrased as "(Garage with apartment above on separate permit)".
- Reissues of an expired ADU permit ("OWNER TAKEOVER & REPLACEMENT OF EXPIRED ADU PERMIT 23-011928"). Expired
  permits are kept, so the ADU counts twice. This is the main reason 291 permits sit on 279 parcels.

**Fixed while building the rule (rounds 1 to 4):**
- The county's standard note "Not to be used as an accessory dwelling unit/have cooking appliances", added to
  garage and shed permits from 2025. About 30 Wilmington permits read as ADUs before the `NOT_ADU` veto.
- NSFR permits that say both "single family" and "ADU" ("SFR - 1BR 1BA - ADU"). The shared parser gives no type
  for these, and they are the county's usual way to file an ADU.
- "ADU to be permitted separately" (this permit is the house) versus "NEW ADU / Primary dwelling permitted
  separately" (this permit is the ADU).
- Converted job-master duplicates, and an underscore hiding "ADU" ("NEW ADU_New construction").

**Left out on purpose:** "guest house", "guest suite", "pool house", "cottage". The precision-over-recall
policy matches Greensboro. Some of these are dwelling units: "UNIT A – NEW Guest House" is counted, a bare
"Detached guest house" is not. The RiverLights "Cottage Twin" homes are a subdivision, not ADUs. A permit that
builds a house and its ADU together ("Single Family Home with ADU") is one ADU row, so that house is not
counted (a handful of cases).

**Possible next step (not done here, to keep the measured rule frozen):** add "garage with (upstairs)
apartment", "attached dwelling unit", "dwelling apartment" and the "/ADU" negation. Then re-measure on a new
sample.

## 5. ADU rule history (proposed rows, not entered)

Here is what the reviewed sources support. The existing row `NC-3774440-adu-2024` (May 21, 2024, LDC-7-424) stays
as it is. Two rows are proposed for `config/reforms/nc.csv`. They are not entered: sibling sessions edit that
file. Ben or the second coder should add them.

| When | What changed | Source |
|---|---|---|
| Before Dec 1, 2021 (old Chapter 18) | ADUs allowed, but hard to build. Two off-street parking spaces were required. A WHQR source says a lot "and a half" was also needed. Size cap 900 sq ft. About a third of residential lots could not host one "because of parking requirements and other limitations". Districts, by-right status and owner occupancy were not found in the sources read | WHQR 2021-06-17 ("staff, council argue over 'poison pill'"); WHQR 2021-07-07 (Planning Director Glenn Harbeck: ADUs "have long been allowed"); WHQR 2024-04-30 (900 sq ft, one-third of lots) |
| **Adopted 2021-08-17, effective 2021-12-01: new Land Development Code (Chapter 18)** | Off-street parking requirement for ADUs removed (a late revision before the vote). The lot-and-a-half minimum dropped ("any residential lot"). Size stayed at 900 sq ft (the 2024 change raised it from 900) | LDC Article 1 (Municode): chapter "adopted on August 17, 2021 … effective on December 1, 2021"; WHQR 2021-08-18; WilmingtonBiz 2021-08-18 |
| Adopted and effective 2024-05-21: LDC-7-424 | Already coded (`NC-3774440-adu-2024`): one ADU per lot, attached, internal or detached, up to 50% of the principal floor area or 1,200 sq ft. About 97.5% of residential lots eligible (zoning administrator to WHQR) | Certified ordinance; WHQR 2024-04-30 and 2024-05-09 |
| 2027-01-15: S.L. 2026-59 (state law) | `config/reforms/nc.csv` has 21 S.L. 2026-59 rows, but **none for Wilmington**. Add one from the same template if the law applies to the city | `config/reforms/nc.csv` |

Proposed rows, using the CSV's columns. Ben decides `by_right` and the tags.

```csv
reform_id,state,jurisdiction_geoid,theme,component,status,announced_date,adoption_date,effective_date,end_date,supersedes,by_right,owner_occ,unit_cap,far_cap,max_stories,min_lot_sqft,adu_max_sqft,adu_detached_allowed,adus_per_lot,lot_split,parking,parking_min_per_unit,fee_change_usd,dollar_year,coverage,coverage_zones,source_url,source_section,source_quote,verified_by,verified_date,coder,coder_2,coder_agreement,coding_notes
NC-3774440-adu-pre2021,NC,3774440,adu,"[predates] Old Chapter 18 (before the 2021 LDC): ADUs allowed with two off-street parking spaces, a lot of about 1.5 times the minimum, and a 900 sq ft cap",in_force,,,,2021-11-30,,,,,,,,900,,1,,Two off-street parking spaces per ADU,2,,,"City of Wilmington: residential districts (district list not read); about two-thirds of residential lots could host one",,https://www.whqr.org/local/2021-06-17/staff-council-argue-over-poison-pill-that-could-kill-future-adus; https://www.whqr.org/local/2024-04-30/nearly-every-house-in-wilmington-could-be-allowed-an-adu-starting-in-may,,"two off-site parking spaces in order to build an ADU",,,claude,,single_coder,"[predates] [earliest-known] In force before the 2010 window; adoption date not found. Code text not read: WHQR only. By-right and owner occupancy unknown (left blank). The lot-and-a-half rule is from the 2021-07-07 WHQR piece (Harbeck quote)."
NC-3774440-adu-2021,NC,3774440,adu,"Land Development Code (Chapter 18, full rewrite): ADU off-street parking requirement removed and the lot-and-a-half minimum dropped; 900 sq ft cap kept",in_force,2021-06-17,2021-08-17,2021-12-01,2024-05-20,NC-3774440-adu-pre2021,,,,,,,900,,1,,None,0,,,"City of Wilmington: any residential lot (setbacks apply)",,https://www.whqr.org/local/2021-08-18/wilmington-has-set-new-development-standards-for-the-next-several-decades; https://mcclibrary.blob.core.usgovcloudapi.net/codecontent/15998/422094/Article%201%20-%20Purpose%20and%20Organization.pdf,LDC Art. 1,"adopted on August 17, 2021 and became effective on December 1, 2021",,,claude,,single_coder,"Dates from LDC Article 1. ADU content (no parking, any residential lot) from WHQR 2021-07-07 and 2021-08-18; the 2021 LDC ADU section itself was not read (the city's LDC user guide PDF returned 404). by_right left blank: not confirmed from the code text. The 2024 row (LDC-7-424) supersedes it."
```

Checks still to make before entering them:
- Read the 2021 LDC's ADU section for districts, by-right status and owner occupancy. Municode has the
  current text; the 2021 text needs the adopting ordinance or an archived copy.
- Find the old code's adoption date for ADUs, or confirm `[predates]`.
- Set `NC-3774440-adu-2024`'s `supersedes` to the 2021 row.

Why it matters for D-025. Wilmington would be one place with **two in-window events**: Dec 2021, a real
loosening with firm dates, and May 2024. ADU permits run 6 to 15 a year in 2019–2021, then 23, 44, 45, 59 and
65 from 2022. The permits start in 2014, so each event has pre-years.

## 6. Open items and caveats

- **Annexation:** current city limits are applied to every year (as in Raleigh and Greensboro).
- **Beach towns:** Carolina Beach, Kure Beach and Wrightsville Beach issue many of their own permits. Their rows
  here are partial and not checked.
- **One permit dated 2027-06-15** (25-028759, a data-entry error). Kept as issued. Callers that cap at the
  current year drop it.
- **Wilmington is still not in `jurisdictions`' BPS universe** (`in_bps = False`). Using it in the ADU panel
  needs its rule rows (§5) and a panel caller that reads `wilmington_permits`. That is engine work, not done
  here.

## 7. Reproduce

```bash
uv run lotline fetch --state NC --source wilmington_permits
```

The download is logged in `manifest.jsonl` (source `wilmington_permits`, 21 files, about 46 MB with the parcel
PID → PIN pages). The adapter's tests run on synthetic rows: `uv run pytest tests/states/nc/test_wilmington_permits.py`.
