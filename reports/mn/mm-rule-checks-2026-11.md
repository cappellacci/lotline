# Missing-middle rule checks: St. Louis Park, Richfield, Euclid (2026-11-11)

Second-coder checks requested by WS-MM-REVIEW step 4a (`docs/research/mm-methodology-review-2026-11.md`, rows
for MN and OH). **No CSV was edited**: each section ends with a proposed correction for Ben to accept.
No permit or outcome data were read. No St. Paul or Ramsey County material was opened. No staff were contacted.

How the sources were read: the three signed ordinances were downloaded as PDFs and read with on-device text
extraction (PDFKit) and OCR (Apple Vision) because the pages are images or the fetch tool could not parse them.
OCR can garble table columns; where a claim rests on column alignment it is flagged below.

## Summary

| Place | Row | Verdict | Proposed change |
|---|---|---|---|
| St. Louis Park, MN | `MN-2757220-missing_middle-2025` | **Confirmed** from the signed ordinance | Dates verified; promote from "snippet" to confirmed; add one caveat on the prior-code baseline |
| Richfield, MN | `MN-2754214-missing_middle-2023` | **Adoption confirmed**; effective date still unknown | Keep; tag effective date as estimated |
| Richfield, MN | `MN-2754214-missing_middle-2010` | **Prior rule confirmed** (CUP text is in the repealed subdivision); start date still a placeholder | Keep `[earliest-known]`; add the citation |
| Euclid, OH | `OH-3925704-missing_middle-2024` | **Confirmed** (passed 2024-10-07, effective 2024-11-06 printed on the signed page) | Second coder = agree on dates/dose; one gap left on the repealed U1 text |

## 1. St. Louis Park, MN: Ord. 2690-25

**Source.** City records system (Laserfiche), document 826140, the signed ordinance with DocuSign envelope
(103 pages): `https://laserfiche.stlouispark.org/WebLink/ElectronicFile.aspx?docid=826140&dbid=0&repo=SLP`.
The city's Proposed Ordinances index lists it as "Approved Ordinance No. 2690-25"
(`https://www.stlouisparkmn.gov/Government/City-Code/Proposed-Ordinances`). The `…/250207-zoningcodeupdate-ordinance-final.pdf`
linked in the row's `source_url` is the **unsigned draft** ("Ordinance No. XXX-XX", blank dates); cite the Laserfiche copy instead.

**Dates (last page, §102 and the signature block).**
- First reading: February 18, 2025.
- Second reading and adoption: March 3, 2025 ("Adopted by the city council March 3, 2025").
- Publication: March 13, 2025.
- Effective: March 28, 2025. §102 says it takes effect "no sooner than fifteen days after its passage and publication"; 15 days after publication is March 28.

So the coded `adoption_date` 2025-03-03 and `effective_date` 2025-03-28 are both right. The snippet-sourced date is now verified.
(The 7–0 vote in the current notes came from the earlier batch and was not re-checked; the ordinance page carries no vote.)

**Dose.** Table 36-163(a), Principal Uses in Neighborhood Districts, lists two-unit (duplex), two-unit attached (twinhome),
courtyard cottage and three-unit as "PS" (permitted with standards) in N-1/N-2, and four-unit as "PS" in a single column.
"PS" is not a conditional use: §36-163 separates "PS" from "C", and a variance route applies to a standards miss. The extracted
table loses column alignment, so which column the single four-unit "PS" sits in comes from a second table (minimum lot width
and area, which lists "three-unit" in the N-1 block and "four-unit" only in the N-2 block, 60 ft / 7,800 sq ft). That agrees with
the earlier second coder: 3 units in N-1, 4 in N-2. The row's `unit_cap=3` (cap holding in both districts) stands.

**Caveat on the "before" side.** The ordinance's own text replaces "R-1 or R-2" and, in places, "R-1, R-2 and R-3" with "N-1 or N-2".
The redline strike-throughs do not survive text extraction, so I cannot show from this document that every pre-2025
single-family district had two-family prohibited. R-3 also appears among the replaced district names (struck text, partly garbled); I did not read what R-3 allowed, but it may have been a two-family district folded into N-1/N-2 in places. Consequence: the 1→3 step is the dose on the former R-1/R-2 land; the share of the city that
was already two-family-permitted before is not measured here. This was true of the existing "inferred, not verified" note; it is
now narrowed, not resolved. A resolving source would be the pre-2025 chapter 36 use table (Municode, which returned 403 to the
fetcher) or the 2025-02-18 council packet.

