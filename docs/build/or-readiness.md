# Oregon data readiness for the V9 freeze (WS-OR, steps 1–6)

*WS-OR, 2026-11-04; rules updated 2026-11-05 with Ben's agent's checks of the state-law rows (§4). Brief: `docs/build/workstreams/WS-OR.md`; test: validation plan V9. No model runs: these are
counts of the processed input tables in `~/lotline-data/processed/or`, built from `main` at b690097 (after #287
and #288), plus `config/reforms/or.csv` (after #284 and #290) and `config/fees/or.csv` (#286). Counts of blind
tables are row and year counts only; no Oregon outcome value from 2018 on was read.*

**Bottom line.** Oregon's inputs are ready for WS-ENGINE to run the frozen V9 prediction, with Oregon **not** in
`REFORM_STATES` (`model/scenarios/adu.py`).
- **168 jurisdictions** (136 cities, 32 county remainders) have BPS permits through 2017, an eligible-lot count
  (ACS fallback, tier 3) and market inputs.
- **Rules:** 556 rows. 526 are state-law rows (one per covered jurisdiction, read from the statutes and second
  coded); 30 are local rows for Portland, Bend, Metro cities that adopted early or late, five smaller cities and
  two counties (§4).
- **Fees:** Portland, Bend and Salem SDCs; Eugene water only.
- **Everything from 2018 on is blind** (V9-OR-TRANSFER, statewide). The freeze is a conditional forecast: observed
  2018–2025 market inputs are used, production outcomes are not (Ben, 2026-11-04).

## 1. Coverage of each model input (168 jurisdictions: 136 places, 32 county remainders)

| Input | Real | Fallback | Open |
|---|---|---|---|
| **Jurisdictions** | 136 of Oregon's 241 incorporated cities and towns (2.82 million of 2.99 million city residents; 4.24 million statewide) and 32 county remainders: every GEOID in BPS through 2017 | — | **105 cities have no BPS row in 2010–2017** and are outside the universe. Most are small, but they include Klamath Falls (21,813), The Dalles (16,010), Gladstone (12,017, a Metro city), Sutherlin, Madras and Milton-Freewater. Their names appear in BPS only to 2004–2005, in 537 pre-2018 rows with no GEOID. Places that first reported after 2017 can't be listed without unblinding |
| **Eligible lots (denominator)** | — | **All 168 on the ACS fallback** (D-017), 2010–2017, `low` quality, tier 3 | **Held flat from 2017.** ACS stock vintages ending 2018 or later are hidden (#287), so the last count is the 2013–2017 vintage. Model code reads eligible lots as "the latest count at or before the year" (`estimate_adu.nearest_roll`, `calibrate_adu`), so **every year 2018–2025 uses the 2013–2017 count**. That understates the base in fast-growing places (Bend, Redmond, Happy Valley) by their 2018–2025 single-family growth |
| **Parcels (RLIS, Metro)** | — | Not used for the freeze | Metro publishes **no pre-2018 RLIS taxlot archive** (the hub lists only the current roll; the yearly "Vacant and Developed Land" layers hold no taxlot attributes). The current roll is blind (snapshot rule), so RLIS joins after unblinding (step 8). The RLIS Open Database license is attribution-only, compatible with CC BY 4.0 and ODC-By, with no share-alike on derived works |
| Permits, all places | Census BPS (West Region place files) through **2017** | — | 2018 on: blind |
| Permits with an ADU flag | — | — | Portland and Bend permit adapters (step 7) aren't written yet. They're needed to **score** V9 after unblinding, not to freeze it |
| **ADU rules** | **State law for 118 universe jurisdictions** (92 places, 26 county remainders) (SB 1051: cities over 2,500, counties over 15,000, from 2018-07-01; HB 2001: no owner occupancy or added parking from 2020-01-01). **Local:** Portland (since 1998; RIP 2021, RIP2 2022), Bend (2016, 2025), Clackamas County (2014) and Marion County (2017) | The rest draw a rule type (D-022) | 49 universe places (55,401 people) are under every state threshold and have no row |
| **Missing-middle rules** | **HB 2001: 61 universe jurisdictions.** Large tier: 33 places (2.24 million people) plus the 3 Metro county remainders, all middle housing by 2022-06-30. Medium tier: 25 places, duplexes by 2021-06-30, or a year after PSU certified them over 10,000 (Independence and Lincoln City 2022-12-15, Sweet Home 2023-12-15). **2023 c.223:** 35 more places, duplexes by 2025-06-30. **SB 458** land divisions from 2022-07-01. **Local:** Portland RIP (2021-08-01, early) and RIP2; Bend (2021-11-05, early; duplexes and triplexes already allowed); 6 early and 2 late Metro adopters; Independence, Lincoln City and Sweet Home (own codes, 2022); Florence (2023); Scappoose and Stayton (duplexes in some zones before 2010) | — | HB 2138 (2027) is coded but lies after the freeze window |
| Rule tiers by population | 2020 Census (P.L. 94-171) | — | The statutes don't say how population is measured (DLCD uses PSU estimates). About 20 cities within 5% of a threshold could be in the wrong tier (listed in `logbook.d/2026-11-04-ws-or-state-law.md`). Ben's agent checked the 2,500–10,000 tier against PSU certified estimates: 3 cities moved to the medium tier (§4); the other 47 are confirmed |
| **Fees** | **Portland** $35,885 per house, $0 per ADU (waiver since 2010), $27,439 per fourplex unit. **Bend** $34,598, $6,323, $25,610. **Salem** $23,798, $0 (exempt), $20,663. All are current FY25-26/26-27 schedules | The Handbook prior of $50,000 (D-034) elsewhere | **Eugene's city SDCs are missing** (eugene-or.gov sits behind a bot check). No 2017 vintage. Portland exempts all new housing permitted 2025-08-15 to 2028-09-30 (`OR-4159000-fees-2025`). **Decision (Ben, 2026-11-04):** the per-unit baseline is the regular schedule, and the exemption stays a dated reform row (recorded in the Portland rows' `notes`). **Eugene:** Admin Order 58-25-05-F (FY26, read by Ben's agent 2026-11-04) is coded: parks, local and regional wastewater, stormwater, and transportation per trip. Trips per home come from the methodology's Appendix F (Table B-9: house 1.00, ADU 0.52, apartment 0.62, condo/townhome 0.52). Lower bounds before stormwater: a house **$14,441.89**, an ADU **$7,958.95**. The ADU figure may be $1,954.84 too high: the city's Transportation SDC page gives new ADUs a 100% transportation reduction, not confirmed in the order. Stormwater (general vs LID capacity) is still unchecked, so every Eugene `amount_per_unit_usd` stays empty and **Eugene stays on the Handbook prior** for the fees scenario. **Bend reads $23,162, not $34,598,** in `local_fees` until #247 is fixed: the newest-year rule drops Bend's FY25-26 parks row beside the FY26-27 city rows |
| Market (rent, value, rates, costs) | ACS rent and value (B25064, B25077) to 2024; FHFA; FRED; CBP | — | Used for 2018–2025 by decision (conditional forecast) |
| Demand index | processed (from CBP, not BPS) | — | — |
| **Housing need (OHNA)** | — | **Not an input to the freeze** | The official source is DAS OEA's *Oregon Housing Needs Analysis 2026 Production Targets and Adopted Methodology* (Dec 2025, PDF only, no license stated). It gives per-UGB targets and 20-year need by income band, for 2025–2045. **Every edition is built partly from post-2018 production:** underproduction from 2022–2024 ACS stock, the Metro split weighted by units built in the last five years. So it is outcome-contaminated: use it only after unblinding or for post-2025 scenarios. The 2020–21 RHNA pilot may have used about 2018 data, but its reports return 404 (unverified). Handover to WS-ENGINE for `config/params/` after the freeze |
| Holdouts | `V9-OR-TRANSFER`: all Oregon outcomes from 2018-01-01 | — | — |

## 2. What is blind, and how it was checked

`V9-OR-TRANSFER` (statewide, geoid `41`, from 2018-01-01) hides:
- every BPS place, county-remainder and state-total row from 2018 on, including rows without a GEOID (#288);
- ACS housing-stock tables (B25024, B25034, B25003) for every 5-year vintage ending 2018 or later, at all levels
  (#287);
- every Oregon parcel roll taken from 2018 on.

Not hidden, by decision (Ben, 2026-11-04, recorded in V9): FHFA, FRED, CBP, ACS rent and value, and 2020 Census
population.

Checks on the rebuilt tables (counts only):
- BPS: 4,609 rows, **0 from 2018 on**, latest year 2017.
- ACS stock variables end at end year 2017; rent and value run to 2024.
- Eligible lots cover 2010–2017 only.

**Incidents:**
1. **Null-GEOID BPS rows (fixed).** The first build on main after #287 left **8 BPS rows from 2018 on with a null
   GEOID, carrying 96 non-null permit-count cells**: the statewide prefix match never held out a null GEOID. Only
   row and cell counts were read, never values or names. WS-CORE fixed it in #288, the table was rebuilt, and
   nothing built from the bad file was used.
2. **Bend ADU approvals in a search summary.** While researching Bend's 2016 ADU ordinance, the research subagent
   read a web-search summary that mentioned Bend ADU approvals in years after 2018. The number wasn't recorded,
   used or passed on; it never reached the main session or any file. Bend ADU permits are a V9 target, so this is
   disclosed.

Portland ADU permit counts for 2009–2016 appear in the findings of Ord. 189050. They are before the window and
were not used.

## 3. What the freeze will predict

From validation plan V9; WS-ENGINE commits `results/frozen/V9-OR-TRANSFER.json` to `main` before any unblinding.
- **ADU permits per year, 2018–2025, for Portland and Bend**, each P10–P90. Rules in force:
  - Portland: ADUs since 1998, the ADU SDC waiver from 2010, SB 1051 from 2018, HB 2001's ADU rules from 2020, RIP
    (two ADUs per lot) from 2021-08-01.
  - Bend: ADUs without a conditional use permit from 2016, then the same state rows, and two ADUs per lot from
    2025-07-18.
- **2–4 unit permits (BPS) per year, 2018–2025, for every HB 2001 jurisdiction in the universe** (61: 33
  large-tier places, 3 Metro county remainders and 25 medium-tier places), and the Oregon total, each P10–P90.
  - The 35 cities newly covered in 2025 can be added to the total.
  - Gladstone (Metro) and Klamath Falls and The Dalles (medium tier) are covered by HB 2001 but not in the BPS
    universe, so they can't be predicted or scored.
- **Conditioning:**
  - eligible lots held at 2013–2017;
  - observed market inputs for 2018–2025;
  - Oregon's own uptake not fitted (Oregon is out of `REFORM_STATES`).

## 4. Rules for Ben's ordinance-validation agent

Ben asked whether his agent needs to check any ordinances. **Yes: 22 local rows and two state-law groups.** The
criteria:
- a source couldn't be opened or read;
- the coders disagreed;
- a date, threshold or coverage rests on a secondary source.

Local rows start single-coder; the table shows each one's status after Ben's agent's checks.

| reform_id | Place | What to check | Source |
|---|---|---|---|
| OR-4159000-adu-1998 | Portland | **Partly verified (Ben's agent, 2026-11-04):** owner occupancy dropped in February 1998, cap 33% of the house up to 800 sq ft, detached allowed (city adopted report, pp. 95–96). Still to check: the ordinance itself (No. 171879, adoption 1997-12-17, effective day 1998-02-02, from the first reading of a record the agent couldn't load) | https://efiles.portlandoregon.gov/record/2455968/file/document; https://www.portland.gov/sites/default/files/2020-02/accessory_structures_adopted_report.pdf |
| OR-4159000-adu-2021 | Portland | **Confirmed (Ben's agent, 2026-11-04):** 2 ADUs, the lesser of 75% or 800 sq ft, no added ADU parking; Ord. 190093 adopted 2020-08-12. Caveat: 2021-08-01 comes from the city's code-change record (directive h), not the exhibit | https://www.portland.gov/bps/planning/rip/documents/exhibit-b-volume-2-code-and-commentary/download |
| OR-4159000-adu-2022 | Portland | **Confirmed (Ben's agent, 2026-11-04):** Ord. 190851, passed 2022-06-01, in effect after 11:59 p.m. on 2022-06-30 (coded 2022-06-30, as for HB 2001's deadline) | https://www.portland.gov/sites/default/files/code/205-acc-dwelling-unit.pdf |
| OR-4159000-missing_middle-2021 | Portland | **Confirmed (Ben's agent, 2026-11-04):** 4 units (6 if half affordable) in R7, R5, R2.5; Ord. 190093 adopted 2020-08-12, effective 2021-08-01 (Ord. 190851 Finding 10) | https://www.portland.gov/bps/planning/rip/documents/exhibit-b-volume-2-code-and-commentary/download |
| OR-4159000-parking-2021 | Portland | **Confirmed (Ben's agent, 2026-11-04):** no parking minimum for household living in single-dwelling zones from 2021-08-01 (Ord. 190093; packet #198) | same as above |
| OR-4159000-missing_middle-2022-rip2 | Portland | **Confirmed with a scope correction (Ben's agent, 2026-11-04):** R10/R20 extension; attached houses, cottage clusters and SB 458 divisions in R20–R2.5 and RM1; 'detached duplexes' dropped (news page only). Still unread: the R10/R20 unit cap and the 16-home cottage-cluster limit | https://www.portland.gov/council/documents/ordinance/passed/190851 |
| OR-4159000-fees-2010 | Portland | **Partly verified (Ben's agent, 2026-11-04)** from a later city ordinance (maybe the proposed text): SDCs suspended for ADUs from 2010-03-03, first to 2013-06-30, extended to 2016-07-31 and 2018-07-31. Still to check: Res. 36766 itself and its effective date | https://efiles.portlandoregon.gov/Record/12080419/File/Document |
| OR-4159000-fees-2018 | Portland | **Partly verified (Ben's agent, 2026-11-04):** PCC 17.14.070.F confirms the 2018-08-01 start and the 10-year short-term-rental covenant; a PBOT memo ties it to Res. 37353. **Still open:** the signed ordinance (No. 189050, passed 2018-06-27) and fee_change_usd −16,130 with its dollar year | same as above; https://www.portland.gov/code/17/14/070 |
| OR-4159000-fees-2025 | Portland | **Corrected (Ben's agent, 2026-11-04):** new dwelling units including middle housing, **not ADUs** (they keep the subsection F waiver); Ord. 192082 passed 2025-07-16, effective 2025-08-15 to permits issued by 2028-09-30. −$20,000 is the city's average estimate ($15k–35k), dollar year not stated | https://www.portland.gov/code/17/14/070; https://www.portland.gov/council/documents/ordinance/passed/192082 |
| OR-4105800-adu-2016 | Bend | **Confirmed (Ben's agent, 2026-11-04):** Ord. 2260, adopted 2016-02-17: one ADU per lot, 600/800 sq ft by lot size, one extra parking space, no conditional use permit. Effective 2016-03-18 is computed from Bend's 30-day rule (city ordinance register; clause not verified) | https://bendoregon.gov/wp-content/uploads/2025/12/2260-with-Exhibits.pdf |
| OR-4105800-missing_middle-2019 | Bend | **Corrected (Ben's agent, 2026-11-04):** `[predates]` kept; the dated change is Ord. 2271 (new row below), not Ord. 2260. Still open: when duplexes and triplexes were first allowed | https://bendoregon.gov/home/showpublisheddocument/42896/637032924597730000 |
| OR-4105800-missing_middle-2016 | Bend | **New row, single source, partly verified:** Ord. 2271 (adopted 2016-09-21; effective 2016-10-21 computed) made duplexes and triplexes permitted rather than conditional in some zones. Still open: the zones, the minimum lot sizes, the verbatim quote and the ordinance's own effective clause | https://bendoregon.gov/wp-content/uploads/2025/12/Original_36_2.pdf |
| OR-4105800-missing_middle-2021 | Bend | **Partly verified (Ben's agent, 2026-11-04):** Ord. NS-2423 adopted 2021-10-06; effective 2021-11-05 per the city announcement and the 30-day rule. Still open: the ordinance text (PDF wouldn't render) | https://bendoregon.gov/wp-content/uploads/2025/12/2423.pdf |
| OR-4105800-adu-2025 | Bend | **Confirmed (Ben's agent, 2026-11-04):** Ord. NS-2532 adopted 2025-06-18, effective 2025-07-18 (city update page): two ADUs per lot, the second capped at 500 sq ft | https://bendoregon.gov/wp-content/uploads/2025/12/NS-2532-Ordinance.pdf |
| OR-4182800-missing_middle-2021 | Wilsonville | **Corrected (Ben's agent, 2026-11-04):** Ord. 851 adopted 2021-10-18, effective 2021-11-18 (stated in Section 3 and a later ordinance) | https://www.wilsonvilleoregon.gov/sites/default/files/fileattachments/ordinance/117031/ord._no._851.pdf |
| OR-4174950-missing_middle-2022-local | Tualatin | **Checked (Ben's agent, 2026-11-04):** Ord. 1463-21 adopted 2021-12-13 (not DLCD's 12-17); effective 2022-01-12, computed from its own 30-day clause | https://old.tualatinoregon.gov/sites/default/files/fileattachments/planning/project/55892/ordinance_no._1463-21.pdf |
| OR-4148650-missing_middle-2022-local | Milwaukie | **Confirmed (Ben's agent, 2026-11-04):** Ord. 2218 adopted 2022-05-03, effective 2022-06-03 as the city code states (was computed as 06-02) | https://milwaukieoregon.gov/sites/default/files/2022-0419-rs_packet_exhibits.pdf |
| OR-4126200-missing_middle-2022-local | Forest Grove | **Checked (Ben's agent, 2026-11-04):** Ord. 2022-01 adopted 2022-05-09, effective 2022-06-08 (computed from its 30-day clause). **Still open:** the end date of the Westside infrastructure extension (not in the approval; 2023-12-31 is only a forecast horizon) | https://www.forestgrove-or.gov/Archive.aspx?ADID=331; https://www.forestgrove-or.gov/Archive/ViewFile/Item/802 |
| OR-4131250-missing_middle-2022-local | Gresham | **Corrected, partly verified (Ben's agent, 2026-11-04):** Ord. 1830 adopted 2022-06-07 as an emergency (was 05-17 from DLCD), effective 2022-06-16 as the city lists it. **Still open:** why an emergency enactment shows a later effective date, and the zones (ordinance text not retrieved) | https://www.greshamoregon.gov/globalassets/government/city-codes-and-policies/development-code/development-code-amendments.pdf?id=1798 |
| OR-4174850-missing_middle-2022-local | Troutdale | **Confirmed (Ben's agent, 2026-11-04):** Ord. 879 adopted and effective on passage 2022-06-28, two days before the state row; kept as the local row | https://www.troutdaleoregon.gov/media/21991 |
| OR-4173650-missing_middle-2022-local | Tigard | **Partly verified (Ben's agent, 2026-11-04):** Ord. 22-06 adopted 2022-06-07 (council recap), effective 2022-07-07 (DLCD); the model code applied 2022-07-01 to 07-06 (DLCD guidance). Still open: the signed ordinance | https://www.tigard-or.gov/Home/Components/News/News/497/372 |
| OR-4140550-missing_middle-2022-local | Lake Oswego | **Confirmed (Ben's agent, 2026-11-04):** Ord. 2892 enacted 2022-06-07, effective 2022-07-07 (stated); the model code applied until then (city FAQ) | https://ecode360.com/LA4508/laws/LF1981067.pdf |

Also check, though not row-by-row:
- **On-time Metro cities** (no local row; the state row stands): Beaverton, Hillsboro, Oregon City, Sherwood,
  West Linn and Happy Valley.
  - Hillsboro's adoption date differs between the city (2022-05-17) and DLCD (2022-06-07).
  - Happy Valley may have been early.

**State-law rows:** the two coders agreed on every threshold, date, unit cap and owner-occupancy value, and
`by_right` was adjudicated. Two groups rested on secondary text, and Ben's agent checked both on 2026-11-05.
Its verdicts, in WS-OR's words, are in `docs/research/ordinances/or-state-law-check-2026-11-05.csv`, and the
generator adds each one to the row's notes and sets `verified_by`.

| Rows | Result (Ben's agent, 2026-11-05) |
|---|---|
| The 50 `OR-*-missing_middle-2025` rows and their `-landdiv` rows (2023 c.223 duplex tier, 2,500–10,000) | **Tier and deadline confirmed** against 2023 c.223 §§20–21; a city that hadn't acted came under the model code on 2025-06-30 (§21(3)). Land divisions follow the duplex duty, because ORS 92.031 cross-refers to ORS 197.758(3). **3 cities were in the wrong tier:** PSU's certified estimates put Independence (10,081), Lincoln City (10,067) and Sweet Home (10,097) over 10,000 before 2023, which made them HB 2001 medium cities. Their state rows now start a year after certification (computed: 2022-12-15, 2022-12-15, 2023-12-15), and each city's own earlier code has a local row (Ord. 1598, Ord. 2022-10 and Ord. 1305; the first two are `DATE UNCONFIRMED`). **Own codes before the deadline:** Florence from 2023-08-17 (new local row, `[earliest-known]`). Hood River (2021) and Madras (2022) have no date in the source, so they stay at 2025-06-30 with a note. Dayton, Millersburg, Sublimity and Toledo adopted in the first half of 2025; they're noted, not coded, because rules are read on 1 July. **Duplexes in some zones before 2010:** Scappoose (R-1 outside the floodplain) and Stayton (LD and MD) get partial-coverage `[predates]` rows. Estacada (R-1) and Tillamook (R-7.5, R-5.0) had duplexes before 2023, date unknown: note only. **Winston** (first reading 2025-08-04) and **Sheridan** (treated as not adopted) stay at 2025-06-30 |
| The 28 county `OR-<county>-adu-2018` rows | **Values confirmed** (date, at least one ADU per detached house, UGB-only coverage). **Citation corrected:** the UGB limit comes from Oregon Laws 2018 c.15 (HB 4031) §7, operative 2018-07-01 (§12), not from SB 1051. WS-OR read the session law (archived copy) and the 28 rows now cite it. **Earlier county rules:** Clackamas from 2014-10-13 (ZDO 839, Ord. ZDO-249; `DATE UNCONFIRMED`) and Marion from 2017-12-20 (Ord. 1382; changes nothing, since rules are read on 1 July 2018) get local rows. Washington had "long allowed" ADUs (no ordinance found): note only. **Local conditions noted:** Benton's owner-occupancy rule; inside UGBs Columbia applies the city's owner-occupancy rule (both barred by HB 2001 from 2020). **Not researched locally** (the agent's search budget ran out): Klamath, Lane, Lincoln, Linn, Malheur, Tillamook, Umatilla, Union, Wasco and Yamhill. Their rows stand as coded, with a note; Lane is the largest |

Blind rule: the agent saw a post-2017 count on one Clackamas page and on one Florence page. WS-OR opened neither,
records no count, and its notes don't cite either page.

All statutes were read from Internet Archive copies of the official files, because oregonlegislature.gov refused
connections from our network. A check against the live site would close that.

## 5. Remaining gaps and what closes each

| Gap | Effect on the freeze | Closes it |
|---|---|---|
| 105 cities outside the BPS universe (Klamath Falls 21,813, The Dalles 16,010, Gladstone 12,017…) | Can't be predicted or scored | **Accepted gap (Ben, 2026-11-04).** They hold 172,147 people (2020 Census), 4.1% of Oregon's 4,237,256 |
| Eligible lots held at 2013–2017 | Understates the base in growing places | RLIS current roll after unblinding (step 8) |
| Eugene stormwater (general vs LID) and the ADU transportation reduction | Eugene on the Handbook prior | Ben's agent checks the order and the Transportation SDC page; then fill `amount_per_unit_usd` |
| Bend parks SDC dropped by the newest-year rule (#247) | Bend's fee read as $23,162 instead of $34,598 | Fix #247 (WS-ENGINE), or code Bend parks FY26-27 when the district publishes it |
| Local rows single-coder | Dates may shift by weeks | Ben's validation agent (§4) |
| `DATE UNCONFIRMED` rows: Independence and Lincoln City (effective dates computed as adoption + 30 days), Clackamas 2014, Marion 2017 | Up to a year earlier or later in two places | Each city's or county's signed ordinance |
| County ADU rules not checked locally (10 counties, Lane the largest) | Earlier county rules, if any, are missed | Another pass of Ben's agent |
| Stayton's zones (the table was misaligned in extraction) | The partial-coverage share may be on the wrong zones | Read Table 17.16.070.1 |
| Portland and Bend permit adapters (step 7) | None for the freeze; needed to score | Write on synthetic fixtures, run after unblinding |

## 6. How these numbers were made

- **Data build:** `lotline fetch --state OR` on main at fbdfbb3, then `--source bps`, `jurisdictions` and `eligible`
  again on b690097 after #288.
- **Counts:** a short read-only script over those tables (row, year and non-null counts for blind tables),
  `config/reforms/or.csv` and the 2020 Census populations.
- **Rule rows:** state-law rows from `scripts/dev/or_state_reform_rows.py`; the second-coder sheet is
  `docs/research/ordinances/or-second-coder-2026-11-04.csv`.
- **Metro membership:** `config/crosswalks/or_metro_cities.csv`, from Metro's RLIS District Boundary and City
  Limits layers.
- "Universe" means the 168 GEOIDs in the BPS table through 2017. Population shares use 2020 Census P.L. 94-171.
