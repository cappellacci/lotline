### LB-NNN · 2026-11-11 · Rules: second-coder checks for St. Louis Park, Richfield and Euclid missing-middle rows
- **Question:** are the dates, doses and approval types in three single-coder or snippet-sourced missing-middle rows
  (WS-MM-REVIEW step 4a) supported by the signed ordinances?
- **What I did:**
  - Downloaded the signed St. Louis Park Ord. 2690-25 (city Laserfiche), Richfield Bill 2023-2 (Municode ordinance
    download) and Euclid Ord. 120-2024 (city PDF); read them with PDFKit text extraction and Apple Vision OCR.
  - Compared each against the row in `config/reforms/{mn,oh}.csv` and wrote proposed corrections; no CSV edited.
  - Used three web-fetch subagents first; they could not parse the PDFs, so the reading above was done locally.
- **Inputs:** `config/reforms/mn.csv`, `config/reforms/oh.csv`, `docs/research/mm-methodology-review-2026-11.md` (PR #392 branch).
- **Outputs:** `reports/mn/mm-rule-checks-2026-11.md`.
- **Findings:**
  - St. Louis Park confirmed: first reading 2025-02-18, adopted 2025-03-03, published 2025-03-13, effective 2025-03-28;
    duplex and three-unit PS in N-1/N-2, four-unit in N-2. The draft PDF in `source_url` is unsigned.
  - Richfield: passed 2023-01-24; CUP rule (arterial/collector lots) repealed; MR-1 rezoned to R; cap stays 2. Effective
    date and the 2010 start date remain unknown.
  - Euclid confirmed: passed 2024-10-07, effective 2024-11-06 (page 33), two-family "P" in U1 (5,000 sq ft, 40 ft). The
    old U1 permitted-use text is not printed in the ordinance, so "U1 was single-family only" stays an inference.
- **Decisions:** none. Row edits proposed in the report for Ben to accept.
- **AI:** Claude (Sonnet 5.5) read and compared the documents. OCR can garble table columns; the four-unit column placement in
  St. Louis Park was cross-checked against the lot-dimension table. Closed as "no usable source": Richfield publication notice,
  pre-2025 St. Louis Park chapter 36, Euclid old §1351.02. No St. Paul material, permit data, staff emails or records requests.
- **Open / next:** Ben accepts or rejects row edits; optional browser pass for Municode/amlegal pages that returned 403.