**Also noted.** The index lists a further 2026 ordinance "amending city code chapter 36… replacing the chapter in its entirety"
(posted July 9, 2026, council date Aug. 3, 2026; status not shown). It falls after the post-period of every fitted outcome year
but could change the rule in force in 2026; not read.

**Proposed row edits (`MN-2757220-missing_middle-2025`):**
- `source_url`: replace the draft PDF with the Laserfiche URL above (keep the draft as a second URL if wanted).
- `coder_2` stays `codex-2026-11-02`; add `verified_by`/`verified_date` for this check: `claude 2026-11-11`.
- `coding_notes`: append "Dates confirmed from the signed ordinance (Laserfiche 826140): 1st reading 2025-02-18, adopted 2025-03-03, published 2025-03-13, effective 2025-03-28. The draft PDF in the earlier source_url is unsigned. Pre-2025 baseline: R-3 appears among districts replaced by N-1/N-2 (use not read); the 1→3 dose is for former R-1/R-2 land."
- No change to dates, `by_right`, or `unit_cap`.

## 2. Richfield, MN: Bill No. 2023-2 (and the 2010 row)

**Source.** The signed Bill No. 2023-2, "An ordinance amending the Richfield zoning code regulations related to two family uses;
consolidating the R and MR-1 districts into a low density residential zoning district; and modifying low density residential design
standards and lot dimensions" (21 pp): `https://mcclibraryfunctions.azurewebsites.us/api/ordinanceDownload/15207/1201593/pdf`
(the URL already in the row). The two council PDFs in the row (`…/01-24-2023%20City%20Council%20Agenda.pdf`, `…/01-24-2023%20Regular.pdf`)
now return **404**; the city's AgendaCenter loads by script and could not be read. I did not guess other URLs.

**Adoption (confirmed).** "Passed by the City Council of the City of Richfield, Minnesota this 24th day of January, 2023" (Mayor Supple, Acting
City Clerk Swanson). §16: "effective in accordance with Section 3.09 of the Richfield City Charter."

**Effective date (not found).** The publication date is not in the ordinance and no legal notice was reachable. The existing note
(effective ≈ 30 days after publication under Charter 3.09) was not re-verified; the charter text was not opened. Estimated effective
is late February to March 2023. Nothing fitted depends on a day: both 2023-01-24 and any date in Feb–Mar 2023 fall in event-year 2023.

**What changed (confirmed from the ordinance text).**
- §512.05 use table: the MR-1 column is removed; the "Two-family dwellings" row shows "C" for the R column in the old table
  text that is struck and replaced (the OCR garbles the redline, so the new "P" in R is read from the council-approved summary already
  cited, and the repeal below).
- §514.07 "Conditional uses": "Subdivision 2 [Two-family dwellings] is repealed", with the old conditions printed: lot abuts an
  **arterial or collector street**; lot area and width per §514.11; two off-street spaces per unit (one enclosed); 960 sq ft per new unit,
  500 sq ft for a conversion. This confirms the 2010 row's description of the prior rule.
- Appendix I, §15: boundary paragraphs repealed, "rezoning all affected property as Low Density Residential District – R" (the MR-1 land).
- §514.09: anything not listed is prohibited in R; multifamily (3+ units) is still not allowed in R.
- R-1 is untouched (two-family still prohibited there).

**Approval type and dose.** The unit cap is unchanged at 2. What changed is the approval path (CUP on arterial/collector lots only → by
right across R, plus the former MR-1 land becomes R). This matches the review's reading ("method change, no cap rise, D-042"). One more
fact for the method decision: MR-1 was already a by-right two-family district, so for the former MR-1 properties nothing changed in
use; the by-right switch is real only on former-R land.

**2010 row.** The prior rule is now sourced from the repealed subdivision above, but nothing shows *when* the CUP rule began
(the printed history notes in this document go back only to Bills 1996-22, 2007-19, 2008-12, 2009-5/-7, 2014-4, 2015-4, 2016-3, 2017-6, 2021-12 on
unrelated sections). `2010-01-01` stays a placeholder, `[earliest-known]`.

**Proposed row edits:**
- `MN-2754214-missing_middle-2023`: `coder_2` = `claude-2026-11-11`, `coder_agreement` = `agree` on adoption date, cap (2), and CUP→by-right;
  `coding_notes` append "Signed ordinance read 2026-11-11: passed 2023-01-24; repeals §514.07 Subd. 2 CUP; rezones MR-1 to R; effective date by Charter 3.09, publication date not found; the two council-PDF URLs are now 404, use the ordinance URL). Change `effective_date` only if Ben wants a rule: keep 2023-01-24 (adoption proxy).
