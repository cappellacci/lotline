### LB-NNN · 2026-10-20 · Build: Parameter table refreshed and checked in CI
- **Question:** Does the Model & Assumptions parameter table stay in step with `config/params/`?
- **What I did:** Regenerated the table in `docs/model_and_assumptions.md` (it lacked the parameters added by #137: `tiers.yaml` and `min_eligible_parcels_publish`). Added two CI steps: `scripts/dev/params_table.py --check` (fails when the table is stale) and `ruff format --check .` (a formatting slip after a merge went unnoticed on 2026-10-19 because CI ran only `ruff check`).
- **Inputs:** Ben's approval (2026-10-19) to check the table in CI; #135, #137.
- **Outputs:** `docs/model_and_assumptions.md`, `.github/workflows/tests.yml`.
- **Findings:** none beyond the stale table.
- **Decisions:** none new.
- **AI:** Claude Code (WS-CORE) made the change; the check fails before regenerating and passes after.
- **Open / next:** none.
