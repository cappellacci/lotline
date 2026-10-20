# Thread 3: Local demand index (WS-DATA-DEMAND)

**Goal:** a pre-period local labor-demand index per place (or county) and year for MN, NC, OH and TX, as the causal diagram's C04 control and modifier: a shift-share (Bartik) employment index from each area's pre-period industry mix.

**Read first:** `docs/research/lotline-causal-diagram.md` §3a (C04: "shift-share employment index from pre-period industry mix", E081); D-023 (the index replaces household growth as a modifier when available); `src/lotline/adapters/national/` (adapter patterns; the Census API key is already handled in `acs.py`).

**Data (public APIs, no scraping):**
- **Census County Business Patterns** (CBP; api.census.gov, employment by NAICS by county, annual): the pre-period industry shares, e.g. the 2010–2012 average.
- **National industry employment growth:** CBP national totals, or BLS CES/QCEW national series via FRED or the BLS public API (no key needed for small pulls). The census.gov rate limit in `io/http.py` applies.
- **County level** is the realistic resolution; map places to counties with `geoparts.county_shares` (places spanning counties are weighted).

**Deliver (one PR):**
1. Adapters `adapters/national/cbp.py` (and a national-growth source if not CBP) through the IO layer, with provenance.
2. `build/demand.py`: the Bartik index = Σ_industries (pre-period county share × national log employment growth, from the base year to t), by county-year, then mapped to places. Document leave-one-out (excluding the county's own employment from national growth) if feasible.
3. A processed table (`market_geo_year` column `demand_bartik`, or its own table; propose a contract change in an issue if it needs a schema change) and a schema entry.
4. Tests: a hand-worked two-industry example; leave-one-out on a synthetic set.

**Done when:** PR open with green CI and coverage (counties × years per state). No modelling; WS-ENGINE uses it in D-024/D-025.
