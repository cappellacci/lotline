"""ADU rule agent swarm: deterministic helpers (docs/build/rule-agents/adu/DESIGN.md).

Modules:
- `coding`   — the JSON a coder writes per place (rule eras, fields, evidence) and its checks.
- `dates`    — how the effective date is chosen from adoption / effective / codified / first-seen evidence.
- `fetch`    — polite, robots-respecting retrieval into LOTLINE_DATA_DIR, with a block classifier and
               PDF text (pypdf).
- `handoff`  — structured human lookup tasks (write, read back, auto-close records-request-only cases).
- `score`    — first-pass score: which values are weak enough to need the blind second look.
- `reconcile`— field-by-field comparison of the primary and blind second coder (all or targeted fields).
- `rows`     — reconciled coding -> `reforms` rows (schema-validated), plus comparison with coded rows.
- `places`   — place enumeration and the holdout guard.
- `cli`      — `python -m lotline.rule_agents.adu <command>` for the agents to call.
"""

CATEGORY = "adu"
HELPERS_VERSION = "0.2.0"
