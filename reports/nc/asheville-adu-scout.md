# Asheville ADU permits: scout, adapter and counts

*Data thread, 2026-11-10. Asheville city (place 3702140; Buncombe County 37021). No model runs: these are
counts of the processed `permits` table and of `eligible_parcels`. Branch `claude/nc-asheville-permits-fc519a`.*

**Verdict: usable.** Asheville publishes every permit in its Accela system (November 2013 on) as one open
map-service layer under a public-domain dedication (PDDL 1.0). Rows are individual records. From 2022 the city
types ADUs itself ("ADU Detached", "ADU Attached"); before 2022 ADUs are found from the work description.
Adapter: `src/lotline/adapters/states/nc/asheville_permits.py` (source id `asheville_permits`), 12 tests on a
synthetic fixture. **361 ADU permits, 2014 to 2026-11-08.**

## 1. Sources scouted

| # | Candidate | URL | Format | Years | Rows | ADUs findable | Parcel ID | Units | License / terms | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **City of Asheville "Accela Permits View"** (Hub item "City of Asheville Permit Inspections", owner AVLGIS) | `https://gis.ashevillenc.gov/server/rest/services/Permits/AccelaPermitsView/FeatureServer/2`; item `b8fdb63db30b42d0875afb617e1551f4` | ArcGIS REST (JSON), no geometry needed, max 200,000 records per request | 2014-01-02 to 2026-11-08 (Accela launched November 2013); refreshed nightly | 66,521 records, one per permit / application (`record_id` unique) | **Yes.** `record_type_category` "ADU Detached" (New Building) and "ADU Attached" (Existing Building) from 2022; earlier, the `description` (ADU, accessory apartment, accessory dwelling) | `parcel_number` / `apn`: a 4-6 digit city-internal key, **not** the Buncombe County PIN (15 digits, e.g. `963470749800000`) | None. Type from category (SFD, Duplex, Townhome, ADU ...); multifamily counts only in the description | **Open Data Commons PDDL 1.0** ("Please visit this link for Licensing Information: http://opendatacommons.org/licenses/pddl/1.0/"), the same text as the city's other Hub items (e.g. Homestay Permits). No redistribution limit. `gis.ashevillenc.gov/robots.txt` is a 404; hub `robots.txt` asks a 60 s crawl delay on HTML pages only | **Used** |
| 2 | Asheville Open Data Hub search (`data-avl.opendata.arcgis.com`, queries "permit", "building permits", "accela") | `https://data-avl.opendata.arcgis.com` | Hub catalog | — | — | — | — | — | — | Lists only #1 (mislabelled "Permit Inspections": its description talks of inspections since 2000, but the layer holds permit records from 2014), Homestay Permits and Buncombe layers |
| 3 | Accela Planning View | `.../Permits/AccelaPlanningView/FeatureServer/1` | ArcGIS REST | — | Planning cases (rezonings, site plans) | No | — | — | same server | Not needed |
| 4 | Clariti folder (`.../Clariti/ClaritiData`) | `https://gis.ashevillenc.gov/server/rest/services/Clariti` | ArcGIS REST | current | Parcel zoning centroids, setbacks | No permits | — | — | — | Not a permit source. Watch item: if Asheville moves permitting from Accela to Clariti, the Accela view may stop growing |
| 5 | SimpliCity (`simplicity.ashevillenc.gov`) and the Accela Citizen Access portal | — | Web apps over the same records | — | One permit at a time | — | — | — | — | Not a bulk source; nothing it adds |
| 6 | Buncombe County Permits & Inspections | `gis.buncombecounty.org` (DeveloperMapper: special use permits only) | — | — | — | — | — | — | — | County permits cover the unincorporated county, not the city; not needed for 3702140 |

No records request is needed.

## 2. What the adapter does

Rules are in the module docstring and `PROVENANCE`; the short version:

- **Kept:** `record_module = 'Permits'`, type Residential or Commercial (49,375 records); records never issued
  are dropped (in review, plan check, denied, **revoked**, pending ...; 2,689), expired ones kept → **46,686
  permits**.
- **Years:** the layer has **no issue date**; `issue_year` is the year the record was opened (application),
  `issue_date` null, `date_precision = "year"`, `application_date` kept. Applications precede issue by weeks,
  so a few December applications land a year early.
