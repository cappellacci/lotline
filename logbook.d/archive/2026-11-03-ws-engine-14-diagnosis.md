### LB-NNN · 2026-11-03 · engine · Why does the ADU anchor miss? (exploratory, after D-040)

- **Question:** before adding modifiers, what drives the D-039/D-040 misses?
- **Outputs:** `reports/adu-statewide/diagnosis-2026-11-03.md`, `reports/adu-statewide/diagnose_places.py`.
- **Findings:**
  - 66% of Austin's "secondary apartments" are co-built with a new house. Without them, Austin's rate is
    0.72 per 1,000 a year, in line with Raleigh and Durham.
  - Met Council records about half of Minneapolis's own ADU permits.
  - The pro forma market term correlates negatively with observed rates across places.
  - Rule age and rule type add little.
- **What Claude did and how it was checked:** read-only queries of the permit tables and the D-039 fit; no
  fit, no config change. Every grouping is labelled post hoc.
