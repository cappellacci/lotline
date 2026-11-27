### LB-NNN · 2026-11-14 · ADU model · Recompute the anchor's draw terms for Form A + place types

- **Question:** the engine's θ and α draws shift with the judgment parameters, using slopes computed for D-053's
  fit. Ben asked for them to be recomputed for the D-088 fit ("Recompute slopes").
- **Outputs:**
  - `scripts/dev/adu_types_slopes.py`;
  - `config/params/adu_anchor.yaml`, regenerated;
  - the information terms removed from `adu_place_types.yaml`, and the override in `scenarios.adu.anchor_terms`
    dropped;
  - `reports/adu-types-slopes/`;
  - a note under D-089 in `docs/analysis_plan.md`;
  - page https://claude.ai/artifact/FiiNrCDR2gxt3q8FBjtRnZ.
- **Result:**
  - θ slopes are close to D-053's and α slopes are about half.
  - The core term's slopes are negligible.
  - Statewide additional homes move by at most 3.4% at P50 and 5.7% at P90.
- **What Claude did:**
  - wrote the script and ran it offline;
  - reran it from the start after a laptop restart cut off the first attempt;
  - reran the statewide engine check.
- **How it was checked:**
  - the central refit reproduces D-088 exactly;
  - each θ and α slope was compared with D-053's;
  - the engine totals were compared run against run;
  - the full test suite and `compliance_check.py`.
