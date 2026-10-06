# Logbook fragments

Parallel Claude Code instances don't edit `LOGBOOK.md` directly (it would conflict on every PR). Instead, **each PR adds
one fragment** here, and Ben folds them into `LOGBOOK.md` with:

```bash
python scripts/dev/merge_logbook.py           # dry run: prints what would be appended
python scripts/dev/merge_logbook.py --apply   # appends entries, numbers them, deletes the fragments
```

**File name:** `logbook.d/<YYYY-MM-DD>-<branch>.md`, with `/` in the branch name replaced by `-`
(e.g. `2026-10-06-ws-bootstrap.md`).

**Content:** one entry in the `LOGBOOK.md` template, with `LB-NNN` left literally as `LB-NNN`. The merge script assigns
numbers in date order (then file name) after the last entry in `LOGBOOK.md`.

```
### LB-NNN · YYYY-MM-DD · <Workstream>: <short title>
- **Question:** what this step set out to answer
- **What I did:** method, in 2–4 bullets
- **Inputs:** sources, datasets, prior entries
- **Outputs:** file paths / artifact links
- **Findings:** the 1–3 things that matter
- **Decisions:** anything proposed for the HANDOFF decisions log (Ben records it)
- **AI:** what Claude did and how it was checked
- **Open / next:**
```

Workstreams: `Rules` · `Scope` · `Data feasibility` · `Policy analysis` · `Literature` · `Study design` · `Build` ·
`Validation` · `Deliverables` · `Admin`
