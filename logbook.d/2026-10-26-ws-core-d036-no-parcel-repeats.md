### LB-NNN · 2026-10-26 · Build: D-036, repeated project totals on permits with no parcel (#221)
- **Question:** how to count a multi-building project's repeated unit total once when the permit file has no
  parcel number (Fort Worth, Dallas), without cancelling out real rows of duplexes, fourplexes or identical
  apartment buildings.
- **What I did:**
  - Added a no-parcel branch to `lotline.build.permits.flag_repeated_totals` (used by `count_units`): group by
    jurisdiction, year, day (`issue_date`, else `application_date`) and the same 50+ unit count, 3+ permits;
    collapse only permits under 300 sq ft per unit or with no floor area, once on the lowest `permit_id`.
  - New parameter `repeated_total_max_sqft_per_unit` (300; 200–500) in `config/params/permits.yaml`, sourced to
    Ben's decision and the IBC/IRC minimum dwelling size; regenerated the params table.
  - Analysis-plan entry D-036 (amends D-008) with the Fort Worth and Dallas before/after tables from #221.
- **Inputs:** issue #221 and its comments (WS-TX measurements, Ben's decision); D-008.
- **Outputs:** `src/lotline/build/permits.py`, `config/params/permits.yaml`, `docs/model_and_assumptions.md`,
  `docs/analysis_plan.md` (D-036), `tests/core/test_build_permits.py`.
- **Findings:** the issue's before/after tables were measured without the area test; the final rule removes
  somewhat less (87–92% of grouped units fall under it). To re-measure on the Texas tables.
- **Decisions:** D-036 (Ben, 2026-10-26) recorded in the analysis plan; propose adding it to HANDOFF.
- **AI:** Claude Code (Opus 5.5) wrote the code, tests and entry. Checked with hand-worked synthetic tests
  (3 × 471 units at 8,036 sq ft → 471; 3 × 60 at 60,000 sq ft → 180; 10 × 4 → 40; mixed group; date fallback;
  demolitions; parameter switch; parcel rule unchanged) and the full test suite, ruff, compliance check and
  params-table check. No engine, scenario or dev-run scripts were run; no downloaded data was read.
- **Open / next:** WS-TX to re-measure Fort Worth and Dallas 5+ vs BPS with the final rule; decide whether an
  area-only rule should catch single or paired implausible permits.
