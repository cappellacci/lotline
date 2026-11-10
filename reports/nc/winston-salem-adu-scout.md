# Winston-Salem ADU permits: scout report

*Data thread, 2026-11-10 (branch `claude/nc-winston-salem-permits-51b037`). Place 3775000, Forsyth County 37067.
No engine, scenario or calibration runs. Nothing was downloaded into `LOTLINE_DATA_DIR`.*

**Verdict: no usable source, so no adapter.** Winston-Salem's only open bulk permit layer is MapForsyth's
`Development_And_Permits` FeatureServer, layer 0 "Permits Issued", published by the joint City-County office.
Its service description says "since January 1, 2013", but it holds **3,059 residential permits issued
2021-01-04 to 2021-12-30 only** (`Permit_Yea` = 2021 on every row). It has no ADU code and no free-text
description, and 2021 is before by-right ADUs (2022-02-07). So it can't give ADU permits by year. The host
refused this network for most of 2026-11-10 and answered later the same day, after Ben read the layer from
another network (§2a). The records request and the ADU-list request in §4 are now the way forward.

The rule history *is* settled, from primary documents on the city's Legistar API, and it changes how NC's ADU
panel should read Winston-Salem (§3). The city also published its own count: **10 ADUs permitted from
2022-02-07 to the end of February 2023** (3 attached, 7 detached; Legistar matter 23-0026). The earlier regime
(2017-2022) approved only **2** ADUs.

## 1. Who issues permits

Winston-Salem/Forsyth County Inspections is a joint City-County division. It issues building, electrical,
plumbing and mechanical permits for the City of Winston-Salem and for Forsyth County, except the Town of
Kernersville, which runs its own inspections. The UDO is also joint: rules tagged (W) apply in the city, (F) in
the unincorporated county. So one county-wide permit file would cover the city, and the city's rows would have
to be placed by corporate limits, as `durham_permits` does. MapForsyth publishes the limits as
`Planning_Inspection/Planning_Inspection/MapServer/0`, on the same unreachable host.

## 2. Candidate sources

