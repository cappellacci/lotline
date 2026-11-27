## LB-xxx · 2026-11-06 · WS-APP · The data tab opens with a summary of what was gathered

**Question answered:** Ben (2026-11-06): the data tab's opening line ("What the estimate is built on: ...") should be a summary of what was gathered and why.

**Outputs**
- `src/lotline/app/build.py`: `overall()` sums the data dashboard summary across states: states, coded rules, places with a coded rule, parcels and permit years.
- `src/lotline/app/template.html`: the data tab's lead sentence is now built from those totals. With today's five-state summary it reads: "We pulled in data from five states, looked up and coded 915 local zoning and housing rules in 327 cities and towns, assessed 23.1 million parcels, and read building permits from 1992 to 2025, to measure and compare how housing reforms have actually performed." Without a summary, a general sentence stands in.
- `tests/app/test_build.py`: `overall()` sums across states by hand, and the result is embedded.

**What Claude did and how it was checked:** Claude Code (Opus 5.5, WS-APP instance) wrote it from Ben's draft wording. "Coded reforms" was changed to "coded ... rules" because the coded entries include moratoriums and fee rules as well as reforms. Checked by `tests/app` (29 passed) and `compliance_check.py`, and by reading the sentence on a page built from the real summary.
