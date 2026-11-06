## LB-xxx · 2026-11-06 · WS-ENGINE · Housing-need denominators and the "% of need" output

**Question answered:** What does each state's five-year result get compared with, so a policymaker reads "x% of the homes the state expects to need" or "x% of the state's estimated shortage", and where do those numbers come from?

**Outputs**
- `config/params/housing_need.yaml` (generated): `household_growth_5y_<st>` for MN, NC, TX, OH, OR and `shortage_stock_<st>` for 50 states and DC, each with source URL, vintage and kind.
- `scripts/dev/housing_need.py`: builds it from Up for Growth 2024, Freddie Mac Feb 2020, five state demographers' population projections and ACS (households per person 2020–2024; housing units 2014–2018).
- `src/lotline/model/aggregate.py`: `share_of_need`, `headline_kind`; every share carries `denominator_kind` and its label.
- `tests/model/test_aggregate_need.py`: hand-worked shares and the config's reading rules.
- `docs/analysis_plan.md` D-057: two dated deviations from the brief; `docs/research/lotline-evidence-register.csv` E114 (CRS IN12628).

**Decisions proposed for HANDOFF**
- D-057: household growth is derived (population × constant headship) because no state demographer publishes households; Ohio's falling projection sends its headline to the shortage.
- D-057: the shortage uses Up for Growth as the value and Freddie Mac 2020 % × ACS stock as the second estimate (Zillow has no state figures); no range where Freddie shows no deficit.

**What Claude did and how it was checked:** Claude Code (Opus 5.5, WS-ENGINE instance) had a research subagent find the published figures and URLs, put the two missing-source problems to Ben (he chose both options), then wrote the generator, module and tests. Checked by hand-worked unit tests, the 51 Up for Growth rows summing to its published 3.85M, Freddie's California share × ACS stock (808k vs the Insight's ~820k), the full suite, ruff and `compliance_check.py`. Not checked by a person: the transcribed Freddie Mac map labels and demographer totals against their source files.
