# Oregon data readiness for the V9 freeze (WS-OR, steps 1–6)

*WS-OR, 2026-11-04. Brief: `docs/build/workstreams/WS-OR.md`; test: validation plan V9. No model runs: these are
counts of the processed input tables in `~/lotline-data/processed/or`, built from `main` at b690097 (after #287
and #288), plus `config/reforms/or.csv` (after #284 and #290) and `config/fees/or.csv` (#286). Counts of blind
tables are row and year counts only; no Oregon outcome value from 2018 on was read.*

**Bottom line.** Oregon's inputs are ready for WS-ENGINE to run the frozen V9 prediction, with Oregon **not** in
`REFORM_STATES` (`model/scenarios/adu.py`).
- **168 jurisdictions** (136 cities, 32 county remainders) have BPS permits through 2017, an eligible-lot count
  (ACS fallback, tier 3) and market inputs.
- **Rules:** 547 rows. 526 are state-law rows (one per covered jurisdiction, read from the statutes and second
  coded); 21 are local rows for Portland, Bend and Metro cities that adopted early or late.
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
| **ADU rules** | **State law for 118 universe jurisdictions** (92 places, 26 county remainders) (SB 1051: cities over 2,500, counties over 15,000, from 2018-07-01; HB 2001: no owner occupancy or added parking from 2020-01-01). **Local:** Portland (since 1998; RIP 2021, RIP2 2022), Bend (2016, 2025) | The rest draw a rule type (D-022) | 49 universe places (55,401 people) are under every state threshold and have no row |
| **Missing-middle rules** | **HB 2001: 58 universe jurisdictions.** Large tier: 33 places (2.24 million people) plus the 3 Metro county remainders, all middle housing by 2022-06-30. Medium tier: 22 places, duplexes by 2021-06-30. **2023 c.223:** 38 more places, duplexes by 2025-06-30. **SB 458** land divisions from 2022-07-01. **Local:** Portland RIP (2021-08-01, early) and RIP2; Bend (2021-11-05, early; duplexes and triplexes already allowed); 6 early and 2 late Metro adopters | — | HB 2138 (2027) is coded but lies after the freeze window |
| Rule tiers by population | 2020 Census (P.L. 94-171) | — | The statutes don't say how population is measured (DLCD uses PSU estimates). About 20 cities within 5% of a threshold could be in the wrong tier (listed in `logbook.d/2026-11-04-ws-or-state-law.md`) |
| **Fees** | **Portland** $35,885 per house, $0 per ADU (waiver since 2010), $27,439 per fourplex unit. **Bend** $34,598, $6,323, $25,610. **Salem** $23,798, $0 (exempt), $20,663. All are current FY25-26/26-27 schedules | The Handbook prior of $50,000 (D-034) elsewhere | **Eugene's city SDCs are missing** (eugene-or.gov sits behind a bot check). No 2017 vintage. Portland exempts all new housing permitted 2025-08-15 to 2028-09-30 (`OR-4159000-fees-2025`). **Decision (Ben, 2026-11-04):** the per-unit baseline is the regular schedule, and the exemption stays a dated reform row (recorded in the Portland rows' `notes`). **Eugene:** Admin Order 58-25-05-F (FY26, read by Ben's agent 2026-11-04) is coded: parks, local and regional wastewater, stormwater, and transportation per trip. The trip count per home isn't in the order, so every Eugene `amount_per_unit_usd` is left empty and **Eugene stays on the Handbook prior** for the fees scenario. Partial lower bounds: a house $10,682.58 and an ADU $6,004.11, before transportation and stormwater. **Bend reads $23,162, not $34,598,** in `local_fees` until #247 is fixed: the newest-year rule drops Bend's FY25-26 parks row beside the FY26-27 city rows |
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
- **2–4 unit permits (BPS) per year, 2018–2025, for every HB 2001 jurisdiction in the universe** (58: 33
  large-tier places, 3 Metro county remainders and 22 medium-tier places), and the Oregon total, each P10–P90.
  - The 38 cities newly covered in 2025 can be added to the total.
  - Gladstone (Metro) and Klamath Falls and The Dalles (medium tier) are covered by HB 2001 but not in the BPS
    universe, so they can't be predicted or scored.
- **Conditioning:**
  - eligible lots held at 2013–2017;
  - observed market inputs for 2018–2025;
  - Oregon's own uptake not fitted (Oregon is out of `REFORM_STATES`).

## 4. Rules for Ben's ordinance-validation agent

Ben asked whether his agent needs to check any ordinances. **Yes: 21 local rows and two state-law groups.** The
criteria:
- a source couldn't be opened or read;
- the coders disagreed;
- a date, threshold or coverage rests on a secondary source.

**Every local row is single-coder** and needs the check.

| reform_id | Place | What to check | Source |
|---|---|---|---|
| OR-4159000-adu-1998 | Portland | Size cap, owner occupancy and parking in the 1997 code text (Exhibit A not in the record); when owner occupancy was dropped (2016, 2017 or 2020 in secondary sources) | https://efiles.portlandoregon.gov/record/2455968/file/document |
| OR-4159000-adu-2021 | Portland | RIP ADU terms (2 ADUs, 800 sq ft / 75% cap, no added parking) and the 2021-08-01 date | https://www.portland.gov/bps/planning/rip/documents/exhibit-b-volume-2-code-and-commentary/download |
| OR-4159000-adu-2022 | Portland | RIP2 ADU extension to R10/R20; effective 2022-06-30 | https://www.portland.gov/sites/default/files/code/205-acc-dwelling-unit.pdf |
| OR-4159000-missing_middle-2021 | Portland | RIP unit caps (4; 6 if affordable) and zones | https://www.portland.gov/bps/planning/rip/documents/exhibit-b-volume-2-code-and-commentary/download |
| OR-4159000-parking-2021 | Portland | Parking minimums removed in single-dwelling zones from 2021-08-01 | same as above |
| OR-4159000-missing_middle-2022-rip2 | Portland | RIP2 scope and date; quote came through a short fetch extract | https://www.portland.gov/council/documents/ordinance/passed/190851 |
| OR-4159000-fees-2010 | Portland | Res. 36766 itself (coded from Ord. 189050's findings); extension dates | https://efiles.portlandoregon.gov/Record/12080419/File/Document |
| OR-4159000-fees-2018 | Portland | Waiver terms; fee_change_usd −16,130 and its dollar year | same as above |
| OR-4159000-fees-2025 | Portland | PCC 17.14.070.J text and dates (quote from a fetch extract); the ~$20,000 per unit figure | https://www.portland.gov/code/17/14/070 |
| OR-4105800-adu-2016 | Bend | **Ordinance not found**: number, text, effective date (from news reports) | https://kbnd.com/kbnd-news/local-news-feed/240002 |
| OR-4105800-missing_middle-2019 | Bend | `[predates]`: when duplexes and triplexes were first allowed; whether 2016 dropped their permit requirement | https://bendoregon.gov/home/showpublisheddocument/42896/637032924597730000 |
| OR-4105800-missing_middle-2021 | Bend | NS-2423 adoption and effective dates (read from a third-party copy) | https://cascadebusnews.com/wp-content/uploads/2021/10/CC-Notice-of-Decision-10-12-21.pdf |
| OR-4105800-adu-2025 | Bend | Ord. 2532 text (coded from the city's update list); second-ADU size cap | https://bendoregon.gov/resources/city-codes-policies-ordinances-and-resolutions/development-code-and-sign-code-updates/ |
| OR-4182800-missing_middle-2021 | Wilsonville | Ord. 851 effective date (computed from the signing date) | https://www.ci.wilsonville.or.us/sites/default/files/fileattachments/ordinance/117031/ord._no._851.pdf |
| OR-4174950-missing_middle-2022-local | Tualatin | Adoption 2021-12-13 vs DLCD's 2021-12-17; computed effective date | https://mccmeetingspublic.blob.core.usgovcloudapi.net/tualtnor-meet-19816dc20672497581506db8fdf74f7d/ITEM-Attachment-001-63a317784c6948d08cdb11f537cd939d.pdf |
| OR-4148650-missing_middle-2022-local | Milwaukie | Computed effective date (adoption + 30 days) | https://www.milwaukieoregon.gov/sites/default/files/fileattachments/planning/page/122372/za-2021-002_middle_housing_nod.pdf |
| OR-4126200-missing_middle-2022-local | Forest Grove | Second-reading date (scan); end of the DLCD infrastructure extension for the Westside area | https://forestgrove-or.gov/Archive.aspx?ADID=331 |
| OR-4131250-missing_middle-2022-local | Gresham | Adoption date (DLCD tracker only); zones (search snippet) | https://www.greshamoregon.gov/globalassets/government/city-codes-and-policies/development-code/development-code-amendments.pdf?id=1798 |
| OR-4174850-missing_middle-2022-local | Troutdale | Effective date: on passage 2022-06-28 vs DLCD's 2022-06-30 (the row may be redundant) | https://www.troutdaleoregon.gov/media/21991 |
| OR-4173650-missing_middle-2022-local | Tigard | Ordinance number (search snippet) and text; whether the model code applied 2022-06-30 to 07-06 | https://oregon.gov/lcd/UP/Documents/HB%202001%20Tracker%20Updated%206302022.pdf |
| OR-4140550-missing_middle-2022-local | Lake Oswego | Ord. 2892 text (ecode360 blocked); same model-code question | https://oregon.gov/lcd/UP/Documents/HB%202001%20Tracker%20Updated%206302022.pdf |

Also check, though not row-by-row:
- **On-time Metro cities** (no local row; the state row stands): Beaverton, Hillsboro, Oregon City, Sherwood,
  West Linn and Happy Valley.
  - Hillsboro's adoption date differs between the city (2022-05-17) and DLCD (2022-06-07).
  - Happy Valley may have been early.

**State-law rows:** the two coders agreed on every threshold, date, unit cap and owner-occupancy value, and
`by_right` was adjudicated. Two groups rest on secondary text:

| Rows | What to check | Source |
|---|---|---|
| The 50 `OR-*-missing_middle-2025` and their `-landdiv` rows (2023 c.223 duplex tier, 2,500–10,000) | Read the 2023 session law (chapter 223, §§20–21) for the tier and the June 30, 2025 deadline; coded from the ORS 197A.420 text and note on oregon.public.law | https://www.oregonlegislature.gov/bills_laws/ors/ors197A.html |
| The 32 county `OR-<county>-adu-2018` rows | Whether 2018 c.15 limited SB 1051's county ADU duty to land inside the UGB before 2018-07-01 (the coverage text says it did; the law wasn't read) | Oregon Laws 2018 chapter 15 (session law, not located); current text at https://www.oregonlegislature.gov/bills_laws/ors/ors197A.html (ORS 197A.425) |

All statutes were read from Internet Archive copies of the official files, because oregonlegislature.gov refused
connections from our network. A check against the live site would close that.

## 5. Remaining gaps and what closes each

| Gap | Effect on the freeze | Closes it |
|---|---|---|
| 105 cities outside the BPS universe (Klamath Falls 21,813, The Dalles 16,010, Gladstone 12,017…) | Can't be predicted or scored | **Accepted gap (Ben, 2026-11-04).** They hold 172,147 people (2020 Census), 4.1% of Oregon's 4,237,256 |
| Eligible lots held at 2013–2017 | Understates the base in growing places | RLIS current roll after unblinding (step 8) |
| Eugene transportation SDC per home | Eugene on the Handbook prior | Trips per residential unit from Eugene's SDC methodology report |
| Bend parks SDC dropped by the newest-year rule (#247) | Bend's fee read as $23,162 instead of $34,598 | Fix #247 (WS-ENGINE), or code Bend parks FY26-27 when the district publishes it |
| Local rows single-coder | Dates may shift by weeks | Ben's validation agent (§4) |
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
