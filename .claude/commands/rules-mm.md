---
description: Research missing-middle (2-4 homes on single-family lots) local rules for one state with a two-coder agent swarm; writes a schema-valid reforms table and a human lookup sheet
argument-hint: "<STATE> [--limit N] [--only GEOID ...] [--skip-coded] [--min-pop N] [--single-coder] [--run RUN_ID] [--resume] [--browser]"
---

# /rules-mm — missing-middle rule swarm for one state

Arguments: `$ARGUMENTS`. Design: `docs/build/rule-agents/mm/DESIGN.md`; lessons: `LESSONS.md` (same folder).
You are the orchestrator. You run the deterministic steps yourself through
`uv run python -m lotline.rule_agents.mm …` and hand research to the subagents `rules-mm-scout`,
`rules-mm-coder`, `rules-mm-reconciler`, `rules-mm-verifier`.

## Never

- Edit `config/`, `src/`, `docs/` or any repo file during a run; outputs stay in the run folder (Ben merges).
- Run engine, scenario, calibration or model scripts; open permit/BPS data; write outcome numbers (holdouts).
- Fetch outside `python -m lotline.rule_agents.mm fetch`; retry a refusal another way; file records requests,
  send emails or fill forms; solve or bypass a challenge.

## Steps

1. **Init.** `uv run python -m lotline.rule_agents.mm init <ST> [--run RUN_ID]` → prints `RUN`. With `--resume`,
   reuse the existing run and skip places whose stage outputs exist.
2. **Places + brief.** `… places <RUN> [--limit N] [--only …] [--skip-coded] [--min-pop N]` (writes
   `places.csv` and `brief.md`; for a state with no jurisdictions table pass `--jurisdictions <csv>` with
   `geoid,name,pop_2020`). Show Ben the list and the brief's holdouts; if the brief says "No default recorded"
   for the effective-date rule, ask Ben for the state's rule (one question) or proceed with "hand off when
   silent".
3. **Scout** each place (`rules-mm-scout`, prompt: `RUN=<RUN> GEOID=<g>`), 4 at a time.
4. **Code.** For each place start `rules-mm-coder` as coder **a** (prompt `RUN GEOID coder=a`). Unless
   `--single-coder`, also start coder **b** with `model: opus` (a different tier from a; LESSONS S-4) and the
   prompt `RUN GEOID coder=b` — never paste coder a's output into b's prompt. Run a and b in parallel.
5. **Check.** `… check <RUN>`. Re-run a coder once for a file that still fails; then move on (the place's
   remaining problems go into the report).
6. **Reconcile.** `… reconcile <RUN>`. Places with 0 diffs: write `final/<g>.json` yourself as
   `{"finding": <coder a's finding>, "coder_2": "rules-mm-coder-b (opus)", "agreement": "agree"}` with b's
   blockers appended. Places with diffs: `rules-mm-reconciler`. With `--single-coder`: copy a's finding with
   `"agreement": "single_coder"`, `"coder_2": null`.
7. **Verify** each final with `rules-mm-verifier`, then `… check <RUN>` again.
8. **Browser check (only with `--browser` and Ben present).** For priority-1 tasks from step 9's sheet, open
   each start URL in the built-in browser one page at a time; read; stop at any challenge, CAPTCHA or login and
   leave that task for Ben. Record answers in `out/human-lookups.csv` with `checked_by = rules-mm-browser`,
   then `… ingest <RUN> <RUN>/out/human-lookups.csv` and re-run steps 4–7 for those places only.
9. **Build.** `… build <RUN>` (schema-valid `out/reforms_mm_<st>.csv`), `… handoff <RUN>`
   (`out/human-lookups.csv` + `.md`), `… compare <RUN>` (against `config/reforms/<st>.csv`).
10. **Report** `out/run-report.md`: places run; rules by `date_basis`; events (dated cap rises), none rows,
    always-allowed (`predates`) places, standards rows; agreement counts; every major diff and its decision;
    hand-off tasks by blocker kind; compare mismatches; problems still listed by `check`; places to check
    first (largest population with low confidence or a mismatch). Then tell Ben, in plain words, what to
    decide: which rows to merge, which hand-offs to do first.

## When Ben answers the hand-offs

`… ingest <RUN> <answers.csv>` refuses rows without a quote or with bad dates and saves the rest under
`answers/`. Re-run steps 4–9 with `--only` those places, giving the coder the answers file as extra evidence
(`source_kind: human_lookup`). Records-request-only sources close as `no_usable_source`.
