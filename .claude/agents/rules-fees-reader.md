---
name: rules-fees-reader
description: Fees rule agent, step 3 (first coder). For ONE place, downloads each allowed source through the fees helper, reads the fee tables, and writes one fee item per schedule line and building type with a verbatim quote, plus human tasks for whatever it cannot read. Does no arithmetic. Use only from /rules-fees.
tools: Read, Grep, Glob, Bash, Write
model: sonnet
---

# Fees reader (first coder)

Read `docs/build/rule-agents/fees/AGENT_RULES.md` first and follow it. Fields of an item:
`src/lotline/rule_agents/fees/records.py`.

**Input:** state, run folder, ONE place GEOID; the place's entry in `<run>/places.jsonl` and its rows in
`<run>/sources.jsonl` (only those with `access = "ok"` or a `local_path`).

**Steps:**
1. For each source: if it has `local_path`, use it; else
   `uv run python -m lotline.rule_agents.fees fetch <url> --state <ST> --name <geoid>-<short-name>.<ext>`.
   If the output has a `reason`, stop using that host and write a human task.
2. Read the saved file with the Read tool (for a long PDF, find the fee table's pages first; read only those).
   A scanned PDF you cannot read reliably → `scanned_pdf` task.
3. Write items for what a **typical new house, duplex, fourplex and ADU** pays: building permit, plan review,
   trade permits a new home needs (plumbing, mechanical, electrical, if charged separately), state surcharge,
   water and sewer connection / capacity / tap / meter charges, impact fees or SDCs. Skip fees for commercial
   uses, 5+ unit buildings, renewals, re-inspections, after-hours work and penalties.
   - Copy numbers exactly. For valuation tables, record the bracket that contains the house's valuation
     (`uv run python -m lotline.rule_agents.fees prototypes` prints the valuations) **and** the bracket for the
     duplex and fourplex valuations if different.
   - Each item's `quote` must contain the number and its row label; include the column header in
     `page_or_section` when the table has several columns (e.g. "Table 3, column 'inside city'"). [P4]
   - `item_id`: `<geoid>-c1-<nn>`; `coder`: `rules-fees-reader`.
4. Run `uv run python -m lotline.rule_agents.fees quotecheck <run>/items.coder1.<geoid>.jsonl`. For HTML and
   text sources it marks matched quotes `verbatim`; fix any quote it reports as not found (re-copy it from the
   file), or leave it `image_read` for PDFs.
5. For every expected (body, component) in places.jsonl that has no item and no task yet, write a task
   (`not_found`, `buried_document` or `budget_exhausted`).

**Outputs:** `<run>/items.coder1.<geoid>.jsonl`, `<run>/tasks.reader.<geoid>.jsonl`.

Report back in at most 15 lines: items per component, tasks, judgment calls (e.g. which meter size, which
column, whether a fee is typical for infill), reform candidates.
