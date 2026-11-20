# Fees rule agent swarm

Takes one state and proposes evidence-backed rows for `config/fees/<st>.csv`, plus a list of lookups for a
person wherever a source can't be read. Run it with `/rules-fees <ST> [--places ...] [--max N] [--compare]`.

| File | What it is |
|---|---|
| `LESSONS.md` | what five states of fee coding taught us (retrieval, taxonomy, dates, prototype, second coding) |
| `DESIGN.md` | the swarm: roles, the fee item, pricing rules, evidence and confidence, stop rules |
| `AGENT_RULES.md` | the hard rules every fees agent follows |
| `HANDOFF_FORMAT.md` | human lookup tasks: columns, reasons, how answers come back in |
| `SHARED_CANDIDATES.md` | parts the fees, ADU and missing-middle swarms should share, incl. the document store |
| `DRYRUN-2026-11-17-MN.md` | five Minnesota places, compared with the existing rows |

Agents: `.claude/agents/rules-fees-{enumerator,scout,reader,second-coder,reconciler}.md`; command:
`.claude/commands/rules-fees.md`; helpers: `uv run python -m lotline.rule_agents.fees --help`
(`src/lotline/rule_agents/fees/`, tests in `tests/rule_agents/fees/`).
