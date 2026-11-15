### LB-NNN · 2026-11-14 · ADU model · What has been tried for the five-state ADU fit, and what worked?

- **Question:** Ben asked for a short handoff for his ADU thread, covering what was tried and what worked, in
  case it helps find a better way.
- **Outputs:**
  - `docs/build/handoffs/16-adu-model-what-we-tried.md`;
  - a row in `docs/build/handoffs/README.md`.
- **Result:**
  - One table covers D-079 to D-090 and the engine switch.
  - The lessons: a coarse national place type is the only change that passed held-out scoring. Extra place
    covariates and time terms didn't. A place's own recent rate beats every model form on the places with
    counts.
  - Four ideas for a better way: forecast from own history plus drift where counts exist, add a drift term,
    find counts for cheap suburbs on open portals, and look at counting source.
- **What Claude did:** wrote the summary from the analysis-plan entries and the PR summaries.
- **How it was checked:**
  - each number was checked against its D-entry or PR body;
  - two first-draft claims were corrected: α's range across fit sets, and the engine-switch split by state.
