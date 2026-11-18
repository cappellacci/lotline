# Guardrails for every rule swarm (MM, ADU, fees)

*2026-11-17, from Ben's "Multi-state model setup guide" session. Every `/rules-<cat>` command reads this
first; agents follow it over anything in their own brief.*

1. **Outside studies are checks, not inputs** (D-037, "route one"). Uptake is calibrated on our own states
   (MN, NC, OH, TX, plus OR). Outside research supplies citations and benchmarks to compare results with; it
   never supplies a rate for the model to borrow. A swarm codes **local rules** (what was allowed, where,
   from when, at what fee). It never recommends "use X%" or any model parameter.
2. **Each model has one owner.** ADU belongs to the "ADU statewide prediction methodology" session; missing
   middle to "Missing Middle Analysis refresh"; fees has no owner session yet, so Ben decides who merges fee
   changes. A swarm writes its rows and notes to its run folder (and, through a reviewed PR, to
   `docs/research/` or the coded-rule CSVs) and hands them to that owner. It never edits `config/params/`,
   `config/reforms/`, `config/fees/` or `src/lotline/model/` itself.
3. **Start from what exists.** Before researching, read the relevant `docs/research/` notes and the
   decisions log in `HANDOFF.md` (the orchestrator does this and puts what matters in the brief; coders stay
   blind to existing coded values). A source offered for a parameter carries a citation that can go straight
   into `config/params/`.
4. **Key places by Census GEOID**, never by name alone, so rows drop into the shared place resolver WS-SCALE
   is adding (`geo.py`, per-state `xx_aliases.csv`; PRs #456–#468, contract issue #455, not merged yet).
   Keep the existing `reforms` and `fees` CSV headers exactly (formats in `docs/adding_a_state.md`, PR #452);
   new fields go in notes until WS-CORE adds columns.
5. **Standing rules.** Holdouts are sacred: never `--unblind`, never open outcome data for a blind place, never
   open a stored document flagged `may_contain_outcomes` for one. No downloaded data in the repo (documents live
   in the document store under `LOTLINE_DATA_DIR`). No records requests, staff emails, forms or logins.
   Logbook entries are fragments in `logbook.d/`. Decisions go to Ben in chat in plain words, never settled
   silently in a PR comment.
