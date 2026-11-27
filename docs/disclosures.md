# Lotline: Disclosures

<!-- Rules §7c. Keep this current as the project changes. -->

## AI code-generation tools
We used Anthropic's Claude models throughout the build, including Claude Opus 5.5 (model id `claude-opus-5-5`).
We used them in three ways.

- **Code.** Claude Code (Anthropic's coding agent) wrote and tested code in this repo through pull requests
  that Ben reviews. Each pull request records what Claude did and how it was checked in a `logbook.d/`
  fragment, which is folded into `LOGBOOK.md`. All AI-assisted code is reviewed, tested and explained.
- **Review agents.** A simulated judging panel (`.claude/agents/judge-*.md`) reviews the entry against the
  Rules before each milestone. The rule agents (`/rules-adu`, `/rules-mm`, `/rules-fees`) propose local-rule
  rows, each with a source quote, and a person reviews every row before it is imported. Some agent files pin a
  Claude model (Opus, Sonnet or Haiku); the rest run on the session's model.
- **Documentation.** Claude drafted and edited planning notes and documentation, and Ben reviewed them.

## Pretrained models, weights or embeddings
- None. Lotline's own model is fitted from the public data listed in `data_provenance.md`; it uses no pretrained
  model, weights or embeddings.

## External APIs and hosted services
Lotline's data adapters download public data from these services at run time (`lotline fetch`). Nothing is
sent to them except the query. Every download is logged with its URL and sha256 in `manifest.jsonl` and listed
in [`data_provenance.md`](data_provenance.md), which gives each dataset's license and terms.

| Service | Hosts | Used for | Key / account |
|---|---|---|---|
| U.S. Census Bureau Data API | `api.census.gov` | American Community Survey and 2020 Census tables | Free API key (`CENSUS_API_KEY` in `.env`, never logged or committed) |
| U.S. Census Bureau file downloads | `www2.census.gov`, `www.census.gov` | Building Permits Survey files, CBSA delineation, geographic reference files, and TIGER/Line 2025 place and county-subdivision boundaries (`census_tigerline_2025`). These replaced the TIGERweb map service (`tigerweb.geo.census.gov`) on 2026-11-27, and nothing calls TIGERweb now | None |
| FRED, Federal Reserve Bank of St. Louis | `fred.stlouisfed.org` | Mortgage rate (Freddie Mac PMMS), PPI, CPI, new residential construction | None (Freddie Mac attribution required) |
| FHFA | `www.fhfa.gov` | House Price Index files | None |
| Esri ArcGIS REST services (hosted by public agencies) | `services*.arcgis.com`, `*.opendata.arcgis.com`, `www.arcgis.com`, and city, county and state GIS servers such as `arcgis.metc.state.mn.us`, `enterprise.gisdata.mn.gov`, `gis.ramseycountymn.gov`, `services.nconemap.gov`, `maps.mecklenburgcountync.gov`, `gis.greensboro-nc.gov`, `gis.ashevillenc.gov`, `gis.nhcgov.com`, `gis.cuyahogacounty.gov`, `lcaudgis.co.lucas.oh.us`, `maps.bcohio.gov`, `www.portlandmaps.com` and `maps.medfordmaps.org` | City, county and state permit and parcel layers in Minnesota, North Carolina, Ohio, Texas and Oregon (for example Minneapolis, Met Council, Raleigh, Durham, Columbus, Cleveland, Fort Worth, Portland, Bend, Oregon Metro's RLIS taxlots and the Ohio and NC statewide parcels). Each adapter module names its own layer | None |
| Socrata (Tyler Technologies) open-data APIs | `data.austintexas.gov`, `data.cincinnati-oh.gov`, `data.cstx.gov` | Austin, Cincinnati and College Station building permits | None (optional `SOCRATA_APP_TOKEN`, never logged) |
| CKAN open-data portals | `data.sanantonio.gov`, `data.houstontx.gov` | San Antonio building permits; Houston's monthly permit counts, used as a check | None |
| Agency download pages | `traviscad.org`, Wake County (`services.wake.gov`), Montgomery County Treasurer (`go.mcohio.org`), Warren County GIS (`warrencountyohio.gov`), TxGIO (`data.geographic.texas.gov`), HUD (`www.huduser.gov`), Town of Cary (`data.townofcary.org`) | Appraisal rolls, StratMap parcels, HUD income limits and Cary permits. We download these by hand in a browser, because the site blocks automated access or its `robots.txt` disallows it, and register them with `lotline manifest register` | None |
| Franklin County Auditor | `apps.franklincountyauditor.com` | Appraisal files: permit descriptions (ADU flags), dwelling year built and yearly parcel rolls (Franklin County, Ohio) | None |
| City of Rochester (MN) Laserfiche WebLink | `lf.rochestermn.gov` | Monthly building permit detail spreadsheets (2005-09 on), found through the archive's folder-listing service and downloaded one file per month | None |
| Legistar Web API (Granicus) | `webapi.legistar.com` | City of Columbus Council variance ordinances (ADU approvals before 2026) | None |
| GitHub | `github.com`, `cappellacci.github.io` | Code hosting, Actions CI, CodeQL code scanning, Dependabot, secret scanning, and hosting the interactive tool on GitHub Pages | Project account |

**Data with no stated license.** MnGeo's "Parcels, Compiled from Opt-In Open Data Counties" (`mngeo_parcels`) gives its license as "None". The counties publish it as open data, provided as is. Lotline downloads it into `LOTLINE_DATA_DIR` like every other source and never commits or republishes the records. Published outputs are counts for whole jurisdictions.

**Interactive tool.** GitHub Pages hosts the tool at https://cappellacci.github.io/lotline/. `scripts/publish_app.py` uploads the results bundles as the assets of a GitHub release, and the Pages workflow rebuilds the page from them. No results are committed to the repo.

**Data dashboard page (`reports/data_dashboard/index.html`).** The page loads three open-source files from
the jsDelivr CDN (`cdn.jsdelivr.net`) when it is opened, unmodified and not copied into the repo: d3 7.9.0
(ISC), topojson-client 3.1.0 (ISC) and us-atlas 3.0.1 `counties-10m.json` (ISC; county shapes derived from
Census cartographic boundary files). Nothing is sent to the CDN except the file requests.

**App page (`reports/app/index.html`, built by `scripts/build_app.py`).** The page carries its fonts inline and
loads none from a font host. The brand fonts are committed in `docs/build/identity/fonts/`, unmodified:
Public Sans v2.001 (github.com/uswds/public-sans), IBM Plex Mono 2.5.0 (github.com/IBM/plex) and Source Serif 4
4.005R (github.com/adobe-fonts/source-serif; used by the written reports only). All three are under the SIL Open
Font License 1.1; each family's licence file sits beside its fonts. The OFL is permissive for this use (fonts
may be bundled and redistributed with software, but the fonts may not be sold on their own). The embedded
data dashboard loads the jsDelivr files listed above.

## Third-party code, dependencies and datasets
Lotline's runtime dependencies are httpx, matplotlib, numpy, openpyxl, pandas, pandera, pyarrow, pydantic,
pypdf, pyyaml and xlrd (`pyproject.toml`). The development tools are pip-licenses, pytest, pytest-xdist and
ruff. Each is under a permissive license: MIT, BSD or Apache-2.0, and matplotlib's own PSF-based license. The SBOM (`sbom.spdx.json`) lists every
package with its version, and the CI license scan checks all of them, including the packages these pull in.
The one exception is below, with its justification.

### Dependency license exceptions

| Package | License | Pulled in by | Justification |
|---|---|---|---|
| certifi | MPL-2.0 | httpx | CA certificate bundle only, used unmodified as a runtime dependency; not copied into or distributed with our code. MPL-2.0 is file-level copyleft and places no obligations on our Apache-2.0 code. |

numpy (BSD-3-Clause) bundles a few small components under 0BSD, MIT, Zlib and CC0-1.0, all permissive. CC0 is barred only as the license of our own code (Rules §7b), not for dependencies.

Datasets, with each one's license and terms, are listed in [`data_provenance.md`](data_provenance.md).

## Pre-existing work
- None. All code was written on or after 2026-09-14.
- **Knowledge carried over, not code.** Ben has worked on Dallas housing data outside Lotline. For the Dallas
  permit adapter (`dallas_permits`, 2026-10-23), a written note of his on *public* Dallas sources pointed to the
  City's "New Permits 1971-2024" ArcGIS layer. It warned that some apartment projects repeat their total on
  every building's permit, and that permits are missing from late 2024 through September 2025 (the move to
  DallasNow). No code, configuration or data from that work was used. We wrote the adapter for Lotline from
  the public layer itself and checked every figure in it against that layer and Census BPS.
- **Published format descriptions, not code.** We wrote two file readers ourselves, from public format
  descriptions, with no third-party code:
  - The file geodatabase reader (`src/lotline/adapters/states/tx/filegdb.py`, 2026-10-27) follows Even
    Rouault's public, reverse-engineered format description ("FGDB-Spec",
    github.com/rouault/dump_gdbtable/wiki/FGDB-Spec). No code was taken from GDAL, from that repository's
    scripts or from any other reader. We considered GDAL/pyogrio and turned it down, because its wheels
    statically link GEOS (LGPL-2.1) and SpatiaLite (MPL-1.1/GPL-2/LGPL-2.1).
  - The shapefile reader (`src/lotline/io/shapefile.py`, 2026-11-27), which reads the Census TIGER/Line
    boundaries, follows the ESRI Shapefile Technical Description (1998) and the dBASE III table layout. It
    uses the Python standard library only.
