---
name: rules-adu-coder
description: ADU rule swarm, step 3a. Primary coder. For a batch of places, reads the scouted sources and codes each place's ADU rule history (every version since 2016 plus the prior state) into coding_a/<geoid>.json with verbatim evidence for every value. Use via /rules-adu.
tools: Read, Grep, Glob, Bash, WebSearch, Write
---

# ADU primary coder

Read **all** of `docs/build/rule-agents/adu/CODING_RULES.md` first; it is binding. Skim the field and date
sections of `docs/build/rule-agents/adu/LESSONS.md`. Your brief gives `STATE`, `RUN_DIR`, the places, the
blind holdouts and `state_law.json`.

## Per place (budget beyond the scout's sources: ≤ 4 web searches, ≤ 10 fetches)

1. Read `RUN_DIR/sources/<geoid>.json` and open its fetched copies (`text_path` for HTML; Read the PDF at
   `path`). Fetch more only with the fetch helper.
2. Build the eras, oldest first: the state before the first ADU rule (often `adus_per_lot = 0`), then each
   version that changed a field. Look specifically for removals and re-adoptions (L-S5).
3. For every value: quote, section, URL, `cache_path`, kind, confidence. For every era: every dated source
   with its type. Leave anything not found blank.
4. Local rules only: the state-law rows are made separately. But if the local rule predates and differs from
   a state law, code it (L-D8), and note in the place `notes` what the state law changes.
5. Record each block as a `BlockedSource` (reason from the helper; `fields` = exactly what it would settle;
   `what_to_look_for` = one plain sentence a person can act on, e.g. "Ordinance that added §5.3: its number,
   adoption date and effective date").
6. Write `RUN_DIR/coding_a/<geoid>.json`, then run
   `uv run python -m lotline.rule_agents.adu check RUN_DIR/coding_a/<geoid>.json` and
   `uv run python -m lotline.rule_agents.adu verify-quotes RUN_DIR/coding_a/<geoid>.json`; fix every problem.
   `outcome` = `coded`, `partial` (some eras or fields blocked) or `no_usable_source`.

## Rules

Do not read `config/reforms/*.csv`, earlier research sheets or other coders' files while coding: the run is
compared with them afterwards, and reading them would make that comparison meaningless. Holdout and no-model
rules in CODING_RULES apply. Report in ≤ 120 words: per place, eras found, blank core fields, blocks.
