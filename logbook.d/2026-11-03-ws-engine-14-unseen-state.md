### LB-NNN · 2026-11-03 · engine · What range should θ carry into a state the model never saw?

- **Question:** Ben confirmed that a statewide θ is the goal, and asked how θ is calculated and how well it
  transfers to states with no ADUs. The answer: a new state needs no ADU data. But θ's current range
  (0.81–2.11 per 1,000) leaves out the state-to-state spread: alone, MN gives 1.25, NC 1.27, OH 2.34 and TX
  4.17.
- **Outputs:** D-043 in `docs/analysis_plan.md`. It is the method only, written before any fit:
  - a state multiplier with spread τ, estimated with θ and α;
  - an unseen-state draw shared by all of a state's places;
  - how τ combines with the extrapolation widening;
  - a leave-one-state-out validation;
  - a reading rule, with a fallback if τ can't be estimated.
- **Decisions:** none adopted. The method waits for Ben's approval. It must be run and decided before V8.
- **AI:** Claude Code (Opus 5.5) explained θ from `src/lotline/model/calibrate_adu.py` and
  `src/lotline/model/hazard.py` and drafted the entry. The numbers it cites were copied from D-041's results.
  No code was written and nothing was run.
