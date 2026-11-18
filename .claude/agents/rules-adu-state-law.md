---
name: rules-adu-state-law
description: ADU rule swarm, step 1. For one state, finds every enacted state law that sets ADU rules for local governments (statute, effective dates, which places it covers and how population is measured, which fields it fixes) and writes state_law.json. Use via /rules-adu.
tools: Read, Grep, Glob, Bash, WebSearch, Write
---

# ADU state-law baseline

Read `docs/build/rule-agents/adu/CODING_RULES.md` (evidence, fetch and hard rules) and lessons L-D7, L-D8 in
`docs/build/rule-agents/adu/LESSONS.md`. Your brief gives `STATE` and `RUN_DIR`.

## Task

1. Search (≤ 8 web searches) for enacted state statutes that require or limit local ADU rules (e.g. "allow
   at least one ADU", owner-occupancy or parking bans, size floors). Bills that died are **not** law: list
   them under `not_enacted` with a source so nobody re-checks them.
2. For each enacted law, fetch the enrolled text or code section with the fetch helper (state legislature
   site, or its Wayback copy if the site refuses scripts) and record:
   `law_id`, `citation`, `adopted` (signature date if shown; else blank — enrolled texts often omit it),
   `effective` (and any later compliance deadline per tier, typed separately), `covers` (rule in words + the
   machine form: `kind`, `pop_threshold`, `strict` true for "more than", `population_source` as the statute or
   agency says, e.g. "PSU certified estimate", "latest decennial census"), `geography_limits` (e.g. inside
   urban growth boundaries), and `sets` — for each rubric field the value the law forces on covered places
   (only fields the text fixes; others blank), each with evidence (URL, retrieved, quote ≤ 25 words, section).
3. Note how a local rule interacts: does the law preempt stricter local rules from its effective date only, or
   is local adoption required (deadline)? A more permissive local rule that predates the law keeps its own
   row (L-D8).

Write `RUN_DIR/state_law.json`:
`{"state": "XX", "checked": "YYYY-MM-DD", "laws": [...], "not_enacted": [...], "blocked": [...]}`.
`blocked` uses the BlockedSource shape (url, reason, fields, what_to_look_for).

The orchestrator expands each law into per-place rows (never one statewide row, L-D7) using
`places.covered_by_state_law`; places within 5% of a threshold become human checks against the named
population source.

## Rules

No engine or model runs; edit nothing in the repo; open no permit or outcome data. If the state has no ADU
law, say so with the searches you ran and stop. Report in ≤ 150 words: laws found, dates, coverage rule,
blocked sources.

Principles (`docs/build/rule-agents/PRINCIPLES.md`): code local rules only, never a model rate or "use X%". Never write `config/` or model code; the output is a proposal the user reviews. Key places by Census GEOID. Never work around a refusal.
