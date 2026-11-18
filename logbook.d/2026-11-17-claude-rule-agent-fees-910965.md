### LB-NNN · 2026-11-17 · Build: fees rule agent swarm, design and Minnesota dry run
- **Question:** Can five states of ad-hoc fee coding be turned into a reusable swarm that takes one state and
  returns evidence-backed `fees` rows, and hands a person a clear task whenever it can't read a source?
- **What I did:**
  - Read the fee logbook fragments, decisions (D-034, D-065, D-066, D-069, D-073), `config/fees/` and the
    lookup lists; wrote the lessons register. Only 29 of 928 coded fee rows (3%) have been re-opened by a second
    coder, and a third have no quote.
  - Designed the swarm: an enumerator for levying bodies, a scout, a reader, a blind second coder, a reconciler,
    and a `/rules-fees` command. Deterministic Python helpers price items at the `proforma.yaml` prototypes,
    classify the component from what the fee pays for, apply Ben's group rule, check robots and quotes, pair
    the two coders, build and validate rows, and render human tasks. Designed a shared primary-document store
    (doc ID = sha256, text sidecars, schedule history chains, a slot for hand-saved files) at the parent
    session's request.
  - Dry run on five Minnesota places (6 sonnet agents, about 560k tokens).
- **Inputs:** `logbook.d/*fee*`, `config/fees/*.csv`, `docs/build/manual-fee-lookups.md`,
  `docs/research/ordinances/` (README, lookups, second-coder sheets), `docs/analysis_plan.md` fee decisions;
  official fee sources fetched into `LOTLINE_DATA_DIR` (manifest source `rule-agents-fees`).
- **Outputs:** `docs/build/rule-agents/fees/` (README, LESSONS, DESIGN, AGENT_RULES, HANDOFF_FORMAT,
  SHARED_CANDIDATES, DRYRUN-2026-11-17-MN), `.claude/agents/rules-fees-*.md` (5),
  `.claude/commands/rules-fees.md`, `src/lotline/rule_agents/fees/`, `tests/rule_agents/fees/` (33 tests).
- **Findings:**
  - Where the swarm could read the source (Coon Rapids, SAC), it reproduced every existing amount, and the
    blind second coder agreed. It found that 12 of 19 coded MN places lack the state permit surcharge
    (~$177 a house), and that Coon Rapids' fourplex permit is overstated by ~$580 a unit (house valuation
    applied per unit).
  - 3 of 5 cities refuse automated readers at `robots.txt` (Plymouth, Minnetonka, Eagan) → 9 human tasks.
  - Without a PDF library most schedules can't be read or quote-checked. With pypdf, 31 of 39 first-coder
    quotes matched word for word; the misses had labels glued on.
- **Decisions (Ben, 2026-11-17, in chat):** pypdf (BSD-3-Clause) added as a dependency; records-request-only
  sources become optional priority-3 tasks for the user; additive evidence columns on `fees` sent to WS-CORE
  as issue #472; the rule agents are framed as an app service (the person in the loop is "the user"). The
  MN state-surcharge rows and the Coon Rapids 35% plan review stay out of `config/`: they are a proposed fees
  table in the dry-run folder for the user to import.
- **AI:** Claude Code (Opus 5.5) wrote the docs, agents, helpers and tests and ran the dry run with sonnet
  subagents. Checks: 33 hand-worked tests (e.g. Apple Valley $1,302.50 + $7.40 × 255 = $3,189.50; Brunswick
  $3,282 × 3 bedrooms = $9,846), the `fees` schema on every built row, a blind second coder on two places,
  run-vs-existing comparison, `compliance_check.py`. No model run. The proposed table's effect was checked with
  `fee_levels.coded_fees` old vs new: +$177.38 a house in 11 places, -$556.79 in Coon Rapids.
- **Open / next:** the Coon Rapids fourplex permit (~$580 a unit high); a reconciler run on a place with real `differ` pairs; the history pass;
  merge the shared parts with the MM and ADU swarms; work the 16 human tasks.
