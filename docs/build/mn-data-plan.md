# Minnesota data plan (thread 13, part B, step 1)

*WS-MN, 2026-11-01. Status: **draft, for Ben's approval** (§5). Brief: `docs/build/handoffs/13-nc-mn-wrap-up.md`
(Part B), which replaces the integration run in thread 8's task 6. Thread 8 (`08-minnesota-data-complete.md`)
was written but never run. Template: `docs/build/nc-data-plan.md`, `docs/build/tx-data-plan.md`.*

**Goal by Thu Nov 12:** Minnesota has the same standing as Ohio and Texas on 2026-11-01. That means a readiness
report saying, for every input, what is real and what is a fallback. It also means St. Paul's V5 inputs are on
`main` in time for WS-ENGINE to freeze the prediction by **Tue Nov 17**. No model runs (data-thread rule).

## 1. What exists today (checked 2026-11-01)

I checked `main` at f9d9624 and `~/lotline-data/processed/mn`. Every outcome table was read through
`holdout.apply`, and parcel rolls with `snapshot=True`. The brief's snapshot is right, with the corrections in
bold.

| Input | On `main` / in the data folder | Gap |
|---|---|---|
| Jurisdictions | 1,053: 763 places, 218 townships, 72 county remainders. 23 are local-only (22 townships and 1 place). Tiers 116 / 69 / 868 | — |
| Parcels | Met Council: 186 metro jurisdictions in 7 counties, yearly rolls 2021–2026, with land use, year built and units. Minneapolis assessor rolls 2017–2026. Ramsey's current roll (2026-10-08, outside St. Paul) | **80 outstate counties have no parcels.** Rolls from 2002–2020 are token-locked (request #11). Hennepin leaves `NUM_UNITS` and `DWELL_TYPE` blank. Met Council parcels carry **no zoning field** |
| **Eligible lots** | **186 jurisdictions from parcels (66.0% of the population of MN places), 865 on ACS** | **The table predates D-035:** every row is either `parcels` or `acs_sf_fallback`, with no `parcels_scaled_acs` or `parcels_interpolated` rows. So parcel-counted places have counts only for their roll years (2021–2026), with no history to 2010. **Two jurisdictions have no row**: Wyoming township (2702572040) and Baldwin (2703286). A rebuild on today's `main` fixes the first problem (task M3). Since the Met Council rolls are yearly, #252's interpolation changes nothing for them; D-035's ACS scaling fills 2010–2020 |
| Permits | BPS statewide. Met Council 2009–2025: 114,363 permits in 186 jurisdictions; 341 ADUs in 53 places after the filter; types SFD, TH, DTQ and MF5. Minneapolis CCS 2016–2026 (211 ADUs inferred). St. Paul to 2023 (no ADU flag; the holdout removes 2024 on) | Outstate cities have no record-level permits. Met Council undercounts Minneapolis internal ADUs (LB-057) |
| ADU rules | 98 rows for 80 places, mostly metro; one coder each | Outstate is mostly uncoded (D-022 draws a rule type). **109 Met Council places have permits but no ADU rule** |
| Missing-middle rules | 2 rows: Minneapolis 2020-01-01 (3 units) and St. Paul 2023-11-26 (4 units, H1/H2). Also two Minneapolis moratorium rows (2022, 2023) and two parking rows | Duluth, St. Louis Park, Rochester, Brooklyn Park and Coon Rapids are in the batch-1 records but not coded |
| Fees | `config/fees/mn.csv`: 171 rows, 2016–2027, mostly Rochester (58) and 2708794 (34) | No Met Council SAC series; most places have nothing |
| Market, demand | ACS, FHFA, FRED, demand index: processed | — |
| **V5 St. Paul** | Holdout in `mn.yaml` (2758000, 2024-01-01 to 2026-12-31). **Three pre-2024 St. Paul rolls survive the snapshot filter: 2021, 2022 and the "2023" roll, exported 2023-12-26** (Ramsey's part of the 2023-10-01 to 2024-01-08 export). Each has about 83,300 parcels, with land use known on more than 99.9% and year built on all. Met Council DTQ and MF5 permits to 2023. The reform row is coded | **No V5 input note.** H1/H2 lots can't be found from the parcels (no zoning): this needs St. Paul's zoning layer (M1) |

## 2. What "done" needs

As in NC and Texas, an end-to-end run already works with fallbacks: the ACS denominator (D-017), rule draws
(D-022) and the $50,000 fee prior (D-034). So the **must-do** items are the ones V5 or the readiness report
can't do without; everything else is **accuracy**.

## 3. Subtasks

"Automatable" means public APIs, data already in the repo, or official pages opened directly, with no broad web
searching. Costs are my wall-clock time, and whether the work is token-heavy.

| # | Subtask | Feeds | Source | Automatable? | Cost | Priority | Owner |
|---|---|---|---|---|---|---|---|
| **M1** | **St. Paul V5 input note** `reports/mn/V5-stpaul-inputs.md`. The prediction (WS-MN, validation plan V5): St. Paul DTQ and MF5 units on H1/H2 lots, 2024–2026, from data up to 2023. The note lists what exists and is dated by 2023: the 2021–2023 rolls (newest exported 2023-12-26); the 2023 reform rows; Met Council permits to 2023; market and demand capped at 2023 (the same annual rule as NC's V5 check). It gives the exact files and columns, and what's missing. **H1/H2 lots:** the reform row says "former R1–R4, RT1, RT2 and low-density PD, now H1 and H2". Two options: (a) St. Paul's current zoning layer, reading the H1/H2 polygons and joining them to the 2023 roll's points (current zoning is an input, not an outcome, but rezonings since 2024 would leak in a little: disclose it); (b) a pre-reform zoning layer translated as for Charlotte, if the city publishes one with a date before 2024. I check (b) with one metadata query and fall back to (a) | V5 freeze (WS-ENGINE, #45) | `stpaul_zoning` (ArcGIS REST, in WS-MN's source list; not built), processed tables | Yes | 3–4 h, low tokens; adapter plus tests if (a) or (b) needs one | **Must** | Me; **Ben chooses (a) or (b)** if (b) exists |
| **M2** | **Outstate parcels**, `adapters/states/mn/mngeo_parcels.py` for MnGeo's opt-in compiled parcels: 59 of 87 counties (all 7 metro), about 2.7M records, current roll only, license "None" (as-is: recorded in `docs/disclosures.md` and the provenance). Steps: (i) distinct `useclass1` values per county with ArcGIS statistics queries (no parcel download); (ii) a crosswalk to `land_use_std` (the GAC standard schema shares one vocabulary, so one shared file plus per-county exceptions); (iii) the D-017 gate (90% known land use) and the 0.6–1.4 check against ACS one-unit homes, both as in NC; (iv) **after Ben approves**, the download of the about 52 outstate counties. Metro counties stay on `metc_parcels` and `mpls_assessor_parcels` through `parcel_sources`. The snapshot rule keeps St. Paul out of the current roll | Eligible lots and tiers for Greater Minnesota | MnGeo FeatureServer (`enterprise.gisdata.mn.gov`, `plan_parcels_open`) | Yes; robots.txt checked first | Code lists and crosswalk: 2–3 h, moderate tokens. Download: about 2M outstate records, about 1 h unattended. Adapter and tests: 3 h | **Must** (it is most of MN's denominator gap) | Me; **needs approval (download)** |
| **M3** | **Rebuild `jurisdictions` and `eligible_parcels`** after M2, on today's `main`, so D-035's scaled history (2010–2020) is filled for every parcel-counted place. Report jurisdictions by denominator source and quality, check that no jurisdiction has two sources (D-020), explain why Wyoming township and Baldwin have no row, and compare totals with ACS one-unit homes by county | Every engine's denominator | `lotline fetch --state MN --source eligible` | Yes | 1–2 h, low tokens | **Must** (the current table has no history) | Me |
| **M4** | **Missing-middle rules from the batch-1 records**. Minneapolis 2020-01-01 is already coded; I add the injunction windows (2022-06-17; 2023-11-04 to 2024-05-13) as sensitivity rows, checking the two existing moratorium rows first. Also Duluth, St. Louis Park, Rochester (not legal), Brooklyn Park and Coon Rapids (not legal), coded as one-home rows where duplexes aren't allowed. Everyone else goes in `docs/research/ordinances/mn-mm-lookups-todo.csv` (NC and TX format), with the 40 largest places first, metro and outstate | D-024 events and controls; current-rules scenario | `docs/research/ordinances/batch1-2026-10-20.json` | Yes (no new research) | 2–3 h, moderate tokens | **Must** | Me, then **Ben** for the CSV |
| **M5** | **Readiness report** `docs/build/mn-readiness.md` (counts only), in the Ohio and Texas format. §2 counts the D-025 places with Met Council ADU-flagged permits and a dated rule. Today: **185 covered places (St. Paul out), 76 with an ADU rule, 49 with an in-window change, 109 with no rule.** The report lists the covered places with no rule, largest first. Plus a second-coder sheet for MN, in-window event rows first, and a refresh of the MN rows of `docs/data_availability.md` | Ben's Nov 10 benchmark-state choice; the engine week | — | Yes | 3–4 h, moderate tokens | **Must** | Me |
| M6 | Outstate ADU fill-in table, `mn-adu-outstate-lookups-todo.csv`: the 30 largest outstate places (Rochester, Duluth and St. Cloud are coded; next Mankato, Moorhead, Winona, Owatonna, Austin, Willmar and others) | ADU current rules (D-022 fewer draws) | — | Yes | 1 h | If time | Me, then **Ben** |
| M7 | Met Council SAC per-unit history as fee rows, and which places are in the sewer service area | Fee scenario (metro) | Met Council SAC pages and PDFs | Partly | 2–3 h, token-heavy (PDFs) | If time | Me |
| M8 | Met Council Regional Planned Land Use and the Minneapolis zoning layers, for rule coverage (D-021) | ADU and MM coverage shares | ArcGIS REST | Yes | 3 h | If time (accuracy) | Me |

**Out of scope:** new record-level permit sources for outstate cities; pre-2021 metro rolls (waiting on #11);
any model run.

**Order and dates:**
- **Mon Nov 2:** M1 starts. The H1/H2 zoning check comes first, because V5 is the tightest date.
- **Tue–Wed Nov 3–4:** M2 (i)–(iii). The download waits for approval.
- **By Fri Nov 6:** M1 note open as a PR.
- **Mon Nov 9:** M2 download, then M3.
- **Tue–Wed Nov 10–11:** M4.
- **By Thu Nov 12:** M5 open as a PR.
- **After that, if time allows:** M6–M8.

One small PR each.

## 4. V5 St. Paul: what the freeze needs (Nov 17)

| Need | Status | What closes it |
|---|---|---|
| Pre-2024 St. Paul parcels | 2021, 2022 and 2023 rolls, the newest exported 2023-12-26 (before the window) | — |
| H1/H2 lots (formerly R1–R4, RT1, RT2, low-density PD) | Missing: no zoning on the parcels | M1 (a) or (b) |
| Reform rows | `MN-2758000-missing_middle-2023` and `-adu-2023`, effective 2023-11-26; one coder | Second coder (M5 sheet) |
| Baseline permits | Met Council DTQ and MF5 for St. Paul, 2009–2023; BPS 2758000 to 2023 | — |
| Market and demand | Processed | Cap annual inputs at 2023 (the window opens 2024-01-01) |
| Missing-middle effect | Whatever D-024 estimate or prior is on `main` at the freeze, as for Charlotte | WS-ENGINE |
| Known exposure | D-013: post-reform St. Paul figures appeared in a research doc. Not repeated, not used | Disclosed in the freeze file |
| Freeze file | `results/frozen/V5-MN-STPAUL.json` | WS-ENGINE, by Nov 17 |

Nothing in this plan opens a St. Paul outcome from 2024-01-01, or a St. Paul roll exported after 2023.

## 5. Decisions I need from Ben

1. **Approve the plan:** M1–M5 as must-do; M6–M8 if time allows.
2. **Approve M2's download**: MnGeo opt-in parcels for the outstate counties, about 2M records into
   `~/lotline-data`, about 1 h unattended. The license is "None" (as-is); I record it in `docs/disclosures.md`.
3. **V5 H1/H2 source:** (b), a pre-reform zoning layer, if one exists with a date before 2024; otherwise (a),
   the current zoning layer, with the leak from post-2024 rezonings disclosed. I recommend (b) if it exists, (a)
   otherwise.
4. **Second coding:** the MN rule rows are all single-coder, as NC's and Texas's were. Use the same worksheet
   approach (the M5 sheet)?

**Rule added 2026-11-01 (HANDOFF, from the NC review):** a row whose date is only a code rewrite carries
`[predates]` and is never an event. M4 codes it that way where the batch-1 records show a recodification, and
the M5 counts leave `[predates]` rows out of the D-024 and D-025 events. NC's review found 10 of 31
`[earliest-known]` rows were rewrites, so the MN second-coder sheet puts in-window `[earliest-known]` rows first.
