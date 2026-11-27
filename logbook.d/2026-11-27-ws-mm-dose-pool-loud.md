### LB-NNN · 2026-11-27 · Missing middle · Empty dose pool raises; Pencils stage tested

- **Question:** Does the missing-middle scenario fail loudly when an uncoded place has no dose pool to draw
  from, and does a test prove the funnel's Pencils stage uses the feasible share F(PCR)?
- **Outputs:**
  - `src/lotline/model/scenarios/mm.py`: `simulate` raises `ValueError` when an uncoded place meets an
    empty dose pool. Before this it drew dose 0, which counts every eligible lot as newly legal.
  - `tests/model/test_scenario_mm.py`: hand-worked tests for the raise. There are also two Pencils tests:
    300 + 100 = 400 with `f_share`, and the `f_ratio` fallback, 900. Swapping `f_share` for `f_ratio` now
    fails the suite. Before, it passed.
- **Decision:** Ben, 2026-11-27: "Raise an error" (the review of main@98b3f113 flagged both items).
- **What Claude did and how it was checked:** wrote the change and the tests. A mutation check showed the
  Pencils test catches the swap. The six states' results bundles hash the same as on `main`, so no state hits
  the new error. The non-slow suite and compliance pass.
