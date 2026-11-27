### LB-NNN · 2026-11-17 · Build: ADU rule agent swarm (design, prototype, NC dry run)
- **Question:** can the ad-hoc ADU rule research of October–November become a standalone, reusable agent
  swarm that takes one state and returns schema-valid `reforms` rows, with every value cited and every
  unreadable source handed to a person as a short, structured lookup?
- **What I did:**
  - mined the ADU logbook fragments, LOGBOOK, the decisions, the manual-lookup docs and the ordinance research
    sheets into a lessons register (60 lessons with IDs, each tied to its source);
  - designed the swarm: a `/rules-adu` orchestrator command, six subagents (state law, scout, coder, blind
    second coder, verifier, hand-off packager) and deterministic helpers for everything a test can check;
  - built the helpers (`python -m lotline.rule_agents.adu`): robots-respecting fetch with a block classifier,
    the coding model and its checks, the date rules, coder comparison and merge, row building with schema
    validation, human tasks, and comparison with coded rows;
  - dry-ran the swarm on five NC places already coded (Raleigh, Greensboro, Wilmington, Asheville, Matthews),
    blind to the coded rows, and fixed the nine problems it found.
- **Inputs:** the logbook fragments and docs listed in `LESSONS.md`; `config/reforms/nc.csv` (comparison only,
  after coding); live public sources fetched into `LOTLINE_DATA_DIR`.
- **Outputs:**
  - `docs/build/rule-agents/adu/` (`LESSONS.md`, `DESIGN.md`, `CODING_RULES.md`, `SHARED_CANDIDATES.md`,
    `DRYRUN-2026-11-17-NC.md`);
  - `.claude/agents/rules-adu-*.md` (6) and `.claude/commands/rules-adu.md`;
  - `src/lotline/rule_agents/adu/` (incl. `score.py`) and `tests/rule_agents/adu/` (61 tests);
  - `pyproject.toml` / `uv.lock`: `pypdf`;
  - the dry-run folder `~/lotline-data/rule_agents/adu/NC/dryrun-2026-11-17/`, outside the repo.
- **Findings:**
  - Of 62 field comparisons with the second-coded NC rows: 34 matched and 1 differed (an adoption date known
    only to the month). The swarm left 18 fields blank, each now a lookup. No value it coded contradicts a
    coded row.
  - Both coders missed two later amendments (Raleigh 2022, Wilmington 2022), so the scout now runs an
    amendment sweep. The swarm found one lead not in config: an Asheville 2026-08-25 change, read on a
    mirror only.
  - About 1.0M subagent tokens for 5 places (about 200k a place); the blind coder is the largest share.
    The run ended with 12 lookups, 165 minutes in all.
- **Decisions (Ben, same day; proposed for HANDOFF in the PR):**
  - `pypdf` (BSD-3-Clause) added: text PDFs get a page-separated text copy and PDF quotes are checked by
    machine (all 71 dry-run quotes found after a whitespace-tolerant second pass for pypdf's word breaks);
  - Raleigh's 2019 cottage overlay is "no ADUs" (the `config/` change goes to the ADU model's owner session);
  - the second coder runs only where the first pass is weak: new `score` step (strong = high confidence,
    primary source, quote found by machine), plus uncoded-amendment leads and a ~10% full audit sample;
  - the shared primary-document store is approved; each swarm runs on its own, so the store is a shared
    format that no swarm depends on another to fill.
- **AI:** Claude Code (Opus) wrote the docs, agents and helpers. Subagents mined the lessons and ran the dry
  run (scout and packager on Sonnet). Checks:
  - unit tests on synthetic fixtures, with hand-worked expectations;
  - `check` on every dry-run coding;
  - `verify-quotes` on HTML sources, and PDF quotes checked by the coders against extracted text;
  - the comparison table against `config/reforms/nc.csv`;
  - `compliance_check.py` (0 FAIL).

  The dry-run codings were relabelled by script for three new rules (`prior_to`, date tags, block
  vocabulary); no value was changed.
- **Open / next:**
  - Ben's decisions above;
  - the parent session merges the shared fetch, evidence, hand-off and document-store pieces with the MM and
    fee swarms;
  - a first real run on a state not yet coded.
- **Addendum, 2026-11-18 (moved onto the shared core, after #480 merged):**
  - fetch is now `common.fetch.get(url, "adu", ...)`: store first, into the shared document store; the local
    fetcher, block classifier and PDF text code are deleted (`adu/fetch.py` is a shim);
  - evidence and blockers are the shared models (`source_kind` vocabulary, `doc_id` into the store, the
    shared confidence rule enforced by `check`); `score` and `verify-quotes` check quotes against the stored
    document by `doc_id`;
  - lookup sheets use the shared answer columns, browser tips, answer checks, `held_docs` and saved-file
    registration; records-request-only sources stay optional, priority 3;
  - `/rules-adu` gains `doctor` as step 0, the budget ledger, `outline` / `excerpts` for reading, and ends by
    telling the user the `import ... reforms ST` command (a new test checks `import` accepts `rows.csv`);
  - not carried over: the old fetcher's Wayback `final_url`; coders now ask for an exact 14-digit capture.
  - Checks: tests (rule agents and full suite), ruff, `compliance_check.py` (0 FAIL).
