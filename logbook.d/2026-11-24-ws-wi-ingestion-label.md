### LB-NNN · 2026-11-24 · Build: Wisconsin on the app as a data-ingestion test; review handoff
- **Question:** how to show Wisconsin on the live app without presenting it as part of the model's core evidence.
- **What I did:**
  - Added a state role `ingestion_test` (schemas 1.23), shown in the picker as "Data-ingestion test (not core)".
  - The Results page for such a state opens with a note: national data only, added to test bringing in a new state;
    its frozen V8 forecast came in about a third below the permits counted for 2021–2025 (`reports/wi/V8-score.md`);
    the miss led to the baseline fix every state now uses (`benchmark_levels`, #512); shown for transparency.
  - Replaced the ADU no-price filter in `results.build_bundle` with an error. `place_inputs` fills missing prices
    with the state median, so the filter dropped nothing; a gap now means the stored table needs a rebuild.
  - Wrote `docs/build/handoffs/17-code-review-and-cleanup.md` for the next thread.
- **Inputs:** `reports/wi/V8-score.md` (already unblinded totals; nothing rescored).
- **Outputs:** `src/lotline/schemas.py`, `src/lotline/app/build.py`, `src/lotline/app/template.html`,
  `src/lotline/cli.py`, `src/lotline/model/results.py`, `docs/schemas.md`, `tests/app/test_build.py`,
  `docs/build/handoffs/17-code-review-and-cleanup.md`.
- **Findings:** no model result changes.
- **Decisions:** Wisconsin is shown under its own role, not as a development or transfer state (Ben, 2026-11-24).
- **AI:** Claude Opus 5.5 wrote the code, note and handoff; checked with the full test suite, ruff and the compliance
  check, and on the published page.
- **Open / next:** Thread 17 (code review and cleanup).
