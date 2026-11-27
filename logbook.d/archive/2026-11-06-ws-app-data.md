## LB-xxx · 2026-11-06 · WS-APP · App section 2 (The data): tier badge, available vs used, data dashboard embedded

**Question answered:** Can a reader of the app see what each state's estimate is built on (Rules §8, "data available vs. used") without leaving the page or needing a server?

**Outputs**
- `src/lotline/app/build.py`:
  - `sources_table` and `data_section`. *Available* is every source the registry runs for the state, with its title, link and canonical table. *Used*, for parcel rolls, is taken from the data dashboard summary: the parcels each source supplies after the one-source-per-place rule.
  - `build_app(data_summary=...)` embeds the data dashboard's own page (`lotline.dashboard.render`) as a JSON string. The page loads it into a frame only when the reader opens it.
- `scripts/build_app.py`: `--data-summary` (default `reports/data_dashboard/summary.json`, skipped if missing) and `--no-data-summary`.
- Section 2 of `src/lotline/app/template.html`:
  - the data tier badge (tier colour + words) and the proxy caveat
  - coverage tiles: population covered, jurisdictions, parcels, reforms, permit years; exact counts, not rounded
  - jurisdictions by tier
  - the available-vs-used table
  - a button that opens the full data dashboard
  - without a summary, the page says which command builds it
- `tests/app/test_build.py`: available = the registry's list; used comes from the summary; sources are still listed without a summary; the dashboard is embedded when a summary exists and is null otherwise.

**What Claude did and how it was checked:** Claude Code (Opus 5.5, WS-APP instance) wrote the code and tests. Checked by `tests/app` (23 passed), ruff and `compliance_check.py`. A local build used the fixture bundle relabelled as MN together with the real data dashboard summary, kept in the scratchpad and never committed. In a browser it showed the coverage tiles and the sources table, and the embedded dashboard opened and drew its 15 charts. Non-parcel sources are marked "available" only, because the bundle does not yet record which sources each scenario read.
