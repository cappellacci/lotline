# Texas readiness (thread 12, step 3)

*WS-TX, 2026-10-26; updated 2026-10-27 after the StratMap load (#238), and 2026-10-30 after the rule and fee
work (#241, #242, #244) and the land-use and jurisdiction fixes in this update. Status: **draft**. Numbers come
from the processed tables in `~/lotline-data` (rebuilt 2026-10-30) and the repo files. **No engine, scenario or
development run was made** (data-thread rule). Plan: `docs/build/tx-data-plan.md`.*

## In short

- **Texas runs end to end.** All 1,006 jurisdictions (952 places, 54 county remainders) have a Census permit
  outcome, ACS, FHFA and a demand index.
- **Parcels:** **478 count eligible parcels from real rolls** (458 places holding 69% of the people in Texas
  places, plus 20 county remainders). That is up from 458 on 2026-10-27; Wichita Falls, Burleson, Cleburne and
  Mansfield are among the newcomers. 526 stay on the ACS fallback and 2 have neither. Tiers: 125 tier 1, 176
  tier 2, 705 tier 3.
- **Places of 100,000+:** 33 of 40 count from parcels. Not counting from parcels: Houston, Amarillo, League
  City, Mesquite, Pearland, Round Rock and Tyler.
- **Rules:** 102 rule rows (`config/reforms/tx.csv`).
  - **ADU:** coded for 38 places: 22 with a rule that allows ADUs somewhere, 16 "none".
  - **Missing middle:** coded for 39 places: 10 allow 2 or more homes on some single-family lots (by right or by
    permit), 29 allow one.
  - **Second coder:** 80 rows are flagged. The worksheet is `docs/research/ordinances/tx-second-coder-2026-10-30.csv`.
- **Fees:** 55 rows (`config/fees/tx.csv`) for six cities: Austin, San Antonio (SAWS), Fort Worth, Houston,
  Dallas (tap and inspection charges only) and Corpus Christi.
- **Decision (Ben, 2026-10-30): pool Texas into the ADU estimate (D-025).** Austin and San Antonio enter as
  treated places and Fort Worth and Dallas as comparisons. WS-ENGINE implements the pooling; proposed as a
  HANDOFF decision in the PR.

## 1. Coverage of each model input

"Real" means Texas's own data for that jurisdiction; "fallback" means the method's stated default for missing
data.

| Input | Now (2026-10-30) | Fallback where missing | What closes the gap |
|---|---|---|---|
| Jurisdictions and tiers | 1,006 (952 places, 54 county remainders); tier 1: 125, tier 2: 176, tier 3: 705 | — | More counties' land use |
| Permit outcome (BPS) | All 1,006 are BPS reporters; 983 have a row in 2010-2024, 865 in all 15 years | A missing place-year is missing, never 0 (D-024) | — |
| Record-level permits | Austin 151,655 (1971-2026); San Antonio 35,695 (2020-07 on; 2,585 ETJ, under Bexar); Fort Worth 297,362 (2001 on); Dallas 134,124 (to 2024-11-12): 4 cities, 22% of the people in Texas places | BPS counts by building size; no ADU outcome | Houston has none; Dallas 2025 needs the city's workbooks or a records request |
| ADU flag | Austin (R-102), San Antonio (own permit type), Fort Worth and Dallas (description parser) | — | — |
| Denominator (eligible parcels) | **478 jurisdictions from parcels**: 198 with both StratMap rolls (2019, 2025), 178 with 2019 only, 101 with 2025 only, and Austin on its 2026 TCAD roll. Other years are ACS scaled to the rolls (D-035). Example, 2023 ADU-eligible: Wichita Falls 30,367 (ACS fallback before: 29,957) | ACS one-unit homes (D-017), quality "low", for 526 jurisdictions; 2 with neither | More counties' own codes (§3) |
| ADU rules | 38 places: 22 allow ADUs somewhere, 16 "none". Dated in the window (D-025 events), among others: Austin 2015 and 2024, San Antonio 2023, Dallas 2018 ("none", board case), Plano 2019 and 2023, Frisco 2019, College Station 2018 and 2023, McKinney 2022, Denton 2026, Lewisville 2026, League City 2026, Killeen 2026 (overlay only) | D-022 draws a rule type for uncoded places | Second coder; Pasadena (pending) |
| Missing-middle rules | 39 places. Dated changes in the window (D-024 events): Austin (HOME, 2024-02-05, 3 units), Houston (Livable Places, 2023-11-27), League City (RSF-2 duplexes, 2020-09-29), Lewisville (R-7.5, R-6, R-5 duplexes, 2022-12-01), Lubbock (up to 4 in SF-2, 2023-10-01). Allowed before the window: El Paso (R-4, R-5), Beaumont and Wichita Falls (duplex by permit), Denton (R4 by SUP), Pearland (R-4 by CUP, 2006). One home per lot: 29 places | Uncoded places count as untreated by default (D-022) | Laredo (partial), Pasadena (pending) |
| Fees | Austin: building permit fees, water and wastewater impact fees by plat date, street impact fee, meter, tap and inspection fees, parkland fee by density. SAWS water by elevation area and wastewater by basin (FY2027, plus the 2014-2015 schedule). Fort Worth water and wastewater by collection date (2025, 2026) and earlier tiers. Houston collected rates (2021 and 2026, 1 service unit per home). Dallas tap and inspection charges. Corpus Christi trust-fund lot fees | Handbook $50,000 per home (D-034) where no per-home total can be formed | A rule for fees that vary by area or plat date (§3, decision for Ben) |
| Prices | No sale prices (non-disclosure); appraised values on every TCAD and StratMap parcel | ACS values moved forward with FHFA | Nothing to collect: state law |
| Market and rates | ACS for 950 of 952 places and all 54 counties (2010-2024); FHFA; FRED | — | — |
| Demand index | 253 of 254 counties, 2010-2023 | — | — |
| Zoning | None on parcels; rule rows name their districts (`coverage_zones`); Dallas permits carry base zoning | Rule rows' coverage text | No open statewide zoning (National Zoning Atlas license) |

## 2. What Texas adds to the estimation panels

**ADU estimate (D-025), pooled (Ben, 2026-10-30).** A place enters with record-level ADU counts and a dated
rule:

| Place | Role | Years with ADU-flagged permits | Rule rows | Notes |
|---|---|---|---|---|
| Austin (4805000) | treated (2015 easing, HOME 2024) | 1971-2026 | 2010, 2015 (effective 2015-11-30), 2023, 2024 | R-102 nearly stops after HOME, when ADUs became 2- and 3-unit uses |
| San Antonio (4865000) | treated (UDC amendment, effective 2023-01-01) | 2020-07 on | 2010, 2023 | 39 to 60 ADU permits a year, 2021-2025 |
| Fort Worth (4827000) | comparison (no rentable ADU) | 2001 on | 2010 ("none") | 113 non-rental ADUs in 25 years (#222) |
| Dallas (4819000) | comparison (no by-right ADU) | 1971 to 2024-11 | 2010, 2018 (effective 2018-06-30, "none") | One ADU in the window |

Other places with dated rules (Plano, Frisco, College Station, Denton, McKinney and others) have no
record-level permits, so they cannot enter.

**Missing-middle estimate (D-024).** The outcome is BPS 2-4 unit homes, so all 232 Texas places of 10,000+
people are in. Five places have a dated change in the window (Austin, Houston, League City, Lewisville,
Lubbock). Five allow two or more homes from before 2010 (El Paso, Beaumont, Wichita Falls, Denton, Pearland).
29 are untreated on evidence rather than by default.

## 3. Remaining gaps and what closes each

| Gap | Effect | Closed by | Owner |
|---|---|---|---|
| Land use missing in many counties' 2025 records | 526 jurisdictions on the ACS denominator. Many 2025 county parts carry no land-use code at all (Travis, El Paso, Fort Bend, Montgomery, Lubbock, Smith and others), so they count from 2019 only or not at all | Ask TxGIO why the 2022, 2026 and many 2025 county parts carry no land use | **Ben** (TxGIO) |
| County codes that are land types, not uses | Williamson (Round Rock, Georgetown, Cedar Park), Galveston (League City), Bell, Denton, Brazoria and Liberty send land-type (valuation) codes. Reading them as uses would overcount house lots (Williamson's RES is about 87% single-family), so they are recorded in `config/crosswalks/tx_county_land_use.csv` with `applied = no` | Each district's property-use (state class) table in its appraisal export; Williamson's and Galveston's would bring the most places in | Me, if Ben wants it |
| Harris and Bexar codes | Harris Z1-Z5 (63k parcels) and Bexar 2025 codes are undocumented: download.hcad.org timed out, the Bexar CAD help site returned 403. Houston also stays out because its 2019 extract is partial | The districts' code tables | Later |
| Releases not read | 2024 is registered but not read (about 2.6 GB per statewide roll in memory) | Per-vintage parcel files (a WS-CORE contract change) | WS-CORE |
| Fees that vary by area or plat date | SAWS (elevation area, basin) and Fort Worth (plat cohort) have no single per-home amount, so the fee scenario uses the Handbook $50,000 there | A rule for which row stands for a typical new home, with the others as the range | **Ben** (decision) |
| Rule rows awaiting a second coder | 80 of 102. Dated events can't be relied on until checked | `docs/research/ordinances/tx-second-coder-2026-10-30.csv` (priority 1 first) | **Ben** |
| Open lookups | ADU: Pasadena; partial for McKinney, Carrollton, League City, Tyler, Edinburg. Missing middle: Laredo (partial), Pasadena. Fees: all 5 partial | `docs/research/ordinances/tx-*-lookups-todo.csv` | **Ben** |
| Dallas 2025 permits; Houston record-level permits | Dallas ends 2024-11-12; no ADU outcome for Houston | City workbooks or a records request; HCAD parcel changes | Later |
| Two places without ACS (Marshall Creek, Starbase) | No denominator | Marshall Creek should leave the jurisdictions table; Starbase's early history belongs to the Cameron County remainder | WS-CORE |

**Fixed in this update (2026-10-30):**
- Parcels outside any Texas jurisdiction (unincorporated parts of counties whose remainder is not a BPS
  reporter) are left out in `stratmap_parcels.resolve_jurisdictions`. The 200 non-jurisdiction rows that sat
  in `eligible_parcels` are gone.
- Because the county completeness check (80%) now counts only parcels inside jurisdictions, four small cities'
  2019 county parts pass it: Jefferson, Kempner, Lampasas and Mingus.
- Johnson's and Wichita's own state-category codes are now read (`tx_county_land_use.csv`, `applied = yes`).
- TCAD was rebuilt for the PTAD C and X crosswalk rows.
