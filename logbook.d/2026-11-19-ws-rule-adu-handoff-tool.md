### LB-NNN · 2026-11-19 · rule-agents · Why did the ADU lookup list need an agent to rebuild it by hand?

**Question.** In South Burlington VT's ADU test run, the hand-off agent spent 48k tokens rebuilding tasks the
`adu tasks` tool had dropped: the uncoded period before 2022 lost 7 of 9 fields, and the 2019 parking
ordinance produced no task.

**Cause.** `settled_fields_dropped` treated a field as settled when every coded era had it, whatever period
the blocker was about, so a blocker for an uncoded period lost fields the 2022 era had answered.

**Outputs.**
- `src/lotline/rule_agents/adu/cli.py`: `settled_fields_dropped(fields, final, era_id)` checks only the named
  era; a blocker naming a period with no coded era keeps every field; no era still means every coded era.
- `.claude/agents/rules-adu-coder.md`, `rules-adu-second-coder.md`: a blocker's `era_id` names its era or a
  label for an uncoded period (`before-2022`, `2019`), never blank unless it is about every era.
- `.claude/agents/rules-adu-handoff.md`: runs on haiku, only polishes wording; never adds, drops or rebuilds
  tasks or opens documents (a missing task is reported as a tool bug).
- Test: `test_a_blocker_for_an_uncoded_period_keeps_every_field`.

**How Claude did it and how it was checked.** Claude (Opus 5.5) reran the tool on a copy of the South
Burlington run, reproduced both losses, fixed them and reran: with labelled periods the tool alone produced
the three tasks the agent had rebuilt (pre-2022 with all 9 fields; 2019 parking merged with the 2022 task
on the same page). Rule-agent tests pass, ruff clean, compliance 0 FAIL.
