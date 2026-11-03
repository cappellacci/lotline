# Minnesota data readiness (thread 13, M5)

*WS-MN, 2026-11-02. Plan: `docs/build/mn-data-plan.md` (#256, approved 2026-11-01). No model runs: these are
counts of the processed input tables in `~/lotline-data/processed/mn`, rebuilt on 2026-11-02 with the MnGeo
parcels (#261), and of `config/reforms/mn.csv` (with #260's rows) and `config/fees/mn.csv`. §4 has the
commands. Updated through 2026-11-02 for the second-coder review and Ben's lookups (§6), with the engine kickoff
in §0. This branch is stacked on #260 and #261 and should be merged after them. This report replaces thread
8's integration run: under the data-thread rule, data threads don't run the engines.*

**Bottom line.** Minnesota is ready for the engines. Every one of its 1,053 jurisdictions has:
- a data tier;
- BPS permits (or its county's row, for the 23 local-only ones) and market inputs;
- a rule, either coded or drawn under D-022.

1,051 have an eligible-lot count for 2010–2024. Wyoming township and Baldwin have none, as before this work.

- **86% of Minnesotans** (counted in places and townships) live in a jurisdiction counted from real parcels:
  539 of 1,053, up from 186. MnGeo's opt-in compilation added 353 outstate jurisdictions in 31 counties.
- **Of the 40 largest places, only Mankato is on ACS.** Its county (Blue Earth) has not opted in.
- **The ADU panel (D-025) holds 71 Minnesota places with Met Council or Minneapolis permits and a dated rule:**
  43 with an in-window rule change and 28 "no ADUs" controls. 39 of the 43 have their event on a confirmed date;
  4 of the 54 event rows are still DATE UNCONFIRMED. 109 more covered places have no rule yet. Minnesota is the
  largest contributor to D-025, as it already is today (the Twin Cities panel).
- **The missing-middle panel (D-024) has 100 Minnesota places of 10,000+, with 3 in-window events:**
  Minneapolis (2020), Richfield (2023) and St. Louis Park (2025), all adopted on dates confirmed from official
  records. St. Paul's 2023 reform is the V5 holdout.
- **V5 St. Paul inputs** are in #259: 55,269 eligible H1/H2 lots on the pre-window roll, from the city's dated
  zoning snapshot.
- **Every rule row has been second-coded** (Codex, 2026-11-02): 8 agreed, 60 adjudicated by Ben (all
  recommendations accepted), and Ben's lookups then settled all but 4 reform dates. See §6.

**Starting an engine run? Begin with §0.**

## 0. Engine kickoff (2026-11-02)

What an engine thread needs from Minnesota, in one place. Details are in §2 and §6.

- **Merge first, in order:** #256 (plan), #259 (V5 St. Paul inputs), #260 (missing-middle rules), #261 (MnGeo
  parcels and the statewide eligible rebuild), then this PR (#262, stacked on #260 and #261). Engines read
  `config/reforms/mn.csv` from `main`, so nothing here counts until #262 is merged.
- **Eligible lots changed for every MN place** (#261). The rebuilt tables are already in `LOTLINE_DATA_DIR`
  (2026-11-02): don't rebuild, but anything run on the old table is stale.
- **Holdout:** St. Paul (2758000), outcomes from 2024-01-01 and rolls exported on or after that day. Go through
  `holdout.apply` (rolls with `snapshot=True`); never pass `--unblind`. Don't use the post-reform St. Paul
  figures (D-013).
- **Tags in `config/reforms/mn.csv`, which every engine must respect:**
  - `[predates]` (Stillwater, Baytown, Denmark, Rochester missing middle, and others): never an event.
  - `[earliest-known]` (10 ADU event rows, including the four 2025 Scott County rows with no Board date): run
    with and without them as events.
  - `DATE UNCONFIRMED` (4 rows: Eagan 2014, Richfield 2015, St. Louis Park 2020, Fridley 2022): counts as an
    event at its date; also run without them (Ben, 2026-11-02).
  - A "none" row (`adus_per_lot = 0`, or missing-middle `unit_cap = 1`) is a control, never an event.

| Run | What MN adds | Run variants | Caveats |
|---|---|---|---|
| **D-025 ADU** (`src/lotline/model/pooled_adu.py`, `scripts/dev/estimate_pooled_adu.py`) | 71 places: 43 with an in-window change (54 event rows), 28 "no ADUs" controls. Met Council covers every metro community; Minneapolis CCS covers Minneapolis | Main: all event rows. Sensitivities: without the 4 DATE UNCONFIRMED rows; without the 10 `[earliest-known]` rows | ADU flags start in 2014 (Met Council) and 2016 (Minneapolis), so the 2010–2013 events (Scott County townships, Hugo, Medina, Roseville, Lakeville) have no ADU-flagged pre-years. 12 event rows fall in 2025 and have almost no post-period; Sunfish Lake (2025-12-09) may fall just outside the window. Drop Minneapolis 2026 (partial) |
| **D-024 missing middle** (`src/lotline/model/estimate_mm.py`) | 100 BPS places of 10,000+; 3 in-window events: Minneapolis 2020-01-01, Richfield 2023-01-24, St. Louis Park 2025-03-28. Controls on evidence: Brooklyn Park (R-1), Coon Rapids, Rochester (R-1) | Main: the 3 events. Sensitivity: Minneapolis with the injunction windows (2022-06-15 to 07-26; 2023-11-04 to 2024-05-13) | Richfield's effective date is coded as passage; the true date is about a month later. Its pre-2023 rule (conditional duplexes on arterial lots) is a partial dose. St. Paul is excluded (V5) |
| **V5 St. Paul** (#45, freeze **by Nov 17**) | `reports/mn/V5-stpaul-inputs.md` (#259): 55,269 eligible H1/H2 lots on the pre-window roll | — | Cap annual inputs at 2023. Disclose D-013's exposure in the freeze file |

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
| **Rule change in the window** | **43** | Minneapolis (2014, 2016, 2021, 2023) and 42 suburbs. 10 of their 54 event rows are dated `[earliest-known]` (4 are the 2025 Scott County rows, adoption date unknown) and 4 are DATE UNCONFIRMED; only 39 places have an event on a confirmed date. Run with and without the unconfirmed dates |
| **"No ADUs" controls** | **28** | Coded "none" rows in covered places |
| Rule, no event, not a control | 5 | Rules only before the window, or `[predates]` (Stillwater, Baytown, Denmark) |
| **Covered, no rule yet** | 109 | Largest: Brooklyn Center 33,782, Chaska, Prior Lake, Shoreview, Hastings, Lino Lakes, Northfield, Waconia, North St. Paul, East Bethel, Lake Elmo, White Bear township, Little Canada, Victoria. Each one coded joins the panel at once |
| Rules but no permit source | Duluth, Rochester, St. Cloud | Outstate: no record-level permits, so they can't enter |

So Minnesota's 71 places stay the core of the D-025 panel. Today's estimate already uses the Twin Cities places
(`scripts/dev/estimate_pooled_adu.py`, `metc_residential_permits`). This work adds no new place to it, but the
109 covered places without a rule are the cheapest way to grow it: one lookup each.

**Missing-middle estimate (D-024).** The outcome is BPS 2–4 unit homes, so **all 100 Minnesota BPS places of
10,000+ are in**.

| Group | Places |
|---|---|
| **In-window events** | Minneapolis (2020-01-01; the injunction windows 2022-06-15 to 2022-07-26 and 2023-11-04 to 2024-05-13 as sensitivity) and St. Louis Park (2025-03-28, Ord. 2690-25; duplex and 3-unit in N-1 and N-2, 4-unit in N-2) and Richfield (Bill No. 2023-2, passed 2023-01-24: duplexes by right in R, previously conditional on arterial or collector lots only; effective about 30 days after publication, date not found, coded as passage) |
| Untreated on evidence | Brooklyn Park (R-1), Coon Rapids (LDR1/LDR2) |
| Untreated on evidence (R-1) | Rochester: R-1 has allowed one home per lot since a 1998 amendment, so the 2023 UDC changed nothing there (`[predates]`); 2-4 units with staff approval in other districts |
| Outside the panel | St. Paul 2023 (V5 holdout); Duluth 2026 (after the window) |

## 3. Remaining gaps and what closes each

| Gap | Effect | What closes it | Owner |
|---|---|---|---|
| **4 D-025 event dates unconfirmed** | 4 of the 43 event places have no event on a confirmed date | City clerks, council minutes or signed ordinances (`mn-second-coder-lookups-2026-11-02.csv`) | **Ben** |
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
2. **Lookups:** the 4 unconfirmed dates in `mn-second-coder-lookups-2026-11-02.csv` need primary records; then
   `mn-mm-lookups-todo.csv` (33 places). Hugo and Rochester are settled (§6).
3. **County code tables** for Crow Wing, Itasca, Koochiching, Jackson and Houston. Ask each assessor for their
   three-digit property-type code list (the codes 151, 111, 765 and others are unlabelled).
4. ~~Decide whether seasonal cabins count as houses~~: **decided 2026-11-02, they stay out** (§3).
5. **Review order:** #256 (plan), #259 (V5), #260 (rules), #261 (parcels), then this PR (stacked on #260 and
   #261).

## 6. Second-coder review and lookups (2026-11-02)

Ben's second agent (Codex) filled all 109 rows of `mn-second-coder-2026-11-02.csv` (8 yes, 92 partly, 9 no).
It counted a date as confirmed only with a signed ordinance or an effective-date record, and it wrote over the
sheet's left-hand columns (our coding as sent is the sheet at 54e9727). Ben accepted all 62 recommendations in
`mn-second-coder-decisions-2026-11-02.csv`, then worked the lookups himself, one place at a time. Every change is
in a script, idempotent and in run order:

1. `scripts/dev/mn_second_coder_2026_11_02.py`: the reviewer's findings appended as notes; 8 rows marked agree.
2. `scripts/dev/mn_second_coder_decisions_2026_11_02.py`: the 62 decisions; writes the lookup list.
3. `scripts/dev/mn_lookups_2026_11_02.py`: Ben's lookups (sources, dates and reasons are in each row's notes).

| Outcome | Rows |
|---|---|
| **Deleted** (not ADU reforms) | Hopkins 2024 (accessory-structure footprints), Grant 2016 (state-law opt-out), Burnsville 2020 (no 2020 adoption), Medina 2024 (a height rule) |
| **Added** | Roseville 2011 (Ord. 1418, conditional to permitted), Mounds View 2025b (Ord. 1045, detached by CUP), Scott County 2025 amendment for Cedar Lake, Helena, Jackson and St. Lawrence townships, Richfield missing middle 2010 (conditional duplexes) and 2023 (by right, a D-024 event) |
| **`[predates]`** (never events) | Stillwater (ADUs since the late 1990s; the 2017 date was a rental ordinance), Baytown (2040 plan), Denmark (2017 code), Rochester missing middle (R-1 one home since 1998) |
| **Dates confirmed from official records** | Andover, Crystal, Golden Valley, Hugo (Ord. 2011-459), Inver Grove Heights 2015 (Ord. 1305), Lakeville, Medina 2011, Minnetonka, Mound, Mounds View 2025a and 2025b, Oakdale, Plymouth, Ramsey, Rogers (effective date), Rosemount, Roseville 2011 and 2021, Scott County 2010 (four townships), St. Louis Park missing middle, Sunfish Lake, Vadnais Heights, Wayzata, White Bear Lake, Forest Lake |
| **Values fixed** | Chanhassen (CUP, not by right), Mounds View 2025b (CUP), Richfield (no detached ADUs), Oakdale (by right), Brooklyn Park one-home row (R-1 only), Roseville 2011 cap (600 sq ft); blank fields filled for about 15 places from code readings |
| **Re-dated** | Burnsville 2018 (2018-05-22), Columbia Heights (2024-08-26), Cottage Grove (2023-01-01), Fridley (2022-09-01, earliest known), Golden Valley (effective 2022-11-11), Inver Grove Heights 2015 (effective 2015-11-02), Mounds View (2025-06-29 and 2025-09-13), Richfield ADU (2015-07-01, earliest known), St. Paul ADUs (2018-12-01) and parking (2021-10-01), Minneapolis injunction (2022-06-15), Wayzata (effective 2022-06-30) |
| **Still DATE UNCONFIRMED** | Eagan 2014 (almost certainly Ord. 528), St. Louis Park ADU 2020 (Council likely first saw it 2020-10-05), Richfield ADU 2015 (Bill No. 2015-4), Fridley 2022: each needs the city clerk's signed ordinance |

**Rule decisions recorded here:** seasonal cabins stay out of eligibility (Ben, 2026-11-02); a "none" row is a
control, never an event; a `DATE UNCONFIRMED` row counts as an event and engines also run without it (Ben,
2026-11-02, for HANDOFF). Open, not blocking: whether Stillwater's 2021 RA expansion was adopted; Sunfish Lake's
publication date (if after 2025-12-31 its event leaves the window); the Richfield missing-middle publication
date.

The agent's research tracker, evidence register, PDF inventory and issues note are in `docs/research/ordinances/`;
its 14 PDFs are in `LOTLINE_DATA_DIR/manual/mn/second_coder_2026-11-02/`.
