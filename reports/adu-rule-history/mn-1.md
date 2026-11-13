# D-086 ADU rule history: Minnesota, first coder, batch mn-1

Coder: Claude (claude-d086), 2026-11-13. Coded from ordinance sources only; no permit counts were opened.
Rows go in `config/reforms/mn.csv`. All new rows are `single_coder`.

**Convention note.** The brief says `coder = claude-d086` and "set the replaced row's `end_date`". Two MN tests
block both (`tests/states/mn/test_reforms.py`): `coder` may only be `claude`, `ben` or `pipeline+ben`, and in MN
`end_date` is used only for `suspended` windows (chains run through `supersedes`). Editing that test was out of
scope, so the new rows use `coder = claude`, with "D-086 first coder (claude-d086)" in `coding_notes`. No `end_date`
was set. Each chain is linked by `supersedes` alone, the way every other MN chain is.

## D-023 grade changes inside 2014-2025 (candidate events)

**None in this batch.** Every change found is an adoption (no ADUs, then a rule), which D-086 says is not an event.

**One existing event is probably wrong: Inver Grove Heights 2018.** D-079 counted it as an event. The 2015 row
(`MN-2731076-adu-2015`, Ord. 1305) leaves `by_right` and `owner_occ` blank. But the council minutes settle both:

- **2015-07-13** (first reading): the Housing Committee preferred a permitted use, and the council set a one-acre
  minimum lot for detached units.
- **2015-08-24** (third reading): the ordinance "restricts rental of both the primary property and the ADU. The owner
  must occupy either", and "there will be an administrative process". The 1,000 sq ft cap is also in these minutes.

So the 2015 rule was by right with owner occupancy (grade 2/3). The 2018 row (Ord. 1358) is by right with owner
occupancy too, also 2/3. The dose does not change in 2018. I did **not** edit the 2015 row, because Ben adjudicated
it and the brief forbids changing existing fields unless a source shows them wrong (a blank is not wrong). **Ben or
the second coder should fill `by_right=True` and `owner_occ=True` on that row (and `adu_max_sqft=1000`,
`adu_detached_allowed=True`, `min_lot_sqft=43560` for detached units).** Otherwise the blanks may keep producing a
spurious event.

## Per place

