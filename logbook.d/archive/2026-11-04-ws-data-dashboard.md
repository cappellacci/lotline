### LB-NNN · 2026-11-04 · Build: Data dashboard for checking and showing the collected data

- **Question:** Can one page show, for all states together and for each one, what we have collected (parcel
  coverage by county and municipality, land use and zoning, population covered, ordinance dates, housing vs
  population growth), so we can check the data and show the effort behind it, and pick up a fifth state with no code changes?
- **What I did:**
  - `src/lotline/dashboard/summarize.py`: state-agnostic summary of processed tables (states found from
    `config/states/`): latest roll per jurisdiction, one parcel source per jurisdiction (`parcel_sources`, else
    the largest), population covered (unincorporated areas = county remainder), eligible parcels, reforms
    timeline, growth series, and automatic data checks.
  - `src/lotline/dashboard/template.html` + `render.py`: one self-contained page (d3, topojson-client and
    us-atlas from jsDelivr, ISC): county choropleth with six measures and municipality dots, click-to-filter
    by county, land-use bars, sources table, ordinance timeline, indexed growth chart, permits by size, data
    checks, searchable jurisdiction table with CSV download. Light and dark themes.
  - `src/lotline/adapters/national/pep.py`: Census Population Estimates (state + county, 2010–2025, two
    vintages spliced at 2020) through the IO layer; registered as documented-only in `registry.py`.
  - `scripts/build_data_dashboard.py` writes `reports/data_dashboard/` (gitignored).
- **Inputs:** processed `jurisdictions`, `parcels`, `eligible_parcels`, `acs_geo_year`, `bps_place_year` for
  MN, NC, OH and TX; `config/reforms/*.csv`; cached TIGERweb place/township polygons; Census PEP (new download,
  2 files, in `manifest.jsonl` and `docs/data_provenance.md`).
- **Outputs:** the files above; `docs/data_dashboard.md`; `tests/dashboard/test_dashboard.py`;
  `docs/disclosures.md` (CDN libraries); `docs/data_provenance.md` (regenerated, `census_pep` added).
- **Findings:** across the four states 94% of the 2020 population lives in a jurisdiction with parcels on file
  (2,905 of 3,465 jurisdictions; 23.1M parcels). The checks flag: TX 36.5% and NC 19.2% of parcels have unknown
  land use; 27 TX counties have no jurisdiction in the table (no BPS row), so nothing there is counted; two NC
  reform GEOIDs (3731060, 3758860) match no jurisdiction; Chapel Hill has a coded reform but no parcels; only 5%
  of TX reforms are second-coded.
- **Decisions:** proposed: the data dashboard is a validation and communication aid built only from processed
  tables (holdouts already filtered) and never a model input; Census PEP is documented-only.
- **AI:** Claude Code designed and wrote the summary, page, adapter, tests and docs. Checked by 12 hand-worked
  tests (latest-roll rule, source choice, population remainder, eligible-year choice, reform dating, growth
  sums, PEP splice, JSON escaping, and a made-up state "ZZ" built from config and processed tables alone),
  the full suite (1,383 passed), `compliance_check.py` (0 FAIL), ruff, and by opening the page in a browser
  (all states, MN, TX, county filter, dark mode).
- **Open / next:** a `lotline dashboard` CLI subcommand (CLI is a WS-CORE contract); fold the page into the
  WS-APP Streamlit tool or publish it; look into the flagged items above (TX land-use crosswalk, missing TX
  counties, NC GEOIDs).
