# Texas missing-middle rule checks: second coder, 2026-11-11

**Scope.** Step 1 of the missing-middle review sequence (`docs/research/mm-methodology-review-2026-11.md`, PR #392,
table "4a. Firm up the current set"). Second-coder checks of the Texas `missing_middle` rows that carry or carried
the D-054 / D-055 fit: League City, Lewisville, Houston 2023 and Lubbock (row plus the missing Ch. 40 row). For
each one: the rule, its effective date, its dose (units allowed by right on a single-family lot) and the rule just
before it.

**Rules only.** No permit or BPS outcome was read or tabulated, no engine, fit or scenario was run, and nothing
touches St. Paul. `config/reforms/tx.csv` is **not edited**, because Texas coding closed on 2026-11-01. The rows
below are proposals for Ben. No records requests were filed and no staff were emailed. No bot check was bypassed.

## Ben's decisions (2026-11-11, in chat)

1. **Keep League City and Houston.** The aim is to count and estimate how many 2–4 unit buildings the state
   produces, so these places stay in play whether a period falls before or after a rule. Places where duplexes
   have long been legal show what gets built in a healthy market.
2. **Include standards reforms like Houston's MUR.** Don't exclude them. The value is in showing that making a
   housing type feasible works, not only making it legal.
3. **Drop the League City RSF-5 recheck.** It is a special-use cell and doesn't change the by-right dose.

The recommendations below to drop League City and Houston from the event set are **superseded**. The proposals
and the fit-set section have been revised to match.

## Plain-language summary

| Place | What we coded | What the check found | Effect on the fit set |
|---|---|---|---|
| **League City** | 2020 UDC first allowed duplexes in RSF-2 (1 → 2) | **Not an event.** The 2020 UDC "amended and recodified" the old zoning ordinance. RSF-2 and its duplex permission are older: RSF-2 existed by 2015, and a 2011 draft use table already shows duplex P in RSF-2. | **Remove as an event.** The true start date is unknown, at least 2015 and probably 2011 or earlier. |
| **Lewisville** | 2022 UDC allows duplexes by right in R-7.5, R-6, R-5 (1 → 2) | **Confirmed.** The adopted 2022 use table shows duplex "A" in those three districts, and 2022 staff materials call it new. Effective 2022-12-01. | **Keep.** Clear the CHECK flag and add the prior "no" row. |
| **Houston** | Livable Places, 2023-11-27, cap 2 → 8 | **The date is right; the dose is wrong.** 3+ unit buildings were already legal before 2023 as "multi-family residential", with no unit cap. Livable Places added an optional, lighter standards route ("multi-unit residential") for 3–8 units: **at most 4 on a local street**, 8 elsewhere. It changed feasibility, not legal permission. | **Not a cap-rise event** under D-024's definition. Either drop it, or keep it in a separately labelled "standards" class (Ben's call). |
| **Lubbock** | 2023 UDC: duplex and 3–4 units "L" in SF-2 (dose 4); pre-UDC row missing | **Partly right** (as found on 2026-11-07). The cells are confirmed, but the block-face rule keeps duplexes off all-single-family block faces, so the gain on built-out lots is about zero. **Ch. 40 text: no usable source.** | **Stay out** (D-059 stands). Close the Ch. 40 row as "no usable source"; an inferred prior row is offered for reference only. |

Net result: **of the four Texas fit-set places checked, one is confirmed (Lewisville). League City and Houston are
not cap-rise events as coded, and Lubbock stays out.** Per Ben's decisions above, League City and Houston stay in
anyway: League City as an always-allowed place, Houston as a standards event. The "Effect on the fit set" column
shows the second coder's original recommendation.

## Check table

Confidence: **H** = read in the official text or an image of it; **M** = official staff material or a code
mirror, or a consistent indirect source; **L** = inference or search snippet only.

