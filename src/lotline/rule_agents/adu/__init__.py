"""ADU rule agent swarm: deterministic helpers (docs/build/rule-agents/adu/DESIGN.md).

Runs on the shared core `lotline.rule_agents.common` (document store, store-first fetch, evidence and
blocker models, lookup-sheet parts, ledger, doctor, import); the modules here are the ADU-specific part.

Modules:
- `coding`   — the JSON a coder writes per place (rule eras, fields, evidence) and its checks.
- `dates`    — how the effective date is chosen from adoption / effective / codified / first-seen evidence.
- `fetch`    — `common.fetch.get(url, "adu", ...)` (store first) and the shared quote checks.
- `handoff`  — ADU lookup tasks on `common.handoff` (records-request-only sources are optional, priority 3).
- `score`    — first-pass score: which values are weak enough to need the blind second look.
- `reconcile`— field-by-field comparison of the primary and blind second coder (all or targeted fields).
- `rows`     — reconciled coding -> `reforms` rows (schema-validated), plus comparison with coded rows.
- `places`   — place enumeration and the holdout guard.
- `cli`      — `python -m lotline.rule_agents.adu <command>` for the agents to call.
"""

CATEGORY = "adu"
HELPERS_VERSION = "0.3.0"
