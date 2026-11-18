"""Rule agent swarms: research and code local housing rules for one state, one category at a time.

- `common`: the shared core (2026-11-17), built from the missing-middle swarm as the master copy:
  `docstore` (one content-addressed store of primary documents for all swarms, with text sidecars, an index,
  citations and a drop folder for files a person saves), `fetch` (store-first, robots-respecting, one try),
  `access` (blocker classifier), `evidence` (evidence and blocker models, confidence rule), `text` (quote
  checks), `excerpts` (short page-cited passages so coders don't read whole codes), `budget` (per-place
  spending limits and ledger), `handoff` (shared parts of the human lookup sheet), `dates`, `pdftext`.
- `mm`: missing middle (`/rules-mm`). The ADU and fee swarms move onto `common` after their PRs merge.

Shared command line: `python -m lotline.rule_agents --help`. Design: docs/build/rule-agents/CORE.md.
"""