- **ADU, city type** (2022 on): `building_type_std = ADU`, `type_confidence = high`, 1 unit `derived`.
- **ADU, description:** the shared parser (`lotline.parse.permit_text`) names an ADU on a house, accessory
  structure, alteration, addition or remodel permit → ADU, `inferred`. Never on trade, site-work, deck,
  demolition, duplex, townhouse or commercial permits (they are companions of a permit counted elsewhere, or,
  for "NEW RESIDENTIAL BUILDING 8", a parser misread). Text about an ADU that already exists or goes away
  ("beneath an existing ... ADU", "where the ADU was", "from a permitted ADU") is not a new ADU
  (`EXISTING_ADU`). A house permit that also builds the new house stays `SFD` with
  `reform_flag_raw = "adu_text_with_new_house"` (6 permits).
- **Other types:** SFD / SFD Waiver / Modular SFD 1, Townhome 1, manufactured home 1, Duplex 2 (1 for a half);
  multifamily from the parser's count; demolitions 0 new.
- **Privacy:** address, project name, contractor business and license, comments and short notes are never
  requested; the description (which often names the owner) is read in memory and dropped.

**Cross-check against BPS.** In 2024, the one year Asheville reported all 12 months to BPS (279 single-unit
homes, `units_1_rep = 279`), the permits give 199 houses + 56 townhouses + 30 ADUs = 285. BPS place rows for
Asheville are almost wholly imputed in 2015-2022 (`units_1_rep = 0`), which makes this source worth more.

## 3. ADU permits by year

Application year; eligible lots from `eligible.parquet` (theme `adu`, `parcels_scaled_acs`, data tier 2,
quality "low"). 2025 uses the 2024 denominator (no 2025 row); 2026 runs to 2026-11-08.

| Year | City-typed | From description | **ADU permits** | Eligible lots | **Per 1,000 lots** | Recall-adjusted (÷ 0.63 before 2022) | House + ADU (kept as SFD) |
|---|---|---|---|---|---|---|---|
| 2014 | 0 | 13 | **13** | 17,242 | 0.75 | 21 | 0 |
| 2015 | 0 | 14 | **14** | 17,232 | 0.81 | 22 | 0 |
| 2016 | 0 | 36 | **36** | 16,884 | 2.13 | 57 | 0 |
| 2017 | 0 | 49 | **49** | 18,058 | 2.71 | 78 | 1 |
| 2018 | 0 | 34 | **34** | 18,598 | 1.83 | 54 | 0 |
| 2019 | 0 | 20 | **20** | 18,991 | 1.05 | 32 | 0 |
| 2020 | 0 | 20 | **20** | 19,780 | 1.01 | 32 | 1 |
| 2021 | 0 | 19 | **19** | 20,651 | 0.92 | 30 | 1 |
| 2022 | 18 | 8 | **26** | 20,675 | 1.26 | 26 | 3 |
| 2023 | 34 | 4 | **38** | 21,220 | 1.79 | 38 | 0 |
| 2024 | 26 | 4 | **30** | 21,263 | 1.41 | 30 | 0 |
| 2025 | 33 | 5 | **38** | (21,263) | 1.79 | 38 | 0 |
| 2026 (to Nov 8) | 19 | 5 | 24 | — | — | 24 | 0 |

