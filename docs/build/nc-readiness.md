# North Carolina data readiness (threads 10 and 13)

*WS-NC, 2026-11-01. Plan: `docs/build/nc-data-plan.md` (S1–S13). No model runs: these are counts of the
processed input tables in `~/lotline-data/processed/nc` and of `config/reforms/nc.csv` and `config/fees/nc.csv`
on `main` at f9d9624. `eligible_parcels` was last rebuilt on 2026-11-01 for #252, and `jurisdictions` and the
OneMap parcels on 2026-10-23. §4 has the commands. This report replaces S10's integration run: under the
data-thread rule, data threads don't run the engines.*

**Bottom line.** North Carolina is ready for the engines. Every one of its 454 jurisdictions has:
- an eligible-lot count for 2010–2024 and a data tier;
- market inputs (ACS, FHFA, FRED, the demand index);
- a rule, either coded or drawn under D-022.

The 257 BPS reporters also have a permit outcome. The other 197 are places that BPS files under their county
(Charlotte, Wilmington, the Mecklenburg towns and others).

- **65% of the population of NC places** lives in a jurisdiction counted from real parcels: 218 jurisdictions
  (192 places and 26 county remainders).
- **The ADU panel (D-025) gains 8 NC places with an in-window rule change**: Raleigh, Durham, unincorporated
  Durham County, Greensboro, Cornelius, Huntersville, Matthews and Mint Hill; Davidson and
  Pineville are covered but have no rule yet.
- **The missing-middle panel (D-024) has 55 NC places of 10,000+, 11 of them with a dated change in the window.**
  But the dates of 9 of those 11 rest on the ordinance's adoption date only (`[earliest-known]`). Only Durham
  and Raleigh are firm events.
