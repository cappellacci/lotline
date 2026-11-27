### LB-NNN · 2026-11-27 · Build: the ADU net-new equation computed in one place
- **Question:** the code review of main @98b3f113 found ADU's homes-per-permit equation written three times
  (central path, every draw, the bundle), with only the central path tested. Dropping the formalization
  factor from the per-draw path would raise the ADU headline about 11% with no test failing. Can it live in
  one place, with a test on the path the bundle reads?
- **What I did:**
  - `net_new_homes(added, p)` in `scenarios/adu_params.py` computes added × adu_net_new_share ×
    (1 − adu_formalization_share).
  - `central_path`, every draw in `run`, and `bundle_adu` all call it. The bundle's per-draw share is
    `net_new_homes(1.0, p)`.
  - Kept the original multiplication order, so results are bit-identical.
  - New hand-worked test, `test_every_draw_turns_added_permits_into_homes_by_the_same_factor`: 0.5 × 0.8 = 0.4
    homes per permit in every draw and in the central path.
- **Decision:** Ben (2026-11-27, via the review thread) chose one helper plus a per-draw test.
- **Outputs:** `src/lotline/model/scenarios/adu_params.py`, `adu.py`, `bundle_adu.py`,
  `tests/model/test_scenario_adu.py`; PR (branch `ws/adu-net-new`).
- **AI:** Claude Opus 5.5 made the change. Checked three ways:
  - A mutation run: dropping the per-draw formalization factor now fails the new test.
  - MN bundle hashes on main and on the branch.
  - The non-slow tests.
