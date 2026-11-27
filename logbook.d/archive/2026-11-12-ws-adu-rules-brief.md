### LB-NNN · 2026-11-12 · `study-design` · Brief for coding ADU rule details in the fit places
- **Question:** the D-079 refit missed active cities and suburbs, and the coded rule details (by right, owner
  occupancy, parking) differ sharply between places, but many are blank. What research would let a model
  version fit a separate effect for each detail?
- **Decided by:** Ben, 2026-11-12 ("Let's write a markdown for an agent to research the uncoded cities").
- **Outputs:**
  - `docs/build/workstreams/WS-ADU-RULES.md`: the brief.
  - `docs/research/ordinances/adu-fit-rules-todo-2026-11-12.csv`: the worklist, 64 fit-set places plus St.
    Paul (rules only). Priorities: 46 / 18 / 1.
- **What Claude did and how it was checked:**
  - Built the worklist from `config/reforms/*.csv` and the D-079 fit set (`fit_set.csv`, #411).
  - Checked each place's coded ADU rows, rows in force by 2025, for blank rubric fields.
  - Took outcome numbers out of the brief, so the coding stays blind to which places the model misses.
- **Open:** run the workstream; Ben accepts proposed rows. A model version with rule-detail effects needs its
  own pre-registration.
