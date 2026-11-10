# Cary ADU permits: scout and first counts

*Data thread, 2026-11-10 (branch `claude/nc-cary-permits-7aa92e`). No engine, scenario or calibration runs:
these are descriptive counts of one processed input table.*

**Verdict: usable.** Cary publishes every permit application since January 2019 as open data (CC0 on the
dataset page). The data has a Wake PIN, housing units and Census-style permit types. The adapter
`src/lotline/adapters/states/nc/cary_permits.py` reads it. Cary issued **43 ADU permits from 2019 to
2026-11-09**: about 3 a year to 2023, 13 in 2024, 6 in 2025 and 11 so far in 2026. Against about 38,000–40,000
eligible lots, that is 0.8 per 10,000 lots a year before 2024 and 1.5–3.3 since. **Most of Cary's ADUs were
called "utility dwelling units" (UDUs) before June 2025.** A search for "ADU" alone would have found only
6 of the 29 units issued before ACT 32 (19 say "UDU"; 4 say "accessory dwelling").

## 1. Sources found

| Candidate | URL | Format | Years | Rows | ADU signal | Parcel ID | Units | License / terms | Usable? |
|---|---|---|---|---|---|---|---|---|---|
| **Building Permit Applications** (`permit-applications`) | https://data.townofcary.org/explore/dataset/permit-applications/ | Opendatasoft dataset; CSV export (42.1 MB, 88,219 rows on 2026-11-10, daily) | Applied 2019-01-02 to now (current permit system) | **Applications**, not permits (one application can produce several permits) | Description text; one dedicated `ADU` permit type (used once, 2020) | `PIN` (Wake PIN, leading zero dropped; empty on the Chatham side) | `Housing Units` (filled on multifamily) | Dataset page: **CC0 1.0 Universal**. Portal terms of service: all data under **ODbL v1.0**, attribute to the Town of Cary, no endorsement claims | **Yes**: by hand download (below) |
| Building Permit Inspections (`permit-inspections`) | https://data.townofcary.org/explore/dataset/permit-inspections/ | same portal | 2015 to now | Inspections | None of its own | — | — | same | No: no permit facts beyond the application table |
| Solar Permit Applications | same portal | subset (PVRS) | — | — | — | — | — | same | Not relevant |
| Accessory Use Permits (`DEV4` rows in the same table) | same dataset | — | 2019–2020 only | Zoning approvals | "ACCESSORY USE PERMIT - UTILITY DWELLING" etc. (10 rows) | PIN on 9 | — | same | Cross-check only (§4) |

No ArcGIS Hub permit layer and no pre-2019 permit file is on the portal. Earlier permits sit in Cary's old
permit system and would need a records request (§7).

**Terms and access.** There is no personal-use or no-redistribution clause, so nothing blocks us. Two points
to know:

- **License mismatch.** The dataset page says CC0. The portal's terms page says everything is under ODbL v1.0
  with attribution. Lotline commits no data, and its outputs are counts (an ODbL "Produced Work"), so either
  license works. The adapter's `PROVENANCE` carries an attribution line ("Contains data from the Town of Cary,
  North Carolina") to meet ODbL.
- **robots.txt.** `data.townofcary.org/robots.txt` disallows `/api/`, `/explore/download` and
  `/explore/dataset/*/download` for every user agent. As with the Wake roll, the adapter never fetches. A person
  exports the CSV in a browser and registers it:

  ```bash
  uv run lotline manifest register ~/Downloads/permit-applications.csv --source cary_permits --url https://data.townofcary.org/explore/dataset/permit-applications/ --license "CC0 1.0 (dataset); portal terms: ODbL 1.0 with attribution to the Town of Cary"
  ```

  The scout read the dataset pages in a browser like any visitor. It made one API catalog call before reading
  robots.txt and none after.

