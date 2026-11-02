# Minnesota data readiness (thread 13, M5)

*WS-MN, 2026-11-02. Plan: `docs/build/mn-data-plan.md` (#256, approved 2026-11-01). No model runs: these are
counts of the processed input tables in `~/lotline-data/processed/mn`, rebuilt on 2026-11-02 with the MnGeo
parcels (#261), and of `config/reforms/mn.csv` (with #260's rows) and `config/fees/mn.csv`. §4 has the
commands. This branch is stacked on #260 and #261 and should be merged after them. This report replaces thread
8's integration run: under the data-thread rule, data threads don't run the engines.*

**Bottom line.** Minnesota is ready for the engines. Every one of its 1,053 jurisdictions has:
- a data tier;
- BPS permits (or its county's row, for the 23 local-only ones) and market inputs;
- a rule, either coded or drawn under D-022.

1,051 have an eligible-lot count for 2010–2024. Wyoming township and Baldwin have none, as before this work.

- **86% of Minnesotans** (counted in places and townships) live in a jurisdiction counted from real parcels:
  539 of 1,053, up from 186. MnGeo's opt-in compilation added 353 outstate jurisdictions in 31 counties.
- **Of the 40 largest places, only Mankato is on ACS.** Its county (Blue Earth) has not opted in.
- **The ADU panel (D-025) holds 73 Minnesota places with Met Council or Minneapolis permits and a dated rule:**
  45 with an in-window rule change and 28 "no ADUs" controls (after the second-coder review and lookups). Only 32 of
  the 45 have an event on a confirmed date: 16 of the 52 event rows are tagged DATE UNCONFIRMED. 109 more covered places
  have no rule yet. That
  makes Minnesota the largest contributor to D-025, as it already is today (D-023/D-025's Twin Cities panel).
- **The missing-middle panel (D-024) has 100 Minnesota places of 10,000+, with 3 in-window events:**
  Minneapolis (2020), Richfield (2023) and St. Louis Park (2025), all adopted on dates confirmed from official records. St. Paul's 2023 reform is the V5
  holdout.
- **V5 St. Paul inputs** are in #259: 55,269 eligible H1/H2 lots on the pre-window roll, from the city's dated
  zoning snapshot.
- **Every rule row has been second-coded** (Codex, 2026-11-02): 8 agreed, 60 adjudicated by Ben (all
  recommendations accepted), 39 noted with no change; 2 rows deleted as not ADU rules. See §6.

## Corrections to the thread-13 snapshot

| Brief said | Found | Note |
|---|---|---|
| Eligible lots: check whether the 2021–2025 rolls get `parcels_interpolated` after #252 | **The table predated D-035 altogether**: no `parcels_scaled_acs` rows, so parcel-counted places had no count before 2021 | Rebuilt in #261. The Met Council rolls are yearly, so interpolation changes nothing for them; three places get `parcels_interpolated` rows between assessor or roll years |
| Ramsey's "2023" roll date: check | St. Paul's part of the 2023 roll was exported **2023-12-26**, before the window | So St. Paul has three pre-window rolls: 2021, 2022, 2023 (#259) |
| Missing-middle rules: 2 rows | 2 rows, plus two Minneapolis `moratorium` rows (the 2040 Plan injunctions, with start and end dates) and 2 parking rows | The injunction rows serve as the sensitivity rows |
| Fees: mostly two places | 171 rows for **13 jurisdictions**; Rochester (58) and Burnsville (34) have the most | — |

## 1. Coverage of each model input (1,053 jurisdictions: 763 places, 218 townships, 72 county remainders)

Population shares use `jurisdictions.pop_2020`, which is filled for places and townships (4.97 million). County
remainders have no population in that column.

| Input | Real | Fallback | Open |
|---|---|---|---|
| **Eligible lots (denominator)** | **539 from parcels (86% of the population counted)**: 394 places (82.7%), 121 townships (3.2%), 24 county remainders. Metro (182): Met Council yearly rolls 2021–2026. Minneapolis: assessor rolls 2017–2026. Outstate (356): MnGeo current roll, 31 counties. Earlier years are ACS scaled to the rolls (D-035) | **512 on ACS** (D-017): 368 places (12.4%), 96 townships (1.7%), 48 remainders | Places on ACS: those in the 28 counties that haven't opted in (Mankato, Willmar, Albert Lea, Red Wing, Bemidji, Alexandria, North Mankato, New Ulm, Worthington, Marshall and others); in the 18 opt-in counties with no use class (Sauk Rapids, Benton County, among them); in Aitkin, Cass and Cook (ACS check); and in the five bare-code counties (Brainerd, Grand Rapids, International Falls), where 51 of their 58 jurisdictions fail the 90% gate. Wyoming township and Baldwin have no row |
| Window | 1,043 jurisdictions have every year 2010–2024 | — | 8 have 2–14 years (unchanged by this work) |
| Denominator quality | `high` on 1,359 rows in 81 jurisdictions (metro places where units and dwelling type are known) | `low` elsewhere | Zoning unknown, so all land counts as single-family-only (as in NC, OH and TX) |
| **Data tier** | **Tier 1: 130 (62.0% of the population)**, tier 2: 408 (23.8%) | Tier 3: 515 (14.1%) | Outstate year built is blank in most counties, so most outstate places are tier 2 |
| Permits, all places | BPS for every permit-issuing place and township | A missing place-year is missing, never 0 (D-024) | 23 local-only jurisdictions are in their county's BPS row |
| **Record-level permits** | **Met Council** 114,363 (2009–2025, 186 metro jurisdictions; SFD, TH, DTQ, MF5, ADU); **Minneapolis CCS** 129,849 (2016–2026); **St. Paul** 73,228 (2015–2023 after the filter) | — | No outstate city has record-level permits (out of scope) |
| **Permits with an ADU flag** | Met Council: 341 ADUs in 53 places, from 2014 (2016 on in practice). Minneapolis CCS: 211 (inferred from the scope text) | — | Met Council undercounts Minneapolis internal ADUs (LB-057). St. Paul's own file has no ADU flag |
| **ADU rules** | **80 jurisdictions, 98 rows**: 76 metro places, plus Duluth, Rochester and St. Cloud outstate | The rest draw a rule type (D-022) | 109 Met Council places have no rule (largest: Brooklyn Center, Chaska, Prior Lake, Shoreview, Hastings, Lino Lakes, Northfield). The outstate fill-in table (M6) is not done. 9 in-window D-025 event rows are dated `[earliest-known]` |
| **Missing-middle rules** | **8 jurisdictions**: Minneapolis 2020 (3 units), Richfield 2023 (duplexes in R), St. Louis Park 2025 (N-1 up to 3), St. Paul 2023 (V5), Duluth 2026; "one home" in Rochester (R-1), Brooklyn Park and Coon Rapids | Uncoded places draw a rule type (D-022) | `mn-mm-lookups-todo.csv`: 33 of the 40 largest places, largest first (Bloomington's 2026 Phase II is the likeliest new event) |
| Fees | **13 jurisdictions, 171 rows**, 2016–2027: Rochester, Burnsville, Maple Grove, St. Paul, Coon Rapids, Lakeville, Duluth, St. Cloud, St. Louis Park, Apple Valley, Minneapolis, Bloomington, Brooklyn Park | The Handbook prior of $50,000 per home elsewhere (D-034) | No Met Council SAC series (M7, not done) |
| Market (rent, value, rates, costs) | ACS, FHFA, FRED, statewide | — | — |
| Demand index | Processed, every county and place, 2010–2023 | — | — |
| Holdout | **St. Paul V5**: 2758000, outcomes from 2024-01-01; rolls exported from then on hidden (snapshot rule) | — | Freeze by Nov 17 (WS-ENGINE, #45). See `reports/mn/V5-stpaul-inputs.md` (#259) |

## 2. What Minnesota adds to the estimation panels

**ADU estimate (D-025).** To count, a place needs a permit source that covers it and flags ADUs, a dated ADU rule
and eligible lots. Met Council's residential permit survey covers every metro community: it is a full
new-construction file, so a year with no ADU still has permit rows, and the panel's caller doesn't need a
covered-places list. Minneapolis's CCS permits cover Minneapolis. St. Paul never enters.

| Group | Places | Notes |
|---|---|---|
| **Rule change in the window** | **45** | Minneapolis (2014, 2016, 2021, 2023) and 44 suburbs. 7 of their 52 event rows are dated `[earliest-known]` and 16 are DATE UNCONFIRMED; only 32 places have an event on a confirmed date. Run with and without the unconfirmed dates |
| **"No ADUs" controls** | **28** | Coded "none" rows in covered places |
| Rule, no event, not a control | 3 | Rules only before the window, or `[predates]` (Stillwater) |
| **Covered, no rule yet** | 109 | Largest: Brooklyn Center 33,782, Chaska, Prior Lake, Shoreview, Hastings, Lino Lakes, Northfield, Waconia, North St. Paul, East Bethel, Lake Elmo, White Bear township, Little Canada, Victoria. Each one coded joins the panel at once |
| Rules but no permit source | Duluth, Rochester, St. Cloud | Outstate: no record-level permits, so they can't enter |

So Minnesota's 73 places stay the core of the D-025 panel. Today's estimate already uses the Twin Cities places
(`scripts/dev/estimate_pooled_adu.py`, `metc_residential_permits`). This work adds no new place to it, but the
109 covered places without a rule are the cheapest way to grow it: one lookup each.

**Missing-middle estimate (D-024).** The outcome is BPS 2–4 unit homes, so **all 100 Minnesota BPS places of
10,000+ are in**.

| Group | Places |
|---|---|
| **In-window events** | Minneapolis (2020-01-01; the injunction windows 2022-06-15 to 2022-07-26 and 2023-11-04 to 2024-05-13 as sensitivity) and St. Louis Park (2025-03-28, Ord. 2690-25; duplex and 3-unit in N-1 and N-2, 4-unit in N-2) and Richfield (Bill No. 2023-2, passed 2023-01-24: duplexes by right in R; effective about 30 days after publication, date not found, coded as passage) |
| Untreated on evidence | Brooklyn Park (R-1), Coon Rapids (LDR1/LDR2) |
| Untreated on evidence (R-1) | Rochester: R-1 has allowed one home per lot since a 1998 amendment, so the 2023 UDC changed nothing there (`[predates]`); 2-4 units with staff approval in other districts |
| Outside the panel | St. Paul 2023 (V5 holdout); Duluth 2026 (after the window) |

## 3. Remaining gaps and what closes each

| Gap | Effect | What closes it | Owner |
|---|---|---|---|
| **16 D-025 event dates unconfirmed** | 13 of the 45 event places have no event on a confirmed date | City clerks, council minutes or signed ordinances (`mn-second-coder-lookups-2026-11-02.csv`) | **Ben** |
| 109 covered metro places with no ADU rule | Fewer D-025 places; more D-022 draws | An ADU lookup table for them, largest first (not written yet; the outstate one, M6, isn't either) | Ben, then WS-MN |
| Missing-middle rules for the 40 largest places | 33 still draw (D-022) | `mn-mm-lookups-todo.csv` | Ben |
| Bare-code counties (Crow Wing, Itasca, Koochiching, Jackson, Houston) | 51 of their 58 jurisdictions on ACS (Brainerd, Grand Rapids, International Falls) | Each county's property-type code table | Ben (one request each), then WS-MN |
| 18 opt-in counties with no use class; 28 counties not opted in | Their places stay on ACS (Mankato is the only large one) | Nothing open to read: county requests only | Not planned |
| Lake and farm townships | Cabins and farmhouses aren't read as houses, so 14 newly parcel-counted townships count under half their ACS lots, and Aitkin, Cass and Cook stay on ACS | **Decided (Ben, 2026-11-02): seasonal cabins (class 4c12) stay out of eligibility**, as in the metro rules. Accepted as a known undercount against ACS | Settled |
| Pre-2021 metro rolls | Metro history before 2021 is scaled ACS | Met Council's token-locked rolls (#11) | Ben / Met Council |
| Fees | Handbook prior for 1,040 jurisdictions | M7: Met Council SAC history | WS-MN (not started) |
| Zoning (D-021 coverage) | All land counts as single-family-only | M8: Met Council Planned Land Use, Minneapolis zoning | WS-MN (not started) |
| Provenance for St. Paul's zoning archive | The V5 snapshots aren't in `docs/data_provenance.md` | #258 (contract-change) | WS-CORE |

## 4. How these numbers were made

```bash
uv run lotline fetch --state MN --source mngeo_parcels
uv run lotline fetch --state MN --source jurisdictions
uv run lotline fetch --state MN --source eligible
uv run python scripts/dev/mn_readiness_counts.py
uv run python scripts/dev/mn_second_coder_sheet.py
```

- The rebuild ran on #261's branch, on top of `main` at 7fc54e5. `mngeo_parcels` read its raw cache
  (`MN_MNGEO_VINTAGE=2026-09-17`, the default). Met Council and Minneapolis parcels were not re-downloaded.
- Both scripts are read-only. Every permit and BPS table passes through `holdout.apply` before counting, and
  parcel rolls with `snapshot=True`.
- **In window:** effective 2010-01-02 to 2025-12-31.
- **Not events:** a `[predates]` row, a "no ADUs" row (`adus_per_lot = 0`) or a "one home" row
  (`unit_cap = 1`) is never an event.
- **D-020:** after `parcel_sources`, no jurisdiction has two parcel sources (182 Met Council, 408 MnGeo,
  1 Minneapolis assessor).

## 5. Ben's manual items (exact steps)

1. ~~Second-coder pass~~: **done 2026-11-02**; Ben accepted all 62 recommendations (§6).
2. **Lookups:** the 16 unconfirmed dates in `mn-second-coder-lookups-2026-11-02.csv` need primary records; then
   `mn-mm-lookups-todo.csv` (33 places). Hugo and Rochester are settled (§6).
3. **County code tables** for Crow Wing, Itasca, Koochiching, Jackson and Houston. Ask each assessor for their
   three-digit property-type code list (the codes 151, 111, 765 and others are unlabelled).
4. ~~Decide whether seasonal cabins count as houses~~: **decided 2026-11-02, they stay out** (§3).
5. **Review order:** #256 (plan), #259 (V5), #260 (rules), #261 (parcels), then this PR (stacked on #260 and
   #261).

## 6. Second-coder review (2026-11-02)

Ben's second agent (Codex) filled all 109 rows of `mn-second-coder-2026-11-02.csv`: 8 yes, 92 partly, 9 no. It
was stricter than the NC reviewer: a date counts as confirmed only with a signed ordinance or an effective-date
record. It also wrote over the sheet's left-hand columns; our coding as sent is the sheet at 54e9727.

- `scripts/dev/mn_second_coder_2026_11_02.py` appended each finding to `coding_notes` and marked the 8 agreed rows.
- Ben accepted all 62 recommendations in `mn-second-coder-decisions-2026-11-02.csv`, applied by
  `scripts/dev/mn_second_coder_decisions_2026_11_02.py`:
  - **Deleted:** Hopkins 2024 (an accessory-structure footprint rule) and Grant 2016 (a state-law opt-out).
  - **Dates fixed:** Mounds View (2025-06-29), Burnsville 2018 (2018-05-22), Columbia Heights (2024-08-26), St. Paul
    ADUs (2018-12-01) and parking (2021-10-01), the 2022 Minneapolis injunction (2022-06-15).
  - **Values fixed:** Chanhassen (CUP, not by right), Richfield (no detached ADUs), Oakdale (by right); blank fields
    filled for 8 places from the reviewer's code reading.
  - **`[predates]`:** Fridley 2022 (a recodification), Forest Lake (recoded from "no ADUs" to rural ADUs, now
    `MN-2721770-adu-2023`), Rochester missing middle. Brooklyn Park's one-home row now covers R-1 only.
  - **DATE UNCONFIRMED:** 31 rows keep their dates and go on the lookup list. Ben decided (2026-11-02) that a
    DATE UNCONFIRMED row still counts as an event, and engines run with and without such rows.
- The agent's research tracker, evidence register, PDF inventory and issues note are in
  `docs/research/ordinances/`. Its 14 PDFs are in `LOTLINE_DATA_DIR/manual/mn/second_coder_2026-11-02/`.

**Lookups (2026-11-02).** Ben's agent filled `mn-second-coder-lookups-2026-11-02.csv`, but 33 of its 36 answers
repeat the second coder's findings (one cites this repo's own `manual-lookups.csv`), so those dates stay
DATE UNCONFIRMED. Ben accepted four changes, applied by `scripts/dev/mn_lookups_2026_11_02.py`:
- **Forest Lake:** Ord. 719 (2023-01-23, council minutes and ordinance) added ADUs in the A district, so the 2023
  row is an in-window event (`[predates]` removed).
- **Fridley:** the city says Council approved its ADU ordinance in 2022, so `[predates]` is removed; the day is
  DATE UNCONFIRMED.
- **Mounds View:** Ord. 1045 (adopted 2025-08-11, effective 2025-09-11) added detached ADUs:
  `MN-2744530-adu-2025b`, with the Ord. 1042 row renamed `-2025a`. DATE UNCONFIRMED (the source predates adoption).
- **Burnsville 2020:** no 2020 adoption found, so the row is deleted; the 2018 rule stands.
- **Hugo (Ben):** Ord. 2011-459 §1 (2011-10-03) adopted the ADU rules (Hugo Code §90-277), not Ord. 2011-460.
- **Rochester (Ben):** a 1998 city planning record says an amendment removed duplexes and PRDs from R-1, so R-1 was
  one home per lot before the 2023 UDC; the R-1 row stays `[predates]` and is a control.
- **Round 2 (Ben's agent):** official records confirm the adoption dates for Lakeville (Ord. 903), Medina 2011
  (Ord. 514), Minnetonka (2021-10-04), Vadnais Heights (Ord. 774), Oakdale (Ord. 948) and Cottage Grove (zoning
  revision approved 2022-12-21, effective 2023-01-01, re-dated from 2023-08-16), so their DATE UNCONFIRMED tags
  are removed. Golden Valley's month (November 2022) is confirmed, not the day.
- **Ben, round 3:** Medina 2024 deleted (Ord. 733 is a height rule, not an ADU change). Roseville Ord. 1418
  (2011-10-10) added as `MN-2755852-adu-2011`: ADUs went from conditional (the 2006 code) to permitted.
- **Recount:** D-025 74 places (46 changes, 28 controls); 25 of 53 event rows DATE UNCONFIRMED; 24 places with a
  confirmed-date event.
- **Richfield and Eagan (Ben):** Bill No. 2023-2 (passed 2023-01-24) allows duplexes by right in R and folds
  MR-1 into R, so Richfield is a new D-024 event (`MN-2754214-missing_middle-2023`; three-plus units stay
  multifamily). Eagan's ADU ordinance is almost certainly Ord. 528, 2nd Series (unsigned draft; date still
  unconfirmed). Richfield's ADU row is re-dated to 2015-07-01 `[earliest-known]` (city handout dated 7/2015).
- **Crystal (Ben):** Ord. 2017-07 (the Unified Development Code) authorized ADUs: adopted 2018-01-02, effective
  2018-02-10 per the official code (500.09), so the coded dates stand and are now confirmed.
- **Rosemount (Ben):** Ord. 2024-04, adopted and effective 2024-06-04 (official code), first allowed ADUs
  (Dakota County's 2016 profile and 2023 guide list none): internal or attached, A-2, RR, R-1 and R-2, 800 sq ft.
- **Wayzata (Ben):** Ord. 811, adopted 2022-06-21 (official meeting summary), effective 2022-06-30 (Ch. 937
  history); ADUs permitted in all six single-family districts, detached allowed, owner-occupied, one per lot.
- **Plymouth (Ben):** Ord. 2023-12, adopted and effective 2023-09-12, expanded the 2002 rule (Ord. 2002-24, ADUs
  only above garages) to internal, attached and detached units.
- **White Bear Lake (Ben):** Ord. 25-07-2080, adopted 2025-07-22, effective 2025-08-20; the rewrite moved ADUs
  from conditional use (former 1302.125) to by right, so the event stands.
- **Stillwater (Ben):** the 2017-05-02 record is Ord. 1093 (short-term home rentals). ADUs were allowed from the
  late 1990s (2021 Planning Commission report), so the row is `[predates]`. Open: whether the 2021 RA expansion
  was adopted.
- **Mound (Ben):** Ord. No. 7-2024, adopted 2024-10-22, published 2024-11-02, effective 2024-11-03; first allowed
  ADUs (R-1, R-1A, R-2, MU-D, MU-C; 800 sq ft; owner occupancy).
- **Ramsey (Ben):** Ord. 22-04, adopted 2022-02-08, published 2022-02-11, effective 2022-03-14; first general ADU
  allowance (R-1, attached or detached, 800 sq ft, owner occupancy, detached on 1+ acre).
- **Rogers (Ben):** the official code (125-4) confirms the 2020-05-26 effective date; adoption date and ordinance
  not found. ADUs are an accessory use in AG and R1. The 2020 code repealed a prior chapter that was not found, so
  the row is `[earliest-known]`.
