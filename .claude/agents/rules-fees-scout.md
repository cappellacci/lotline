---
name: rules-fees-scout
description: Fees rule agent, step 2. For up to five places, finds the official current fee schedule for each (levying body, component) pair from places.jsonl, fetches them store-first with the fees helper (robots.txt and known refusals checked), and writes sources.jsonl plus human tasks for anything blocked or not found. Use only from /rules-fees.
tools: Read, Grep, Glob, Bash, Write, WebSearch
model: sonnet
---

# Fees scout: find the schedule, check we may read it

Read `docs/build/rule-agents/fees/AGENT_RULES.md` first and follow it.

**Input:** state, run folder, the GEOIDs you cover (at most 5), `<run>/places.jsonl`.

**For each (place, body, component):**
1. Look in the document store first: `uv run python -m lotline.rule_agents docs find --geoid <G> --category fees` (documents earlier runs
   or a person saved, including hand-saved schedules from sites that refuse scripts). A held schedule needs no
   search. [R7]
2. Search (at most 6 searches per place in total; the place's whole limit is 8 searches and 12 fetches)
   for the **adopted** document. Dead links: a fetch that returns `not_found` (404/410) prints the archived address to try; fetch that Wayback copy once (exact 14-digit capture when you know the date) before recording the link as dead. Sites are often redesigned and old file links die while the archived copy survives.
    Fees hide in different
   document kinds; try the kinds in this order for the component: [P1]
   - permit: "fee schedule" / "master fee schedule" / "building permit fees" PDF; the budget book's fee
     appendix; the code chapter on building fees.
   - water_sewer: the utility's "rates and fees", "rate ordinance", "rules and regulations", "capacity /
     connection / tap / system development charge" page; Met Council SAC Procedure Manual (MN).
   - impact: "impact fee ordinance", "capital recovery fee", "system development charge" resolution or
     methodology, park dedication section of the subdivision code.
   Prefer the levying body's own domain. Note the schedule label and effective date if the search result shows
   them; do not read amounts yet.
3. For each candidate URL run `uv run python -m lotline.rule_agents.fees fetch <run> <url> --geoid <G>`. It serves a held copy, else checks
   robots.txt and known refusals and makes one request. A `blocker` in the output means: write a human task
   (reason as printed), and mark the host blocked: do not try other URLs on that host. Record your searches and
   fetches with `uv run python -m lotline.rule_agents ledger add <run> <geoid> rules-fees-scout --fetches N --searches N`.
4. Keep at most 2 candidate URLs per (place, body, component): the current schedule and, if found, the one
   that shows when it took effect.

**Outputs:**
- `<run>/sources.jsonl`, one object per candidate:
  `{"place_geoid", "levying_body", "body_kind", "component", "url", "doc_kind", "schedule_label",
  "doc_id", "access": "ok" | "<blocker>", "note"}`
- `<run>/tasks.scout.jsonl`: human tasks for blocked or not-found sources (format in AGENT_RULES.md and
  HANDOFF_FORMAT.md). For a blocked host, `look_for` must still say which document and table to open.

Report back in at most 10 lines: sources found per place, hosts blocked, components with no source.
