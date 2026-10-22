### LB-NNN · 2026-10-21 · Admin: Wake roll re-downloaded by hand (NC thread 10, S7a)
- **Question:** can the Wake County files be on record as browser downloads, since services.wake.gov's
  robots.txt disallows scripts?
- **What I did:**
  - Ben downloaded `Real_Est_Data_Final_Dec2023.xlsx` and `Qualified_Sales_Past_24Months.xlsx` in a browser
    and registered them with `lotline manifest register`.
  - Compared checksums; superseded the automated sales-file entry; regenerated `docs/data_provenance.md`.
- **Inputs:** https://www.wake.gov/departments-government/tax-administration/data-files-statistics-and-reports/real-estate-property-data-files
- **Outputs:** `manifest.jsonl` (new sales entry), `manifest.superseded.jsonl` (the 2026-10-19 automated sales
  entry), `docs/data_provenance.md`.
- **Findings:**
  - The Dec 2023 roll is byte-identical to the 2026-10-19 automated copy (sha256 7762d75a…, 162,388,401
    bytes), so the processed Wake parcels needed no rebuild. `register` first kept the old automated entry for
    the identical file; the browser copy was then registered under the adapter's documented vintage
    (2023-12-31) and the automated entry superseded (in #207).
  - The sales file differs (Wake refreshes it daily; nothing reads it yet).
- **Decisions:** none.
- **AI:** Claude Code (Opus 5.5) found the right link (the page's link opens a folder listing), checked
  the checksums and ran the manifest steps; Ben did both downloads.
- **Open / next:** Mecklenburg permits and the pre-June-2023 roll (S7b).
