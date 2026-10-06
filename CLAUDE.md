# Lotline

Code name for our entry in the **Housing Data and Technology Innovation Challenge** (Arnold Ventures / The Turnout).
Lotline is a transparent simulator that estimates how state-level housing reforms change housing production over
5 years compared with a baseline, with results added up to a statewide total. It is built so that any jurisdiction
can feed in its own data, however sparse.

**Read `HANDOFF.md` first.** It holds current status, the decisions log, the scoring rubric, key dates and the full
compliance checklist. Official Rules: https://housingchallenge.turnout.rocks/rules.html ·
Handbook: https://housingchallenge.turnout.rocks/handbook.html

## Non-negotiables (from the Official Rules)

- **Original work only.** Everything in this repo must be written on or after 2026-09-14. **Do not copy code from
  sibling repos** in `~/Engineering` (e.g. `NC-Triangle-Housing-Analysis`, the `*-market-monitor` repos,
  `permit-layers-handoff`). Reusing ideas, methods and public data sources is fine; pasting old private code is not.
  If a pre-existing open-source component is used, add it to `docs/disclosures.md`.
- **License:** Apache-2.0 for our code. Every dependency must be permissive (no GPL/AGPL/LGPL/MPL/EUPL, no
  noncommercial or unknown licenses). Disclose any exception (e.g. `certifi`, MPL-2.0) in `docs/disclosures.md`.
- **No committed data or secrets.** Data is fetched by scripts (`scripts/fetch_data.py` → `lotline fetch`) into
  `LOTLINE_DATA_DIR` (default `~/lotline-data`, outside the repo; `data/` stays gitignored as a fallback).
  Keys go in `.env` (gitignored). Every dataset gets a row in `docs/data_provenance.md`.
- **Scenarios:** baseline plus at least 3 benchmark scenarios, using the Handbook's exact definitions.
  Working set: `missing_middle`, `adu`, `fees` (and optionally `parking`).
- **Show uncertainty.** Every result is a range or a sensitivity, never a single number on its own.
- **Tests prove the method.** Core logic has tests that show the code does what the methodology document says.
- **AI assistance is allowed and must be disclosed.** Code that can't be explained or reproduced scores lower.

## Design principles

- Assumptions are kept separate from mechanics: every parameter lives in a config file with a source citation;
  the code never hard-codes them.
- Swapping in alternative datasets is scored (Replicability, 25%), so data inputs sit behind simple adapters.
- A non-technical policymaker is the primary user. Labels are in plain language.

## Before every commit

```bash
python compliance_check.py          # must show 0 FAIL
python compliance_check.py --run    # before merging: also runs setup and tests
```

## Logbook (every session)

`LOGBOOK.md` is the replayable record of how Lotline was built. **At the end of any session that produced
something (a doc, dataset, analysis, design, decision, code change), append one entry** using the template in
that file, without being asked:

- Next `LB-NNN` number, today's date, a workstream tag, and the question the work answered.
- Name every output by path or artifact link; point to any HANDOFF decision it added.
- Say what Claude did and how it was checked (feeds `docs/disclosures.md`).
- Append only; never rewrite old entries. Corrections go in a new entry that references the old one.
- Keep the repo copy (`LOGBOOK.md`) and the project copy (`claude/LOGBOOK.md`) identical, and update the
  "story so far" table when a new phase starts.

**Exception for Claude Code workstream instances** (several run in parallel): don't edit `LOGBOOK.md` or
`HANDOFF.md` directly. Write one fragment per PR to `logbook.d/<YYYY-MM-DD>-<branch>.md` using the same template;
Ben folds fragments in with `scripts/dev/merge_logbook.py`. Propose HANDOFF decisions in the PR description.

## Rules timing (checked 2026-10-04)

Work must be created during the Registration Period (to **Oct 7, 9:00 a.m. ET**) or the Coding Period
(**Oct 14, 9:01 a.m. ET → Dec 16, 11:59 p.m. ET**). The Rules don't cover the week in between. **Make no commits
between Oct 7 09:00 and Oct 14 09:01 ET** unless HANDOFF records that the organizers said gap-week work counts.

## Working in parallel (Claude Code)

The build plan is `docs/build/BUILD_PLAN.md`. Each instance has a brief in `docs/build/workstreams/`.

- **One instance = one workstream = one branch (`ws/<name>`) = one git worktree.** Read `CLAUDE.md`, the build
  plan, then your brief. Work the brief's checklist in order.
- **Edit only the paths your brief says you own.** Shared contracts (`src/lotline/schemas.py`, config loaders,
  CLI, IO) belong to WS-CORE: open an issue labeled `contract-change` instead of editing them.
- **Data lives outside the repo** in `LOTLINE_DATA_DIR` (default `~/lotline-data`), shared by all worktrees.
  Never commit data. Every download goes through the IO layer so it lands in `manifest.jsonl`.
- **Holdouts are sacred.** Never bypass the holdout filter or pass `--unblind` unless the frozen prediction for
  that test is already on `main` and Ben has asked for the unblinding.
- **Every parameter lives in `config/params/` with a source.** Every equation gets a unit test against a
  hand-worked example. Tests use small synthetic fixtures, never real downloaded data.
- **Small PRs linked to issues** (`Closes #NN`). CI (tests + `compliance_check.py` + license scan) must pass.
  Ask Ben before adding a dependency (state its license in the PR) or changing a shared contract.
- Research docs in `docs/research/` are the source of truth for methods. If code needs to deviate, say so in
  the PR and in `docs/analysis_plan.md` (dated deviation entry).
