---
description: Run the ADU rule agent swarm for one state and propose `reforms` rows plus a human lookup list
argument-hint: "<ST> [--places N | --geoids g1,g2] [--run-id id] [--second-coder targeted|full|off] [--audit-rate 0.1] [--skip-state-law] [--compare]"
---

# /rules-adu — ADU rule agent swarm (orchestrator)

Arguments: `$ARGUMENTS`. Design: `docs/build/rule-agents/adu/DESIGN.md`. Binding coding rules:
`docs/build/rule-agents/adu/CODING_RULES.md`. You (the main session) orchestrate: you run helpers, launch
agents, enforce budgets and stop rules, and write the report. You never code values yourself.

## 0. Set up

- Parse: state `ST` (two letters, required); `--places N` (default 10, largest first, population >= 2,500)
  or `--geoids`; `--run-id` (default `<YYYY-MM-DD>-<HHMM>`); `--second-coder` (default `targeted`: a blind second
  look only at values the first pass scored weak, plus a full second coding of a fixed ~10% audit sample;
  `full`: every place, as in the NC dry run; `off`: none, all rows `single_coder`); `--audit-rate` (default
  0.1; 0 turns the audit sample off); `--skip-state-law` (reuse a run's `state_law.json`); `--compare` (dry run: compare with
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

## 2. Scout, then first coder

Batch places in groups of about five. In one message, launch `rules-adu-scout` for every batch (brief:
`STATE`, `RUN_DIR`, the places' rows from `places.csv`, holdouts). When all return, in one message launch
`rules-adu-coder` (coder id `claude-rules-adu`) for every batch.

## 3. Check and score the first pass

- `uv run python -m lotline.rule_agents.adu check RUN_DIR/coding_a/*.json`. Send each failing file back to
  the coder once (SendMessage with the problems). A file that fails again is kept as `partial` with the
  failing fields blanked; say so in the report.
- `uv run python -m lotline.rule_agents.adu score RUN_DIR/coding_a/*.json --sources RUN_DIR/sources --out
  RUN_DIR/score [--audit-rate R]`. A value is strong only when it is `high` confidence, rests on a primary
  source, and its quote was found by machine in the cached copy (on the named PDF page). Each
  `score/<g>.json` has `mode`: `none` (all strong, or nothing coded), `targeted` (`second_coder_fields` lists
  the fields to recode), or `full` (audit sample). It also lists `uncoded_amendments`: ordinances the scout
  found that match no coded era.

## 4. Blind second look

Unless `--second-coder off`, in one message launch `rules-adu-second-coder` (coder id
`claude-rules-adu-blind`) for the places whose mode is `targeted` or `full` (`--second-coder full`: every
place). Its brief per place: geoid, name, `fields` = `second_coder_fields` (or `all`), and the
`uncoded_amendments` lines. **Never** pass the scorecard's `looks`, era keys or reasons, nor `coding_a/`:
they would show the first coder's eras and doubts. Run `check` on `coding_b/`, as in step 3.

## 5. Verify and merge

- Places with a second coding: launch `rules-adu-verifier` per batch; it passes `--score RUN_DIR/score/<g>.json`
  to `diff-coders` and `merge`, so a targeted place is compared only on its looked-at fields (plus any era
  one coder found and the other did not).
- Places with mode `none`, and every place with `--second-coder off`: copy `coding_a/<g>.json` to
  `final/<g>.json` with no `.meta` (rows come out `single_coder`). Their quotes were already machine-checked by
  `score`.
- Each place ends with `final/<g>.json` (and `final/<g>.meta` where a verifier ran).

## 6. Rows

`uv run python -m lotline.rule_agents.adu rows RUN_DIR/final/*.json --out RUN_DIR/rows.csv`. A schema error
stops the run: fix the coding, not the row.

## 7. Human list

Launch `rules-adu-handoff` with `RUN_DIR`. It produces `tasks.csv` and `tasks.md`.

## 8. Report

Write `RUN_DIR/report.md`: places run; per place outcome, eras, rows and `coder_agreement`; blank core
fields; values by confidence; first-pass score (strong / weak values, places by second-coder mode, uncoded
amendments, and for the audit sample how many strong values the full second coding contradicted); blocks by reason and host; open human tasks with total minutes; any holdout or
process incident. With `--compare`, run
`uv run python -m lotline.rule_agents.adu compare --state ST --rows RUN_DIR/rows.csv > RUN_DIR/compare.txt`
and summarise matches and differences, naming the source each side cites.

Tell Ben in plain words: where the files are, how many rows are ready, how many lookups wait for him (and
how long they take), and every judgment call the agents left for him. Rows enter `config/` only after Ben
accepts them, through a dated script in `scripts/dev/`.
