### LB-NNN · 2026-11-17 · Build: WS-SCALE task 7, crosswalks in two formats
- **Question:** Can every code crosswalk use one of two headers, with no change to any adapter's output?
- **What I did:**
  - `src/lotline/adapters/crosswalks.py`: the two formats and one reader. It checks the header and that every
    standard value is in the schema vocabulary.
    - Land use: `field,code,description,land_use_std,notes,source_url`, plus optional `pattern`, `county`,
      `refine_by_units`, `confidence`, `applied`.
    - Building type: `field,code,description,building_type_std,role,derived_units,notes,source_url`.
  - Converted 16 files: 6 MN rule files, OR RLIS, OH DTE, TX TCAD, PTAD and county land use, and the Cary,
    Greensboro, Mecklenburg, Dallas and Fort Worth permit types.
  - Moved Ohio's county name list into `oh_aliases.csv`.
  - Switched the 13 readers to the shared reader.
- **Check:** all 18 loaders return the same rules and maps before and after, compared value for value.
  Every `land_use_std` and `building_type_std` is a pure function of those maps and the unchanged raw data,
  so the columns are unchanged row for row.
- **Outputs:**
  - `src/lotline/adapters/crosswalks.py`, `config/crosswalks/*.csv`, the adapters above;
  - `tests/core/test_crosswalks.py`: every file in the folder is in a format or a listed exception;
  - `docs/adding_a_state.md` steps 8-9.
- **Decisions:** none new.
  - Registries (`nc_land_use_counties.csv`, `mn_mngeo_counties.csv`, Wake towns) stay CSVs, because they are
    tables of counties with their own data, not yaml settings.
  - `or_metro_cities.csv` stays (a dev script reads it).
- **AI:** Claude wrote the reader, the conversion and the check.
- **Open / next:** hard-coded code→type dicts in adapters (Austin, Medford, Bend, Rochester, ...) can move
  into the building-type format later.