| Place | Row id | Coded date / dose | Found date / dose | Prior rule (just before) | Proposed tag | Source | Conf. |
|---|---|---|---|---|---|---|---|
| League City | `TX-4841980-missing_middle-2020` | 2020-09-29 / 1 → 2 (RSF-2) | 2020-09-29 is effective (§125-1.7), but it is a **recodification**. Duplex P in RSF-2 is unchanged from the pre-2020 code. | Duplex **P in RSF-2 already**: 2011 draft Schedule 125-70.B reads "Duplex — — — S P" (RSF-20/10/7/5/2). RSF-2 existed by 2015 (Ord. 2015-15) under the 2005 zoning ordinance (Ord. 2005-24). Adoption date of the RSF-2 duplex permission not found. | **Not an event**: recode as a recodification row (unit_cap 2, no change) and add a prior row tagged `[earliest-known]` at 2015 or `[predates]`; see proposals. | §125-1.1, §125-1.7: zoneomics.com/code/league-city-TX/chapter_1; Table 3.13.1: zoneomics.com/code/league-city-TX/chapter_3; Ord. 2015-15 and Z15-05 staff report (leaguecitytx.gov DocumentCenter 12892, 12812); 2011 Art. III draft "Public Hearing #3" (DocumentCenter 3690); Ord. 2015-02 cites §125-90.C, matching the draft numbering (DocumentCenter 12579) | Recodification: H (code text via mirror). Pre-2020 RSF-2 duplex P: M (adopted draft not confirmed). Start date: unresolved |
| Lewisville | `TX-4842508-missing_middle-2022` | 2022-12-01 / 1 → 2 by right (R-7.5, R-6, R-5) | **Confirmed**: adopted 2022-11-07 (Council item 22-2559), effective "from and after December 1, 2022". Exhibit VII.2-3-2 (p. 197 of the adopted UDC): "Dwelling, Two-Family (Duplex)" is **A** in R-7.5, R-6, R-5 (also DU, TH, TH-2) and blank in AO, R-18, R-12, R-9. Ordinance number not found (blank in the draft). | **Single-family only.** The 2022 staff UDC overview (slide 22) says "Allow duplexes by right in the R-7.5, R-6 and R-5". Written responses (Oct 2022): R-7.5's main change is "to allow for duplexes", and no property was rezoned. Old Ch. 17 §§17-10, 17-11 are titled "Single-Family Residential District regulations"; their text was not read (Municode behind Cloudflare). | **Event; keep.** Clear the CHECK flag and add the prior "none" row (proposal 3). | Council item 22-2559 (cityoflewisville.granicusideas.com, 2022-11-07 meeting); adopted UDC Exhibit A on Legistar (View.ashx …82abce9a…pdf), p. 197 read as an image; staff overview deck and "Summary of Written Inquiries and Responses" (Legistar attachments to 22-2559) | Date and cells: H. Prior rule: M-H (staff statements, not old code text) |
| Houston | `TX-4835000-missing_middle-2023` | 2023-11-27 / 2 → 8 | **Date confirmed**: Ord. 2023-801 (Ch. 42) and 2023-802 (Ch. 26), adopted 2023-09-27 (15–1), effective 2023-11-27. **Dose:** the new "multi-unit residential" (MUR) route, §42-237(c), allows 3–8 units, but **"no more than 4 units" on a local street**. It also requires a site of at least 3,500 sq ft, 50 ft of frontage on a 50 ft street, a depth of at most 150 ft, a 30 ft height cap and on-site parking per §26-492 plus 1 guest space per 6 units. Deed restrictions still apply. | **No legal cap above 2.** §42-1 "multi-family residential" (3 or more units, including triplexes and quadraplexes) was and still is allowed on unrestricted land with no unit cap, but under the heavier multifamily standards: 60 ft right-of-way (vs 50 ft for single-family and MUR, §42-122), larger building lines and bedroom-based parking. City: these types "became infeasible" under early-1980s rules; Livable Places "revive[s]" them. | **Not a cap-rise event.** Options: (a) drop from the D-024 cap-rise fit set; (b) keep in a separately labelled "standards change" class with dose 4 on local streets. Recode unit_cap 8 → 4 for typical single-family lots either way, and fix the prior row's description (proposals 4–5). | Ord. 2023-801 (signed scan, §42-1, §42-122, §42-237); local copy `Houston_LivablePlaces_Ords_2023-801_802.pdf`; Livable Places User Guide (Dec 2023) p. 4, p. 30, §2.3 (local copy); FAQ 2023 pp. 2–4 (local copy); cohips.houstontx.gov/planning/Commissions/chapter42.html; press release 2023-09-27; city workshop deck (2023-03-27), seen only as a search excerpt | Date, MUR limits: H. "3+ legal before as multifamily": H for the current §42-1 definition, M for the pre-2023 text (not read verbatim) |
| Lubbock | `TX-4845000-missing_middle-2023` | 2023-10-01 / 1 → 4, "L" (SF-2) | **Cells confirmed** (2026-11-07, Table 39.02.016-1): duplex and multiplex — in RE, SF-1 and L in SF-2, MDR, HDR. **Effective dose on existing single-family lots ≈ 0:** §39.02.018.c.1.A keeps all-single-family block faces single-family and bars duplexes facing single-family homes. Citywide, the share of residential land open to anything but detached single-family went from about 14% to 99% (Texas Tribune, Oct 2024), so the gain is real on paper, mostly greenfield. The across-the-street sentence probably came with Ord. 2024-O0110 (adopted 2024-08-27, effective 2024-09-16); not confirmed. | See next row. | **Stay out (D-059).** If ever re-entered: `by_right` partial, dose limited to block faces that aren't all single-family. | `docs/research/ordinances/tx-second-coder-lubbock-2026-11-07.{md,csv}`; Texas Tribune, apps.texastribune.org/features/2024/texas-housing-affordability-zoning/; ecode360 Ord. 2024-O0130 PDF (LF2176491) read: signs only, so not the source | Cells: H (mirror). Block-face lineage: L-M |
| Lubbock | (missing pre-UDC row, Ch. 40, 2010–2023) | — | **No usable source** for the text. Ch. 40 (Ord. 7084, 1975; earlier 1983 Code Ch. 29) was repealed by Ord. 2023-O0054. What is known indirectly: R-1 single-family only (ZC 3471-A staff report, 2022); "R-2 Two-Family District" (1983 Code §29-8(n) per the ecode360 Appendix D disposition table, snippet); R-1A "Reduced Setback Single Family"; T "Transition District". The UDC crosswalk maps R-1, R-1A, T → SF-2 and R-2, A-1 → MDR. | (this is the prior row) | **Close as "no usable source".** An inferred row (proposal 7) is offered for the record only, not for use as an event baseline. | Tried and failed: ecode360 and mylubbock.us (403 / bot check, not bypassed); encodeplus (redirects to 403); weblink.ci.lubbock.tx.us Laserfiche (server error); web.archive.org (not reachable from the fetch tool); Municode and American Legal (no Lubbock code); destinyhosted staff reports (scanned images, no OCR on this machine) | R-1 single-family: H (staff report). R-2 allows duplexes by right: L (district name only) |