| # | Source | URL | Format | Years | Rows = permits? | ADU flag | Parcel ID | Units | License / terms | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **MapForsyth "Permits Issued"** (City-County Planning and Development Services) | `https://maps.co.forsyth.nc.us/arcgis/rest/services/Planning_Inspection/Development_And_Permits/FeatureServer/0` | ArcGIS FeatureServer (JSON, paged) | "since 2013" per the description; **only 2021 in the data** | Yes (3,059 residential permits) | No: no ADU type or use code, no description | `PIN` | `NUMBER_UNI` (mostly 0/blank) | Unknown. The copyright text credits City-County Planning and Development Services and MapForsyth; no license seen | **Not usable for ADUs**: read later on 2026-11-10 (§2a). Only 2021, residential, no ADU code, no description |
| 2 | City-County BuildIT portal | `https://buildit.cityofws.org/wsfcpermit` | Web search, one record at a time | Unknown | Yes, one at a time | Permit type, maybe | Probably | Unknown | No bulk export. robots.txt doesn't exist (404) | **Not usable**: rebuilding a dataset from one-record lookups is scraping. Not attempted |
| 3 | `CityofWS/TEST_Accela/FeatureServer` on the same host | `https://maps.co.forsyth.nc.us/arcgis/rest/services/CityofWS/TEST_Accela/FeatureServer` | ArcGIS | Unknown | Unknown | Unknown | Unknown | Unknown | Labelled TEST | Blocked (same host); a test service shouldn't be a source anyway |
| 4 | City of Winston-Salem ArcGIS Online org (`services.arcgis.com/XAnuVx6VEMybNvyd`, 357 services; `services1.arcgis.com/5Yf8nIJWE7cxpd3N`, 134) | listed on 2026-11-10 | ArcGIS | — | — | — | — | — | — | **No permit layer.** Nearest: `Development` (Rezonings, Planning Board Reviews, Major Subdivisions) |
| 5 | MapForsyth Hub (`www.mapforsyth.org`, `mapforsyth-hub-datadownload-mapf.hub.arcgis.com`) | — | Hub | — | — | — | — | — | — | The catalog API returns 0 items. Owner `giomapforsyth` on ArcGIS Online has no permit items |
| 6 | Census BPS, Winston-Salem place row | already loaded | annual totals | 2010-2024 | No (counts by building size) | No (BPS can't tell ADUs apart) | — | — | Public domain | Already in Lotline; it gives no ADU count |
| 7 | City Council information item 23-0026 (2023-04-10) | `https://webapi.legistar.com/v1/winston-salem/matters/19071/attachments` ("INFO - ADU", "MAP - ADU") | Word memo and map | 2022-02 to 2023-02 | Yes: a list of the 10 ADU permits, with attached/detached and ward | Yes: it lists only ADUs | Street address only | 1 each | Public record (Legistar) | **Usable as a check**, not as a series: covers one year |

A third-party paid scraper on Apify ("Winston Salem NC Building Permits") says it reads Forsyth's ArcGIS
FeatureServer and lists fields such as `permitNumber`, `permitType`, `permitClass`, `permitClassDescription`,
`permitStatus`, `parcelNumber` and `applyDate`. That suggests the layer has a parcel number and a permit class.
It was not used, and its field names are unverified.

What was tried on 2026-11-10:

- `curl` to `maps.co.forsyth.nc.us` (443 and 80): TCP connect timeout. `nc -z` failed on both ports.
- The browser pane: navigation failed.
- The web-fetch proxy: `ECONNREFUSED` on the services root, the layer, and `robots.txt`.
- The Wayback Machine has 2021-2026 captures of other services on the host (for example `Tax/TPV_Main` in
  March 2026), so the server is normally up. None of the permits service.
- `www.cityofws.org` (UDO amendment PDFs) answers with a Cloudflare browser check (HTTP 403). It was **not**
  bypassed. Legistar (`webapi.legistar.com/v1/winston-salem`) is open and holds the same ordinance documents.

## 2a. What "Permits Issued" holds (read 2026-11-10, after the host came back)

- **3,059 rows, all issued in 2021.** `IssueDate` runs 2021-01-04 to 2021-12-30, and `Permit_Yea` is 2021 on
  every row. The layer is a one-year snapshot, despite its "since 2013" description. No archive of other
  years exists on the server: of 335 services, none other holds permits.
- **Residential only:** `CASE_GROUP` is Single-Family (2,775) or Multi-Family (284).
- **`CASE_TYPE_` values:**
  - Single-Family: New Building 1,126; Alteration 1,115; Addition 445; Manufactured Home 75; Modular Home 13;
    **Accessory Building 1**.
  - Multi-Family: Alteration/Repair 140; Townhouse/Twin/UR 135; Apartments 7; Duplex 2.
- **`PROPERTY_U` has no accessory-dwelling use code.** The one accessory-building permit is in the
  unincorporated county (`MUNJUR` = FC) and is 1,654 sq ft, so probably not an ADU.
- **Other fields:**
  - `PIN` (parcel), so a permit could be joined to a parcel.
  - `MUNJUR` jurisdiction: WS 1,758; FC 700; LE (Lewisville) 210; CL (Clemmons) 109; Kernersville 51;
    others. This is how the city's rows would be split out.
  - `NUMBER_UNI` (mostly 0 or blank), `SQFT`, `AMOUNT`, `ISSUED`, `CO_DATE`, `STATUS_COD`.
  - Personal fields (`INSPECTOR`, street address, X and Y) would never be requested.
- **No description field,** so ADUs inside alteration or addition permits (conversions, attached units)
  can't be found.
- **Terms:** `copyrightText` and `description` are empty. The service credits "City-County Planning and
  Development Services, MapForsyth". No license was found.
- **Layer 1,** "Residential Development Approvals", has 75 rows: subdivision approvals, not permits.
- **Not used:**
  - `TaxReappraisal/PERMITS`: internal appraiser assignment lists, about 1,850 rows, with staff names.
  - `EnvironmentalHealth/EnvHealth_ResidentialDevelopment`: linework and 2018-2021 parcels, not permits.

An adapter on this layer would give one pre-reform year of new-home counts, which Census BPS already gives.
For ADUs it gives nothing, so it wasn't built.

## 3. ADU rule history (primary sources)

All from attachments to Legistar matters, read through the public Legistar Web API
(`https://webapi.legistar.com/v1/winston-salem/matters/<id>/attachments`).

1. **To 2017: allowed with kinship limits.** ADUs have been in the zoning ordinance "since as early as 1930"
   (2023 information item; 2021 staff report). Occupancy was limited to relatives, dependents, adopted persons
   or household employees of the owner, people over 55, or people with disabilities. Attached ADUs were
   approved administratively. Detached ADUs needed a Board of Adjustment special use permit, issued for a term
   (Norby memo of 2017-08-24, matter 2046).
2. **2017-09-05, UDO-267 (matter 2046, City Council approved): more restrictive.** Following the City Attorney's
   advice on case law, the kinship limits were removed. In the city, attached and detached ADUs alike now
   needed a **Special Use District rezoning**: a site plan, Planning Board and City Council approval, 2-3
   months, a $1,000 minimum fee. Only **two** ADUs were approved this way from 2017 to 2022 (2021 staff report;
   2023 information item). Examples: W-3481 (RS9 to RS9-S, 2021-08-02) and W-3498 (RS12 to RS12-S,
   2021-11-01). A 2018 amendment let detached ADUs with expiring Board of Adjustment permits renew there.
3. **2022-02-07, UDO-CC15, Ordinance #21-0667 (2022 Ordinance Book p. 22; matter 18107): by right.** UDO §5.3.4B
   (attached) and §5.3.4C (detached), (W) provisions: the Zoning Officer "shall issue a zoning permit" when the
   conditions are met.
   - Where: any lot whose principal use is a single-family house (detached: single-family or class A
     manufactured home), in districts that allow that use.
   - One ADU per lot.
   - Attached: up to 50% of the house's heated floor area and at most 1,000 sq ft. Height no more than the house.
   - Detached: up to 70% of the house's floor area and at most 1,000 sq ft; 576 sq ft is always allowed.
     Height up to 25 ft; side and rear setbacks 5 ft; never in front of the house's front façade; on a
     permanent foundation.
   - No additional parking (Table 6.1.2: attached shares the driveway, detached exempt).
   - No owner-occupancy rule; the definitions drop the word "occupancy".
   - "Effective upon adoption" (§5).
   - Votes: Planning Board recommended approval 5-2 (staff report). The General Government Committee forwarded
     it without a recommendation (2021-12-14). Council continued it on 2022-01-03 and approved it 2022-02-07.
   - The county (F) side keeps the Board of Adjustment special use permit for detached ADUs. Only the
     definitions and §5.3.1 went to the County Commissioners, which probably explains the 4/7/22 date in the
     amendment history.
4. **2022-2026: no later city ADU amendment** was found among Legistar matters from 2022-03 on with "accessory"
   or "ADU" in the title.
5. **2027-01-15: S.L. 2026-59 Sec. 44** (G.S. 160D-917), already coded as `NC-SL2026-59-3775000`.

### Proposed rows for `config/reforms/nc.csv` (not applied: shared file)

| Proposed reform_id | status | adoption / effective | by_right | adu_detached_allowed | owner_occ | adu_max_sqft | parking | Note |
|---|---|---|---|---|---|---|---|---|
| `NC-3775000-adu-2017` | superseded (by NC-3775000-adu-2022) | 2017-09-05 / 2017-09-05 | False | True (special use district rezoning) | — | — | (as before) | UDO-267, matter 2046. The kinship limits removed; attached and detached ADUs need Special Use District rezoning (Council). Tag `[earliest-known]` for the effective date: the ordinance text wasn't read, only the Council approval in the matter history |
| `NC-3775000-adu-1930` (optional) | superseded (by NC-3775000-adu-2017) | `[predates]` | False for detached (Board of Adjustment special use permit); True for attached | True | kinship/age/disability occupancy limit | — | — | Pre-window baseline. Never an event |
| `NC-3775000-adu-2022` (existing) | in_force | 2022-02-07 / 2022-02-07 | True | True | False (no rule) | 1000 | No additional parking | **Keep the row. Correct `coding_notes`:** the second coder's "approved June 24, 2021 and effective October 4, 2021" is wrong. Legistar matter 18107 shows Committee 2021-12-14, Council continued 2022-01-03, **approved 2022-02-07**, and the ordinance says effective upon adoption. `owner_occ` can be set to False. Better `source_url`: `https://webapi.legistar.com/v1/winston-salem/matters/18107/attachments` |

**Why it matters for the ADU panel (D-025):** under the 2017-2022 regime, ADUs needed a rezoning, which is
effectively not by right. So Winston-Salem's 2022 event goes from "special use" to "by right" and is a clean,
firm-dated, in-window event in a city of about 250,000. The before and after levels are known roughly from the
city's own documents: about 2 ADUs in 4.4 years (about 0.5 a year), then 10 in the first ~12.7 months (about 9.4
a year). The city had 62,798 ADU-eligible lots in 2022 (`eligible.parquet`, theme `adu`, tier 2,
`parcels_scaled_acs`). That is **about 1.5 ADUs per 10,000 eligible lots in year 1**, against about 0.08 per
10,000 a year before. These are official counts, not a permit file. Treat them as a check on the panel, not a
series, until §4 delivers the permits.

