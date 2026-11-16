### LB-NNN · 2026-11-14 · ADU model · Run the scenario engine on Form A + place types

- **Question:** Ben asked for the core-city term and the town prior to be wired into the scenario engine
  ("Wire it here"). What changes when the engine runs the model he chose in D-088?
- **Outputs:**
  - code: `src/lotline/model/scenarios/adu.py` (`type_terms`, `type_log_multipliers`,
    `central_type_log_multiplier`, a `place_type` column from `places_from_store`, type multipliers in `run`
    and `central_path`, and `anchor_terms` reading the new fit's information terms);
  - typing code moved from the D-088 script into `src/lotline/model/adu_types.py` (`units_table`,
    `raw_types`, `jurisdiction_types`);
  - config: `hazard.yaml` (θ, α), `adu.yaml` (m_o, m_x), `adu_place_types.yaml` (duplicates removed),
    and a header note in `adu_anchor.yaml`;
  - tests in `tests/model/test_scenario_adu.py` and `tests/model/test_adu_types.py`;
  - runs: `scripts/dev/adu_types_engine_check.py` and `scripts/dev/adu_types_engine_page.py`, with results
    in `reports/adu-types-engine/` and the page https://claude.ai/artifact/Wn5ktV2Hvo26TQdTEseNci;
  - an Engine note under D-089 in `docs/analysis_plan.md`.
- **Result:**
  - Additional homes at P50 rise in four states: MN 286 → 634, NC 139 → 575, OH 236 → 422,
    TX 1,902 → 4,809. Oregon barely moves (26 → 29).
  - The ranges widen.
  - The split varies by state. Types and the new anchor make most of the rise in OH and TX; partial rules at
    m_x 0.4 make most of it in MN and NC.
  - Two approximations remain: the anchor slopes are still D-053's, and θ's width still comes from the
    profile interval.
- **What Claude did:**
  - wrote the engine code, the tests, the check and page scripts, and the notes;
  - ran the engine offline before and after the switch, plus an m_x = 1.0 run to split the change.
- **How it was checked:**
  - the moved typing code reproduces all 3,633 saved jurisdiction types and all 64 fit places;
  - hand-worked tests: a core city's hazard is 3 × a suburb's at a ×3 term, and a place with no type runs
    exactly as a suburb;
  - the multiplier draws' means and SDs match config;
  - the page's claims were checked against the run tables, and three were corrected before publishing;
  - the full test suite and `compliance_check.py`.
