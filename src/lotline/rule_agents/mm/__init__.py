"""Deterministic helpers for the missing-middle (MM) rule agent swarm (`/rules-mm`).

The research itself is done by Claude Code subagents (`.claude/agents/rules-mm-*.md`); this package holds the
parts that must not depend on a model's judgment, each with tests on synthetic fixtures
(`tests/rule_agents/mm/`):

- `findings`: the coder's per-place JSON (a "finding") and the checks every finding must pass before it is
  reconciled (evidence for every coded field, quote length, date order, tag consistency).
- `dates`: date parsing and the date-basis tags the engine reads (`[predates]`, `[earliest-known]`,
  `DATE UNCONFIRMED`, `[standards]`; see `lotline.model.rule_tags`).
- `access`: robots.txt checks and the blocker classifier (403/WAF, code-host walls, logins, scanned PDFs).
- `handoff`: structured human lookup tasks (CSV + Markdown checklist) and reading the answers back.
- `reconcile`: the field-by-field comparison of two blind coders.
- `rows`: reconciled findings -> `reforms` rows (theme `missing_middle`), validated against the schema.
- `compare`: an agent run's rows against already-coded `config/reforms/<st>.csv` rows (dry runs).

Design: docs/build/rule-agents/mm/DESIGN.md. Command line: `python -m lotline.rule_agents.mm --help`.
"""

THEME = "missing_middle"