## Notes by place

### League City

- **The 2020 UDC is a recodification.** §125-1.1 says Ord. 2020-25 "amended and recodified" the 1999 Zoning
  Ordinance (Ord. 99-52) and its amendments. §125-1.7 makes the chapter effective on September 29, 2020, the
  adoption day. District names didn't change, and Article I has no old-to-new conversion table.
- **RSF-2 predates 2020.** Ord. 2015-15 rezoned 2.8 acres from RMF-1.2 to RSF-2 (single-family, 2,000 sq ft
  minimum lot), citing Ord. 2005-24 and §125-49. Its Z15-05 staff report says RSF-2 permits zero-lot-line units.
- **The duplex permission predates 2020.** The 2011 draft "Article III Zoning Regulations (PUBLIC HEARING #3)",
  Schedule 125-70.B, lists Duplex as "— — — S P" for RSF-20/10/7/5/2, and Townhouse P only in RSF-2. I read this
  from the PDF text layer myself, and the agent read it too. It is a draft. I didn't find the ordinance that
  adopted it. Ord. 2015-02 cites "Section 125-90.C" and §125-50 (special use permits), which match the draft's
  numbering. That suggests the structure was in force by 2015. The current duplex row matches the draft row
  exactly.
- **RSF-5 conflict (unresolved, doesn't change the by-right dose).** The zoneomics HTML table (Sec. 125-3.13.1)
  has Duplex **S** in RSF-5. I checked the cell order against the header row: RSF-20, -10, -7 blank, RSF-5 S, RSF-2
  P. The 2011 draft also has S in RSF-5. That matches the reading withdrawn on 2026-10-30 (#32). Ben's lookup that
  day, on the official Article 3 PDF, found no duplex by right or by SUP in RSF-5. The mirror's version date is
  unknown. An SUP isn't by right, so the fit's dose doesn't depend on it. **Closed by Ben (2026-11-11): not
  rechecked.**
- **Proposed recode:** the 2020 row stays as a rule row (it is what's in force) but is not a reform event. Add a
  prior row giving RSF-2 duplexes P, with start date not found. The earliest evidence that it was in force is
  2015, and it probably reaches back to 2011 or 2005. With an `[earliest-known]` date of 2015 the place would
  re-enter main runs as a 2015 event on weak evidence. **My recommendation is `[predates]` with the unresolved
  date stated, so League City drops out of the event set.** Ben's call.

### Lewisville

- **Adoption.** Item 22-2559, 2022-11-07, "Adding a New Volume, Volume 2, Unified Development Code". It replaced
  parts of Chapters 2, 4, 6, 9.5, 17 (Zoning) and 17.5. The Planning and Zoning Commission voted 5-0 on
  2022-11-01. The adopting ordinance is in force "from and after December 1, 2022". The ordinance number is
  blank in the draft and was not found.
- **Cells.** I read p. 197 of the adopted UDC (Exhibit A) as an image. The duplex row is A in R-7.5, R-6, R-5,
  DU, TH and TH-2, and blank in AO, R-18, R-12, R-9, ETH, MF-1/2/3 and MHP. Use-specific standards are in
  Art. VII.3.7: no street-facing garage door outside DU. The purpose statements (VI.5.5–VI.5.7) say "single-family
  detached and two-family dwellings".
- **Before.** I did not read the old Chapter 17 text: Municode is behind Cloudflare, and the elaws mirror timed
  out. Two 2022 staff sources treat duplexes in all three districts as new. One is the council overview slide;
  the other is the written responses to residents (R-7.5: "The main changes ... are to allow for duplexes"). Staff
  also said no property's district was changed. That's enough for a prior "none" row at medium-high confidence.

### Houston

- **Dates.** Confirmed from the ordinance vote sheet, the city's Chapter 42 page and the press release.
- **What MUR is.** It's an optional performance-standards route (§42-237(a): to "incentivize" small multi-unit
  housing), not a new permission:
  - §42-1 still defines multi-family residential as three or more units, with no ceiling.
  - The User Guide (p. 30) says MURs are allowed on unrestricted lots, with "up to four units allowed if along a
    local street and up to eight units if elsewhere".
  - A typical single-family lot fronts a local street, so the relevant dose is **4**, not 8.
- **Why 3–4 unit buildings were rare before** (medium confidence; the pre-2023 text was not read verbatim):
  - §42-122 now lets a 50 ft local street serve "exclusively single-family residential lots, MUR's"; anything
    else needs 60 ft.
  - MUR also gets a 5 ft building line and parking by unit size (Ch. 26).
  - The User Guide (p. 4) says these types "became infeasible" under early-1980s suburban-style rules.
- **Consequence for the prior row** `TX-4835000-missing_middle-2010`: its "up to two units counts as single-family"
  reading is correct for the single-family definition. But "unit cap 2" understates what was legal: 3+ units were
  allowed as multifamily under heavier standards. Houston has no legal cap to raise.
- **Relation to the Ch. 42 small-lot rules** (`lot_size` theme, 1999 and 2013 rows): Livable Places leaves the
  §42-183/185 minimum-lot rules in place and layers access and design rules on top. New lots under 33 ft wide must
  use rear or shared access, and "narrow lot" now means under 44 ft of frontage. For fee-simple townhouses on small
  lots that is, if anything, a **tightening**. Those townhouses are 1-unit structures in BPS anyway (D-042). The
  same package raised the detached second-unit cap from 900 to 1,500 sq ft; that is ADU theme, already coded there.
- **Recommendation:** Houston 2023 shouldn't count as a D-024 cap-rise event. If Ben wants feasibility reforms in
  the fit, they need their own class and their own pre-registration, because a "standards" dose isn't comparable
  to "duplexes newly legal".

### Lubbock

- **The 2023 row stands as checked on 2026-11-07**
  (`docs/research/ordinances/tx-second-coder-lubbock-2026-11-07.md`).
  - New today: the Texas Tribune's land-share figure (about 14% → 99% of residential land open to more than
    detached single-family) confirms that the UDC loosened the rules citywide on paper. The paper also notes the
    proximity limits.
  - Lineage: Ord. 2024-O0130 is signs only. 2024-O0110 (2024-08-27 / 2024-09-16) is the likely source of the
    across-the-street sentence (snippets only).
- **Ch. 40: no usable source.** Every route to the text failed or needed a bot-check bypass (list in the table).
  - The best remaining route is OCR of pre-2023 R-2 zone-case staff reports on destinyhosted, e.g. Case 3085-A
    "Madewell 21st Duplexes", GO → R-2. That needs a local OCR tool (poppler/tesseract), which is a new tool
    install, so I didn't do it. Ben can also open ecode360's Appendix D or the Division 2.4 history in his own
    browser.
- **D-059's doubt is not resolved by rules alone.**
  - Duplexes in old R-2 (now MDR) were most likely by right before 2023, and are "L" with design conditions now.
    That is a mild tightening on that land.
  - SF-2 (old R-1, R-1A, T) gained 2–4 units only on block faces that aren't all single-family.
  - Lubbock stays out.

## Proposed rows (for Ben; not applied to `tx.csv`)

Column names follow `config/reforms/tx.csv`. Only the fields that change or matter are shown.

| # | reform_id | Change | Key fields | Note text (start) |
|---|---|---|---|---|
| 1 | `TX-4841980-missing_middle-2020` | edit | `supersedes` = `TX-4841980-missing_middle-2010`; `coder_2` = claude-second-coder-2026-11-11; `coder_agreement` = partly | "Recodification (§125-1.1, Ord. 2020-25 'amended and recodified' Ord. 99-52); duplex P in RSF-2 unchanged from pre-2020 code; not a new permission in 2020. Kept as an always-allowed place for healthy-market production (Ben 2026-11-11)." |
| 2 | `TX-4841980-missing_middle-2010` | **new** | `status` in_force; `effective_date` 2010-01-01; `unit_cap` 2; `coverage_zones` RSF-2; `by_right` True; `source_url` DocumentCenter 3690, 12892, 12579 | "[predates] Duplex P in RSF-2 (2011 draft Schedule 125-70.B 'Duplex — — — S P'; RSF-2 in force by 2015 under Ord. 2005-24, Ord. 2015-15). First enactment not found; rule age a lower bound." (Alternative if Ben prefers: `[earliest-known]` at 2015, which makes it a 2015 event.) |
| 3 | `TX-4842508-missing_middle-2010` | **new** | `unit_cap` 1; `effective_date` 2010-01-01; `coverage_zones` R-7.5;R-6;R-5 | "[earliest-known] No missing-middle rule before the 2022 UDC: R-7.5, R-6, R-5 single-family (old Ch. 17 §§17-10, 17-11 titles); 2022 staff overview slide 22 'Allow duplexes by right in the R-7.5, R-6 and R-5'; written responses Oct 2022. Old Ch. 17 text not read (Municode blocked)." |
| 4 | `TX-4842508-missing_middle-2022` | edit | `supersedes` = row 3; `coder_2` = claude-second-coder-2026-11-11; `coder_agreement` = agree | "Second coder: 2022 adopted UDC p. 197 Exhibit VII.2-3-2 duplex A in R-7.5/R-6/R-5; effective 2022-12-01 (adopting ordinance, item 22-2559); CHECK resolved." |
| 5 | `TX-4835000-missing_middle-2023` | edit | `unit_cap` 8 → **4** (local street; 8 off local streets in `coverage`); `min_lot_sqft` 3500; `max_stories` blank (30 ft cap in notes); `coder_agreement` = partly | "Second coder: MUR (§42-237) is an optional standards route, not a new permission: §42-1 multi-family (3+, no cap) was already allowed on unrestricted land. Max 4 units on local streets, 8 elsewhere; site ≥3,500 sq ft, ≥50 ft frontage, ≤150 ft deep, 30 ft height. A standards (feasibility) event, not a legal cap rise; kept as an event in its own class (Ben 2026-11-11)." |
| 6 | `TX-4835000-missing_middle-2010` | edit (notes only) | — | Add: "3+ units were legal before 2023 as §42-1 multi-family under heavier standards (60 ft ROW, §42-122; building lines; parking); unit_cap 2 is the single-family definition, not a legal cap." |
| 7 | `TX-4845000-missing_middle-2010` | **new, for record only** | `unit_cap` 1; `coverage_zones` R-1;R-1A;T | "No usable source for Ch. 40 text. Inferred: R-1 single-family only (ZC 3471-A); R-2 'Two-Family District' (1983 Code §29-8(n)) presumably duplex by right; crosswalk R-1/R-1A/T → SF-2. Not for use as an event baseline (D-059)." |

## Effect on the fit set (Ben's direction, 2026-11-11; the method-only D-entry writes it down)

- **Lewisville** stays as a cap-rise event (1 → 2 by right, 2022-12-01), now second-coded.
- **League City** stays, but as an **always-allowed place**, not a 2020 event. Its duplex production in RSF-2 is
  a reading of what a market builds when duplexes are legal, which is the level the statewide count needs.
  - **Method gap:** under `rule_tags.py`, a `[predates]` row is never an event and is moved before the panel, so
    today's fit would carry League City as "treated throughout" with no before period.
  - **For the D-entry:** say how always-allowed places enter, for example as a level or steady-state rate rather
    than a before/after jump. That choice belongs in the method entry, not in this rule check.
- **Houston** stays as an event (2023-11-27), coded as a **standards / feasibility class** with dose 4 on local
  streets, 8 elsewhere. Ben wants to show that such reforms work.
  - **For the D-entry:** the class needs its own effect (or a class indicator) and a pass rule written before any
    count. A standards dose isn't on the same scale as "duplexes newly legal".
- **Lubbock** stays out (D-059). The Ch. 40 rule has no usable source.
- **Austin** (HOME, already "agree") wasn't in scope.

The Lubbock decision is unchanged.

## How this was checked

- The facts were gathered by four research agents, one per place. Each had a written brief and reported URLs,
  sections and confidence.
- The coordinating session checked the decisive items itself:
  - the Lewisville use-table page (rendered image, p. 197);
  - the League City duplex row and column headers in the zoneomics HTML;
  - the 2011 draft schedule text;
  - Houston's MUR limits and "infeasible" wording in the local User Guide and FAQ PDFs.
- Items read only from search snippets are marked L or M above.
