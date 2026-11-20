---
description: Research missing-middle (2-4 homes on single-family lots) local rules for one state with a two-coder agent swarm; writes a schema-valid reforms table and a human lookup sheet
argument-hint: "<STATE> [--limit N] [--only GEOID ...] [--jurisdictions CSV] [--skip-coded] [--min-pop N] [--single-coder | --both-coders] [--budget TOKENS] [--run RUN_ID] [--resume] [--browser]"
---

# /rules-mm — missing-middle rule swarm for one state

Arguments: `$ARGUMENTS`. What this is for and what it never does: `docs/build/rule-agents/PRINCIPLES.md`. Design: `docs/build/rule-agents/mm/DESIGN.md`; lessons: `LESSONS.md` (same folder).
You are the orchestrator. You run the deterministic steps yourself through
`uv run python -m lotline.rule_agents.mm …` and hand research to the subagents `rules-mm-scout`,
`rules-mm-coder`, `rules-mm-reconciler`, `rules-mm-verifier`. Shared tools (document store, passages,
spending ledger): `uv run python -m lotline.rule_agents …` (design: `docs/build/rule-agents/CORE.md`).

## Spending (keep token use down)

- Every place has a budget (default 250k tokens, 12 fetches, 8 searches; the Agent tool's token count
  includes everything an agent reads). With `--budget N`, save it once right after init:
  `uv run python -m lotline.rule_agents ledger limits <RUN> --tokens N`, so every agent's `ledger status`
  uses it. After each
  subagent returns, record (only you record tokens; agents record their fetches and searches) the tokens the Agent tool reports:
  `uv run python -m lotline.rule_agents ledger add <RUN> <GEOID> <agent> --tokens N`.
- Each agent also has its own share of the place's tokens (scout 60k, first coder 60k, second coder 50k, verifier/reconciler 30k, hand-off 20k, fees enumerator 30k; scaled to `--budget`), and the second coder's and reviewer's unspent shares are held back from the others, so an early agent cannot spend the check. Before starting a subagent for a place,
  `uv run python -m lotline.rule_agents ledger status <RUN> <GEOID> --agent <agent name>`;
  exit code 3 (`"stop": true`) means no more research on that place: take what is coded, turn every open
  field into a `budget_spent` blocker, and move on. If no coder has written a finding yet, you write
  `findings/<g>.coder-a.json` yourself: no rules, one `budget_spent` blocker per source the scout listed
  (its URL), so the place still gets hand-off tasks; it goes to step 6 as a single-coder place.
- Give subagents only `RUN`, `GEOID` and `COUNTY` (from `places.csv`) in their prompts; they read what they need.
- End the report with `uv run python -m lotline.rule_agents ledger summary <RUN>`.

## Never

- Edit `config/`, `src/`, `docs/` or any repo file during a run; outputs stay in the run folder; the user reviews
  the table and imports it (`docs/build/rule-agents/PRINCIPLES.md`).
- Run engine, scenario, calibration or model scripts; open permit/BPS data; write outcome numbers (holdouts).
- Fetch outside `python -m lotline.rule_agents.mm fetch` (store first, then polite network); retry a refusal another way; file records requests,
  send emails or fill forms; solve or bypass a challenge.

## Steps

0. **Setup check.** `uv run python -m lotline.rule_agents doctor <ST> --category mm`; stop and show the user
   what to fix if it does not say "Ready.".
1. **Init.** `uv run python -m lotline.rule_agents.mm init <ST> [--run RUN_ID]` → prints `RUN`. With `--resume`,
   reuse the existing run and skip places whose stage outputs exist. With `--budget N`, run `ledger limits`
   now (Spending).
2. **Places + brief.** `… places <RUN> [--limit N] [--only …] [--skip-coded] [--min-pop N]` (writes
   `places.csv` and `brief.md`; for a state with no jurisdictions table pass `--jurisdictions <csv>` with
   `geoid,name,pop_2020` (`county_geoid` if known)). Show the user the list and the brief's holdouts; if the brief says "No default recorded"
   for the effective-date rule, ask the user for the state's rule (one question) or proceed with "hand off when
   silent".
3. **Scout** each place (`rules-mm-scout`, prompt: `RUN=<RUN> GEOID=<g> COUNTY=<c>`), 4 at a time. The
   scout checks the document store first, so documents another swarm already fetched cost nothing.
4. **Code.** For each place start `rules-mm-coder` as coder **a** (prompt `RUN GEOID COUNTY coder=a`).
   **Second coder only where it matters** (it was ~40% of tokens in the dry runs):
   once a's file passes `check` (step 5), run `… select-b <RUN>` and start coder **b** (`model: opus`, a
   different tier from a; LESSONS S-4; prompt `RUN GEOID COUNTY coder=b`, never a's output) only for the
   places it lists: an **event** (a rule with `unit_cap` ≥ 2 not coded `predates`), any rule below `high`
   confidence, or the 10% audit sample. `--both-coders` runs b
   everywhere; `--single-coder` never.
5. **Check.** `… check <RUN>`. Re-run a coder once for a file that still fails; then move on (the place's
   remaining problems go into the report).
6. **Reconcile.** `… reconcile <RUN>`. Places with 0 diffs: write `final/<g>.json` yourself as
   `{"finding": <coder a's finding>, "coder_2": "rules-mm-coder-b (opus)", "agreement": "agree"}` with b's
   blockers appended. Places with diffs: `rules-mm-reconciler`. Places with no coder b (`--single-coder`, or
   not selected in step 4): copy a's finding with `"agreement": "single_coder"`, `"coder_2": null`.
7. **Verify** each final with `rules-mm-verifier`, then `… check <RUN>` again. Skip the verifier for a final
   with no rules (nothing to check; its blockers go straight to step 9), also when the budget stopped it.
8. **Browser check (only with `--browser`; may run unattended).** For priority-1 tasks from step 9's sheet, open
   each start URL in the built-in browser one page at a time; read; stop at any challenge, CAPTCHA or login and
   leave that task for the user. Record answers in `out/human-lookups.csv` with `checked_by = rules-mm-browser`,
   then `… ingest <RUN> <RUN>/out/human-lookups.csv` and re-run steps 4–7 for those places only.
9. **Build.** `… build <RUN>` (schema-valid `out/reforms_mm_<st>.csv`), `… handoff <RUN>`
   (`out/human-lookups.csv` + `.md`), `… compare <RUN>` (against `config/reforms/<st>.csv`).
10. **Report** `out/run-report.md`: places run; rules by `date_basis`; events (dated cap rises), none rows,
    always-allowed (`predates`) places, standards rows; agreement counts; every major diff and its decision;
    hand-off tasks by blocker kind; compare mismatches; problems still listed by `check`; places to check
    first (largest population with low confidence or a mismatch). Tell the user how to review and import the table: `uv run python -m lotline.rule_agents import
    <RUN>/out/reforms_mm_<st>.csv reforms <ST>` (preview), then `--yes`. Then tell the user, in plain words, what to
    decide: which rows to merge, which hand-offs to do first.

## When the user answers the hand-offs

`… ingest <RUN> <answers.csv>` refuses rows without a quote or with bad dates and saves the rest under
`answers/`. Re-run steps 4–9 with `--only` those places, giving the coder the answers file as extra evidence
(`source_kind: human_lookup`). Records-request-only sources are optional tasks: the user files the request or marks `no_usable_source`.