## 4. Ways forward (for Ben)

1. ~~Two-minute check from another network~~ **Done on 2026-11-10 (§2a): the layer is 2021 only, with no ADU
   code.** Original step, kept for the record:
   `https://maps.co.forsyth.nc.us/arcgis/rest/services/Planning_Inspection/Development_And_Permits/FeatureServer/0?f=json`.
   - If it loads, save the JSON (fields, description, copyright, `maxRecordCount`) to the shared notes folder
     or an issue, and look for a license or terms link on `www.mapforsyth.org`.
   - With field names and terms in hand, the adapter is about a day's work on the `greensboro_permits`
     pattern: the description parser for ADUs, and corporate limits to place permits in the city.
   - The download still has to go through `lotline.io.arcgis.download_layer` from a network that reaches the
     host. If only Ben's browser reaches it, `lotline manifest register` on a hand export (as for
     `meck_permits`) works.
2. **Records request** (if the host stays closed or the terms forbid reuse). Draft:

   > To: Winston-Salem/Forsyth County Inspections Division and City-County Planning and Development Services
   > (GIS Office / MapForsyth)
   > Subject: Public records request: building permit data, 2013 to present
   >
   > Under N.C.G.S. Chapter 132, I request an electronic copy (CSV, Excel or file geodatabase) of all
   > building permits issued by Winston-Salem/Forsyth County Inspections from January 1, 2013 to the present,
   > with these fields where they exist: permit number, permit type, class or subtype, work description,
   > status, application, issue and final or certificate-of-occupancy dates, parcel number (PIN), jurisdiction
   > (city or county), zoning district, number of dwelling units, and valuation. I don't need owner or
   > contractor names, phone numbers or emails. If it is easier, the attribute table of the "Permits Issued"
   > layer (Planning_Inspection/Development_And_Permits/FeatureServer/0) for every year since 2013 is enough
   > (the published layer holds only 2021). Please also say under
   > what terms the data may be reused and republished. The data is for a non-commercial research model of
   > housing production; it will not be redistributed as is.

3. **Ask for the ADU list directly** (cheapest, and enough for the panel): the Planning staff who wrote
   matter 23-0026 already keep a list of ADU zoning permits by date. One email asking for "all ADU zoning
   permits issued under UDO §5.3.4B/C since 2022-02-07, by issue date and attached/detached" would give the
   series without the full permit file.

## 5. What was not done

- No adapter, tests, `nc.yaml` entry or `docs/data_provenance.md` row: the open layer has no ADU signal (§2a),
  and only aggregate queries were run against it (counts and distinct values, nothing saved), so there is
  no dataset to cite. They go in with whatever the records request returns.
- No precision/recall sample: there is no parser output to check.
- The 10 permitted ADUs are not linked to parcels. The memo lists street addresses; they are left out of this
  report on purpose.
