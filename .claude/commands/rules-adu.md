---
description: Run the ADU rule agent swarm for one state and propose `reforms` rows plus a human lookup list
argument-hint: "<ST> [--places N | --geoids g1,g2] [--run-id id] [--no-second-coder] [--skip-state-law] [--compare]"
---

# /rules-adu — ADU rule agent swarm (orchestrator)

Arguments: `$ARGUMENTS`. Design: `docs/build/rule-agents/adu/DESIGN.md`. Binding coding rules:
`docs/build/rule-agents/adu/CODING_RULES.md`. You (the main session) orchestrate: you run helpers, launch
agents, enforce budgets and stop rules, and write the report. You never code values yourself.

## 0. Set up

- Parse: state `ST` (two letters, required); `--places N` (default 10, largest first, population >= 2,500)
  or `--geoids`; `--run-id` (default `<YYYY-MM-DD>-<HHMM>`); `--no-second-coder` (D-088: cheaper; all rows
  `single_coder`); `--skip-state-law` (reuse a run's `state_law.json`); `--compare` (dry run: compare with
  `config/reforms/<st>.csv` at the end).
- `RUN_DIR=$(uv run python -m lotline.rule_agents.adu run-dir --state ST --run-id ID)`.
- `uv run python -m lotline.rule_agents.adu worklist --state ST --run-id ID [--limit N | --geoids ...]`.
  It prints the blind holdouts: pass them to every agent. If the jurisdictions table is missing, stop and say
  which build step makes it.
- Never run engine, scenario, calibration or dev-run scripts. Never edit `config/`. Never download data except
  through the fetch helper (it writes under `LOTLINE_DATA_DIR`).

## 1. State law

Unless skipped, launch `rules-adu-state-law` with `STATE`, `RUN_DIR`. For each enacted law, expand coverage
with `places.covered_by_state_law` (a short `uv run python -c`) and list near-threshold places for the human
list. State-law rows are one per covered place (never one statewide row; `adoption_date` blank when the
enrolled text has no signature date) and go to `RUN_DIR/state_law_rows.csv` through the same schema check.

## 2. Scout, then code

Batch places in groups of about five. In one message, launch `rules-adu-scout` for every batch (brief:
`STATE`, `RUN_DIR`, the places' rows from `places.csv`, holdouts). When all return, in one message launch
`rules-adu-coder` (coder id `claude-rules-adu`) and, unless `--no-second-coder`, `rules-adu-second-coder`
(coder id `claude-rules-adu-blind`) for every batch. Give the second coder only the `sources/` and
`state_law.json` paths, never `coding_a/`.

## 3. Check

`uv run python -m lotline.rule_agents.adu check RUN_DIR/coding_a/*.json RUN_DIR/coding_b/*.json`. Send each
failing file back to its agent once (SendMessage with the problems). A file that fails again is kept as
`partial` with the failing fields blanked; say so in the report.

## 4. Verify and merge

Launch `rules-adu-verifier` per batch. With `--no-second-coder`, run `verify-quotes` on coding_a and `merge`
with coding_a as both inputs (rows come out `single_coder`). Each place gets `final/<g>.json` and
`final/<g>.meta`.

## 5. Rows

`uv run python -m lotline.rule_agents.adu rows RUN_DIR/final/*.json --out RUN_DIR/rows.csv`. A schema error
stops the run: fix the coding, not the row.

## 6. Human list

Launch `rules-adu-handoff` with `RUN_DIR`. It produces `tasks.csv` and `tasks.md`.

## 7. Report

Write `RUN_DIR/report.md`: places run; per place outcome, eras, rows and `coder_agreement`; blank core
fields; values by confidence; blocks by reason and host; open human tasks with total minutes; any holdout or
process incident. With `--compare`, run
`uv run python -m lotline.rule_agents.adu compare --state ST --rows RUN_DIR/rows.csv > RUN_DIR/compare.txt`
and summarise matches and differences, naming the source each side cites.

Tell Ben in plain words: where the files are, how many rows are ready, how many lookups wait for him (and
how long they take), and every judgment call the agents left for him. Rows enter `config/` only after Ben
accepts them, through a dated script in `scripts/dev/`.