**A manifest note.** The first registration (2026-11-10 09:10 UTC, 29.5 MB) was overwritten in place by a
second, complete export (42.1 MB, 88,219 rows, the portal's own count). `register` hard-links the Downloads
file into `raw/`, so the overwrite changed both. The stale entry is superseded in `manifest.superseded.jsonl`,
and the complete file is registered (sha256 `a85a87e1…`). **Next time, save each export under a new file name,
or move it out of Downloads after registering.**

## 2. Fields used and checks

| Field | Use |
|---|---|
| Permit Number | `permit_id` (format `YY-NNNNNNNN`) |
| Permit Type / Permit Type Mapped / Work Class | BPS-style codes: B101 new detached house, B102 townhouse, B103–B105 two-family to 5+, B417 residential accessory, B434 residential alteration/addition, B438 garage/carport/shed, B645 house demolition (`config/crosswalks/nc_cary_permit_types.csv`) |
| Issue Date, Status Current Mapped | Kept only when issued and not "Permit Cancelled" |
| Jurisdiction | **TC** (Cary, Wake side: 85,251 rows) and **CC** (Cary's Chatham side: 2,608 rows, longitude about -78.92, no PIN) are Cary. TOM (Morrisville, 231), WC (Wake County, 71), APEX (26) and RTP (3) are sites outside the town and are dropped |
| PIN | `parcel_id`, padded to 10 digits (`0764681923`). It matches the Wake roll's PIN column, which `wake_realestate` does not read yet |
| Housing Units, Total SqFt, Project Cost, Applied/Completed/CO dates | units, floor area, valuation, application and final dates |

Addresses, coordinates, owner and contractor fields are never read. The description is read in memory for
the ADU rule and is not kept.

**Check against Census BPS (Cary town, 3710740).** With the Chatham side included, new one-unit homes (SFD +
TH) match BPS within about 1% in 2020, 2021, 2023, 2024 and 2025 (3% in 2022). 5+ family units match within
1% in 2021–2024. **2019 is short** (723 against 805 one-unit homes; 349 against 718 multifamily units) because
applications filed in the old system before 2019 are missing. 2020 multifamily is also short (268 against
717). Treat 2019 as partial and 2020 as partial for multifamily. ADUs never reach BPS, so BPS can't check them.

| Year | SFD + TH (adapter) | BPS units_1 | 5+ units (adapter) | BPS units_5p |
|---|---|---|---|---|
| 2019 | 723 | 805 | 349 | 718 |
| 2020 | 796 | 798 | 268 | 717 |
| 2021 | 964 | 964 | 1,336 | 1,337 |
| 2022 | 547 | 563 | 900 | 903 |
| 2023 | 336 | 326 | 989 | 949 |
| 2024 | 368 | 370 | 675 | 680 |
| 2025 | 427 | 431 | 288 | 256 |

## 3. The ADU rule

Cary files nearly every ADU as an alteration/addition (B434), a garage/shed (B438) or a residential accessory
permit (B417). Only the description says the permit adds a dwelling. The shared parser
(`lotline.parse.permit_text`) reads an ADU only as new construction, so it misses common Cary phrasings ("ADU
ADDITION W/ PORCH", "Remodel Lower Level for ADU", "Addition - UDU, Screen Porch, & Deck"). The adapter has
its own narrow rule, `cary_permits.adu_from_text`:

- **Counts:** "ADU", "accessory dwelling", "acc use dwelling", and Cary's pre-ACT 32 **"utility dwelling unit"
  / "UDU"**. The Town defined a UDU as a housekeeping unit inside the house with its own cooking and bathroom
  facilities and its own outside entrance (Planning and Development Services checklist, Oct. 2024). That makes
  a UDU an internal or attached ADU. ACT 32 merged the two terms in June 2025.
- **Doesn't count:** removing or demolishing the unit, an *existing* unit, "NOT A UDU", repairs/re-roofs/decks
  on the unit, "adult", "guest house/suite", "in-law suite", "kitchenette" and "wet bar".
- **Applies only to** residential B434/B438/B417 permits, plus the dedicated `ADU` type. A new house (B101)
  that names an ADU would stay one house. No such permit exists.
- **Type:** detached ("detached", "det.", "cottage") first, then internal conversion (convert, basement,
  lower level, finish attic/bonus room), then attached ("attached", "addition", or a UDU with no other cue).

Tests `tests/states/nc/test_cary_permits.py` cover 31 hand-worked phrasings taken from Cary's real
descriptions, plus synthetic permits for every kept/dropped rule (40 tests, no real data).

## 4. Counts

**ADU permits issued, Cary (3710740), by issue year.** Eligible lots are from
`processed/nc/eligible_parcels/eligible.parquet` (theme `adu`, Wake roll; 2019 and 2023 are real rolls, 2020–2022
interpolated, 2024 ACS-scaled; 2025–2026 use the 2024 count).

| Year | ADU permits | attached | detached | internal | unknown | eligible lots | per 10,000 lots |
|---|---|---|---|---|---|---|---|
| 2019 | 3 | 2 | 1 | 0 | 0 | 37,929 | 0.79 |
| 2020 | 1 | 0 | 0 | 0 | 1 | 38,272 | 0.26 |
| 2021 | 3 | 3 | 0 | 0 | 0 | 38,614 | 0.78 |
| 2022 | 3 | 2 | 1 | 0 | 0 | 38,957 | 0.77 |
| 2023 | 3 | 2 | 0 | 1 | 0 | 39,300 | 0.76 |
| 2024 | 13 | 7 | 3 | 3 | 0 | 39,762 | 3.27 |
| 2025 | 6 | 3 | 0 | 3 | 0 | (39,762) | 1.51 |
| 2026 (to Nov 9) | 11 | 4 | 5 | 2 | 0 | (39,762) | 2.77 (partial year) |
| **Total** | **43** | 23 | 10 | 9 | 1 | | |

- **Timing against ACT 32 (effective 2025-06-02):** 29 permits were issued in the 6.4 years before (about 4.5 a
  year) and 14 in the 5 months of 2025 and the 10 months of 2026 after (about 9.9 a year). Detached units went
  from 5 of 29 (17%) to 5 of 14 (36%). Detached ADUs were limited to R-80/R-40/R-20 before ACT 32, so this
  shift is the first sign of a response. The numbers are small. The 2024 jump (13) came before ACT 32 and is
  mostly UDUs.
- **Applications.** 55 residential applications name an ADU/UDU (applied 2019–2026): 44 issued, 10 cancelled, 1
  in review. One more is on a Wake County (WC) site. The pipeline in 2026 is the largest yet: 16
  applications.
- **All 43 are on the Wake side (TC).** None are on the Chatham side. 39 of the 43 carry a PIN for later
  matching with the Wake-roll counts (`ws/nc-wake-roll-adu`). The 4 without a PIN are on the Wake side with the
  PIN left blank.
- **32 of 43 have a final date** (certificate of occupancy or completion). The 11 open ones are mostly
  2026.
- **Zoning cross-check (DEV4 "Accessory Use Permits").** In 2019–2020 Cary also filed a zoning approval for
  each ADU/UDU: 10 such rows, 6 finaled and 4 cancelled. The 6 finaled sit beside 4 building permits issued in
  2019–2020. Some approvals may lead to permits issued later, so this neither shows nor rules out missed
  permits. After 2020 these approvals are no longer
  in the table.

**Denominator caveat.** Cary's eligible lots come from the Wake roll only (`parcel_sources`: `wake_realestate`).
The Chatham side of Cary is not in the denominator. That fits here, because none of the ADUs are on the Chatham
side. But any rate that adds Chatham permits (new houses, say) needs the Chatham parcels too.

## 5. Hand check

**Matches: all 43 read by hand** (more than the 30 asked for).

- **Precision 43/43.** Every match describes a new unit: a detached ADU, a UDU addition, or a basement,
  garage or upper-floor conversion. 42 come from the description rule; one has the dedicated `ADU` permit type.
- **ADU type:** 41 of 43 look right. "Finishing area over garage for a utility dwelling" and "ATTACHED GARAGE
  W/ACCESSORY DWELLING UNIT" are typed attached; the garage is attached, so that is defensible. "ADU; SCRN
  PCH; REMODEL; DECKS; UNF BSMT" (internal) and "ADDITION/REMODEL/UDU/PORCHES" (attached) are ambiguous.
- **No double counts.** No two ADU matches share a PIN (39 with a PIN).

**Non-matches: 30 drawn at random** (seed 20261110) from the 12,888 kept residential B434/B438/B417 permits
without a match. All 30 are clearly not ADUs: decks, porches, kitchen and bath remodels, foundation repairs, a
bonus room finished into the attic. **Recall in a random draw: no misses (0/30).** A random draw rarely hits a
rare event, so a targeted search follows.

**Targeted near-miss search.** 96 non-matches mention a kitchen in a basement, garage or attic, an in-law or
guest suite, a kitchenette, a studio, "dwelling", or a wet bar. Read by hand:

- **Missed then fixed in the rule:** "FINISH UTILITYDWELLING UNIT ON 2ND FLOOR" (2022) and "RENOVATION AND
  ADDITION W/ ACC USE DWELLING" (2021). Both are now counted and in the totals above. One more is the
  dedicated ADU permit type, which was dropped because its `Permit Type Mapped` is blank (fixed).
- **Likely ADU, not counted:** "DWELLING UNIT ADDITION & DECK" (2025). It is a single phrase, so we left it
  out for precision.
- **Possible ADUs that the text can't confirm (not counted):** 2 in-law suite additions (2026), 1 detached
  guest house (2024), 1 guest suite in a living-room conversion (2020), and 11 basement finishes that add a
  kitchen (2019–2026, for example "FINISH BASEMENT w/ KITCHEN, BATH & ENT ROOM"). Cary required a
  UDU or ADU designation for a second unit, and a reviewer approved each of these as an alteration without one.
  So we treat them as family space, not separate units. **Upper bound if every one were an ADU, plus the
  "DWELLING UNIT ADDITION": 16 more over 2019–2026 (+37%).**
- The rest are kitchen remodels, wet bars, art studios, pool houses with a half bath, and similar.

**Estimated recall: 43 of 44 to 59 likely units (73–98%).** The low end assumes every possible case is an
ADU, which is unlikely for the basement kitchens.

## 6. Cary ADU rules: proposed rows (not written to `config/reforms/nc.csv`)

`config/reforms/nc.csv` already has `NC-3710740-adu-2025` (ACT 32) and `NC-SL2026-59-3710740` (state
mandate). This scout proposes **one new row and corrections to the ACT 32 row**. Sibling sessions edit that file,
so the rows stay here for Ben to fold in.

**Proposed new row: the rule before ACT 32 (`[predates]`, never an event).**

| field | proposed value |
|---|---|
| reform_id | `NC-3710740-adu-pre2019` |
| component | `[predates]` LDO §5.3.4(A) accessory dwelling unit as an accessory use, one per lot, up to the lesser of 33% of the house or 800 sq ft, 1 parking space per bedroom; detached ADUs only in R-80, R-40, R-20 (and some PDD/TC); §5.3.4(B) utility dwelling unit (internal, own kitchen, bath and entrance) in most residential districts, 2 extra parking spaces |
| status | in_force (until 2025-06-02, superseded by NC-3710740-adu-2025) |
| adoption_date / effective_date | unknown; the ADU text is in force by Sept 2005 (the LDO took effect 2003-07-01) → leave blank, tag `[predates]` |
| end_date | 2025-06-01 |
| by_right | True |
| owner_occ | False (no owner-occupancy rule in the text) |
| adu_max_sqft | 800 |
| adu_detached_allowed | False for most districts (True only in R-80/R-40/R-20): code as False with `coverage_zones` = "detached: R-80, R-40, R-20 only; attached/internal (UDU): most residential districts" |
| adus_per_lot | 1 |
| parking / parking_min_per_unit | 1 per bedroom (ADU); 2 (UDU) / 1 |
| source_url | https://www.volusia.org/core/fileparse.php/4554/urlt/26-Affordable-Housing-Accessory-Dwelling-Units-a-Cary-Nort.pdf (2005 text of §5.3.4(A)); https://www.carync.gov/home/showpublisheddocument/1360/637861474077670000 (Planning checklist, Oct. 2024: UDU definition, 33%, 2 spaces); https://ca.news.yahoo.com/cary-could-allow-more-bigger-202209391.html (N&O, 2024-01-17: detached only in R-80/R-40/R-20, about 25 ADUs permitted) |
| coding_notes | "Permits from 2019 show the rule in use: 3 ADU/UDU permits a year 2019–2023 (reports/nc/cary-adu-scout.md). When UDUs and the R-80/R-40/R-20 limit were added is unconfirmed (candidate amendments 2008-LDO-01 to 2017-LDO-01); both predate the 2019 permit record." |

**Proposed corrections to `NC-3710740-adu-2025` (ACT 32).** The row is right in substance. The current LDO
text (American Legal, Supp. No. 62, Ch. 5 §5.3.4(A)) confirms it and adds:

- `source_url`: replace the bare `https://www.carync.gov/` with
  https://files.amlegal.com/pdffiles/Cary_pdf/LDO_Ch05.pdf (§5.3.4(A), Table 5.1-1) and
  https://housing.carync.gov/cary-expands-options-for-adus/ (in effect June 2).
- `owner_occ`: False (the adopted text has no owner-occupancy rule).
- `adus_per_lot`: 1 (§5.3.4(A)(4)).
- `coding_notes`: the size cap is the lesser of 50% of the house or 800 sq ft (1,000 sq ft on lots of 40,000+
  sq ft). Conversions of an existing floor are capped at 50% only. Detached ADUs in R-12, R-8 and TR may be no
  taller than the house. Temporary health care structures (G.S. 160D-915) count as ADUs. The LDO's history
  note cites Ord. 2025-CODE-01 (4-10-25); that it is ACT 32 is likely but unconfirmed.
- **Second-coder view on the 2025 row:** agree on the date (adopted 2025-04-10, effective 2025-06-02) and on
  by_right, 800 sq ft and parking 1. In the 2019–2026 permits the ADU type mix shifts towards detached units
  after June 2025 (5 of 14, against 5 of 29 before), as the rule change predicts.

No change is proposed to `NC-SL2026-59-3710740` (state mandate, effective 2027-01-15).

## 7. Records request (optional, for Ben to send)

The portal starts in 2019. To extend Cary's ADU series back to 2010 (before-and-after periods for D-025), send
this to the Town of Cary public records portal (https://www.carync.gov/ → Public Records Request):

> Under the NC Public Records Law (G.S. 132-1), please provide, in electronic form (CSV or Excel), a list of all
> building permits issued from January 1, 2005 through December 31, 2018 whose description or permit type refers
> to an accessory dwelling unit, utility dwelling unit, accessory use permit for a dwelling, or "ADU"/"UDU". For
> each, please include: permit number, permit type, work description, application date, issue date,
> certificate of occupancy or final date, status, and parcel PIN. Owner names and contact details are not
> needed. A count by year is also helpful if a full list is not practical.

## 8. Limitations

- Rows are applications. One application can produce several permits, but ADUs appear once each.
- The series starts in 2019, so the only in-window rule change it sees is ACT 32 (2025). Before 2019 it has no
  data.
- ADUs are read from text, so a unit described only as an "in-law suite" or a basement apartment is missed
  (§5).
- 2026 is a partial year, issued to 2026-11-09.
- The export changes daily. Counts are for the registered file of 2026-11-10 (sha256 `a85a87e1…`).
