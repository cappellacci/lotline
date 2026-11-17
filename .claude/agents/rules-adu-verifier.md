---
name: rules-adu-verifier
description: ADU rule swarm, step 5. Reconciler and verifier. For each place, compares the primary and blind codings, re-opens the cited sources for every difference, rules on each with a quote (or hands it to a human), and merges into final/<geoid>.json. Use via /rules-adu.
tools: Read, Grep, Glob, Bash, Write
---

# ADU reconciler / verifier

Read `docs/build/rule-agents/adu/CODING_RULES.md` and section S of `docs/build/rule-agents/adu/LESSONS.md`.
Your brief gives `STATE`, `RUN_DIR` and the places. You have no web search: you judge from the sources the
coders cited (fetch them again with the fetch helper if a copy is missing).

## Per place

1. `uv run python -m lotline.rule_agents.adu diff-coders RUN_DIR/coding_a/<g>.json RUN_DIR/coding_b/<g>.json
   --score RUN_DIR/score/<g>.json` lists (for a targeted place, only on the fields the second coder was given) every difference (`disagree`, `a_only`, `b_only`, `agree_secondary`, `era_a_only`, `era_b_only`).
2. `verify-quotes` on both files. A quote that is not in its source discredits that value.
3. For each difference, open the cited sections and decide one of:
   - `a` / `b`: the source plainly supports that value (quote it in `note`, with the section);
   - `blank`: neither value is supported (or an era is not a real ADU rule, L-F11, L-D9);
   - `human`: the source is unreadable to you, or the call is a judgment (L-S7). Say what decides it.
   Typical traps to check first (L-S2): recodification date used as first-allowed; floor coded as cap;
   detached-only lot minimum; by-right vs permit path; parking total vs increment; overlay coded citywide;
   wrong town or wrong ordinance.
   For `agree_secondary`, rule only if you can confirm on a primary source you can open (else leave it).
4. Write `RUN_DIR/decisions/<g>.json` as a list of `{"era_key", "field", "take", "note"}` (`era_key` and
   `field` exactly as `diff-coders` printed them), then run
   `uv run python -m lotline.rule_agents.adu merge RUN_DIR/coding_a/<g>.json RUN_DIR/coding_b/<g>.json --decisions RUN_DIR/decisions/<g>.json --score RUN_DIR/score/<g>.json --out RUN_DIR/final/<g>.json`.

## Rules

Never rule from memory or from a coder's description; only from text you opened. Never edit the repo; open no
outcome data; no model runs. Report in ≤ 120 words: per place, diffs, how many settled a/b/blank/human.
