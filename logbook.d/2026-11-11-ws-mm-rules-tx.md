### LB-NNN · 2026-11-11 · WS-MM-REVIEW (step 1, TX): second-coder rule checks for Texas missing-middle events
- **Question:** are the Texas missing-middle events in the D-054 / D-055 fit set real cap rises, and what did the
  rule look like just before? The places are League City 2020, Lewisville 2022, Houston 2023, and Lubbock 2023
  with its missing Ch. 40 row.
- **What I did:** four research agents read the codes and staff materials, one place each, using the web only.
  No records requests, no emails, and no bot check was bypassed. I then checked the decisive items myself:
  - Lewisville's adopted 2022 use table, p. 197, read as an image;
  - League City's zoneomics duplex row against its header;
  - the 2011 League City draft schedule;
  - Houston's Livable Places User Guide and FAQ (local PDFs).
- **Inputs:** local PDFs in `lotline-data/manual/texas/Official-PDFs` (Houston); `config/reforms/tx.csv`;
  `docs/research/ordinances/tx-second-coder-lubbock-2026-11-07.md`. No permit or BPS outcomes were read.
- **Outputs:** `reports/tx/mm-rule-checks-2026-11.md`, with 7 proposed row changes. `tx.csv` is not edited:
  Texas coding is closed.
- **Findings:**
  - **Lewisville: confirmed.** Duplexes became allowed by right in R-7.5, R-6 and R-5, effective 2022-12-01. They
    were new then.
  - **League City 2020: not an event.** The UDC recodified the old ordinance, and RSF-2 duplexes were already P,
    probably by 2011 and at the latest by 2015.
  - **Houston 2023: date right, dose wrong.** 3+ units were already legal as multifamily. Livable Places added a
    lighter standards route capped at 4 units on local streets and 8 elsewhere. That is not a cap rise.
  - **Lubbock: no usable source for the Ch. 40 text.** It stays out (D-059).
  - **Open conflict:** League City RSF-5 duplex shows S (special use permit) on the zoneomics mirror but nothing in
    Ben's 2026-10-30 lookup of the official PDF.
- **AI:** Claude Code (Opus 5.5) ran the agents, checked the decisive pages, and wrote the report and proposals.
  Snippet-only facts are marked L or M in the report.
- **Open / next:**
  - Ben accepts or rejects proposals 1–7.
  - The method-only D-entry decides whether League City and Houston leave the cap-rise set, and whether
    "standards" reforms get their own class.
  - Optional: OCR of the Lubbock R-2 zone-case staff reports, which needs a local OCR install.