By kind (all years): detached 124, attached 44, internal conversion 19, unknown 174 (mostly pre-2022 text
matches that don't say).

**Reading it.** Asheville runs at about 1-2.7 ADU permits per 1,000 eligible lots a year. The peak is
2016-2018, right after Ordinance 4431 (June 2015) raised the size cap and opened nonconforming lots; then
counts settle near 20 a year before the city's own ADU types begin. The step at 2022 is partly a method
change (the city's flag finds more ADUs than the description), so the pre-2022 counts are a floor. The
recall-adjusted column is an upper reading that assumes the parser missed pre-2022 ADUs at its 2022-2026 rate;
the truth is between the two columns.

## 4. Hand check of the description rule

Two independent draws of 30 matches (text-inferred ADUs) and 30 non-matches each. Non-matches were drawn
from the 6,260 house, accessory and alteration permits whose description has a likely word (apartment,
in-law, guest, carriage, cottage, studio, kitchen, living space, garage, basement, dwelling, rental, tiny),
not from all permits, so a miss would show. Owner names are left out below.

**Draw 1 (seed 11/12), before the `EXISTING_ADU` rule:** 26 of 30 matches were ADUs. The 4 false: 18-05607
(enclosing a carport under an existing ADU), 18-06038 (garage where an ADU was), 19-03208 (change of use from
a permitted ADU to storage), 18-02777 (basement in-law suite with no kitchen; its amendment moved the ADU to a
separate permit). The first three led to the `EXISTING_ADU` rule, which removes them. Non-matches: 0 clear
misses; 1 borderline (24-05185, basement with bedroom, bath and kitchenette "for family and friends").

**Draw 2 (seed 21/22), final rule (the one in the adapter):**

| Matches | Verdict | | Matches | Verdict |
|---|---|---|---|---|
| 17-09346 basement into accessory apartment | ADU | | 18-04775 basement finish; amendment split the ADU onto another permit | **not** |
| 17-08452 324 sq ft ADU | ADU | | 21-00965 lower level into lease ADU | ADU |
| 17-06783 ADU in basement | ADU | | 15-13411 new detached ADU in backyard | ADU |
| 20-06137 new ADU with garage | ADU | | 17-06296 garage with ADU above | ADU |
| 16-03301 new build, basement attached ADU | ADU (house also new, not counted) | | 19-08590 two-story dwelling and ADU | ADU |
| 18-06221 garage with accessory apartment | ADU | | 14-07870 in-law suite over garage, family use, no kitchen stated | **not** |
| 16-03525 new 16x16 ADU | ADU | | 22-00356 437 sq ft detached ADU | ADU |
| 21-04919 removing kitchen, "no longer using as ADU" | **not** | | 16-11634 apartment over garage | ADU |
| 21-03914 application to create ADU in basement of new house | ADU | | 18-04070 free-standing 2-bed ADU | ADU |
| 17-01982 garage into guest suite apartment with kitchenette | ADU | | 23-03853 existing structure into ADU | ADU |
| 16-08190 finish basement for ADU | ADU | | 19-00068 new single-story ADU | ADU |
| 24-10617 basement into in-law suite with kitchen | ADU | | 16-12559 basement apartment ADU | ADU |
| 14-02431 garage with accessory apartment | ADU | | 19-07241 ADU in basement | ADU |
| 20-01956 800 sq ft carriage house ADU | ADU | | 20-07339 new house, basement ADU | ADU (house also new) |
| 18-04701 accessory apartment in basement | ADU | | 16-11597 new ADU | ADU |

**Precision 27 / 30 = 90%** (draw 1 under the final rule: 26 / 27). Non-matches, draw 2: 0 clear misses; 2
borderline (18-02271 addition for an in-law suite, 15-16364 "new guest cottage & garage"), neither stating a
kitchen. The other 28 are kitchens, baths, basements, garages and roofs.

**Recall.** The sample shows few misses among likely candidates, but the better measure is the city's own
flag: of the 130 city-typed ADU permits kept (2022-2026), the description rule alone finds **82 (63%)**:
74% of detached (64 / 86) and 41% of attached (18 / 44). Attached ADUs are often written as "finish
basement", "studio apartment" or "mother-in-law suite", which the parser leaves alone on purpose. Two
missed patterns seen: "additional dwelling unit" and "small house on the property".

**Not done here (shared parser):** "no longer using as ADU" and "in-law suite" without a kitchen are parser
behaviours in `lotline.parse.permit_text`; changing them would change every state's counts, so they are left
for the parser's owner (follow-up).

## 5. Asheville ADU rule history: proposed rows

`config/reforms/nc.csv` already has three Asheville ADU rows (2015, 2026 Ord. 5256, S.L. 2026-59). These are
**proposals only** (not written to the CSV, to avoid conflicts with sibling sessions):

| Proposed id | Date | Rule | Citation | Fields | Note |
|---|---|---|---|---|---|
| `NC-3702140-adu-1997` (new) | adopted and effective 1997-05-27 | Unified Development Ordinance: "accessory apartments" a use by right subject to special requirements in all residential districts except Urban Residential; by 2015 the limits were 50% of the primary dwelling, no square-foot cap, height up to 40 ft, and attached units inside the house were not addressed (whether these date from 1997 is not checked) | Ordinance No. 2369 (UDO text) and No. 2370 (maps), council minutes 1997-05-27 (Ordinance Book 16 p. 201; effective on adoption, 30-day window for applications in design); April 3, 1997 minutes (search excerpt, not read in full: accessory apartments a use by right in all residential areas under the proposed UDO); 2015 city news item for the pre-2015 limits | by_right True; adu_allowed_detached True; attached blank; max size 50% of primary, no sq ft cap; owner occupancy not found; parking blank | `[predates]`: before the 2010 window, so it only says ADUs were legal throughout. Planner quoted in 2015: ADUs "part of Asheville's history for at least the last 70 years" |
| `NC-3702140-adu-2015` (existing; propose edits) | 2015-06-23 | Ord. 4431 | as coded | add: attached ADUs newly defined (lesser of 70% / 1,000 sq ft); ADUs allowed on legally created nonconforming lots (city: 3,200+ parcels) and inside nonconforming houses; detached height reduced; parking only where the house needs it, to the side or rear | The second coder read the effective date as 2015-06-24; Section 4 says effective upon adoption (06-23). Keep 06-23. **This row is an in-window event** (the 2016-2018 permit peak follows it); suggest it is not tagged `[predates]` |
| `NC-3702140-adu-2026a` (new) | effective 2026-01-27 | ADU UDO text amendment clean-ups: "minor zoning code clean ups to reduce costs and barriers" (city table); a press headline, not matched to this ordinance by date, says a UDO change lets owners convert existing nonconforming buildings into ADUs without Board review | Text Change 25-05915PZ, Ordinance 5175 (city "Recently Adopted Changes" table) | every field blank until the ordinance is read (D-022 unknown) | After the estimation window |
| `NC-3702140-adu-2026` (existing) | 2026-08-25 | Ord. 5256 | as coded | — | No change proposed |

Owner occupancy: no source found in 1997, 2015 or now; a 2015 NC State survey of six NC cities lists
Asheville as not requiring it (secondary source). Leave blank.

## 6. Limitations and follow-ups

- No issue date (application years); no county PIN, so no parcel joins and no one-ADU-per-lot check.
- Pre-2022 ADU counts are a floor (description recall 63%, lower for attached ADUs).
- 6 permits build a new house and an ADU together; they are counted as houses.
- 2014 is the first full year: only two years (2014, 2015) come before the 2015 rule change.
- Follow-ups: (a) shared parser: "no longer ... ADU", in-law suites without a kitchen, "additional dwelling
  unit"; (b) code the proposed rows into `config/reforms/nc.csv` once sibling sessions have merged; (c) read
  Ordinance 5175.

Sources: [Accela Permits View layer](https://gis.ashevillenc.gov/server/rest/services/Permits/AccelaPermitsView/FeatureServer/2),
[Hub item](https://www.arcgis.com/home/item.html?id=b8fdb63db30b42d0875afb617e1551f4),
[PDDL 1.0](http://opendatacommons.org/licenses/pddl/1.0/),
[City ADU page](https://www.ashevillenc.gov/department/development-services/residential-permits-and-development/accessory-dwelling-units/),
[2015 ADU news item](https://www.ashevillenc.gov/news/proposed-change-to-accessory-dwelling-units-designed-to-promote-affordable-housing/),
[UDO text amendments table](https://www.ashevillenc.gov/department/planning-urban-design/zoning-administration/text-amendments-to-unified-development-ordinance/),
[Council minutes 1997-05-27](https://council-minutes-archive.ashevillenc.gov/Minutes.1997-05-27.pdf),
[Council minutes 1997-04-03](https://council-minutes-archive.ashevillenc.gov/Minutes.1997-04-03.pdf),
[NC State backyard cottages survey](https://outreach.design.ncsu.edu/ah+sc/wp-content/uploads/2015/04/Backyard-Cottages-in-Six-Cities-in-North-Carolina.pdf).
