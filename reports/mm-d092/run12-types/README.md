# D-092 deviation (c), run 12: one φ against φ by place type (2026-11-15)

**What this is:** the pre-registered test of place types for missing middle. Types use ADU D-088's rule: core
city, suburb or town, from housing units and OMB areas. The test asks whether each type needs its own
lumpiness φ.

- **Go-ahead:** Ben, 2026-11-15, "Yes, run it".
- **Command:**

  ```bash
  uv run python scripts/dev/mm_types_d092.py --out reports/mm-d092/run12-types
  ```

  It ran on cached tables only. St. Paul and Ramsey are not in the panel, and nothing was unblinded.
- **Nothing was written to config.**

## Result: φ by type is not adopted

| | One φ (Y1) | φ by type (YT) |
|---|---:|---:|
| φ fitted on 2016 | 9.13 | core 8.14 · suburb 11.66 · town 4.17 |
| Held-out log score on 2021 (468 places) | 12,231.1 | 12,255.9 |
| **YT − Y1** | | **+24.8 (paired SE 32.9)**, against a bar of > 2 SE |
| 2021 coverage, P10–P90 | 0.79 | 0.78 |

The rule keeps one φ, so **the refit and §7 rerun are not done**. Run 11's results stand.

## Reported, never selected

- **φ on both origins:**
  - town 5.9 (5.2–6.8);
  - core city 15.8 (13.9–18.2);
  - suburb 16.3 (15.1–17.7);
  - one φ: 13.6.
- **2021 coverage by type, one φ against φ by type:**
  - core 0.70 against 0.70 (40 places);
  - suburb 0.79 against 0.80 (330);
  - town 0.83 against 0.77 (98).
- **φ by state and type, both origins:**

  | | core | suburb | town |
  |---|---:|---:|---:|
  | MN | 8.3 | 9.3 | 3.8 |
  | NC | 6.6 | 11.8 | 5.7 |
  | OH | 3.1 | 12.4 | 4.9 |
  | TX | 20.1 (edge) | 20.1 (edge) | 8.3 |

  "Edge" means the estimate reached the search's upper limit.

## What it says

1. **The guess was half wrong.**
   - Towns are the least lumpy, not the most.
   - Core cities and suburbs are about equally lumpy.
   - Within every state, suburbs are lumpier than towns.
2. **The type difference doesn't predict well out of sample.** Fitted on 2016, φ by type scores better on 2021,
   but by less than one standard error. Coverage doesn't move.
3. **State differs more than type.** Texas's φ hits the search's edge for both core cities and suburbs. In the
   other three states, φ is 3–12. A state term won't carry to a new state, so it isn't a candidate (deviation (c)).
4. **So place types don't narrow missing middle's ranges.** The reform rate can't take a type term either,
   because the fit places are almost all Oregon. For missing middle, types are recorded and coded, and not used.

## What this means for the next step (for Ben; not done)

- **Counting projects instead of buildings** is the remaining lever. Texas's lumpiness, at the edge, points to
  large multi-building projects: the noise is in the unit counted.
- The type table and the `--phi-by-type` option stay in the code. A later run can pick them up if a project
  count changes the picture.
