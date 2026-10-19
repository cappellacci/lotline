# Lotline: Disclosures

<!-- Rules §7c. Keep this current as the project changes. -->

## AI code-generation tools
- Claude (Anthropic), used for planning, code and documentation. All AI-assisted code is reviewed, tested and explained.
- Claude Code (Anthropic's coding agent CLI), used to write and test code in this repo through pull requests that Ben reviews.
  Each PR records what Claude did and how it was checked in a `logbook.d/` fragment, folded into `LOGBOOK.md`.

## Pretrained models, weights or embeddings
- None so far.

## External APIs and hosted services
Lotline's data adapters download public data from these services at run time (`lotline fetch`); nothing is
sent to them except the query. Every download is logged with its URL and sha256 in `manifest.jsonl` and listed
in [`data_provenance.md`](data_provenance.md), which gives each dataset's license and terms.

| Service | Hosts | Used for | Key / account |
|---|---|---|---|
| U.S. Census Bureau Data API | `api.census.gov` | American Community Survey and 2020 Census tables | Free API key (`CENSUS_API_KEY` in `.env`, never logged or committed) |
| U.S. Census Bureau file downloads | `www2.census.gov`, `www.census.gov` | Building Permits Survey files, CBSA delineation, geographic reference files | None |
| Census TIGERweb (ArcGIS REST) | `tigerweb.geo.census.gov` | Place and county-subdivision boundaries (ACS 2025) | None |
| FRED, Federal Reserve Bank of St. Louis | `fred.stlouisfed.org` | Mortgage rate (Freddie Mac PMMS), PPI, CPI, new residential construction | None (Freddie Mac attribution required) |
| FHFA | `www.fhfa.gov` | House Price Index files | None |
| Esri ArcGIS REST services (hosted by public agencies) | `services*.arcgis.com`, `arcgis.metc.state.mn.us`, `www.arcgis.com`, `*.opendata.arcgis.com` | City, county and state permit and parcel layers (Minneapolis, Met Council, Raleigh, Durham, Columbus, NC OneMap, Ohio statewide parcels, St. Paul) | None |
| Socrata (Tyler Technologies) open-data APIs | `data.austintexas.gov`, `data.cincinnati-oh.gov` | Austin and Cincinnati building permits | None (optional `SOCRATA_APP_TOKEN`, never logged) |
| Agency download pages | `traviscad.org`, Wake County (`services.wake.gov`) | Appraisal rolls, downloaded by hand in a browser because the site blocks automated access or its `robots.txt` disallows it, then registered with `lotline manifest register` | None |
| Franklin County Auditor | `auditor.franklincountyohio.gov` | Exploratory download of permit and dwelling tables (Columbus ADU research); not used in any table | None |
| GitHub | `github.com` | Code hosting, Actions CI, CodeQL code scanning, Dependabot, secret scanning | Project account |

The interactive tool's hosting service will be added here when it is deployed.

## Third-party code, dependencies and datasets
- Dependencies: see the SBOM (`sbom.spdx.json`) and the license scan. Exceptions (non-permissive licenses) are listed here with a justification.

### Dependency license exceptions

| Package | License | Pulled in by | Justification |
|---|---|---|---|
| certifi | MPL-2.0 | httpx | CA certificate bundle only, used unmodified as a runtime dependency; not copied into or distributed with our code. MPL-2.0 is file-level copyleft and places no obligations on our Apache-2.0 code. |

Note: numpy (BSD-3-Clause) bundles a few small components under 0BSD, MIT, Zlib and CC0-1.0, all permissive. CC0 is barred only as the license of our own code (Rules §7b), not for dependencies.
- Datasets: see `data_provenance.md`.

## Pre-existing work
- None. All code was written on or after 2026-09-14.