- **No rule row has a second coder yet** (87 rows; worksheet in #254).

## Corrections to the thread-13 snapshot

| Brief said | On `main` | Note |
|---|---|---|
| 322 jurisdictions (222 places, 100 county remainders) | **454: 157 BPS places, 197 local-only places (`in_bps = False`), 100 county remainders** | The OneMap load (S1, 2026-10-21) made the places that BPS files under their county into jurisdictions of their own. The tiers 124 / 94 / 236 in the brief already counted all 454 |
| Wilmington, Hickory, Salisbury, Statesville filed under their counties | **Wilmington and Statesville are local-only jurisdictions now**, counted from parcels. **Hickory and Salisbury are not in the table** | Their parcels' counties (Catawba, Rowan) send no usable land use, so they were not split off. Their rule rows (3731060, 3758860) apply only through their counties' rule mix (D-021 `county_mix`) |
| 46 counties have no usable land use | 48 counties load. 52 don't: 46 have no usable land use, and 6 were left out after the ACS check (Pender, Bertie, Greene, Hertford, Halifax, Sampson; `reports/nc/onemap_county_check.md`) | — |
| ADU rules: 64 rows, 39 places in total (both themes) | 64 ADU rows (62 in force, 2 pending), 22 missing-middle rows and 1 parking row: **87 rows, 39 jurisdictions**. 37 jurisdictions have a local ADU rule; Chapel Hill has only the state-law row | — |
| Stale branches | All three are superseded; see §3 | — |

The rest of the snapshot checks out: 3,837,161 OneMap parcels in 48 counties; Wake rolls for 2019 and 2023;
the Charlotte layer dated 2023-05-31; 218 jurisdictions counted from parcels, 13 of them with
`parcels_interpolated` years (Wake 2020–2022, #252); 132 fee rows. **D-020 holds:** after `parcel_sources`, no
jurisdiction has two parcel sources.

## 1. Coverage of each model input (454 jurisdictions: 354 places, 100 county remainders)

Population shares use `jurisdictions.pop_2020`, which is filled for places only (5.61 million). County
remainders have no population in that column, so they are counted but not weighted.

| Input | Real | Fallback | Open |
|---|---|---|---|
| **Eligible lots (denominator)** | **218 jurisdictions from parcels (64.9% of place population)**: 85 BPS places (52.8%), 107 local-only places (12.2%) and 26 county remainders. 13 Wake jurisdictions have two real rolls (2019 and 2023) with interpolated years in between (D-035 addendum); the other 205 have one roll (OneMap 2026), with ACS-scaled history (D-035) | **236 on the ACS fallback** (D-017): 72 BPS places (12.2%), 90 local-only places (22.9%) and 74 county remainders. Of the 40 largest places, **10 are on ACS: Charlotte, Concord, Greenville, Jacksonville, Chapel Hill, Kannapolis, Sanford, Thomasville, Asheboro, Clayton** | Charlotte: the pre-UDO layer has no land use. Concord and Kannapolis: Cabarrus sends no land-use code. The other 7: their counties send no usable land use |
| Window | All 454 have every year from 2010 to 2024 | — | — |
| Denominator quality | `high` on some years for the 13 Wake jurisdictions (the Wake roll separates townhouses) | `low` everywhere else | Zoning is unknown, so all land counts as single-family-only (as in Ohio and Texas) |
| **Data tier** | **Tier 1: 124 (45.7% of place population)**, tier 2: 94 (19.3%) | **Tier 3: 236 (35.1%)**, Charlotte included | Tier 1 needs land use and year built on at least 80% of built parcels |
| Permits, all places | Census BPS for the 257 reporters; 215 of them have every year from 2010 to 2024 | A missing place-year is missing, never 0 (D-024) | The 197 local-only places have no BPS row of their own: BPS counts them in their county's row |
| **Record-level permits** | **Raleigh** 177,473 (2000–2026); **Durham** 77,603 (2007–2026; city and unincorporated county, annexations dated from 2013, #94); **Greensboro** 111,648 (1990–2026); **Mecklenburg file** 449,925 after the holdout filter (the six towns any year; Charlotte and the unincorporated county to 2023-05-31) | — | The Mecklenburg legacy file thins out in 2025 (the towns' permits fall from about 3,000 a year to 1,569 in 2025 and 263 in 2026) as the county moved to Accela. The Accela file isn't loaded. In some years, Greensboro's per-apartment permits repeat the building's unit count |
| **Permits with an ADU flag** | Raleigh 291 ADUs (flagged from 2019); Durham 392 (city 362, county 30); Greensboro 35; Mecklenburg towns 75 (Davidson 20, Cornelius 14, Huntersville 14, Mint Hill 10, Matthews 9, Pineville 8) | — | Greensboro and the Mecklenburg counts come from the description parser, so they are lower bounds. 2025–2026 in the towns is incomplete (see above) |
| **ADU rules** | **37 jurisdictions with a local ADU row** (43 local ADU rows), plus 21 S.L. 2026-59 rows (effective 2027-01-15; 2 of them pending) | The rest draw a rule type (D-022) | **25 of the 43 local ADU rows carry `[earliest-known]` dates** (the ordinance's adoption date, or no adoption date). Missing: Goldsboro and New Bern (no ordinance supplied). Monroe has no row on purpose (ADUs only in one overlay) |
| **Missing-middle rules** | **21 jurisdictions, 22 rows**. Firm in-window events: Durham city and county (2019), Raleigh (2021, 2022). Before 2010: Apex (2000), Salisbury (2008). After the window: Asheville and Statesville (2026) | Uncoded places draw a rule type (D-022) | **20 of the 36 places in `nc-mm-lookups-todo.csv` are still open**, Greensboro, Winston-Salem, Fayetteville and Cary among them. Fuquay-Varina and Indian Trail don't allow duplexes on single-family lots (pass 2) but have no one-home row, so they still draw |
| Fees | **16 jurisdictions, 132 rows**: Raleigh (56), Concord, Fuquay-Varina, Durham (2024 guide), Johnston, Brunswick, Asheville, Greensboro, Wilmington and New Hanover (CFPUA), Apex, Wilson, Winston-Salem and Forsyth, Buncombe, Cabarrus. Years 2018–2026, mostly 2026 | Handbook prior of $50,000 per home elsewhere (D-034) | Lookups open: Charlotte Water, Fayetteville PWC, Cary, High Point. Cabarrus (WSACC wholesale only) is a floor |
| Market (rent, value, rates, costs) | ACS 2010–2024 for every place and county; FHFA to 2025; FRED | — | — |
| Demand index | Every county and place, 2010–2023 | — | — |
| Holdout | **Charlotte V5**: 3712000, plus 37119 from 2023-06-01 | — | Freeze by Nov 17 (WS-ENGINE, #45). See `reports/nc/V5-charlotte-inputs.md` for the input check |

## 2. What North Carolina adds to the estimation panels

**ADU estimate (D-025).** To count, a place needs a permit source that covers it and flags ADUs, a dated ADU rule
and eligible lots. All four NC sources are full permit files, not ADU-only files, so a year with no ADU still
has permit rows, and the panel's caller doesn't need a covered-places list (unlike Franklin and Montgomery in
Ohio).

| Place | Rule rows in the window | ADU-flagged permits | Notes |
|---|---|---|---|
| Raleigh (3755000) | 2019-02-19 (overlay only), **2020-07-07 by right**, 2022-08-08 (two ADUs in Frequent Transit Areas) | 291, 2019–2026 | Flags start in 2019, so the 2020 change has one pre-year in the flagged data (as `estimate_pooled_adu.TRANSPORT` already uses) |
| Durham city (3719000) | **2019-09-03** (Expanding Housing Choices), 2023-11-20 (SCAD) | 362, 2008–2026 | — |
| Durham County remainder (37063) | **2019-10-28** | 30, 2008–2026 | Small counts |
| Greensboro (3728000) | **2024-04-16** | 35, 2002–2026 | Lower bound (description parser). Two post-years |
| Cornelius (3714700) | 2023-01-17 | 14 | Mecklenburg file. 2025–2026 incomplete |
| Huntersville (3733120) | 2024-09-17 | 14 | One full post-year (2024 to the file's thinning in 2025) |
| Matthews (3741960) | 2014-04-01 `[earliest-known]` | 9 | The date may be later than the real start |
| Mint Hill (3743480) | 2011-07-01 `[earliest-known]` | 10 | Same |
| **Covered, no rule yet** | Davidson (3716400), Pineville (3752220) | 20, 8 | One lookup each would add them |

**Do the six Mecklenburg towns qualify?** Four do (Cornelius, Huntersville, Matthews, Mint Hill); Davidson and
Pineville need a rule row first. The towns aren't held out: the holdout covers only Charlotte and the
unincorporated county. Caveats for WS-ENGINE:
- ADU counts are small (8 to 20 per town over the life of the file) and come from the description parser.
- The legacy file ends in 2025, so 2025 should be treated as partial and 2026 dropped.
- Matthews' and Mint Hill's dates are `[earliest-known]`.

**Charlotte** has ADU permits before the window (184, 2002 to May 2023) and a 2012 rule. It is left out here:
annual tables hide all of 2023, and its 2023-06-01 rule change falls on the holdout boundary. If WS-ENGINE wants
it, it could only enter for 2010–2022 with the 2012 rule, and only after Ben agrees.

So the D-025 panel gains **8 NC places with an in-window rule change** (Raleigh, Durham city and county,
Greensboro, and the four towns). Of these, **5 have firm dates**: Raleigh, Durham city and county, Greensboro
and Cornelius; Huntersville's is firm too but has only one post-year. **Firm dates are the ones to lean on.**

**Missing-middle estimate (D-024).** The outcome is BPS 2–4 unit homes, so **all 55 NC BPS places of 10,000+
are in**. Local-only places can't enter (they have no BPS row), and neither can Charlotte (holdout).

| Group | Places |
|---|---|
| **Firm in-window events** | Durham (2019-09-03), Raleigh (2021-08-05 and 2022-08-08). Unincorporated Durham County (2019-10-28) if county remainders are in the panel |
| In-window rows dated `[earliest-known]` (the ordinance's adoption date, not when duplexes became legal) | Wake Forest 2013, Wilson 2013, Morrisville 2014, Sanford 2018, Burlington 2019, Asheboro 2021, Mooresville 2022, Garner 2022, Monroe 2022 (special use permit only) |
| Treated before 2010 | Apex (2000) |
| Coded but out of the panel | Charlotte 2023 (holdout); Kannapolis 2022, Cornelius 2018, Mint Hill 2011 and Statesville 2026 (local-only, no BPS row); Hickory 2011 and Salisbury 2008 (not jurisdictions); Asheville 2026 (after the window) |

**Don't code the 9 `[earliest-known]` rows as in-window events until a second coder confirms the start.** These
codes may have carried duplex rules forward from an earlier ordinance; if so, the place was treated all along.
Until then, the safe reading is "treated by the coded date". WS-ENGINE should run D-024 with and without them.

## 3. Remaining gaps and what closes each

| Gap | Effect | What closes it | Owner |
|---|---|---|---|
| **No second coder on any NC rule row** | The 24 rows that would set the timing of D-024 and D-025 events rest on one coder | The worksheet `docs/research/ordinances/nc-second-coder-2026-11-01.csv` (#254): the 24 `panel_event` rows are first | **Ben** |
| `[earliest-known]` dates on 9 D-024 and 2 D-025 event rows | Event timing unknown; possible always-treated places counted as events | The second coder (above), or the ordinance history for each | Ben |
| Mecklenburg archive (V5 option a) | V5 uses the town prior (option b) with its range | Mecklenburg County's answer by **Nov 10** | Ben |
| Mecklenburg Accela file | The towns' 2025–2026 permits are missing, and so are Charlotte's outcomes after unblinding | A hand download from the county's Open Data Viewer (out of scope for thread 13) | Later |
| 10 of the 40 largest places on ACS | ACS denominator for Charlotte, Concord, Greenville, Jacksonville, Chapel Hill and others | County land-use sources beyond OneMap (not planned); Charlotte only through the archive | — |
| Missing-middle lookups (20 places open) | More D-022 draws among large places | `nc-mm-lookups-todo.csv`; also code Fuquay-Varina and Indian Trail as one-home rows (pass 2 found no duplexes) | Ben, then WS-NC |
| ADU lookups (Goldsboro, New Bern) and rules for Davidson and Pineville | Two more D-025 places (Davidson, Pineville) | `nc-adu-lookups-todo.csv` (add Davidson and Pineville) | Ben |
| Fee lookups (Charlotte Water, Fayetteville PWC, Cary, High Point) | Handbook prior for those places | `nc-fee-lookups-todo.csv` | Ben |
| Durham V0 comparison | Whether V0 can compare Durham city alone with BPS (the interim rule compares city plus county) | Ben's decision (`2026-10-21-ws-nc-94-durham-annexations.md`: annexations explain only 53 permits) | **Ben** |
| Troutman, Princeville (dev-run outliers) | Scaled ACS overstates Troutman's past (73% of its houses built since 2015); Edgecombe files mobile homes as single-family | A year-built backcast (suggested to WS-CORE); none for Princeville | WS-CORE / not planned |
| Population of county remainders | `pop_2020` is empty for the 100 remainders | A WS-CORE fill, if weighting needs it | WS-CORE |

**Stale branches (for Ben to close):**
- `ws/nc-3-onemap` (remote only) holds only the merge of #122, the first Wake adapter. Every file it touches is on
  `main`, in a later form (the Nov 2019 roll was added in #208's work). Superseded.
- `ws/nc-3-wake` has the same three commits (#122, merged into `ws/nc-3-onemap`, not `main`). Superseded by
  `ws/nc-3-wake-main`.
- `ws/nc-dev-run-2026-10-22` (#213, open) is a report-only development run. Its outliers were handled in
  `ws/nc-outliers` (merged). It is older than #252 and the rules passes, so its numbers are stale. Close it
  unless you want the report kept as a record.

## 4. How these numbers were made

```bash
uv run python scripts/dev/nc_readiness_counts.py
```

The script is read-only. It reads the processed tables with `DataStore` and the two config CSVs, and passes
every permit and BPS table through `holdout.apply` before counting. It rebuilt nothing: the tables are as last
built by `lotline fetch --state NC --source eligible` (2026-11-01, after #252, on 8b95d30; recorded in
`2026-10-23-ws-nc-rules-pass2.md`) and by the 2026-10-23 OneMap, jurisdictions and eligible rebuild
(`2026-10-23-ws-nc-outliers.md`). Checked against `main` at f9d9624; nothing in `src/lotline` that builds
these tables changed between 8b95d30 and f9d9624.
- **D-025 coverage:** a place counts as covered by a permit source if the source holds 1,000 or more of its
  permits. That leaves out stray records, such as Stallings (140, mostly in Union County) and Concord (7).
- **In window:** effective 2010-01-02 to 2025-12-31, as in the Ohio and Texas reports.
- **`[earliest-known]`:** the row's `coding_notes` say so, or it has no adoption date.

## 5. Ben's manual items (exact steps)

1. **Second-coder pass** on #254's worksheet, the 24 `panel_event` rows first. Fill `second_coder`,
   `agrees (yes/no/partly)`, `correct_value` and `second_coder_note`, then tell WS-NC to apply it, as
   `tx_second_coder_2026_10_30.py` did for Texas.
2. **Mecklenburg archive:** has the county answered? If nothing arrives by **Tue Nov 10**, V5 stays on option (b).
3. **Lookups:** add rows for Davidson and Pineville to `nc-adu-lookups-todo.csv` (ADU rules: one row each would
   bring both into D-025), and fill the open missing-middle and fee rows (§3).
4. **Durham V0:** decide whether V0 may compare Durham city alone with BPS 3719000.
5. **Close the stale branches** listed in §3 (delete `ws/nc-3-onemap` and `ws/nc-3-wake`; close #213).
