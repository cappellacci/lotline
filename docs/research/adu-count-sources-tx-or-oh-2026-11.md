# ADU count sources in Texas, Oregon and Ohio (search of 2026-11-15)

**Question.** Which public, record-level building-permit files would let more Texas, Oregon and Ohio places enter
the ADU fit, especially core cities? This is a report only. No source has been added, no adapter written and no
model run. Ben decides what gets added.

**Entry bar** (D-074 step 2, D-078 in `docs/analysis_plan.md`): one row per permit, at least 1,000 permits; a way to
spot ADUs (a type or class code, description wording, or a unit count on lots that already have a house); years
overlapping about 2015–2025; a permissive or public licence, or at least an open portal with no terms against reuse.
A place also needs coded ADU rules (`config/reforms/<state>.csv`) to enter the fit. The rules status below comes
from those files.

## Bottom line

- **No new core city clears the bar cleanly.** The only core-city lead is **Houston**, and it is a partial count.
  Houston's own planning department publishes geocoded new single-family permits for 2015–2024. ADUs show up only in
  the project-name text, and ADUs filed as additions or accessory structures are not in the file. That makes it a
  lower bound, not a count.
- **Oregon has two likely-usable county sources:** Deschutes County (public domain) and Jackson County (CC BY 4.0).
  Both cover mostly unincorporated areas. Only their metadata was read (V9 holdout).
- **Ohio has one weak lead:** Summit County's permit table (Akron area). It has no ADU code. It would need a
  "second dwelling on the parcel" join like Franklin County's, and Akron has no coded ADU rule yet.
- **Texas small-city find:** San Marcos has a coded `Accessory Dwelling` permit type. It counts only 1 to 8 ADUs a
  year, and San Marcos has no coded ADU rule.
- **Registered sources:** the Fort Worth endpoint has moved, and Dallas has a newer permit table that still can't
  separate ADUs. Cincinnati's fit is short because its permit text rarely names ADUs before 2023. Details are below.
- **Two Oregon city-year ADU tables exist:** Corvallis's own table and DLCD's Housing Production Survey. These are
  holdout outcomes, not fit inputs, and were not opened. Ben may want them later for scoring the Oregon test.

## Candidates, most promising first

"Rules" says whether the place has coded ADU rows. Counts marked *count query* came from server-side counts with a
word filter; they are rough (no hand check) and are given only for Texas and Ohio.

