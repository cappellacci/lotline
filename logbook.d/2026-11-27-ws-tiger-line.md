### LB-NNN · 2026-11-27 · review · Boundaries from the archived TIGER/Line 2025 files

**Question:** Will a new state's boundary fetch still work after Census changes its map service?

**Outputs:**
- `src/lotline/io/shapefile.py` (new): a small standard-library reader for polygon shapefiles (`.shp` and
  `.dbf` inside a zip), so the boundaries need no GIS dependency.
- `src/lotline/adapters/national/tiger_boundaries.py` v2.0: reads the TIGER/Line 2025 place and
  county-subdivision zips from www2.census.gov (source `census_tigerline_2025`), keeping incorporated places
  (class C) only. It replaces the TIGERweb map-service layers (`census_tigerweb_acs2025`).
- `src/lotline/dashboard/summarize.py`: uses `tiger_boundaries.cached`.
- Adapter provenance text now says TIGER/Line 2025; `docs/data_provenance.md` is regenerated.
- Tests: `tests/core/test_tiger_boundaries.py` (rewritten: a shapefile written by hand; the class filter;
  the cache); the TIGERweb test in `test_geo.py` is removed.

**What Claude did:**
- Worked stability-review finding 3 (2026-11-27). While checking it, TIGERweb was refusing every request
  from this machine ("Request Rejected", even the layer the adapter used). States without cached boundaries
  (OR, WI, any new state) could not fetch them.
- Downloaded the 12 TIGER/Line zips for MN, NC, OH, TX, WI and OR through the IO layer.
- Compared them with the cached TIGERweb polygons for MN, NC, OH and TX:
  - the place and township sets are identical;
  - of about 33,000 random points, 4 land differently, all on a boundary.

**Checked:** core and states tests pass; the fast tier passed before the wording changes; ruff clean;
compliance 0 FAIL. Processed tables built from the old polygons are unchanged until refetched.
