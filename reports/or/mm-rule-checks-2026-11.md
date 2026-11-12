# Oregon missing-middle rule checks, November 2026

**Question:** are Oregon's `missing_middle` rule rows ready to join the fit? Two jobs, both **from the rule rows and
the code's logic only**: (1) second-code the 7 single-coder rows and the 2 `DATE UNCONFIRMED` rows; (2) list each
place's first cap-rise event under `calibrate_mm.event_year` / `prior_cap`.

**No outcome was read or tabulated** (no BPS, permits or rolls); no engine, fit or scenario was run. Step 2 ran only
the code's own rule functions (`rule_tags.apply`, `estimate_mm.rules_by_year`, `adoption_year`, `blank_shares`,
`calibrate_mm.event_year`, `prior_cap`, `adu.rule_coverage` with no parcel roll) on `config/reforms/or.csv`. **`or.csv`
is not edited**: every correction below is a proposal for Ben. No records requests or staff emails; sources that
would need them are closed as "no usable source". Context: `docs/research/mm-methodology-review-2026-11.md`
(PR #392, branch `ws/mm-review`, not yet on `main`) and the brief `WS-MM-REVIEW.md` (branch `ws/mm-review-brief`).

## Summary

- **Of the 9 rows, none could be confirmed in full from primary ordinance text**, and four are not as coded:
  Stayton (wrong zone), Sweet Home (R-1 duplexes are corner-lot only), Florence (duplexes probably allowed before the
  coded "first" rule), Scappoose (also R-4 and A-1). Bend's effective date is probably not 2016-10-21. Most city
  code sites (Bend, Lincoln City, Independence planning pages, Sweet Home's ordinance page) returned 403/404 to
  automated reading; text was read from mirrors (Zoneomics), newsletters and PDFs where possible.
- **None of the date doubts moves an event year**, with one exception to settle (Bend): the code reads rules on
  1 July, so a date only matters if it crosses 1 July. Independence (E 2023) and Lincoln City (E 2022) are robust to
  any effective date within about two months of the coded one.
- **Event years (rows alone):** of 111 places, **108 have a first cap-rise event** in 2013–2025: 24 in 2021
  (1→2, medium tier), 37 in 2022 (36 to 4 on the large tier, 1 to 2: Lincoln City), 2 in 2023, 1 in 2024 and
  44 in 2025 (1→2, the 2023 c.223 small-city duplex duty). **Three places have none under the code:** Bend,
  Scappoose, Stayton (details below). With at least 3 post-years in a panel to 2025 (E ≤ 2022) there are
  **61 places**, or 62 if Bend is repaired; the 44 places at E = 2025 have at most one partial post-year.
- **Of the 49 `[earliest-known]` rows** (48 places): 47 are the 2025 small-city duty rows (blank adoption date;
  deadline from ORS note), 1 is Florence's 2023-local row, 1 is Bend's 2019 `[predates]` table row (prior state, not
  an event). The deadline dates behind the 47 are **confirmed** (below). The real doubt is the *prior cap* at those
  places, not the date.
- **A code finding for the method entry:** every state SB 458 `-landdiv` row (111 rows) has a blank
  `adoption_date`, so `rule_tags.flags` marks it `earliest_known`, and the `earliest_known` sensitivity
  (`dropped_places`) would drop essentially all of Oregon, not the 49 flagged rows. Give those rows adoption dates
  (SB 458 signed 2021; no emergency clause) or exclude them from the flag. Not edited here.

## 1. Second-coding the nine rows

Method: a second coder (three Sonnet subagents, web reading only, briefed to report `agree` / `disagree` /
`cannot confirm` per fact, with citations) read each row's primary source where reachable. They did not see
outcomes. Same model family as the first coder, so this is not fully independent. "Inferred" means a deduction, not text.

| Row | Verdict | Proposed correction (Ben decides) |
|---|---|---|
| Bend 2016 `OR-4105800-missing_middle-2016` (single) | **Effective date disagrees; rest cannot confirm** | `effective_date` 2016-12-06 (city code history lists NS-2271 so; read from a search summary only, page 403); adoption 2016-09-21 unconfirmed; zones and the cap 3 still unconfirmed. Event year unaffected (both dates fall before 1 July 2017). Keep single-coder; see Bend note. |
| Independence `OR-4136150-...-2022-local` (DATE UNCONFIRMED) | **Partly confirmed** | Adoption 2022-07-12 stands: code header "Adopted by Ordinance 1598 – July 12th, 2022" plus the 2022-07-08 newsletter ("Council will consider … duplexes on all lots zoned for single-family"). Effective clause not found (2022-08-11 stays inferred). The proposal "duplexes a permitted use in all residential zones" is from the March 2022 newsletter (proposed text). Keep `DATE UNCONFIRMED`. Independence crossed 10,000 in PSU's certified estimates around 2021, consistent with a state duty (computed row 2022-12-15, unverified). |
| Lincoln City `OR-4142600-...-2022-local` (DATE UNCONFIRMED) | **Cannot confirm** | Planning Commission hearing on ZOA 2022-04 on 2022-02-15; Council 2022-03-14 and a 2022-03-28 agenda item "Ord. 2022-10 Duplex Fix" (agenda, vote not seen). Ordinance text, effective clause, zones not read (403). Keep `DATE UNCONFIRMED`. Close as "no usable source" unless Ben finds the ordinance. |
| Sweet Home `OR-4171950-...-2022-local` | **Dose disagrees** | Adoption 2022-09-27 agrees (city ordinance index). Effective clause not seen. Reading of the post-Ord. 1305 code (Zoneomics mirror): R-1 §17.10.020(2) permits duplexes but §17.10.050(2) allows "no more than one duplex per corner lot", with a 7,000 sq ft lot; R-2 and R-3 permit duplexes with one structure per lot. So "duplexes wherever single-family dwellings are" is **not supported**. Propose `coverage` text "R-1: corner lots only; R-2, R-3 duplexes permitted" (matches the code's limited-scope regex, coverage 0.2) or `coverage_zones` R-2;R-3. Also: the code mentions duplexes "created through conversion", so Ord. 1305 may not be the first duplex rule. Ord. 1321 (2023-07-25) date agrees; its content is unread (scan). |
| Florence `OR-4126050-...-2023-local` (`[earliest-known]`) | **Current rule agrees; "first" does not** | Ord. 6, Series 2023: passed 2023-07-17; effective 2023-08-17 per Ch. 10 history, 2023-08-16 per the ordinance index (unresolved). Table 10-10-2-A: duplex P (Type I) in LDR, MDR, RMH, HDR; cap 2 agrees. But Ord. 7, Series 2019 (effective 2019-12-18) amended "all sections", and a 2021 annexation ordinance (snippet) says MDR allows duplexes outright. Duplexes were probably allowed in some zones before 2023. Propose: tag `[predates]` for MDR or add a pre-2023 row once the 2019 text (DLCD notice, DocumentCenter View/2246) is read; until then treat Florence as unresolved (drop in sensitivity). |
| Scappoose `OR-4165500-...-2004-local` (`[predates]`) | **Wording agrees; zones too narrow** | SMC 17.44.030 R-1 duplexes "permitted outright" outside the Scappoose Creek flood plain (via mirror; city PDF 404). Duplexes are also permitted outright in R-4 (17.50.030) and A-1 (17.56.020), with triplexes and quadplexes outright in A-1. The city has no R-2/R-3. Propose `coverage_zones` R-1;R-4;A-1 and a note that A-1 reaches cap 4. First ordinance not found (Ord. 634 of 1995 is the earliest in the history): keep `[predates]`. |
| Stayton `OR-4170200-...-2007-local` (`[predates]`) | **Zone disagrees** | Table 17.16.070.1 duplex row, parsed from the city PDF: permitted in **MD and DMD** only (footnote 13: site plan review for more than one duplex); **LD blank (prohibited)**; S/C/P in commercial and mixed-use zones. Propose `coverage_zones` MD;DMD (not LD;MD). Parsing aligned columns by text, so confirm with the PDF image. Whether Ord. 1060 (2023) touched the row is unknown. Keep `[predates]`. |

Cited sources (first-hand where noted): Bend city ordinance register and Comp Plan adopted-amendments table
(search summary); Independence code Subchapter 30 PDF and newsletters (2022-03-18, 2022-07-08) at
ci.independence.or.us; PSU Population Research Center certified estimates 2020 and 2022; Lincoln City
council/commission agendas (summaries); Sweet Home ordinance index (sweethomeor.gov/1215/Ordinances) and
zoneomics.com/code/sweet-home-OR; Florence Ch. 10 (DocumentCenter/View/190) and Ordinance Index (View/756);
Scappoose via zoneomics.com/code/scappoose-OR; Stayton `17.16 Zoning.pdf` (staytonoregon.gov).

**State-law dates, re-checked (they set most of the events):** compliance deadlines are June 30, 2021 (cities over
10,000 outside Metro, duplex), June 30, 2022 (over 25,000 and Metro cities, all middle housing), June 30, 2025
(other cities under ORS 197A.420(3), duplex) and Jan 1, 2027 (HB 2138), from the enrolled HB 2138 §4 restating
2019 c.639 §3 and the ORS 197A.420 note. Confirmed against the statute text. The statute does not define population; OAR 660-046-0020 uses
PSU's certified estimate while `or.csv` uses the 2020 Census (already noted in the rows). **Thin spot:** the medium-tier event is dated
2021-06-30, one day before the 1 July reading, so an effective date of 1 July or later would move 24 places
from 2021 to 2022. The statute says "by June 30, 2021", so this holds. Cities crossing a threshold later get
"computed" state rows (2022-12-15, 2023-12-15); OAR 660-046-0050 (read via snippet) gives a newly qualifying medium
city one year and a large city two years, which these rows do not obviously follow. Unchecked.

## 2. First cap-rise events (rows alone)

**Rule used (code):** T = `adoption_year` (first year, from 1990, with a rule in force on 1 July with P(by right)
≥ 0.5 and dose above 0; `[predates]` and before-window rows are always in force); event year E =
`event_year(T, dose_by_year, 2013, 2025)`: T if inside the window, else the first year the dose rises; prior cap
= `prior_cap` at 1 July E−1 (largest `unit_cap` of live rows with coverage ≥ 0.5; 1 if none), new cap at 1 July
E. A place has an event only if new cap > prior cap (D-042). Coverage without a parcel roll falls to the D-021
judgment shares (0.75 for a zone list or lot minimum; 0.2 for "only in…" text), so every row here passes the 0.5
test except as noted. **Coverage is therefore a judgment, not measured:** the real roll may move a place across 0.5.
The full table is `reports/or/mm-first-events-2026-11.csv` (111 rows: GEOID, name, event year, prior and new cap,
rows that set the event, flags).

| Event year | Prior → new cap | Places | Basis |
|---|---|---|---|
| 2021 | 1 → 2 | 24 | HB 2001 medium tier (deadline 2021-06-30) |
| 2022 | 1 → 4 | 36 | large tier (2022-06-30); includes Portland (local RIP 2021-08-01, read 1 July 2022), Tualatin, Forest Grove, Troutdale, Tigard, Lake Oswego, 3 unincorporated counties |
| 2022 | 1 → 2 | 1 | Lincoln City (local 2022-04-27; state row 2022-12-15) |
| 2023 | 1 → 2 | 2 | Independence and Sweet Home (local 2022; Sweet Home's coding disputed above) |
| 2024 | 1 → 2 | 1 | Florence (local 2023-08-17; disputed above) |
| 2025 | 1 → 2 | 44 | 2023 c.223 small-city duplex duty (2025-06-30), all `[earliest-known]` |
| none | — | 3 | Bend, Scappoose, Stayton |

**Places by group**

- **2021, 1→2 (24):** Ashland (4103050); Astoria (4103150); Baker City (4103650); Canby (4110750); Central Point (4112400); Coos Bay (4115250); Cottage Grove (4115950); Dallas (4117700); Hermiston (4133700); Klamath Falls (4139700); La Grande (4140350); Lebanon (4141650); Molalla (4149450); Monmouth (4149550); Newport (4152450); North Bend (4153000); Ontario (4154900); Pendleton (4157150); Prineville (4159850); Roseburg (4163650); Sandy (4165250); Silverton (4167650); St. Helens (4164600); The Dalles (4172950).
- **2022, 1→4 (36):** Albany (4101000); Beaverton (4105350); Cornelius (4115550); Corvallis (4115800); Durham (4121250); Eugene (4123850); Fairview (4124250); Forest Grove (4126200); Gladstone (4129000); Grants Pass (4130550); Gresham (4131250); Happy Valley (4132050); Hillsboro (4134100); Keizer (4138500); King City (4139150); Lake Oswego (4140550); McMinnville (4145000); Medford (4147000); Milwaukie (4148650); Newberg (4152100); Oregon City (4155200); Portland (4159000); Redmond (4161200); Salem (4164900); Sherwood (4167100); Springfield (4169600); Tigard (4173650); Troutdale (4174850); Tualatin (4174950); Unincorporated Clackamas Count (41005); Unincorporated Multnomah Count (41051); Unincorporated Washington Coun (41067); West Linn (4180150); Wilsonville (4182800); Wood Village (4183950); Woodburn (4183750).
- **2022, 1→2 (1):** Lincoln City (4142600).
- **2023, 1→2:** Independence (4136150); Sweet Home (4171950).
- **2024, 1→2:** Florence (4126050).
- **2025, 1→2 (44):** Aumsville (4103250); Bandon (4103800); Boardman (4107200); Brookings (4108650); Burns (4109800); Coquille (4115350); Creswell (4116950); Dayton (4118250); Dundee (4121050); Eagle Point (4121550); Estacada (4123800); Gervais (4128650); Harrisburg (4132550); Hood River (4134900); Hubbard (4135450); Jacksonville (4137000); Jefferson (4137250); Junction City (4138000); La Pine (4141050); Lafayette (4140300); Madras (4145250); Millersburg (4148300); Milton-Freewater (4148600); Mount Angel (4150150); Myrtle Creek (4150950); North Plains (4153150); Nyssa (4153750); Oakridge (4154100); Philomath (4157450); Phoenix (4157500); Reedsport (4161300); Seaside (4165950); Shady Cove (4166550); Sheridan (4167050); Sisters (4167950); Sublimity (4170700); Sutherlin (4171650); Talent (4172500); Tillamook (4173700); Toledo (4174000); Umatilla (4175650); Veneta (4177050); Warrenton (4178900); Winston (4183400).

**The three places with no event (and what to decide):**

- **Bend (4105800):** the code reads T = 1990 because the 2019 table row is `[predates]` (cap 3), takes E = 2017
  from the first dose rise (the 2016 Ord. 2271 row, cap 3, wider coverage), finds 3 → 3, and drops the place.
  The real first rise to cap 4 is Ord. NS-2423 (effective 2021-11-05) / the state row: **E = 2022, 3 → 4**.
  Fix in the method entry (choose the first dose rise that is also a cap rise); not a rows edit. If the 2016 row is
  wrong or untrusted, nothing else changes.
- **Scappoose (4165500), Stayton (4170200):** `[predates]` duplex rules at cap 2, so 2025 is 2 → 2. With the
  corrected zones above, Stayton's rule covers only MD and DMD, which is likely under half of eligible
  single-family lots once measured, so the 2025 duty would be a real **1 → 2 rise at E = 2025** (likely; needs the roll). Scappoose's
  R-1 is likely its main single-family zone, so it stays no-rise.

**The 49 `[earliest-known]` rows needing a check:**

| Group | Rows | Verdict from rows and statute |
|---|---|---|
| 2025 small-city duty (2023 c.223) | 47 | Date confirmed (June 30, 2025) from the statute. The flag is the blank `adoption_date` plus the deadline source. What is unchecked is the prior cap: Scappoose and Stayton show small cities already allowing duplexes locally, so some of the other 45 may not be 1 → 2. Only 45 rows are in range and they have at most one partial post-year in a 2010–2025 panel, so they add little to the fit whatever the tag. Do not drop them for the date; check prior duplex rules if any is to carry weight. |
| Florence 2023-local | 1 | Unresolved: probably an earlier duplex rule (Ord. 7, 2019). Drop in the sensitivity. |
| Bend 2019 table row | 1 | Not an event (`[predates]`). It fixes Bend's prior cap at 3. Reading was a 2019 draft showing existing text; the 2016 Ord. 2271 is the nearest dated change. |

## 3. What this leaves for the method-only D-entry

1. Settle Bend (first dose rise vs first cap rise) and the `-landdiv` blank-date flag problem.
2. Decide how to treat a rule taking effect between 1 July and year end: Portland's 2021-08-01 rule counts from 2022,
   leaving about 11 untreated-in-model months of exposure in 2021. Same for Bend 2021-11-05.
3. Prior-cap uncertainty at small cities (E = 2025) and the judgment coverage shares.
4. Four of nine rows remain below the standard of the other 266: Lincoln City, Independence (date), Sweet Home and Florence (substance).
   Hand to Ben: the primary texts that would settle them (Bend Exhibit O, Independence Ord. 1598 and minutes,
   Lincoln City Ord. 2022-10, signed Sweet Home Ord. 1305, Florence 2019 DLCD notice) are online but were not machine-readable
   from here; otherwise close as "no usable source".
