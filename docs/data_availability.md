# Lotline: Data Available vs. Used, by State

Hand-written companion to `docs/data_provenance.md` (which is generated and can't hold hand-written text).
It answers two questions the Rules (§8) and the Handbook (Data and Resources) ask of the data document:

1. **For each state, what data exist, what Lotline uses, and why the rest isn't used.**
2. **Could anything Lotline publishes identify a person or a single property** (re-identification and
   small-cell risk)?

**Status date:** 2026-10-19, `main` at commit `99b206c` (Texas section: 2026-10-30, after #244 and the land-use update). Every "used" entry names the module that reads the data,
so it can be checked in `src/lotline/`. "In review" means an open pull request adds it; it is not on `main` yet.
What "available" means comes from our own scouting: `docs/research/lotline-data-availability.md` (R1–R10),
`docs/research/lotline-data-catalog.csv`, `docs/research/lotline-data-catalog-mn.csv` and
`docs/research/lotline-mn-scouting.md`. Update this file in the same PR that adds or drops a source.

**How to read the "Used" column**

| Entry | Meaning |
|---|---|
| `module_name` | Read by `src/lotline/adapters/.../module_name.py` (or the named config file) on `main` |
| in review (#NN) | An open pull request adds it |
| not yet | Usable, planned, not built |
| no | Not used, on purpose; the last column says why |

## Shared by all four states

These national sources feed every state the same way.

| Data need | Available | Used | Why not / limits |
|---|---|---|---|
| Permits by building size (R4) | Census Building Permits Survey (BPS), every permit-issuing place and township, 1, 2, 3–4, 5+ units | `bps` (place level); `bps_state` (state totals, used only to check `bps`) | No ADU flag: detached ADUs sit inside 1-unit permits and conversions are left out. Places that don't report every month are imputed by Census; the adapter flags those place-years (`imputed`). 5–6 unit buildings sit inside "5+" |
| Homes by type, year built, values, rents (R1, R2, R7) | ACS 5-year tables B25024, B25034, B25077, B25064, B25003 with margins of error | `acs` | Area estimates, not parcels. 0.3–2% of estimates are suppressed by Census (small places and townships). Where a state has no parcels, ACS one-unit detached homes are the eligible-parcel fallback (`build/eligible.py`, quality always `low`) |
| Price trends (R7) | FHFA House Price Index (state, county, ZIP, tract) | `fhfa` | Thin places suppressed by FHFA (e.g. 179 of 254 Texas counties have no county index); missing years stay missing, never interpolated |
| Construction costs and rates | BLS producer price index for residential construction inputs, CPI, 30-year mortgage rate (via FRED); NAHB, Census Characteristics of New Housing and Survey of Construction (published reports) | `fred` (index and rates); `config/params/proforma.yaml` (cost per sq ft, sizes, build times, each with a source) | No local construction-cost data for any of the four states: costs are national, so the same per-sq-ft cost applies everywhere. Several proforma values are marked "approx." in the config and need re-checking |
| Fees (R8) | Handbook benchmark: $50,000 per unit, cut by 50% | `config/params/fees.yaml` | Fixed by the Handbook. Real local fees we found are much lower (see each state). No state has a machine-readable per-unit fee database |
| Geography | Census TIGERweb boundaries, 2020 geography code files, CBSA delineations | `tiger_boundaries`, `geoparts`, `cbsa`, `decennial` | One boundary vintage (2025) for every year, so annexations move points near city edges |
| Zoning (R3), every state | National Zoning Atlas | no | Its terms forbid downloading, redistributing or building derivatives without written permission, so it can't sit behind an Apache-2.0 public pipeline (data availability §0) |

## Minnesota (primary state)

| Data need | Available | Used | Why not / limits |
|---|---|---|---|
| Permits by building size (R4) | BPS; Met Council Residential Permits, 7-county metro, 2009 on, units by housing type; Minneapolis permits (new and removed units); St. Paul permits (no unit counts) | `bps`, `metc_permits`, `mpls_permits`, `stpaul_permits` | Outside the 7-county metro only BPS exists. Met Council lumps 2–4 unit buildings together ("DTQ") and 5–6 units sit in "5+". St. Paul has no unit counts and its layer stopped updating on 2025-07-01, so Met Council is the St. Paul outcome source |
| ADU / building type flag (R5) | Met Council ADU category; Minneapolis scope-of-work text; St. Paul none | `metc_permits` (ADU category), `mpls_permits` (ADU inferred from text, `type_confidence = inferred`) | Met Council doesn't say when its ADU category started. No ADU data outside the metro |
| Completions and demolitions (R6) | Minneapolis completion dates and units removed; St. Paul final dates; Met Council has no completion date | `mpls_permits`, `stpaul_permits` | Minneapolis keeps only a rolling window from Dec 2016 |
| Parcels with land use (R1) | Met Council Regional Parcels (7-county, public domain); MnGeo opt-in compilation (59 of 87 counties); Hennepin and Ramsey county layers | not yet | No Minnesota parcel adapter on `main`, so every MN jurisdiction uses the ACS fallback for eligible parcels (`acs_sf_fallback`, quality `low`) |
| Year built (R1) | Regional Parcels `YEAR_BUILT` (Hennepin leaves units and dwelling type blank); MnGeo opt-in (~43% of records outside the metro); ACS B25034 | `acs` (area level only) | Parcel-level year built waits on a parcel adapter |
| Lot size (R1) | Regional Parcels; MnGeo opt-in | not yet | As above |
| Parcel history (R2) | Regional Parcels year-end archives 2021–2025 (open); 2002–2020 services token-locked | not yet | Pre-2021 vintages need a request to Met Council |
| Zoning (R3) | Minneapolis Primary Zoning and Built Form (CC0); St. Paul zoning (public domain, service unclear); Met Council Planned Land Use (plan designations, not zoning) | no | No zoning is joined to parcels yet. The eligible-parcel rule counts a parcel with unknown zoning as single-family-only (`build/eligible.py`), which can overstate eligibility where zoning already allows more |
| Sale prices and rents (R7) | Regional Parcels last sale price and date; eCRV sales (bulk access for government agencies only); ACS; FHFA | `acs`, `fhfa` | No open sales history; parcel last-sale price waits on a parcel adapter |
| Fees (R8) | Minneapolis fees paid per permit; city fee reports under Minn. Stat. §326B.145 (PDFs); Met Council sewer availability charge | `mpls_permits` (`fees_paid_usd` = city fees and taxes per permit) | Fee reports are PDFs, not parsed. The scenario uses the Handbook $50,000 |
| Reform dates (R9) | Minneapolis triplex rule (2020-01-01) and 2040 Plan litigation; St. Paul ADU (2016, 2018) and 2023 reform; no statewide ADU or middle-housing law enacted | no | `config/reforms/` has no `mn.csv` yet. The St. Paul 2023 date appears only as the V5 blind-test window in `config/states/mn.yaml`, so St. Paul 2024–2026 outcomes stay hidden |

## North Carolina

| Data need | Available | Used | Why not / limits |
|---|---|---|---|
| Permits by building size (R4) | BPS; Raleigh permits 2000 on (units, Census land-use code); Durham City-County permits 2007 on (dwelling units); Mecklenburg permits (no unit counts) | `bps`, `raleigh_permits`, `durham_permits` | Raleigh's unit field is nearly empty from 2024, so units are rebuilt from the land-use code. Mecklenburg (Charlotte) permits have no unit counts and aren't loaded. Charlotte's BPS rows sit under Mecklenburg County (37119) and are held out for the V5 blind test |
| ADU / building type flag (R5) | Raleigh ADU type and missing-middle flags; Durham building type | `raleigh_permits` (`adu_type`, `reform_flag_raw`), `durham_permits` (ADU from building type, subtype unknown) | No ADU flag elsewhere in the state |
| Completions and demolitions (R6) | Raleigh certificate-of-occupancy date; Durham CO sign-off date | `raleigh_permits`, `durham_permits` | Raleigh demolitions only through the work class |
| Parcels with land use (R1) | NC OneMap statewide parcels (current only; each county has its own land-use codes); Wake County real estate files | in review (#121 `onemap_parcels`, ten largest counties; #122 `wake_realestate`) | On `main`, every NC jurisdiction uses the ACS fallback (`acs_sf_fallback`, quality `low`) |
| Year built (R1) | OneMap structure year (completeness varies by county); Wake files; ACS B25034 | `acs`; parcel level in review (#121, #122) | |
| Lot size (R1) | OneMap; Wake files | in review (#121, #122) | |
| Parcel history (R2) | Wake pre-revaluation December 2023 roll; NCSU Libraries county archives | in review (#122, Wake 2023 roll) | NCSU archives have unclear redistribution terms and irregular years: no |
| Zoning (R3) | City zoning layers (Charlotte UDO, Raleigh, Durham) | in review (#120, Charlotte UDO zoning translation) | Other cities not yet. Unknown zoning counts as single-family-only |
| Sale prices and rents (R7) | No statewide sale-price file (OneMap has sale date only); Wake qualified sales; ACS; FHFA | `acs`, `fhfa` | County sales files would have to be assembled county by county: not yet |
| Fees (R8) | Raleigh fee guide (~$7.4k plus 0.38% of value); Charlotte Water fees; the new statewide fee disclosure (S.L. 2026-59), first report not yet published; 2015 UNC EFC connection-fee tables | `config/reforms/nc_carthage_towns.csv` (towns named in the *Carthage* impact-fee case, with 2015 fees) | Fee schedules are PDFs; the scenario uses the Handbook $50,000 |
| Reform dates (R9) | Durham Expanding Housing Choices (2019) and SCAD (2023), Durham County (2019), Raleigh ADU and Missing Middle changes (2020–2022), Charlotte UDO (2023), Greensboro ADU change (2024), statewide ADU law S.L. 2026-59 (effective 2027) | `config/reforms/nc.csv` (14 coded reform components) | |

## Ohio (sparse-evidence state)

| Data need | Available | Used | Why not / limits |
|---|---|---|---|
| Permits by building size (R4) | BPS (Ohio townships issue few permits); Columbus permits 2010 on (Census building-type code, units); Cincinnati permits (units); Cleveland permits (no unit counts, ODbL license) | `bps`, `columbus_permits`, `cincy_permits` | Cleveland: no unit counts, and its ODbL share-alike license needs care: no |
| ADU / building type flag (R5) | Cincinnati work descriptions; Franklin County Auditor permit file (work descriptions for Columbus and its suburbs, 1990 on); Columbus Council variance ordinances (Legistar, 2003 to 2025) | `cincy_permits` (ADU from text), `franklin_permits` (ADUs outside Columbus), `columbus_permits` (ADU flags joined from the auditor file by permit number), `columbus_variances` (ADU approvals), `montgomery_permits` (ADUs from the Montgomery Auditor's CAMA permit notes) | Read from free text with named rules that favour recall (2026-10-28): Columbus permits flagged for 2019 to Sep 2025 rose from 14 to 34 against the 57 ADU permits the city reports. Council variances add the approvals a Columbus ADU needed before Ord. 2526-2025: 121 for that period against the city's 110, an upper bound on built ADUs (the panel keeps the larger source each year). The auditor file is not a complete record of new houses, so it supplies ADUs only |
| Completions and demolitions (R6) | Cincinnati CO date; Columbus last status date (a proxy) | `cincy_permits`, `columbus_permits` | |
| Parcels with land use (R1) | Ohio Statewide Parcels (88 counties, land-use class and lot area only); county auditor layers (Summit Fiscal Office; Lucas yearly cadastres 2013–2025; Cuyahoga Fiscal Office) | `oh_parcels` (all 88 counties; blank land use in Summit, Lucas, Cuyahoga and Butler filled from the county layers) | Still on the ACS fallback (D-017, over 10% unknown): Dayton 18.6% (Montgomery's county server fails TLS verification), Hamilton 10.4% (Butler parcels with no appraisal record), Middletown 15.2% (its Warren County part; no open Warren layer found). Lucas's yearly cadastres (2013–2025) have no land use, only parcel shapes |
| Year built (R1) | Not in the statewide layer; Summit (`RESYRBLT`), Cuyahoga (`min_age`) and Butler (`YRBLT`) county layers; Franklin County Auditor `Dwelling.xlsx` (`YRBLT`, one row per dwelling card); ACS B25034 | `oh_parcels` (Summit, Cuyahoga, Butler, Franklin), `acs` | Lucas and Montgomery publish no parcel year built; Montgomery's geodatabase has no parcel land-use code either |
| Lot size (R1) | Statewide layer `LandArea`, else polygon area | `oh_parcels` | Franklin leaves `LandArea` empty for 97.5% of parcels, so lot sizes there are GIS polygon areas |
| Parcel history (R2) | 2022 statewide vintage (login required); Franklin Auditor archives | no / not yet | The 2022 vintage is token-gated and skipped |
| Zoning (R3) | Columbus base zoning (CC0) | not yet | Unknown zoning counts as single-family-only |
| Sale prices and rents (R7) | County auditor transfer files (88 different systems); ACS; FHFA | `acs`, `fhfa` | No statewide sales file |
| Fees (R8) | Columbus water and sewer capacity charges; no state fee reporting | not yet | The scenario uses the Handbook $50,000 |
| Reform dates (R9) | Cincinnati Connected Communities (2024), Columbus Zone In (2024) and ADUs (2025), Cleveland form-based code (2024) | `config/reforms/oh.csv` (8 coded reform components) | No mature statewide reform: Ohio results lean on the mechanism and out-of-state evidence |

## Texas ("no sale prices" state)

| Data need | Available | Used | Why not / limits |
|---|---|---|---|
| Permits by building size (R4) | BPS; record-level permits for Austin (Census class codes), Fort Worth (filed 2001 on, unit counts), Dallas (1971 to 2024-11, unit counts), San Antonio (2020-07 on, no unit field); Houston monthly aggregates only; Collin CAD and Arlington only from 2023 | `bps`, `austin_permits`, `fw_permits`, `dallas_permits`, `sa_permits` | Fort Worth and Dallas apartment permits repeat project totals and have no parcel number; D-036 groups them by same day and unit count (#230). Dallas's layer ends 2024-11-12 (move to DallasNow); its Socrata set (2018-2025) has no unit field and no license. San Antonio's 2-4 and 5+ units stay with BPS. Houston has no record-level permits |
| ADU / building type flag (R5) | Austin class R-102; San Antonio's "Res Accessory Dwelling Permit" type; Fort Worth and Dallas only in work descriptions | `austin_permits`, `sa_permits`, `fw_permits`, `dallas_permits` (description parser) | R-102 nearly stops after HOME (2024), when ADUs became 2- and 3-unit uses. Fort Worth's ADUs are non-rental (its rule), Dallas has one in the window |
| Completions and demolitions (R6) | Austin completion dates and demolitions; Fort Worth final-inspection dates | `austin_permits`, `fw_permits` | Demolitions are not in the Fort Worth, Dallas or San Antonio record sets used |
| Parcels with land use (R1) | TCAD roll (Travis); TxGIO StratMap Land Parcels, statewide, CC0, from 253 appraisal districts (2019, 2021-2026); Harris CAD | `tcad_parcels` (City of Austin, Travis County part); `stratmap_parcels` (2019-03 and 2025-06 releases, 21.0M parcels; own file geodatabase reader, #238) | Ben downloads and registers both by hand. StratMap's 2022 and 2026 releases carry no land-use codes, so they are not read; partial county extracts (under 80% of the county's parcels in the other release) are left out. Counties with 90%+ known land use: 63 (2019), 65 (2025). Johnson's and Wichita's own state-category codes are read (`config/crosswalks/tx_county_land_use.csv`); other districts' codes are land types and are not used. 478 of 1,006 jurisdictions count from parcels; Houston does not (partial 2019 extract, undocumented Harris Z codes). Parcels outside any Texas jurisdiction are left out. Austin stays on TCAD (`parcel_sources`) |
| Year built (R1) | TCAD improvement year built; StratMap (filled by some districts only); ACS B25034 | `tcad_parcels`, `stratmap_parcels`, `acs` | StratMap has year built for 33% (2019) and 36% (2025) of parcels; tiers 125 / 176 / 705 |
| Lot size (R1) | TCAD land size; StratMap legal and GIS areas, and the polygons | `tcad_parcels`, `stratmap_parcels` | Stated areas where a unit is given; else the polygon's true area (Web Mercator corrected for latitude) |
| Parcel history (R2) | TCAD annual rolls; StratMap collections 2019 and 2021-2026 | `stratmap_parcels` (2019 and 2025 rolls as D-035 anchors) | 198 jurisdictions have both rolls; the 2024 release is registered but not read (memory: per-vintage files would need a WS-CORE change) |
| Zoning (R3) | Austin zoning GIS; Dallas permits carry base zoning; Mercatus DFW 2024 file (license not stated) | no | Parcels carry no zoning; the HOME reform rows name the zones (SF-1 to SF-3) in `config/reforms/tx.csv` |
| Sale prices and rents (R7) | Sale prices are confidential in Texas (non-disclosure, Tax Code §22.27); MLS and Zillow terms don't allow redistribution; appraised values (TCAD, StratMap); ACS; FHFA | `tcad_parcels` and `stratmap_parcels` (appraised values, `value_basis = appraisal`), `acs`, `fhfa` | No transaction prices: the pro forma uses appraised values and ACS values moved forward with FHFA |
| Fees (R8) | City and utility fee schedules and impact-fee ordinances | `config/fees/tx.csv` (55 rows: Austin permit, impact, meter, tap and parkland fees; SAWS by elevation area and basin; Fort Worth by collection date; Houston collected rates 2021 and 2026; Dallas tap and inspection charges; Corpus Christi lot fees) | SAWS and Fort Worth fees vary by area or plat date, so no single per-home amount is formed yet (a rule is proposed to Ben); places without a per-home total use the Handbook $50,000 (D-034). Dallas: no impact fee found, not officially confirmed |
| Reform dates (R9) | City ordinances and code PDFs (Ben's two research workbooks and his own lookups, 2026-10-27 to 30); the zoneomics.com mirror; 2019 and 2025 state laws | `config/reforms/tx.csv` (102 rows) | ADU rules for 38 places (22 allow ADUs somewhere, 16 "none"); missing-middle rules for 39 (5 dated changes in the window: Austin, Houston, League City, Lewisville, Lubbock). 80 rows await a second coder (`docs/research/ordinances/tx-second-coder-2026-10-30.csv`); open: Pasadena, Laredo (partial) |

## Biggest gaps, by state

- **Minnesota:** no parcels, zoning or coded reforms on `main` yet, so the eligible-parcel denominator is the
  ACS fallback (quality `low`) everywhere, even though rich open metro parcels exist.
- **North Carolina:** parcels (#121, #122) and Charlotte zoning (#120) are in review; until they merge, NC is in
  the same ACS-fallback position. No sale prices statewide.
- **Ohio:** parcels for 2 of 88 counties, with land use and lot size only (no year built, units or values).
  No ADU flag in Columbus. Thin reform evidence by design.
- **Texas:** StratMap parcels are loaded (2019 and 2025 releases), but many counties' 2025 records carry no
  land use and several send land-type rather than use codes, so 526 of 1,006 jurisdictions, Houston among them,
  stay on the ACS denominator; no sale prices (state law); record-level permits for four cities, with repeated
  apartment totals in two (D-036); 80 rule rows await a second coder.
- **All states:** no open zoning statewide (National Zoning Atlas license), national construction costs only,
  and fees fixed at the Handbook's $50,000.

## Re-identification and small-cell risk

**What Lotline holds.** Downloaded data stay in `LOTLINE_DATA_DIR`, outside the repository, and are never
committed (CLAUDE.md; `data/` is gitignored). Two kinds of record-level data are held there:

- **Parcel rolls: no owner or mailing fields.** Each parcel adapter lists exactly the fields it reads, and none
  is an owner name or a mailing or situs address:
  - `oh_parcels`: `OUT_FIELDS` is object ID, county, parcel IDs, land-use class, land area, export date and
    polygon area. Situs and mailing address fields are listed in `PERSONAL` and a test checks they are never
    requested (`tests/states/oh/test_oh_parcels.py`).
  - `tcad_parcels`: the fixed-width roll is sliced only at the positions in `PROP_FIELDS`, `PROP_ENT_FIELDS`,
    `STATE_CD_FIELDS`, `LAND_DET_FIELDS` and `IMP_DET_FIELDS` (IDs, values, land-use codes, acreage, year
    built, taxing entity). Owner names, owner and mortgage-company addresses, deeds and the situs address are
    never sliced from the record. It does read the homestead flag (`hs_exempt`), which says whether the owner
    lives there; that stays in the data directory.
  - Minnesota and North Carolina have no parcel adapter on `main`; #121 and #122 should be reviewed against
    the same rule.
- **Permits: no names or street addresses, but they point to properties.** Every permit adapter requests a
  fixed field list that leaves out applicant, owner and contractor names and street addresses (`FIELDS`,
  `OUT_FIELDS` or `SELECT` in each module; tests for Minneapolis, St. Paul, Columbus, Cincinnati and Austin
  check the `PERSONAL` fields are never requested). They do keep parcel IDs, and St. Paul (latitude and
  longitude) and Durham (point geometry) also request a location. A parcel ID or a point identifies one property, so
  permit and parcel tables are treated as address-level data: used inside the pipeline, never published
  record by record.

**What Lotline publishes.** Only counts and rates for whole jurisdictions (a city, township or county), regions
and the state, never a parcel, permit or address. Committed reports (`reports/<state>/V0*.md`) hold
place-by-year totals only.

**Small cells.** Decision D-015 (pending: PR #137, not yet on `main`) sets a publishing minimum,
`min_eligible_parcels_publish` = 20 eligible parcels (tested range 10–50) in `config/params/aggregate.yaml`. A
place below it is folded into its county or region and never shown alone. Nothing reads the parameter yet;
the aggregation step and the app must apply it before any place-level result is published. A small place can
still have very few permits in a year. Those counts come from public BPS and city records, so a published
count adds nothing a reader couldn't already look up, but the minimum keeps a single home from standing out
as its own result.

**Suppression in the sources.** Census suppresses 0.3–2% of ACS estimates and Lotline keeps the margins of
error. FHFA suppresses indexes for thin places. Census imputes BPS months a place didn't report, and Lotline
flags those place-years. Lotline never fills a suppressed cell by interpolation, so it never re-creates a
number a publisher held back.
