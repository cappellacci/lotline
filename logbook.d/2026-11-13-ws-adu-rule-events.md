### LB-NNN · 2026-11-13 · ADU model · How do we get enough rule-change events to test how much a reform moves uptake? (D-086 proposed)

- **Question:** Ben asked to try more rule-change events ("Cool let's try both of those"). D-079's rule-change
  term needs 8 events in 3 states and has 5 in 2. Where can more come from, and how are they coded honestly?
- **Outputs:** D-086 (proposed) in `docs/analysis_plan.md`, on `ws/adu-rule-events`.
- **What Claude did and how it was checked:**
  - Counted inputs only: 26 fit places have permit files covering years before their first coded ADU row
    (MN 20, NC 4, OH 1, TX 1). No ADU count was read.
  - Found that first adoptions cannot identify the term (Form A has no count without a rule). So D-086 codes
    each fit place's rule history from public ordinance sources, blind to counts, with a second coder on every
    row that makes an event, and keeps D-079's event definition and bar.
  - Nothing coded or fitted yet; waits for Ben to accept.