- `MN-2754214-missing_middle-2010`: add `source_url` the ordinance PDF above and `source_section` "§514.07 Subd. 2 (repealed by Bill 2023-2)"; keep `[earliest-known]`; still single coder for the *start date* (the content of the rule is now second-read).

## 3. Euclid, OH: Ord. 120-2024

**Source.** The signed ordinance PDF (33 pp, scanned images; the row already cites it):
`https://irp.cdn-website.com/83d949c5/files/uploaded/120-2024_-_Ord_amending_enacting_and_repealing_various_chapters_of_part_13_of_P_and_Z_Code.pdf`.
Read by OCR. amlegal (`codelibrary.amlegal.com`) returned 403; the city site's legislation list shows only 2021 entries and the
council minutes folders did not load, so no minutes were found.

**Dates (page 33).** §5: "in full force and effect from and after the earliest period allowed by law." Stamped: "Passed: October 7, 2024 /
Effective: November 6, 2024." Not an emergency ordinance (no emergency clause; effective = passage + 30 days, the usual Ohio municipal
referendum period). The coded `adoption_date` 2024-10-07 and `effective_date` 2024-11-06 are confirmed.
(The Planning and Zoning Commission recommended it on August 13, 2024, per the recitals.)

**Districts and dose.** §1341.01 is amended so the districts "Class U1 or Single Family House Districts" become "U1 Residential District"
and "Class U2 or Two Family House Districts" become "U2 Residential District". New Table 1352.04 (principally permitted and conditional
uses in the U1 and U2 Residential Districts; "a blank cell indicates that a use is prohibited") marks single-family, **two-family**
and **double-house** dwellings "P" in both U1 and U2, and three-family "P" in U2 only. Table 1352.07: two-family needs 5,000 sq ft and 40 ft
in U1 (4,000 sq ft and 35 ft in U2), the same as single-family in each district. §1352.06: two-family limited to 2½ stories / 35 ft in both.
The ordinance repeals Chapters 1321, 1351 (U1 Single-Family House Districts), 1353 (U2 Two-Family House Districts) and 1355 (U3).
Dose = 1→2 units by right on U1 land. Cap 2 and `by_right=True` stand. Not checked: whether the zoning map changed (the ordinance
text does not mention a map amendment in the pages read).

**Prior code.** The repealed chapter titles ("U1 Single-Family House Districts" vs "U2 Two-Family House Districts") and the ordinance's own
structure (a separate two-family district, with its own permitted-use section 1353.02) indicate that two-family was not allowed
as of right in U1 before. But the repealed §1351.02 (the old U1 permitted-use list) is **not printed** in the ordinance (only
§1351.03 conditional uses is: schools, library, churches, day care, with no two-family), and the old code on amlegal was unreachable.
So "U1 formerly single-family only" is well supported but still inferred. A reading that would close it: the pre-2024 §1351.02 on amlegal
from a browser, or a pre-2024 snapshot of the code.

**Proposed row edits (`OH-3925704-missing_middle-2024`):**
- `coder_2` = `claude-2026-11-11` (dates, table and districts read independently from the signed page), `coder_agreement` = `agree`
  (change from `single_coder` to `partial` if Ben wants the open prior-code inference to count against it; I recommend `agree` with the caveat in the notes).
- `coding_notes`: append "Second read 2026-11-11 by OCR of the signed ordinance: page 33 'Passed: October 7, 2024 / Effective: November 6, 2024', no emergency clause. Old §1351.02 not printed in the ordinance; prior U1 = single-family only is inferred from chapter titles."
- No change to dates, `unit_cap=2`, `by_right`.

## What closed as "no usable source"
- Richfield publication/effective date (legal notice, charter text, agenda center): not reachable.
- Richfield 2023-01-24 agenda and packet PDFs: 404.
- St. Louis Park pre-2025 chapter 36 and 2025 minutes: Municode 403, minutes not on the current site.
- Euclid old §1351.02 text, council minutes: amlegal 403, minutes not reachable.
No records requests or staff emails were made.

## What this does to the fit set (for the method entry)
Both fit-place events (St. Louis Park, Euclid) survive with confirmed dates and the 1→3 / 1→2 doses. Richfield stays out of the cap-rise
fit; its by-right switch is verified as a CUP-to-by-right change at cap 2, on former-R land only.
