### LB-NNN · 2026-11-10 · Data feasibility: Chapel Hill ADU permits (legacy LAMA file) and rule history
- **Question:** can Lotline count ADU permits for Chapel Hill (3711800) from public record-level data, and
  what is the town's local ADU rule history?
- **What I did:**
  - Scouted the town's open-data hub, both GIS servers, ArcGIS Online, the OpenGov permit portal, Orange
    County's portal, data.gov and Council records (Legistar API). Found the "LAMA Legacy Permit Data
    Production" File Geodatabase (permits created 2015-05 to 2021-05). The current OpenGov portal has no
    export and blocks automated access (Cloudflare), so it was not touched further.
  - Wrote a standard-library File Geodatabase table reader (`filegdb.py`, from the public format
    description) instead of adding GDAL/pyogrio. Checked it value by value against GDAL on three real tables
    (0 mismatches; GDAL used only in a scratch environment).
  - Built the `chapel_hill_permits` adapter with a Chapel Hill ADU rule (named + created, not negated or
    existing-only), tested on synthetic, hand-built geodatabase tables. Fetched through the IO layer
    (manifest entry) and hand-checked the rule.
  - Read the 2023 Housing Choices ordinance (2023-06-21/O-6), the 2026 omnibus (2026-01-21/O-1), the staff
    reports and the town page for the rule history.
- **Inputs:** hub item f336a911f4fc424bbe1a53a5e7abb529; Legistar matters 23-0560 and 26-0015;
  `processed/nc/eligible_parcels/eligible.parquet`.
- **Outputs:** `src/lotline/adapters/states/nc/chapel_hill_permits.py`, `src/lotline/adapters/states/nc/filegdb.py`,
  `tests/states/nc/test_chapel_hill_permits.py`, `tests/states/nc/test_filegdb.py`, `tests/states/nc/gdb_writer.py`,
  `config/states/nc.yaml` (source entry), `docs/data_provenance.md` (Chapel Hill rows),
  `reports/nc/chapel-hill-adu-scout.md`.
- **Findings:**
  - 30 ADU permits 2015-2021 (5,747 issued building permits), about 0.52 per 1,000 eligible lots a year in
    2016-2020: about 3× Durham's rate over the same years. Chapel Hill's denominator is the ACS fallback (low).
  - Accessory apartments have been allowed by right since the LUMO (2003-01-27, 750 sq ft cap). 2023 raised
    the cap to 1,000 sq ft; 2026 dropped the small-house 75% rule and parking minimums. None of the post-2021
    permits are public: a records request draft is in the report.
  - Hand check: 30/30 matches are new ADUs (2 probable); 60 random non-matches held no missed ADU; a full read
    of every ADU-noun description found about 3 likely misses (recall about 90% for named ADUs).
- **Decisions:** proposed for HANDOFF (PR description): Chapel Hill LAMA permits as an NC ADU source for
  2015-2021; send the records request for 2021-2026; add the three proposed Chapel Hill rows to `nc.csv`.
- **AI:** Claude Code (Opus 5.5) scouted the sources, wrote the reader, adapter, tests and report, and did the
  hand check by reading every match and the random samples. Checked by the GDAL comparison, `pytest`, `ruff`
  and `compliance_check.py`.
- **Open / next:** Ben to send the records request; WS-CORE may move `filegdb.py` into `lotline.io`;
  Carrboro scout (own permits; start from its GIS download page); rule rows into `nc.csv` once siblings merge.
