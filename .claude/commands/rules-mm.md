---
description: Research missing-middle (2-4 homes on single-family lots) local rules for one state with a two-coder agent swarm; writes a schema-valid reforms table and a human lookup sheet
argument-hint: "<STATE> [--limit N] [--only GEOID ...] [--skip-coded] [--min-pop N] [--single-coder | --both-coders] [--budget TOKENS] [--run RUN_ID] [--resume] [--browser]"
---

# /rules-mm — missing-middle rule swarm for one state

Arguments: `$ARGUMENTS`. **Read `docs/build/rule-agents/GUARDRAILS.md` first; it overrides this file.**
Design: `docs/build/rule-agents/mm/DESIGN.md`; lessons: `LESSONS.md` (same folder).
You are the orchestrator. You run the deterministic steps yourself through
`uv run python -m lotline.rule_agents.mm …` and hand research to the subagents `rules-mm-scout`,
`rules-mm-coder`, `rules-mm-reconciler`, `rules-mm-verifier`. Shared tools (document store, passages,
spending ledger): `uv run python -m lotline.rule_agents …` (design: `docs/build/rule-agents/CORE.md`).

## Spending (Ben, 2026-11-17: keep token use down)

- Every place has a budget (default 120k tokens, 12 fetches, 8 searches; `--budget` sets tokens). After each
  subagent returns, record the tokens the Agent tool reports:
  `uv run python -m lotline.rule_agents ledger add <RUN> <GEOID> <agent> --tokens N`.
- Before starting a subagent for a place, `uv run python -m lotline.rule_agents ledger status <RUN> <GEOID>`;
  exit code 3 (`"stop": true`) means no more research on that place: take what is coded, turn every open
  field into a `budget_spent` blocker, and move on.
- Give subagents only `RUN`, `GEOID` and `COUNTY` (from `places.csv`) in their prompts; they read what they need.
- End the report with `uv run python -m lotline.rule_agents ledger summary <RUN>`.

## Never

- Edit `config/`, `src/`, `docs/` or any repo file during a run; outputs stay in the run folder and go to the
  missing-middle model's owner ("Missing Middle Analysis refresh" session) through a reviewed PR.
- Recommend a model rate or parameter ("use X%"): outside studies are checks, never inputs (D-037).
- Run engine, scenario, calibration or model scripts; open permit/BPS data; write outcome numbers (holdouts).
- Fetch outside `python -m lotline.rule_agents.mm fetch` (store first, then polite network); retry a refusal another way; file records requests,
  send emails or fill forms; solve or bypass a challenge.

## Steps

1. **Init.** `uv run python -m lotline.rule_agents.mm init <ST> [--run RUN_ID]` → prints `RUN`. With `--resume`,
   reuse the existing run and skip places whose stage outputs exist.
2. **Start from what exists.** Read the MM notes in `docs/research/` (`mm-uptake-evidence.md`,
   `lotline-causal-diagram-mm.md`, the state's `ordinances/` sheets) and the `HANDOFF.md` decisions log; carry
   into the brief only rules and dates-of-law context (state preemption dates, the effective-date default),
   never existing coded values (coders stay blind).
3. **Places + brief.** `… places <RUN> [--limit N] [--only …] [--skip-coded] [--min-pop N]` (writes
   `places.csv` and `brief.md`; for a state with no jurisdictions table pass `--jurisdictions <csv>` with
   `geoid,name,pop_2020`). Show Ben the list and the brief's holdouts; if the brief says "No default recorded"
   for the effective-date rule, ask Ben for the state's rule (one question) or proceed with "hand off when
   silent".
4. **Scout** each place (`rules-mm-scout`, prompt: `RUN=<RUN> GEOID=<g> COUNTY=<c>`), 4 at a time. The
   scout checks the document store first, so documents another swarm already fetched cost nothing.
5. **Code.** For each place start `rules-mm-coder` as coder **a** (prompt `RUN GEOID COUNTY coder=a`).
   **Second coder only where it matters** (the ADU rule Ben approved 2026-11-17; it was ~40% of tokens):
   once a's file passes `check` (step 6), run `… select-b <RUN>` and start coder **b** (`model: opus`, a
   different tier from a; LESSONS S-4; prompt `RUN GEOID COUNTY coder=b`, never a's output) only for the
   places it lists: an **event** (a rule with `unit_cap` ≥ 2 not coded `predates`), any rule below `high`
   confidence, or the 10% audit sample. `--both-coders` runs b
   everywhere; `--single-coder` never.
6. **Check.** `… check <RUN>`. Re-run a coder once for a file that still fails; then move on (the place's
   remaining problems go into the report).
7. **Reconcile.** `… reconcile <RUN>`. Places with 0 diffs: write `final/<g>.json` yourself as
   `{"finding": <coder a's finding>, "coder_2": "rules-mm-coder-b (opus)", "agreement": "agree"}` with b's
   blockers appended. Places with diffs: `rules-mm-reconciler`. Places with no coder b (`--single-coder`, or
   not selected in step 5): copy a's finding with `"agreement": "single_coder"`, `"coder_2": null`.
8. **Verify** each final with `rules-mm-verifier`, then `… check <RUN>` again.
9. **Browser check (only with `--browser`; may run unattended).** For priority-1 tasks from step 10's sheet, open
   each start URL in the built-in browser one page at a time; read; stop at any challenge, CAPTCHA or login and
   leave that task for Ben. Record answers in `out/human-lookups.csv` with `checked_by = rules-mm-browser`,
   then `… ingest <RUN> <RUN>/out/human-lookups.csv` and re-run steps 5–8 for those places only.
10. **Build.** `… build <RUN>` (schema-valid `out/reforms_mm_<st>.csv`), `… handoff <RUN>`
   (`out/human-lookups.csv` + `.md`), `… compare <RUN>` (against `config/reforms/<st>.csv`).
11. **Report** `out/run-report.md`: places run; rules by `date_basis`; events (dated cap rises), none rows,
    always-allowed (`predates`) places, standards rows; agreement counts; every major diff and its decision;
    hand-off tasks by blocker kind; compare mismatches; problems still listed by `check`; places to check
    first (largest population with low confidence or a mismatch). Then tell Ben, in plain words, what to
    decide: which rows to merge, which hand-offs to do first.

## When Ben answers the hand-offs

`… ingest <RUN> <answers.csv>` refuses rows without a quote or with bad dates and saves the rest under
`answers/`. Re-run steps 5–10 with `--only` those places, giving the coder the answers file as extra evidence
(`source_kind: human_lookup`). Records-request-only sources close as `no_usable_source`.
