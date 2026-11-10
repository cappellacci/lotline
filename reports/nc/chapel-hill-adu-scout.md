# Chapel Hill, NC: ADU permit scout (place 3711800)

*2026-11-10 · data thread · branch `claude/nc-chapel-hill-permits-0b16da`*

**Verdict: partly usable.** Chapel Hill publishes record-level building permits with free-text descriptions
for **May 2015 to May 2021** (the town's former permit system, LAMA), as an open zipped File Geodatabase.
That is enough to count ADUs under the town's long-standing accessory-apartment rule: **30 ADU permits in
2015-2021, about 0.5 per 1,000 eligible lots a year**. Permits from mid-2021 on, which cover the 2023
Housing Choices amendments and the 2026 omnibus, sit in an OpenGov portal that has no public export and
blocks automated access. Getting them needs a public-records request (draft below). The town routinely
fills requests like it.

The adapter `src/lotline/adapters/states/nc/chapel_hill_permits.py` is built and tested. The file is read
with a new standard-library reader (`filegdb.py`), so no new dependency is needed.

## 1. Candidate sources

| # | Source | Format / access | Years | Rows are permits? | ADU flag | Parcel ID | Units | License / terms | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **LAMA Legacy Permit Data Production** (town open-data hub item `f336a911f4fc424bbe1a53a5e7abb529`, uploaded 2024-09-16) · https://opendata-townofchapelhill.hub.arcgis.com/content/f336a911f4fc424bbe1a53a5e7abb529 | Zipped File Geodatabase, 19.9 MB, public download (`/sharing/rest/content/items/<id>/data`) | Created 2015-05-11 to 2021-05-10 (issued 2015-2021) | Yes: 18,350 permit records (7,336 building class) plus related inspection, fee, review and property-feature tables | No ADU type. `LandUse` has "Accessory Apartment" (15 records); ADUs are found from the description `Descr` | None (a points layer has x/y; not read) | `New Dwelling Units` / `Total Dwelling Units` property features on about 300 permits | **No license stated on the item**; public record (NCGS 132). Nothing found that restricts reuse | **Used** (adapter) |
| 2 | Permits Issued 2013 to 2016 · https://services2.arcgis.com/7KRXAKALbBGlCW77/arcgis/rest/services/Permits_Issued_2013_to_2016/FeatureServer/0 | ArcGIS feature layer | Jan 2013 to Jun 2016, "not all months" | Yes, 4,972 | Description only (2 ADU-like hits) | Field named PIN holds **owner names** (columns shifted: `Type_of_Work` holds the date; permit number empty) | None | **ODbL** (share-alike) per item; data.gov mirror | Not used: overlaps #1 from 2015, columns broken, personal data in a key field |
| 3 | Online Permit Center (OpenGov; `chapelhillnc.viewpointcloud.com`, linked from the Building Permits page) | Web portal, account sign-up | Mid-2021 to present | Yes (per record) | Unknown (record types not visible) | Likely | Unknown | OpenGov portal terms; **Cloudflare blocks automated access** (HTTP 403 "you have been blocked" in a normal browser session); the `chapelhillnc.portal.opengov.com` address answers "portal does not exist" | **Blocked**: no export, bot protection. Records request instead (§5) |
| 4 | Current Development Activity · https://gisweb.townofchapelhill.org/arcgis/rest/services/MapServices/CurrentDevelopmentActivity/MapServer/0 | ArcGIS layer | Current | No: development applications (projects, up to 4 approvals each) | No | No | No | Town GIS disclaimer | Not usable for ADUs (small residential work does not go through this review) |
| 5 | Permit Notification Tool (ArcGIS web app) | Web map | n/a | No: parcels and town limits only | n/a | n/a | n/a | n/a | Not a permit source |
| 6 | Orange County Permitting Information Portal (EnerGov, `centralpermits.orangecountync.gov`) | Self-service portal | Current | Yes | Unknown | Yes | Unknown | County terms | Not Chapel Hill: the county issues permits for unincorporated Orange and Hillsborough only |
| 7 | Census BPS place rows (already in Lotline) | Annual counts | 2000-present | No | No | No | Yes | Public domain | Already used; cannot separate ADUs |
| 8 | Council records (Legistar API, `webapi.legistar.com/v1/chapelhill`) | API | 2023-2026 | n/a | n/a | n/a | n/a | Public | Used for the rule history. Staff said in 2023 they would monitor building permits for the new housing types; **no monitoring report was found** in Council matters through 2026-10 |

Checked and empty: `opendata.townofchapelhill.org` (old portal, no longer resolves), the town's ArcGIS
Online organisation and both GIS servers (`gisweb.townofchapelhill.org`, `gis-portal.townofchapelhill.org`):
no other permit layer. The town's website (`chapelhillnc.gov`) returns "Access Denied" to scripts (Akamai),
so its pages were read in a normal browser only.

## 2. What the LAMA source holds (as read on 2026-11-10)

- 18,350 permit records: Sub Permit (trade) 9,402, Building 7,336, Zoning 1,398, other 214. Every record's
  `Project_Jurisdiction` is "Town of Chapel Hill".
- Kept by the adapter: **5,747 issued building permits.** Dropped: trade and zoning permits (a zoning
  compliance permit and a building permit are often filed for the same ADU), 335 deleted records, 581 never
  issued (no `D_Start`), and Void / Withdrawn / Incomplete exits.
- `D_Start` is the issue date (`D_Exp` falls 6 months later on 99% of rows, matching NC's six-month expiry);
  `D_Create` is the application date. The property features give cost of construction, heated square feet,
  dwelling units and the certificate-of-occupancy date.
- Personal fields the adapter never reads: address, submitter, project name and location, contractor names,
  review comments, and the points layer's coordinates. The description is read only by the ADU rule.

**Reader check.** `filegdb.py` was compared value by value with GDAL's OpenFileGDB driver (pyogrio, in a
throwaway scratch environment, not a project dependency) on three tables of the real file: permits (18,350 ×
30), property features (151,102 × 8) and inspection schedule (101,450 × 9). **Zero mismatches.** The repo's
tests use hand-built synthetic tables (`tests/states/nc/gdb_writer.py`).

## 3. ADU counts

ADU rule (adapter docstring): the description names an ADU ("ADU", "accessory dwelling/apartment",
"garage/basement apartment", an apartment above/over/underneath something, a garage turned "into … apartment")
**and** says it is being created, **and** does not negate it or describe only an existing one. Only
single-family, accessory-apartment and townhouse properties count. "Guest house", "in-law suite" and
"cottage" are not counted. The shared parser alone finds 11 of the 30, because Chapel Hill staff usually write
ADUs into an addition or renovation ("ADDITION - ADU").

| Issue year | ADU permits | Eligible lots (theme `adu`) | Per 1,000 lots |
|---|---|---|---|
| 2015 (May-Dec) | 2 | 8,972 | 0.22 |
| 2016 | 5 | 9,318 | 0.54 |
| 2017 | 2 | 9,331 | 0.21 |
| 2018 | 8 | 9,399 | 0.85 |
| 2019 | 5 | 10,020 | 0.50 |
| 2020 | 5 | 10,242 | 0.49 |
| 2021 (Jan-May) | 3 | 9,999 | 0.30 |
| **2016-2020** | **25** | 48,310 lot-years | **0.52 / yr** |

**Chapel Hill is on the ACS fallback.** Every eligible-lot row for 3711800 has `denominator_source =
acs_sf_fallback`, `denominator_quality = low`, tier 3 (about 9,000-10,000 lots), not parcels.

For context, the same counts from Lotline's other NC permit tables, 2016-2020, per 1,000 eligible lots a year:
Durham 0.15, Greensboro 0.01, Raleigh 0.01 (both before their ADU reforms). Chapel Hill's rate is about 3×
Durham's under a rule that had allowed accessory apartments since 2003. The small numbers (2-8 a year) make
the year-to-year swings noise.

**Hand check of the rule** (random seed 20261110):

- **All 30 matches**, read in full: 30 are new ADUs (one was dropped while building the rule: "Convert duplex
  into SFD with accessory apartment", a conversion with no net new unit). Two are probable rather than certain
  ("Attic remodel (ADU) and porch addition"; "Garage Addition/Bonus Room … ADU"). One is an after-the-fact
  permit for an apartment added without a permit; it is counted because the unit is newly permitted. Six
  are a new house permitted together with its ADU; each counts as one ADU and the house is not counted.
  **Precision 30/30 (28 certain + 2 probable).**
- **30 random non-matches among residential permits whose description has an ADU-like word** (apartment,
  accessory, ADU, in-law, guest, cottage, kitchen, dwelling unit; 593 such permits): 30 correctly not new ADUs
  (mostly kitchen remodels; one existing-ADU remodel). One is borderline: a 745 sq ft accessory structure
  "to include a bedroom, bathroom, living room and wet bar". There is no kitchen, so it is not an ADU under
  LUMO's definition.
- **30 random non-matches among the other residential building permits:** 30 correctly not ADUs (decks,
  repairs, bathrooms, one new house).
- **Missed cases found in a full read of every description naming an ADU noun (about 70):** "RENOVATION …
  Basement - ADU" (probably a new ADU, no creation word), "PHASE 1 ACCESSORY STRUCTURE/REMODEL … Accessory
  dwelling unit" (unclear), and "garage with in-law suite above" (excluded by design). That suggests recall of
  roughly 90% for ADUs whose description names them. ADUs whose description never names them (for example
  "adding bedroom, kitchen and bathroom" in a basement) cannot be counted, so the true count is likely a little
  higher.

## 4. Chapel Hill ADU rule history: proposed `config/reforms/nc.csv` rows

*Not added to `nc.csv` (sibling sessions edit it). The town page, the 2023 and 2026 ordinances and the 2023
staff memo were read in full. Columns follow the file's header; empty cells are unsourced.*

| reform_id | theme | adoption / effective | by_right | owner_occ | adu_max_sqft | detached | per lot | parking | coverage | source | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `NC-3711800-adu-2003` | adu | 2003-01-27 / 2003-01-27 (LUMO enacted; date from the 2023 ordinance's citation "as enacted on January 27, 2003") | True (administrative zoning compliance permit; LAMA shows ADUs on "Residential Zoning" ZCPs and the 2023 FAQ says accessory apartments are "allowed in all residential zoning districts"; the 2023 amendments "did not alter where they're permitted") | not stated (no owner-occupancy clause in the definition) | 750 (or 75% of the principal unit, whichever is smaller; an attached unit inside an existing footprint up to 1,000) | True ("attached or not attached") | 1 | not sourced | Town planning jurisdiction, residential districts; **most Neighborhood Conservation Districts prohibit** | LUMO Appendix A definition "Dwelling units, single-family with accessory apartment" as quoted (struck) in Ordinance 2023-06-21/O-6, https://chapelhill.legistar1.com/chapelhill/attachments/78ad56a7-d2f1-46e7-abda-949cc163754b.pdf | The pre-2003 Development Ordinance was not checked; ADUs may predate the LUMO. More than 4 unrelated occupants makes the pair a rooming house. Article 6 had no ADU standards before 2023 (ordinance recital). The pre-2023 parking requirement was not read |
| `NC-3711800-adu-2023` | adu | 2023-06-21 / 2023-06-21 ("effective upon enactment", §23) · supersedes `NC-3711800-adu-2003` | True | not stated | 1,000 (75% of the primary when the primary is ≤1,300 sq ft); the Planning Director may grant exceptions inside existing structures | True; height 29 ft or the house's height | 1 | Town page: "Maximum 1 parking space per accessory apartment bedroom" in one place, "Minimum 1 parking space/bedroom" in the FAQ (**conflict, to verify in LUMO 5.9.7**) | All residential districts except NCDs that prohibit ADUs | Ordinance 2023-06-21/O-6 (Housing Choices for a Complete Community; Legistar matter 23-0560, passed 6-3), new LUMO §6.19.1 | Also created "single-family + cottage" (detached ≤1,200 sq ft floor area, 1,000 sq ft footprint, lot ≥ district minimum + 2,700 sq ft) and duplexes in most residential districts (a `missing_middle` row: two-family attached/detached, 3-4 family administrative where multifamily was allowed). The town page describes the old cap as 750 sq ft |
| `NC-3711800-adu-2026` | adu | 2026-01-21 / 2026-01-21 ("effective upon enactment") · supersedes `NC-3711800-adu-2023` | True | not stated | 1,000 (the 75% rule for small houses removed) | True; a detached ADU may sit on its own sublot (then the 4-unrelated limit applies per home) | 1 | Minimum parking requirements eliminated (staff report, Module 9 of the ordinance; PDF strike-through not machine-readable, **verify**) | as 2023 | Ordinance 2026-01-21/O-1 (omnibus text amendment, Legistar matter 26-0015), Module 7 §2, https://chapelhill.legistar1.com/chapelhill/attachments/c9689158-c21a-4d92-913d-b1ce556ec96a.pdf | Cottage floor area 1,200 → 1,500 sq ft and footprint cap removed; zero-frontage and flag lots; smaller minimum lots. The Nov 19, 2025 vote tied 4-4; passed on reconsideration |
| `NC-SL2026-59-3711800` | adu | already in `nc.csv` | | | | | | | | | State law row; unchanged |

**Reading for the model.** Chapel Hill is not a 2023 "adoption" in the Raleigh/Durham sense. ADUs were
allowed by right for 20 years first, so 2015-2021 is a long-run, under-cap regime (750 sq ft) with an observed
rate. The 2023 change is a size increase and the 2026 change removes parking minimums. Neither can be
observed until §5 brings in post-2021 permits.

## 5. Records request for 2021-2026 (draft for Ben to send)

Portal: https://chapelhillnc.justfoia.com/publicportal/home/newrequest (Clerk's Office;
allclerk@chapelhillnc.gov). The town's own log of past requests (open-data layer
`Open_Data_Public_Records_Requests`) shows similar bulk permit-data requests marked *Completed* by Building &
Development Services in 2025-2026 (request IDs 307, 2870 and 46), so a CSV export is a normal response.

> Under the North Carolina Public Records Law (N.C.G.S. Chapter 132), I request an electronic export (CSV or
> Excel) of all **building permits issued by the Town of Chapel Hill from May 1, 2021 to the present** from
> the OpenGov permitting system, with one row per permit and these fields where the system holds them:
> permit number; record/permit type and subtype; work class or description of work; issue date; application
> date; final / certificate-of-occupancy date; status (including void or withdrawn); parcel identification
> number (PIN); zoning district; number of dwelling units added or removed; heated square footage; valuation.
> If the system has a record type or flag for accessory apartments, cottages or two-family dwellings
> (Housing Choices uses), please include it. **Owner, applicant and contractor names and contact details are
> not needed and may be omitted.** This is for non-commercial research on housing production. If an export of
> this scope is not available, a report of the permits for the Housing Choices housing types that staff
> monitor (accessory apartments, cottages, two- to four-family) would also help.

When it arrives: register it with `lotline register` (manual file) and add a second reader to the adapter (or
a sibling `chapel_hill_opengov_permits` adapter). The ADU rule above can be reused if the export has free-text
descriptions.

## 6. Carrboro (noted, not built)

- Carrboro issues its own zoning and building permits (Planning, Zoning & Inspections, Town Hall); Orange
  County does not.
- No Carrboro permit layer was found on ArcGIS Online. Chapel Hill's GIS server has a `Carrboro_Data` service,
  but it holds only town limits and zoning jurisdiction. Carrboro's GIS download page
  (`gis.carrboronc.gov/GIS/downloadForIFrame.htm`) lists building footprints "updated with permit data"
  monthly (shapefile); that may hold new-building dates but not permits. Not opened.
- A Carrboro scout would start from that download page and a records request like §5.

## 7. Limits of this count

- Only mid-2015 to mid-2021; the reform years are not covered.
- Small counts (2-8 a year): any rate from this source alone needs a wide interval.
- The denominator is the ACS fallback (low quality); parcels would change the rate.
- No parcel IDs, so ADUs cannot be placed in NCDs (where most are prohibited) or in the Durham County part
  of town. All are Chapel Hill planning jurisdiction, which includes the ETJ.
- Multifamily unit counts in this source were not checked (ADU focus); treat non-ADU units as unreviewed.