| Place (GEOID) | Versions in 2014-2025 (date: what changed; grade) | Rows added / changed | Searched, where nothing older was found |
|---|---|---|---|
| Andover (2701486) | none 2014-01-01 (grade 0) → Ord. 463 2016-06-21: CUP in R-1 (1/3) | **added** `MN-2701486-adu-2014-none`; 2016 row now supersedes it | City Title 12 PDF: §12-12-5 and the ADU definition carry only Ord. 463 history notes; §12-4-6(A) (1970) bars accessory buildings as dwellings. Inferred from history notes, so confirm. No later change to the §12-12-5 fields (history note is Ord. 463 only). |
| Apple Valley (2701900) | 2003 CUP rule throughout (1/3) | none | Dakota County ADU guide (archived 2022-12): CUP, R-1 at 40,000 sq ft, size 40% of footprint **or 900 sq ft**. The existing row's notes (post-2023 text) say there is no fixed cap. The 900 sq ft cap may have been dropped between 2022 and 2025, but no date was found. Same grade either way. |
| Baytown twp (2716304132) | accessory apartment by Certificate of Compliance in AG/AP/RR/SFE/TZ/SCR throughout (row says 1/3) | none | Township zoning ordinance (amended through 2024-09-04) and the ordinance list: the township adopted the Washington County model zoning ordinance (Ord. 49, undated, between 2006 and 2016) and amended zoning in 2016 (Ord. 55). Neither is dated well enough to move the row's `[predates]` 2018 start. |
| Blaine (2706382) | none 2014-01-01 (0) → Ord. 21-2489 2021-12-20: CUP (1/3) | **added** `MN-2706382-adu-2014-none`; 2021 row now supersedes it | Ramsey staff survey (Jan 2022 packet) lists Blaine among cities without ADU ordinances. The "approvals as early as 2011" note on the 2021 row traces to a Northern Light story (2016-08-10) about **Blaine, Washington**. Discount it. |
| Bloomington (2706616) | 2009 (by right, attached) → 2022-08-08 (detached added) → 2025-05-19 (1,000 sq ft); by right throughout, `owner_occ` blank | none | Chain already coded. No new source read. |
| Burnsville (2708794) | none 2014-01-01 (0) → Ord. 1456 2018-05-22: by right (row `owner_occ` blank) | **added** `MN-2708794-adu-2014-none`; 2018 row now supersedes it | Council report 2017-11-06 (primary): "Leave the ordinance as is, thus, prohibiting accessory dwelling units." See the uncertainties below about a possible later change to the 2018 rule. |
| Cedar Lake twp (2713910450) | Scott County 2010 → 2025-05-06 (both 1/3) | none | Scott County ordinance PDF returned 403, and the energyzoning copy and Wayback were unreachable. No 2014-2024 amendment found. |
| Chanhassen (2710918) | none → 2025-06-09 CUP, detached (1/3) | none | Already coded. |
| Cottage Grove (2713456) | accessory apartment inside the house, permitted accessory use in R-1 to R-4 (row: by right, no owner occupancy), `[earliest-known]` 2023 | none | Zoneomics copy of the code lists accessory apartments as a permitted accessory use in R-1/R-2. The only history note is Ord. 1068 (2023 rewrite). amlegal is script-rendered and Wayback was offline, so the pre-2023 text was not read. The origin is still unknown. |
| Crystal (2714158) | none 2014-01-01 (0) → UDC 2018-02-10: by right (row `owner_occ` blank) | **added** `MN-2714158-adu-2014-none`; 2018 row now supersedes it | CCX Media 2021-12-15: the council "amended its ordinances to allow" ADUs about four years earlier (secondary). |
| Dayton (2715022) | Ord. 2019-22 2019-12-10 (row fields blank) | none | Ramsey 2021 survey: attached/internal ADUs permitted with owner occupancy (by right, 2/3); detached by IUP on 2+ acres. Pre-2019 status not found, so no "none" row. The existing row's blanks could be filled from this and the second coder's note. |
| Denmark twp (2716315688) | accessory apartment by Certificate of Compliance, owner-occupied, throughout (row 2/3) | none | Township Development Code (effective 2022-12-08) history: code adopted 2006-02-06 (Ord. 2006-01), amended 2014-02-03, 2014-12-01, three times in 2017, and twice in 2022. Which amendment (if any) touched §2.1 is not shown. Likely in force since 2006, but not proven. |
| Eagan (2717288) | none 2014-01-01 (0) → Ord. 528 2014-05-05: registered, by right, owner-occupied (2/3) | **added** `MN-2717288-adu-2014-none`; 2014 row now supersedes it | Draft ordinance (Granicus, primary) adds §11.70 subd. 32 and ADU to the E/R-1 lists. 2022 Dakota guide shows the same standards, so no later change found. |
| Edina (2718188) | none 2014-01-01 (0) → 2024-04-16 (by right) | **added** `MN-2718188-adu-2014-none`; 2024 row now supersedes it | Star Tribune 2024 headline "Edina is the next suburb to allow ADUs" (secondary; body paywalled). |
| Forest Lake (2721770) | Ord. 719 2023-01-23: detached Accessory Dwelling in A on 5+ acres as an accessory use (by right) | none | Ord. 719 text and 2023-01-23 minutes (primary): it added the A-district dwelling. Accessory apartments in owner-occupied homes (RR/AP) exist in the code but their start date was not found, so I could not tell whether a pre-2023 rule existed. No row added. The existing row's note ("NO ADU RULE ... coded from 2010-01-01") contradicts its own fields: stale text. |
| Fridley (2722814) | none 2014-01-01 (0) → 2022 ordinance (row 2022-09-01; CUP-type 1/3) | **added** `MN-2722814-adu-2014-none`; 2022 row now supersedes it | City ADU page: "In 2022, the City Council approved an ordinance allowing" ADUs. Exact adoption date and ordinance number are still not found. |
| Golden Valley (2724308) | none 2014-01-01 (0) → Ord. 745/746 2022-11-11: administrative, owner-occupied (2/3) | **added** `MN-2724308-adu-2014-none`; 2022 row now supersedes it | City ADU page and Star Tribune "Golden Valley legalizes accessory dwelling units". |
| Helena twp (2713928322) | Scott County 2010 → 2025-05-06 (both 1/3) | none | As Cedar Lake. |
| Hopkins (2730140) | Ord. 2022-1180 2022-07-28 (by right, owner-occupied) | none | City zoning-update page says the new code allowed ADUs "in all residential districts". It does not say whether the 1970s code allowed any, so no "none" row. 2021 Module 1 memo read; nothing on the prior code. |
| Hugo (2730392) | 2011 rule throughout (row: CUP 1/3) | none | Zoneomics copy: §90-277 history is only Ord. 2011-459 (10-3-2011); §90-203 accessory apartments (owner-occupied) is from the prior code. No 2014-2025 amendment found. |
| Inver Grove Heights (2731076) | none 2014-01-01 (0) → Ord. 1305 eff. 2015-11-02 (by right, owner-occupied: 2/3 per minutes) → Ord. 1358 2018-10-08 (2/3) | **added** `MN-2731076-adu-2014-none`; 2015 row now supersedes it | 2015-07-13 minutes: "The code currently only allows for one dwelling unit per single family zoning district." See the section above on the 2018 event. |
| Jackson twp (2713931580) | Scott County 2010 → 2025-05-06 (both 1/3) | none | As Cedar Lake. |

In total, 9 "no ADUs" rows were added. On 9 existing rows the only change is `supersedes` (plus a one-line D-086
note). No other existing field was changed.

## Uncertain, or existing rows I believe are wrong

- **IGH 2015 row blanks:** see the section above. This is the one finding that changes the event count.
- **Burnsville 2018 row may not hold through 2025.** It codes detached ADUs on 1+ acre lots and a 33% footprint cap.
  Dakota County's guide (updated 2022-12-06) says ADUs "must be within or attached", with a 50% footprint cap. The
  current code (recodified 2026, Ord. 1648) says 50%. A change between 2018 and 2022 is likely (a 2020 Sun
  Thisweek story, "Tiny houses may get a little smaller", returned HTTP 429 and was not read). The grade stays 2/3
  if owner occupancy holds; the guide says the owner must live there 185 days a year. The date is unknown, so no
  row was added. The 2018 row's blank `owner_occ` could be filled True.
- **Blaine 2026 row date:** its effective date is 2026-03-16, but the second coder found second-reading adoption
  on 2026-05-04. This is outside the window.
- **Andover, Crystal, Edina, Golden Valley "none" rows rest on inference or news, not on the old code text.**
  These are the first ones for the second coder to check.
- **Baytown and Fridley `by_right=False`:** a Certificate of Compliance (Baytown) and an attached-ADU permit
  (Fridley) look administrative, while Fridley requires a SUP for detached units. This was not changed.
- **Sources that could not be reached:** Andover Laserfiche (needs cookies), the Scott County ordinance (403),
  Sun Thisweek (429), and the Wayback Machine (offline during the session).
