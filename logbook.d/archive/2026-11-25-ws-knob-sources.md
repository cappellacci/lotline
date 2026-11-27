### LB-NNN · 2026-11-25 · Review · Sliders cite missing middle's own parameters

- **Question:** Why does a slider's source list show ADU parameters (or nothing) while it moves missing middle?
- **Outputs:** `src/lotline/app/knobs.yaml` (a `missing_middle` entry on all five sliders).
- **Decision:** Ben, 2026-11-25 (overnight): "go with your suggested order"; item 6, citation half. The slider range
  itself (P5/P95 instead of the lowest and highest run) is a design choice left for Ben.
- **What Claude did and how it was checked:** Claude Code mapped each missing-middle factor in `results.mm_draws` to
  the config parameters behind it (uptake: mature rate, ramp, units per project; pays-off: hard cost and feasibility
  spread; completion: multifamily; net-new: teardown scale; displacement). `build.knobs()` resolves every key (an
  unknown key raises); app tests pass.