| # | Place (core city?) | Source | Record-level | Permits (approx.) | Years | ADU identification and reliability | Licence | Rules | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Houston, TX** (core city) | COH Planning & Development ArcGIS layer "SF_2015_to_2021" (holds 2015–2024 despite the name): `https://services.arcgis.com/NummVBqZSIJKUeVR/arcgis/rest/services/SF_2015_to_2021/FeatureServer/1` | Yes (one row per sold permit, geocoded) | 57,166 new single-family permits | 2015–2024 (no 2025) | **Text only.** ADUs share the "New Single Family Dwelling" code with houses. The project name names them: "NEW DET. GARAGE W/APT ABOVE", "GAR W/ QUARTERS ABOVE", "NEW SECONDARY DWELLING". *Count query:* 2015 89, 2017 60, 2018 48, 2019 37, 2020 29, 2021 23, 2022 40, 2023 31, 2024 22. **Low reliability:** ADUs filed as additions or accessory structures aren't in the layer, and the wording drifts ("QUARTERS" mostly gone after 2018). | Public ArcGIS item, licence blank (the city's CKAN portal uses ODC-By) | Yes (TX-4835000-adu-2010, -2023) | **Maybe**: a lower bound or trend series only. It would need its own undercount factor k, measured against an independent list such as the HCAD roll, before it could enter the fit. |
| 2 | Deschutes County, OR (unincorporated; Bend and Redmond permit separately) | CivicData BLDS file `deschutes_permit_standard_permits_v7_10369` ("since 2000", daily) plus 1990–2000 and pre-1990 files: `https://www.civicdata.com/dataset/deschutes_permit_standard_permits_v7_10369` | Yes (BLDS standard) | Not read (holdout) | 2000 to present per title; search snippets suggest last update about June 2025 | BLDS `PermitType` / `WorkClass` / `ProposedUse` / `Description` (and optional `HousingUnits`). Actual codes not checked. | "Other (Public Domain)" | Yes (OR-41017) | **Usable (likely).** Caveat: CivicData's API returned a Cloudflare challenge to scripts. If plain file links are also challenged, this becomes not usable (we don't bypass bot checks). |
| 3 | Jackson County, OR (unincorporated plus a `JURISDICTION` field; Medford separate) | `https://spatial.jacksoncountyor.gov/arcgis/rest/services/DevServ/Permit/MapServer/0` (item `ba1745be25084b56ac8781d69a104f7f`); weekly copy at `jcportal.jacksoncountyor.gov/server/rest/services/Property/Permits_Building/FeatureServer/1` | Yes (one point per permit) | Not read (holdout) | Not stated in metadata (`SUBMITDT`, `APPROVEDT`) | `PERMITTYPE` (no published domain) and `PERMITDESC` text. No unit field. Text-based, so reliability is unknown until a hand check. | **CC BY 4.0** (spatial-server item) | Yes (OR-41029) | **Usable (likely)**, once the year span is confirmed after unblinding. |
| 4 | Summit County, OH (Akron is the core city, plus suburbs) | Fiscal Office CAMA permit table SC707: `https://fiscaloffice.summitoh.net/sites/default/files/assets/forms/SC707_PERMIT_5.zip` (data-downloads page) | Yes (one row per parcel and permit) | About 110–120k (estimated from file size) | 2008–2026 seen in sample | No ADU code. `WHY` is a 10-character reason (NEW HOUSE, GARAGE, ADDITION, "OTHER SECO" …); none named ADUs in a ~2,700-row sample. It would need the SC710 dwelling cards to find parcels that gain a second dwelling (the Franklin County approach, untested here). **Low-to-unknown reliability.** | Public download page; no terms found | Akron: **no**. Cuyahoga Falls: yes (OH-3919778) | **Maybe.** It needs a parcel-join method and Akron rule coding before it is worth a pilot. |
| 5 | San Marcos, TX (not a core city) | `https://smgis.sanmarcostx.gov/arcgis/rest/services/Planning/CoSM_BuildingPermits/FeatureServer/0` | Yes | 51,957 | 2011–2026 | **Coded `TYPE = 'Accessory Dwelling'`** (43 rows) plus wording such as "SFR ADU" and "SFR Garage to ADU". *Count query* (by application year): 2015 3, 2016 2, 2017 2, 2018 1, 2019 3, 2020 4, 2021 3, 2022 5, 2023 7, 2024 8, 2025 2. All statuses are included, so filter on status. Good reliability. | "As is" disclaimer, no reuse ban | **No** (4865600 not coded) | **Usable, but small**, and it needs rule coding first. |
| 6 | Benton County, OR (Corvallis coverage unknown) | Building division export: `https://services7.arcgis.com/NURlY7V8UHl6XumF/arcgis/rest/services/Building_Permits_Assessor_VIew/FeatureServer/0` (edited 2026-11) | Yes | Not read | Not stated (`Permit_Date`) | `Permit_Type`, `Building_Use`, `Occupancy_Use`, `Type_of_Structure`, `Description`, `City` | None stated. It exposes applicant e-mails and owner phone numbers, which must not be requested. | Yes (OR-41003; Corvallis OR-4115800) | **Maybe**: no licence, and it is unclear whether Corvallis is in it. |
| 7 | Benton County, OR, all issuers (may include Corvallis and Philomath) | Assessor `BuildingPermitsAll`: `https://services7.arcgis.com/NURlY7V8UHl6XumF/arcgis/rest/services/BuildingPermitsAll/FeatureServer/0` | Yes | Not read | Snapshot ends 2024-07 | `bldg_permit_type_cd`, `property_use_cd`, `bldg_permit_desc`; codes not documented | None stated (PII fields present) | As row 6 | **Maybe**: frozen in mid-2024, no licence. |
| 8 | Fort Worth, TX (core city; registered `fw_permits`) | The open data moved: the Socrata table now returns 404. New home: `https://services5.arcgis.com/3ddLCBXe1bRt7mzj/arcgis/rest/services/CFW_Open_Data_Development_Permits_View/FeatureServer/0` | Yes | 1,624,312 | 2001–2026 | `Use_Type = 'Accessory Dwelling'` has 564 rows (count confirmed here), but this is **not a clean ADU flag**: in a 200-row sample only about a third read as dwellings. The rest are storm shelters, game rooms, sheds and golf-course restrooms, and a third are expired or void. This matches the existing provenance note. | Item licence blank (registered as CC-BY 4.0) | Yes, but the rule allows no separate rentable unit (TX-4827000-adu-2010, `adus_per_lot` 0) | **Not usable for the fit as it stands.** Action for the registered source: **repoint `fw_permits` to the ArcGIS layer**, because the Socrata fetch will fail. |
| 9 | Dallas, TX (core city; dropped) | Newer table: `https://www.dallasopendata.com/resource/e7gq-4sah.json` ("Building Permits", daily) | Yes | 396,710 | 2018 to Nov 2026 (runs past the POSSE extract's Nov 2024 end) | No ADU type or land-use code; `work_description` hits are only about 1–17 a year (*count query*). The reason Dallas was dropped still holds. | Socrata licence field empty | Yes | **Not usable** for ADUs. It could extend Dallas's other series into 2025–26 if wanted. |

## Not usable (checked)

| Place | Source | Reason |
|---|---|---|
| El Paso, TX | `gis.elpasotexas.gov/.../Planning/NewResidential/MapServer/1` (42,763 new residential) | About 20 ADU rows in total; new residential only |
| Arlington, TX | `gis2.arlingtontx.gov/agsext2/.../OD_Property/MapServer/1` (CC BY 4.0) | Rolling 3-year window; no ADU class |
| Collin County cities, TX | data.texas.gov `82ee-gbj5` (Collin CAD permits) | Rolling 3 years from 2023; text only. Could serve a forward-looking check. |
| Irving, Midland, Tyler, Kerrville, Leander, McKinney, TX | ArcGIS layers (URLs in the session notes) | Short spans (2018+ or 2020+), one year per layer, or 0–2 real ADU rows |
| Denton County, TX (unincorporated) | `gis.dentoncounty.gov/.../DEV_Permits/MapServer/0` | Unincorporated only, ends July 2023, about 49 loose hits |
| Plano, TX | dashboard.plano.gov | Charts only |
| Houston, TX, other routes | data.houstontx.gov (monthly counts only); Permitting Center sold-permits search (HTTP 403); old weekly PDF reports (404) | Not record-level, or not reachable |
| Westerville, OH | `webgis.westerville.org/.../TransparencyHub/Permits` | 2,399 permits, 2023–2026 only, no description |
| Oxford, OH | `services2.arcgis.com/FS7YxIXpWoaR2sAe/.../Building_Permits` (7,460) | Description field, but 0 ADU hits |
| Fulton County, OH (rural) | Regional Planning zoning permits (1,500) | 2 ADU-like rows |
| Columbus, OH (registered) | `Building_Permits` FeatureServer (690k, CC0) | No better ADU field; `UNITS` on accessory or garage permits looks like the house's units |
| Cleveland, OH (registered) | `Building_Permits` FeatureServer (ODbL) | Text is the only route; 4–10 hits a year (29 in 2016), renovations included |
| Gresham, OR | Third-party upload (a title company's Excel file) | Not an official release; no licence |
| Beaverton, OR | `SD_Permits_Data` | Site-development (civil) permits, not building permits |
| Tigard, OR | `active_permits` MapServer | Active permits only (rolling 2 years) |
| Clackamas County, OR | docretriever permit search | A search tool, not a bulk file; the GIS portal needs a licence agreement |
| Newberg, OR | OpenGov permit-to-address join | One permit per address, so history is lost; small city |
| Talent, OR | `Talent_Building_Permits_View` | Probably under 1,000 permits |
| Eugene and Springfield, OR | RLID (Lane Council of Governments) | Paid subscription |
| Portland region, OR | Metro "Building Permit Data" (Construction Monitor) | Commercial licence, no redistribution |

**No record-level portal found:**
- **Texas:** Corpus Christi, Lubbock, Round Rock (sign permits only), Georgetown, Frisco, Garland, Waco, Killeen,
  Laredo, Brownsville, Amarillo, Sugar Land, Denton city (Turnstile, no API), and Travis, Williamson and Hays
  counties (Texas counties issue few building permits). Regional councils NCTCOG, H-GAC (septic permits only),
  CAPCOG and AACOG have no permit table.
- **Ohio:** Toledo and Lucas County (the auditor download needs a sign-in), Akron city, Dayton (Accela; nothing
  larger than the registered file), Hamilton County (ezTrak is lookup only), Dublin, Upper Arlington, Worthington,
  Hilliard, Bexley, Grandview Heights, Lakewood, Cleveland Heights, Shaker Heights, Euclid, Kettering, Youngstown,
  Canton, Lorain, Springfield, Mentor, Athens and Kent. Regional councils MORPC, MVRPC and OKI publish aggregates
  only; NOACA, TMACOG and AMATS have no ArcGIS account. Not reachable from here: gis.toledo.oh.gov, the Lucas County
  auditor GIS server, gis.cuyahogacounty.gov and cagisonline.hamilton-co.org.
- **Oregon:** Eugene (city permit reports page 403), Springfield, Hillsboro (server timed out), Washington County
  (timed out), Lake Oswego, Milwaukie, Tualatin, Wilsonville, West Linn, Happy Valley, Oregon City, Albany, Grants
  Pass, Hood River, McMinnville, Ashland, Central Point, Redmond, Woodburn and others. data.oregon.gov has no permit
  records. The state Building Codes Division ePermitting is search-only. The RLIS metadata catalog (all 246
  entries) has no permit dataset.

## Notes on registered sources

- **Cincinnati (`cincy_permits`): why only about 2 years.** The combo-permit file (`thvx-5mem`) runs from 2014, but
  its work descriptions almost never name an ADU before 2023. *Count query*, distinct permits with "accessory
  dwelling", " ADU", "in-law" or "garage apartment": 2017 2, 2019 1, 2020 1, 2023 4, 2024 6, 2025 2, 2026 10; zero
  in every other year. The 2020 spike in a wider "carriage" search is about 10 apartment-over-carriage-house permits
  in one 36-building master plan (commercial sub-type), not backyard ADUs. The main permit file's `description` is
  a category label, so ADUs filed outside a combo permit can't be seen. Many real ADUs sit under sub-type
  "Res Garage/Shed >=800" or "<800", which may help a future rule. **No data fix lengthens Cincinnati's series.**
- **MWVCOG `PermitsSince1998`.** The layer's time extent is 1998-01-01 to 2025-01-01, so it probably runs through
  2024. The item calls it "Salem-Keizer area". Keizer is likely covered; nothing suggests Woodburn, Silverton,
  Dallas, Monmouth, Independence or Stayton. Confirming which places are in it needs a distinct-values query on
  `JURISD`, which waits for unblinding. It has separate ADU unit fields `ADU_IN`, `ADU_OUT`, `DEMOADU_IN` and
  `DEMADU_OUT`. **Keizer is the cheapest new Oregon place after unblinding.**
- **Metro RLIS Housing (`rlis_housing`).** Covers all of Clackamas, Multnomah and Washington counties, with
  `JURIS_CITY`, so every Portland suburb on the list is in its frame. ADU is a `UNIT_SUBTY` value (registered as
  `UNIT_TYPE`; check which field the fetch filters on). It has `YEARBUILT`, `DATASOURCE` (city building
  departments, assessors, Construction Monitor) and `CONFIDENCE`. It is a snapshot, not permits, and YEARBUILT can
  be the main house's year, so it does not meet the bar for yearly counts. It stays useful as the independent list
  for k.
- **Salem `Structure_Permits`.** A daily City of Salem permit service (item `e4f6b72c2aa14f69a3ac4c08b6847074`) that
  could cross-check MWVCOG for Salem. Fields not checked.

## Oregon city-year ADU tables (holdout outcomes, not opened)

- **Corvallis** publishes `BuildingPermits1970` (fields Year, Single_Family_Units, ADUs, Duplex/Multi-Family units;
  item `36f15ae81d364a8dbf15510e2b68b0ba`) and `2020ADUs` (Year, Number_of_ADUs_Permitted; item
  `76de7acbe3bc483ebf63ecc2308025e4`).
- **DLCD Housing Production Survey** (ORS 456.586(4)): cities report units permitted and produced each year by
  type, including ADUs.

Neither is record-level, so neither can enter the fit under D-074. Both are direct city-year ADU counts, which makes
them candidates for **scoring** the Oregon test. Whether and when to use them is Ben's call, after the V9 freeze.

## How this search was done, and what it did not do

- Three Claude Code research subagents ran in parallel, one per state, on 2026-11-15. They used portal catalogs
  (ArcGIS Online, Socrata discovery, CKAN), layer metadata (`?f=json`) and web search. The lead session assembled
  and checked the results.
- **Texas and Ohio:** server-side count queries with ADU word filters, plus samples of at most about 200 rows. The
  Summit County sample was the first ~40 KB of the zip, about 2,700 rows. Nothing was saved in the repo; samples were
  deleted.
- **Fort Worth check:** the lead session re-ran the count (564) and read a 200-row sample. That sample showed the
  `Use_Type` field is noisy, so the subagent's "usable upgrade" verdict was downgraded.
- **Oregon (V9 holdout):** metadata only. No `/query` calls, no counts, no previews, no downloads. Two things
  slipped through in web-search snippets and metadata: a total object count for RLIS Housing (about 488k polygons
  of all types) and Census BPS county totals quoted from FRED. Neither is an ADU count, and neither is recorded
  here.
- St. Paul was not touched. No records requests, no staff contact, no bot-check or sign-in bypass.
- No adapters were written, no data was registered and no model, engine, scenario or `scripts/dev` run was made.
- Licences are as stated on each portal at the time; re-check them before registering any source.
