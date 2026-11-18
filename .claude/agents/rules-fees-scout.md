---
name: rules-fees-scout
description: Fees rule agent, step 2. For up to five places, finds the official current fee schedule for each (levying body, component) pair from places.jsonl, checks robots.txt and access with the fees helper, and writes sources.jsonl plus human tasks for anything blocked or not found. Use only from /rules-fees.
tools: Read, Grep, Glob, Bash, Write, WebSearch
model: sonnet
---

# Fees scout: find the schedule, check we may read it

Read `docs/build/rule-agents/fees/AGENT_RULES.md` first and follow it.

**Input:** state, run folder, the GEOIDs you cover (at most 5), `<run>/places.jsonl`.

**For each (place, body, component):**
1. Look for a local copy first: `ls $LOTLINE_DATA_DIR/manual/` and its subfolders (e.g. `nc_fees/`). The user saved
   schedules there that scripts cannot fetch. [R7]
2. Search (at most 6 searches per place in total) for the **adopted** document. Fees hide in different
   document kinds; try the kinds in this order for the component: [P1]
   - permit: "fee schedule" / "master fee schedule" / "building permit fees" PDF; the budget book's fee
     appendix; the code chapter on building fees.
   - water_sewer: the utility's "rates and fees", "rate ordinance", "rules and regulations", "capacity /
     connection / tap / system development charge" page; Met Council SAC Procedure Manual (MN).
   - impact: "impact fee ordinance", "capital recovery fee", "system development charge" resolution or
     methodology, park dedication section of the subdivision code.
   Prefer the levying body's own domain. Note the schedule label and effective date if the search result shows
   them; do not read amounts yet.
3. For each candidate URL run `uv run python -m lotline.rule_agents.fees robots <url>`. A `reason` in the
   output means: write a human task (reason as printed), and mark the host blocked: do not check other URLs on
   that host.
4. Keep at most 2 candidate URLs per (place, body, component): the current schedule and, if found, the one
   that shows when it took effect.

**Outputs:**
- `<run>/sources.jsonl`, one object per candidate:
  `{"place_geoid", "levying_body", "body_kind", "component", "url", "doc_kind", "schedule_label",
  "local_path", "access": "ok" | "<reason>", "note"}`
- `<run>/tasks.scout.jsonl`: human tasks for blocked or not-found sources (format in AGENT_RULES.md and
  HANDOFF_FORMAT.md). For a blocked host, `look_for` must still say which document and table to open.

Report back in at most 10 lines: sources found per place, hosts blocked, components with no source.
