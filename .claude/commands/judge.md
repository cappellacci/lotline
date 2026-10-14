---
description: Run the Lotline judging panel (gatekeeper + five criterion judges + head judge) and write a scorecard
argument-hint: "[all|gate|transparency|replicability|usability|methodology|policy] [--ref main] [--stage build|submission] [--with-data] [--focus <topic>]"
---

# /judge — run the Lotline judging panel

Arguments: `$ARGUMENTS`

The panel is defined in `.claude/agents/judge-*.md`; the shared rules are in `.claude/judging/RUBRIC.md`.

## 1. Parse arguments

- First word selects judges: `all` (default) or one of `gate`, `transparency`, `replicability`, `usability`,
  `methodology`, `policy`. A single judge still writes its report; run the head judge only for `all`.
- `--ref main`: judge a clean clone of `main` (what real judges see). Default: the working tree.
- `--stage build|submission`: default `build` until `challenge.toml` says `stage = "submission"`; then default
  `submission`.
- `--with-data`: judges may use already-downloaded data in `LOTLINE_DATA_DIR` (still never holdouts, never new downloads).
- `--focus <topic>`: passed through to every judge.

## 2. Set up the run (main session, read-only on the repo except the reports folder)

```bash
REPO=$(git rev-parse --show-toplevel)
SHA=$(git -C "$REPO" rev-parse --short HEAD); MAIN=$(git -C "$REPO" rev-parse --short main)
DIRTY=$([ -n "$(git -C "$REPO" status --porcelain)" ] && echo yes || echo no)
RUN_ID="$(date +%Y-%m-%d-%H%M)-$SHA"
RUN_DIR="$REPO/reports/judging/$RUN_ID"; mkdir -p "$RUN_DIR"
```

If `--ref main`: `TARGET=$(mktemp -d)/lotline && git clone --quiet --no-hardlinks --branch main "$REPO" "$TARGET"`;
otherwise `TARGET=$REPO`. Write `RUN_DIR/RUN.md` with run id, target, both SHAs, dirty flag, stage, focus and the
arguments.

## 3. Launch the judges

Launch the selected judges **in parallel in a single message** with the Agent tool
(`subagent_type` = `judge-gatekeeper`, `judge-transparency`, `judge-replicability`, `judge-usability`,
`judge-methodology`, `judge-policy-insight`). Give each the same run brief:

```
Run brief
- RUN_DIR: <abs path>
- TARGET: <abs path> (HEAD <sha>, main <sha>, working tree dirty: <yes/no>)
- REPO (for clean clones): <abs path>
- STAGE: <build|submission>
- WITH_DATA: <yes/no>
- FOCUS: <text or none>
- TODAY: <YYYY-MM-DD>
Read .claude/judging/RUBRIC.md, then your agent instructions. Write your report to RUN_DIR and reply with the short summary.
```

## 4. Synthesize

When all selected judges have replied (for `all`), launch `judge-head` with the same run brief. Then show Ben:

- the head judge's Bottom line, Scores table and This-week actions (or, for a single judge, its summary);
- the path to `RUN_DIR/SCORECARD.md` and the individual reports.

Don't edit any repo files besides `RUN_DIR`, don't open issues, and don't commit. `reports/judging/` is
gitignored; if Ben wants a run kept in git, he can copy the scorecard elsewhere.
