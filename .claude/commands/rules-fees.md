---
description: Run the fees rule agent swarm for one state; proposes evidence-backed rows for config/fees/<st>.csv and a list of lookups for a person
argument-hint: "<ST> [--places GEOID,GEOID,...] [--jurisdictions CSV] [--budget TOKENS] [--max N] [--no-second-coder] [--compare]"
---

# /rules-fees: development fees for one state

Arguments: `$ARGUMENTS`

Design: `docs/build/rule-agents/fees/DESIGN.md`. Rules every agent follows: `AGENT_RULES.md` (same folder).
You (the main session) are the orchestrator. You spawn the agents below, run the Python helper between them,
and never read fee schedules yourself. Keep your own context small: read agents' short reports and the
helper's printed summaries, not the item files.

## 0. Check the set-up

Run `uv run python -m lotline.rule_agents doctor <ST> --category fees`. If any check fails, tell the user what
is missing in plain words (its fix line) and stop.

## 0b. Set up

1. Parse `<ST>` (two letters, required), `--places` (GEOIDs), `--jurisdictions` (CSV, for a state with no
   table), `--budget` (tokens per place; save it with `uv run python -m lotline.rule_agents ledger limits
   "$RUN" --tokens N` once the run folder exists), `--max` (default 5; places are processed largest
   first), `--no-second-coder`, `--compare` (compare with existing rows at the end: dry runs).
2. Run folder: `RUN=$(uv run python -c "from lotline.io.store import data_dir; print(data_dir())")/rule-agents/fees/<ST>/<YYYY-MM-DD>-<HHMM>`;
   `mkdir -p "$RUN"`. Nothing in the run folder is ever committed.
3. Places: from `--places`, else the state's `jurisdictions` table (largest `pop_2020` first, kind `place`)
   via `uv run python -c` with `lotline.rule_agents.common.places.read_jurisdictions("<st>", <csv or None>)`
   (a state with no table: the user's `--jurisdictions` CSV with `geoid,name,pop_2020`; if neither exists,
   stop and ask for it). Read **only** the
   jurisdictions table (no permits, no outcomes). Write `$RUN/plan.json` with state, places (geoid, name,
   pop) and options.
4. Principles shared by all rule agents: `docs/build/rule-agents/PRINCIPLES.md`. Places are keyed by Census
   GEOID.
5. Holdouts: fees are inputs, so holdout places may be coded. Do not open any outcome data for them.
6. Budget: every place has a shared spending budget (`common.budget`: default 250k tokens, 12 fetches, 8
   searches; the Agent tool's token count includes everything an agent reads). After each
   agent returns, record (only you record tokens; agents record their fetches and searches) its token use from the Agent tool's report:
   `uv run python -m lotline.rule_agents ledger add "$RUN" <geoid> <agent> --tokens N`, with `<agent>` the
   agent's full name (`rules-fees-scout`, `rules-fees-reader`, ...) so its lines match its own (agents record their own
   fetches and searches). Each agent also has its own share of the place's tokens (scout 60k, first coder 60k, second coder 50k, verifier/reconciler 30k, hand-off 20k, fees enumerator 30k; scaled to `--budget`), and the second coder's and reviewer's unspent shares are held back from the others, so an early agent cannot spend the check. Before spawning an agent for a place, `ledger status "$RUN" <geoid> --agent <agent name>`; on `stop`,
   hand the place's open components to the user as `budget_spent` tasks.

## 1. Enumerate levying bodies

Spawn one `rules-fees-enumerator` (or `general-purpose` told to follow `.claude/agents/rules-fees-enumerator.md`)
with the state, `$RUN`, the places and `config/fees/<st>.csv`. Wait. Check `$RUN/places.jsonl` has every place.

## 2. Find sources

Spawn one `rules-fees-scout` per 5 places (in parallel if more than one). Wait. Report hosts blocked.

## 3. First coder

Spawn one `rules-fees-reader` per place, at most 4 at a time, each told its GEOID and `$RUN`. Do not pass
existing `config/fees` values in the prompt.

## 4. Blind second coder

Unless `--no-second-coder`: spawn one `rules-fees-second-coder` per place that has items, at most 4 at a time.
Its prompt contains only the state, `$RUN` and the GEOID: **never** coder 1's items, counts or values.

## 5. Pair and reconcile

```bash
# find, not a glob: a glob with no match is an error in zsh (no place had items, or no second coder)
find "$RUN" -maxdepth 1 -name 'items.coder1.*.jsonl' -exec cat {} + > "$RUN/items.coder1.jsonl"
find "$RUN" -maxdepth 1 -name 'items.coder2.*.jsonl' -exec cat {} + > "$RUN/items.coder2.jsonl"
uv run python -m lotline.rule_agents.fees reconcile "$RUN/items.coder1.jsonl" "$RUN/items.coder2.jsonl" --out "$RUN"
```
If any pair is not `agree`, spawn one `rules-fees-reconciler` with `$RUN`. Otherwise copy
`items.merged.jsonl` to `items.final.jsonl`. With `--no-second-coder`, `items.final.jsonl` is the coder-1 file.

## 6. Build, tasks, compare

```bash
uv run python -m lotline.rule_agents.fees build "$RUN/items.final.jsonl" --out "$RUN"
uv run python -m lotline.rule_agents.fees tasks "$RUN"/tasks.*.jsonl --out "$RUN"
uv run python -m lotline.rule_agents.fees compare "$RUN/rows.csv" --state <ST>     # with --compare
```

## 7. Report

Write `$RUN/report.md` and show the user, in plain words and at most ~25 lines:
- places done; rows proposed (high / medium), low rows held back, items excluded;
- second-coder agreement (`agree / partly / differ / only_coder1 / only_coder2`);
- human tasks by reason, with the path to `human_tasks.md`;
- decisions for the user from `decisions.md`, each as one plain question;
- with `--compare`: per place and component, run vs existing totals, and what explains each difference;
- spending per place: `uv run python -m lotline.rule_agents ledger summary "$RUN"`.

Do not copy rows into `config/fees/<st>.csv`, and never touch `config/params/` or model code. The output is a
proposed fees table (`$RUN/rows.csv`) the user reviews and imports. **End the run by telling the user the
import command**, preview first:

```bash
uv run python -m lotline.rule_agents import "$RUN/rows.csv" fees <ST>          # preview: new and changed rows
uv run python -m lotline.rule_agents import "$RUN/rows.csv" fees <ST> --yes    # write config/fees/<st>.csv
```

The importer keys fee rows on `jurisdiction_geoid, year, fee_component, fee_type, building_type_std, basis`,
adds new rows, lists changed ones (`--replace-changed` to take them) and validates the merged table. Never run
it with `--yes` yourself. Outside studies are checks, never a source of a rate to recommend.

## Stop rules

Stop and report (do not push on) when: more than half of the places are blocked on the same host type; an agent
reports it was asked to work around an access control; or a helper command fails twice on the same input.
