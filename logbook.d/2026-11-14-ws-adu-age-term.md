### LB-fragment · 2026-11-14 · ADU model · What would adding housing age, and rescoring on the checked rows, look like?

- **Outputs:** D-087 (proposed) in `docs/analysis_plan.md`, branch `ws/adu-age-term` (built on `ws/adu-owner-share`, #418).
- **Answer:** a method entry, written before any fit. Form A″ = D-084's Form A′ × exp(β_a z_age), with housing age
  standardized on D-083's 57 places (center 0.2045, scale 0.1669). Forms A, A′ and A″ are refitted on the rule rows
  after #419. The decision is two steps under D-084's rule: A′ against A, then A″ against the base in use.
- **HANDOFF:** proposes D-087 (provisional number); Ben to accept or amend.
- **What Claude did:** asked by Ben ("Draft it"); found D-084 already run (#418) and its outlook that age added
  nothing on the old rows, and wrote that evidence into the entry; fixed the center and scale from
  `reports/adu-covariate-screen/factors.csv`. Nothing fitted or scored.
