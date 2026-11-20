# North Carolina missing-middle rule checks (second coder, 2026-11-11)

**Question.** For each NC place that carries the missing-middle fit (D-054/D-055), when did duplexes (or 2–4
units) first become allowed **by right** on single-family-zoned lots, and what did the code allow just before the
coded event? This is step 1 of the sequence approved after the methodology review
(`docs/research/mm-methodology-review-2026-11.md`, PR #392).

**Scope.** These are rule checks only. No permit or BPS outcome was read or tabulated. The CSV is not edited:
proposed rows are listed below for Ben to accept. No records requests were made and no staff were emailed.

**Bottom line.**
- **Garner** is a clean in-window event.
- **Wilson** is a real event, but only in one district (SR6).
- **Wake Forest, Morrisville, Sanford and Burlington** are `[predates]`: their predecessor codes already allowed
  duplexes by right (Burlington and Wake Forest's multifamily districts also allowed 3–4 units) in the districts
  the new code carried over.
  - Morrisville (old R-12) and Burlington (old R-15) each have a small pocket of former single-family land that
    gained duplexes. Neither pocket can be sized without the old zoning map.
- **Durham city's** effective date is **2019-10-01**, not the 2019-09-03 vote.
- For **Durham County** no effective date was found, so the vote date stays.
- **There is no "EHC2".** The follow-up is SCAD (2024-01-01), which added no new unit counts on single-family lots.

## Results

| Place | Row id | Coded date | Finding | Proposed tag / date | Source | Confidence |
|---|---|---|---|---|---|---|
| Wilson | `NC-3774540-missing_middle-2013` | 2013-01-17 | The UDO was adopted 2013-01-17 and took effect **2013-01-18** (§1.10). **SR6** replaced the single-family-only RA-10S and RA-8S, and allows duplexes PS (one per block face). GR6 replaced RA-15, RA-12 and RA-8, and UR replaced RA-6, RA-6I and RA-6S; all but RA-6S already allowed "single & multi-family" | **Real event, 2013-01-18, coverage SR6 only** (plus former RA-6S land in UR). GR6 and the rest of UR: `[predates]` (probable) | 2013 UDO (Wayback); 2008 city district list (Wayback) | Medium |
| Wake Forest | `NC-3770540-missing_middle-2013` | 2013-07-16 | Zoning Ordinance #77-01 (1977, amended through 2010-04-05) permits duplexes in R-10, R-8, R-5 and RD. MF permits 2–4 units. R-15 and R-20 allow none. The 2013 UDO converted R-10 to GR5 and R-5/MF/O-I to GR10 | **`[predates]`** | Old ordinance (Wayback); UDO §2.2 | High |
| Morrisville | `NC-3744520-missing_middle-2014` | 2014-07-01 | Zoning Ordinance v9.2 (2010), Table of Permitted Uses: "Dwelling, duplex" is **S** (staff approval only, so by right) in AD, R-10, R-8, R-6 and R-MF. R-12 is blank. UDO Table 1.6.5 folds R-12, R-10, R-8 and R-6 into LDR and MDR. Effective 2014-07-01 confirmed (§1.2.1) | **`[predates]`**. Only former R-12 land gained duplexes (not sized) | Old ordinance (Wayback); UDO May 2020 §1.2.1 and Table 1.6.5 | Medium-high |
| Sanford | `NC-3759280-missing_middle-2018` | 2018-11-19 | **2018-11-19 is not a UDO date.** It is Lee County's adoption of the Plan SanLee land use plan. The earlier joint UDO's Table 4.6-1 had duplex **P** in RA, R-12, R-10 and R-6 (not R-20, R-14 or R-12SF). Amendments voted 2024-08-06 renamed R-10 to SN-9 and R-6 to UN-6, and merged R-12 into SN-12, which allows no duplexes. That is a loss, not a gain | **`[predates]`**; drop the 2018 date | Old Article 4 (Wayback, 2020); current Article 1 §1.3 | Medium-high |
| Burlington | `NC-3709060-missing_middle-2019` | 2019-11-01 (adopted 2019-07-16) | Old Zoning Ordinance §32.9 table (1971 code). Duplex and 3+ unit "one owner, one lot" are **X (by right) in R-9 and R-6**. In R-12 they were by right only as condos/townhouses; the single-owner form was disallowed in 1984. In R-15 only the condo form was allowed, by special use. R-30 allowed none. The UDO (Table 1.11) maps R-15, R-12, R-9 and R-6 to MDR, MF-A/B to HDR, and R-30 to LDR | **`[predates]`** for the coded 1→4 change. Only former R-15 land (and R-12's single-owner form) is new on 2019-11-01; not sized | Old table §32.9 (Wayback, read from the rendered page); 2019 UDO cover and §1.2 | High (table); medium (pockets) |
| Garner | `NC-3725480-missing_middle-2022` | 2022-07-05 | The 2003 UDO (Supp. S-6, 2018), Table 5.1, allows two-family and 3+ units **only in MF-1 and MF-2**. R-40, R-20, R-15, R-12 and R-9 are blank (prohibited, with no special-use path). The 2022 UDO maps R-20 and R-15 to R2, R-12 and R-9 to R4, and allows two-family P in R2, R4, R8 and MF-A | **Real event, 2022-07-05** (Ord. (2022) 5132, ZTA-22-01; remapping Ord. (2022) 5131); cap 1→2 | Old Article 5 (Wayback); 2022 UDO cover (Wayback); 2022-07-05 agenda | High |
| Durham city | `NC-3719000-missing_middle-2019` | 2019-09-03 (vote) | The county's agenda says EHC "has been implemented by the City Council … effective October 1, 2019". Before EHC, duplexes were by right in RU-5(2), RU-M, RS-M (and RC). EHC added RU-5 and urban-tier RS-8 and RS-10 | **Keep the event; effective_date 2019-10-01.** Coverage: urban-tier RU-5, RS-8 and RS-10 (RS-20 excluded) | BOCC agenda 2019-10-28, item 19-0512 (read); city PDFs (search snippets only) | High (date); medium-low (district list) |
| Durham County | `NC-37063-missing_middle-2019` | 2019-10-28 (vote) | The county agenda adopts the ordinance with no stated effective date. The minutes link is dead (404) | **No usable source** for an effective date. Keep 2019-10-28 (on-adoption is the likely reading) | BOCC agenda 2019-10-28 | Medium-low |
| Durham (EHC2) | none | — | No "EHC2" exists. The successor is **SCAD, TC2200001**: city 4-3 on 2023-11-20, county 3-1 on 2023-12-11, **effective 2024-01-01**. It added detached rowhouses, small-lot splits for lots with pre-1950 houses, larger ADUs and no parking minimums. No source shows triplexes or quadplexes, or duplexes in new districts or tiers | **Don't code as a missing-middle event.** At most an infill/ADU/parking row dated 2024-01-01 | INDY Week; N&O via Yahoo; BCPI | Medium |

## Notes by place

### Wilson
- **Effective date.** The archived adopted UDO (cover "ADOPTED 1.17.2013") says in §1.10: "All other provisions of
  this ordinance shall become effective January 18, 2013".
  - §1.6.2 let applicants follow the old Zoning Ordinance until 2013-07-31, so SR6 duplexes could not be required
    to follow the new rule before then. They could, though, be built under it from 2013-01-18.
  - No ordinance number was found.
- **District conversion** (UDO Ch. 2, "Previous District(s)"):

  | 2013 district | Replaced | Duplexes in the 2013 UDO |
  |---|---|---|
  | SR4 | RA-15(S), RA-12(S) | No |
  | SR6 | RA-10(S), RA-8(S) | **PS** |
  | GR6 | RA-15, RA-12, RA-8 | PS |
  | UR | RA-6(S), RA-6I, RA-6 | PS |

  - §3.2.1, "DWELLING – TWO FAMILY [SR6, GR6, UR]", sets one per block face, Detached House type, at most 2 units.
    This matches the coded row, so the 2013 text is what the CSV describes.
- **Predecessor.** The city's 2008 "Zoning Districts" page describes the "S" districts as single-family only, and
  RA-15, RA-12, RA-8 and RA-6 as "single & multi-family" districts with multifamily densities.
  - The old use table itself was not found: wilsonnc.org blocks automated fetches, and no Wayback copy of the 1961
    ordinance turned up.
  - So "duplexes predate in GR6/UR" is a strong inference from the district descriptions, not a table read.
  - "Duplexes are new in SR6" rests on those districts being single-family only.
- **Dose.** One duplex per block face limits SR6 uptake. The coverage share should be SR6's parcels only, not every
  single-family-zoned parcel in the city.

### Wake Forest
- **Old ordinance.** Zoning Ordinance #77-01, "Adopted January 13, 1977 … Amended through April 5, 2010".
  - R-10 purpose: "single-family and two-family dwelling units on each lot". Its permitted list includes "Duplexes".
  - RD lists "Dwellings (single-family, duplexes)".
  - MF permits "Duplexes, Triplexes, Quadraplexes".
- **Conversion.** UDO §2.2 (2022 edition): "R-20 & R-15 converted to GR3 R-10 converted to GR5 R-5, MF & O-I
  converted to GR10".
  - The 2013 UDO kept duplexes out of GR3, as before.
  - It **removed** them from RD.
- **Adoption.** The town UDO blog (archived) says "officially adopted on Tuesday, July 16, 2013". No separate
  effective date or ordinance number was found. This doesn't matter for a `[predates]` tag.
- When R-10 first allowed duplexes (1977 or a later amendment) is not established. It was before 2010.

### Morrisville
- **Old ordinance.** Town of Morrisville Zoning Ordinance, Version 9.2 (2010-03-26), Article IV, Table of
  Permitted Uses (amended 2009-04-28, Ord. #2009-001).
  - "Dwelling, duplex" is S in AD, R10, R8, R6 and R-MF.
  - The legend reads "S Requires Staff Approval Only".
  - Townhouses were C (Town Board site plan approval). Apartments needed a special use permit.
- **Conversion.** UDO Table 1.6.5 lists AD → VLDR and R-12, R-10, R-8, R-6 → LDR and MDR. The flipbook text layer
  doesn't show which old district went to which of the two.
- **Effective date.** §1.2.1: "in full force and effect from and after July 1, 2014". A town presentation (search
  summary only) says the UDO was adopted in December 2013 and the town-wide rezoning in June 2014.
- **The R-12 pocket.** Former R-12 land is the only place duplexes are new. It is not worth a separate row unless
  the pre-2014 zoning map can be joined to parcels, which no adapter does today.

### Sanford
- **What 2018-11-19 is.** Current Article 1 §1.3 cites the "Plan SanLee land use plan, adopted … by Lee County on
  November 19, 2018" (Sanford adopted it 2018-10-02, Broadway 2018-10-22). §1.5 gives no calendar effective date.
  - Lee County's "UDO Chapter 160D Compliance Modifications 6-7-21" is a 160D re-adoption, not a duplex change.
- **Earlier joint UDO.** Table 4.6-1, captured 2020-10-29, row "Dwelling, Duplex (two-family dwelling)":
  - RA P; RR –; R-20 –; R-14 –; R-12SF –; R-12 P; R-10 P; R-6 P; MF-12 P; O&I S.
  - The joint UDO dates from 2011 or earlier (a joint hearing notice of 2011-05-23). Its first adoption date was
    not found.
- **2024 amendments.** Council vote 2024-08-06 (Rant NC). A September 2024 effective date comes from a search
  summary only.
  - R-10 → SN-9 and R-6 → UN-6 (the duplex P/D districts in today's table).
  - R-14 and R-12 → SN-12 (no duplexes), so some R-12 land **lost** by-right duplexes.
  - The slide-deck mapping is a search summary. The current table was read.
- The `reform_id` year (2018) and dates on the row should go; with `[predates]` the place counts as treated
  throughout the window.

### Burlington
- **Old table.** The old Zoning Ordinance §32.9 table, captured 2019-09-16, six weeks before the UDO took effect
  (footnotes run to 2010), read from the rendered page:

  | Use | R-30 | R-15 | R-12 | R-9 | R-6 |
  |---|---|---|---|---|---|
  | Duplex, one owner, one lot | – | – | – (disallowed 1984) | **X** | **X** |
  | Duplex, condos/townhouses | – | S | X | X | X |
  | Multifamily, one owner, one lot | – | – | – (disallowed 1984) | **X** | **X** |
  | Multifamily, condos/townhouses | – | S | X | X | X |

  - Also: CR is C, MF-A and MF-B are X, O-I is X for duplexes.
  - A 2016 Planning & Zoning packet quotes the R-9 matter-of-right list with the same entries.
- **Conversion and dates.** UDO Table 1.11: R-15, R-12, R-9, R-6 → MDR; MF-A, MF-B → HDR; R-30 → LDR.
  - The UDO cover reads "Adopted: 7.16.19 / Effective Date: 11.1.19". §1.2 repeals the 1971 Zoning Ordinance.
  - No ordinance number was found.
- **Reading.** The coded 1 → 4 jump is wrong for R-9 and R-6, which already allowed 2–4+ units on one lot by right.
  It is partly wrong for R-12, where two-unit and multi-unit buildings were by right under condo/townhouse
  ownership. Only former R-15 parcels went from special use to by right.

### Garner
- **Old UDO.** The 2003 UDO (Supplement S-6, 2018), Table 5.1:
  - "Two-Family Dwelling" is P* only in MF-1 and MF-2.
  - "Multifamily (triplex and higher …)" is also P* only in MF-1 and MF-2.
  - The single-family districts are blank, which means not allowed (§5.1.B).
- **Conversion.** 2022 UDO Figure 1.10-A: R-40 → RA; R-20, R-15 → R2; R-12, R-9 → R4; MF-1 → MF-A; MF-2 → MF-B.
  The UDO notes that remapping was "case-by-case".
- **Dates.** The cover reads "Adopted: July 5, 2022 / Effective: July 5, 2022".
  - The 2022-07-05 council agenda lists ZTA-22-01 as Ordinance (2022) 5132 and CZ-22-01 (town-wide remapping) as
    Ordinance (2022) 5131.
  - The adopted minutes were not read.
- **Unit cap.** Triplex and quadplex start at R8, which has no direct predecessor, so the cap on former
  single-family land is 2.

### Durham (EHC, EHC2)
- **City effective date.** The Durham County BOCC agenda for 2019-10-28 (item 19-0512, pp. 8–9) says EHC "has been
  implemented by the City Council in City jurisdictions effective October 1, 2019". This was read directly.
  - Search snippets of the ordinance (Attachment B, DocumentCenter View/27599) and of the JCCPC timeline
    (View/38097) give the same date. durhamnc.gov returned 403 and the Wayback Machine was down, so those were not
    opened.
- **County effective date.** The same agenda item is "DURHAM COUNTY JURISDICTION ONLY". Its motions adopt the
  consistency statement, the ordinance and a metrics resolution, with no effective date. The minutes link returned
  404, so this is closed as no usable source.
- **Districts before and after.** A city "Duplexes" PDF (snippet only) says new duplexes were already by right in
  RU-5(2), RU-M, RC and RS-M before EHC. The 2023 EHC final report (snippet) says the changes apply in "any
  residential district in the Urban Tier, except RS-20".
  - So the newly treated districts are urban-tier RU-5, RS-8 and RS-10. This matches the row's
    "RU-5 and RU-5(2) in the suburban tier" only in part, and should be re-checked when the ordinance can be opened.
  - Current UDO §6.4.2 and §7.1.6 were read: duplexes in RU-5, RU-5(2) and RU-M; no triplex or quadplex type.
- **EHC2.** None found. SCAD (TC2200001) is the follow-up: effective 2024-01-01 per the N&O, which says the
  ordinance "takes effect Jan. 1".
  - The city's "Detailed Analysis as Approved by City Council" (View/53663) marks rejected items. It returned 403
    and would settle which pieces passed.
  - The readiness doc already carries a 2023-11-20 SCAD ADU row for Durham city. Its effective date may also be
    2024-01-01 (not checked here; ADU rows are out of scope).

## Proposed CSV changes (for Ben to accept; not applied)

| Row | Change |
|---|---|
| `NC-3774540-missing_middle-2013` (Wilson) | adoption 2013-01-17, effective **2013-01-18**; drop `[earliest-known]`; `coverage_zones` = SR6 (plus former RA-6S in UR); note GR6/UR as `[predates]` (probable, from the 2008 district descriptions); keep unit_cap 2, by_right True |
| `NC-3770540-missing_middle-2013` (Wake Forest) | tag **`[predates]`** (Zoning Ordinance #77-01, R-10 duplexes by 2010-04-05); not an in-window event |
| `NC-3744520-missing_middle-2014` (Morrisville) | tag **`[predates]`** (Zoning Ordinance v9.2, 2010: duplex S in R-10/R-8/R-6/R-MF); note the R-12 pocket; not an in-window event |
| `NC-3759280-missing_middle-2018` (Sanford) | tag **`[predates]`**; remove the 2018-11-19 date (a land-use-plan date) and note the 2024 R-12 → SN-12 loss |
| `NC-3709060-missing_middle-2019` (Burlington) | tag **`[predates]`** (§32.9: duplex and multifamily by right in R-9/R-6 before 2019); note the R-15 pocket; not an in-window event |
| `NC-3725480-missing_middle-2022` (Garner) | drop `[earliest-known]`; add Ord. (2022) 5132 / 5131 and the predecessor citation; `coverage_zones` R2, R4 (former R-20/R-15/R-12/R-9); keep as an in-window event |
| `NC-3719000-missing_middle-2019` (Durham city) | effective_date **2019-10-01** (adoption 2019-09-03); coverage note: urban-tier RU-5, RS-8, RS-10 |
| `NC-37063-missing_middle-2019` (Durham County) | keep 2019-10-28; note "effective date: no usable source; on adoption assumed" |
| Durham SCAD | no missing-middle row |

**What this does to the fit's NC treated set.**
- Of the six `[earliest-known]` towns, **Garner** stays as an event and **Wilson** stays with narrowed coverage.
- Wake Forest, Morrisville, Sanford and Burlington become always-treated places, as Asheboro and Goldsboro did.
- Durham city's event moves four weeks later.
- This report does not re-run anything. What the change does to θ is for the method D-entry and the counting step.

## Sources

Archived and online documents actually read (✔) or seen only as search snippets (◐):

- ✔ Wilson 2013 UDO (adopted copy):
  https://web.archive.org/web/20130504183515/http://wilsonnc.org/attachments/pages/545/WilsonUDO_LowRes.pdf
  (§1.6.2, §1.10, Ch. 2 district descriptions, §3.2.1)
- ✔ Wilson zoning districts page, 2008:
  https://web.archive.org/web/20080808135905/http://www.wilsonnc.org/departments/developmentservices/landdevelopment/zoningdistricts/
- ✔ Wake Forest Zoning Ordinance #77-01 (amended through 2010-04-05):
  https://web.archive.org/web/20101225014103/http://wakeforestnc.gov/client_resources/residents/planning/zoning_ordinance.pdf
- ✔ Wake Forest UDO §2.2 (July 2022 edition): https://online.flippingbook.com/view/703728449/17
- ✔ Wake Forest UDO blog (adoption 2013-07-16): https://web.archive.org/web/2013/http://www.wakeforestnc.gov/udo_blog.aspx
- ✔ Morrisville Zoning Ordinance v9.2 (2010):
  https://web.archive.org/web/20100701155624/http://www.ci.morrisville.nc.us/DocumentView.asp?DID=75 (PDF p. 28)
- ✔ Morrisville UDO, May 2020 (§1.2.1; Table 1.6.5 on flipbook p. 13):
  https://user-cjghrlw.cld.bz/Morrisville-Unified-Development-Ordinance-May-2020
- ✔ Sanford/Lee/Broadway UDO Article 4 (2020 capture):
  http://web.archive.org/web/20201029062106id_/http://sanfordnc.net/DocumentCenter/View/2274/Article-4---Zoning-District-Regulations
- ✔ Sanford UDO Article 1 (current): https://sanfordnc.net/DocumentCenter/View/5014/UDO-Article-1---General-Provisions
- ✔ Sanford UDO Article 4 (current): https://www.sanfordnc.net/DocumentCenter/View/5103/UDO-Article-4---Zoning-District-Regulations
- ✔ Rant NC, 2024-08-12: https://rantnc.com/2024/08/12/council-approves-zoning-map-text-changes-that-do-away-with-some-public-hearings/
- ✔ Lee County 160D re-adoption: https://lee-lf.leecountync.gov:23610/WebLink/0/doc/672520/Page1.aspx
- ✔ Burlington old Zoning Ordinance §32.9 Table of Permitted Uses (2019-09-16 capture):
  https://web.archive.org/web/20190916123513/https://burlingtonnc.gov/DocumentCenter/View/15/Table-of-Permitted-Uses
- ✔ Burlington UDO "Adopted Vers 7-30-19":
  https://web.archive.org/web/20260427093034/https://www.burlingtonnc.gov/DocumentCenter/View/17052/Burlington-UDO-Adopted-Vers-7-30-19
- ✔ Burlington Planning & Zoning packet, 2016-08-22: https://burlingtonnc.gov/ArchiveCenter/ViewFile/Item/2856
- ✔ Garner 2003 UDO Article 5: https://web.archive.org/web/2024/https://www.garnernc.gov/home/showdocument?id=146
- ✔ Garner 2022 UDO:
  https://web.archive.org/web/20240222214246/https://www.garnernc.gov/home/showpublisheddocument/10391/638246759731870000
- ✔ Garner council agenda, 2022-07-05:
  https://web.archive.org/web/20220707113336/https://apps.garnernc.gov/TownCouncil/07-05-2022%20-%20AGENDA%20without%20UDO.pdf
- ✔ Durham County BOCC agenda, 2019-10-28: https://dconc.gov/Board-of-Commissioners1/Archived-Agendas--Minutes/2019/20191028RSAgenda.pdf
- ✔ Durham UDO §6.4.2 and §7.1.6: https://udo.durhamnc.gov/udo/6_04_Residential%20Urban%20RU%20Development.htm,
  https://udo.durhamnc.gov/udo/7_01_Housing%20Types.htm
- ✔ SCAD coverage:
  - https://indyweek.com/news/durham-county-board-of-commissioners-approves-scad/
  - https://ca.news.yahoo.com/durham-county-made-easier-build-103000894.html
  - https://bcpi.substack.com/p/scad-comes-before-council-tonight
- ◐ Durham city PDFs (403 to automated fetches, Wayback down during this check):
  - DocumentCenter/View/27599 (EHC ordinance, Attachment B)
  - View/38097 (JCCPC timeline)
  - View/24696 (Duplexes)
  - View/53854 (EHC final report)
  - View/53663 (SCAD as approved)

## How this was done

- Claude Code ran four research sub-agents in parallel (Wilson + Sanford, Wake Forest + Morrisville, Burlington +
  Garner, Durham).
- It then checked the weakest points itself in the built-in browser and with archived PDFs:
  - found and read the 2013 Wilson UDO and the 2008 district list;
  - read Burlington's old §32.9 table from the rendered page, because the text layer loses the columns;
  - read Morrisville's Table 1.6.5 from the flipbook text layer.
- Documents were saved only to the session scratchpad, outside the repo.
- Search-snippet evidence is marked ◐ and never carries a tag on its own: the Durham city date also rests on the
  county agenda, which was read.
