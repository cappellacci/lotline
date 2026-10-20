# Thread 4: Policy Scenario Comparison skeleton and deck outline (WS-DOCS)

**Goal:** the structure and all non-numeric text of deliverable D6 (Policy Scenario Comparison, ≤4 pages) and an outline for the slide deck (D2, ≤30 slides) and the video script (D3, ≤5 minutes), so results drop in later.

**Read first:** the Rules §7a and the Handbook deliverable definitions (links in `CLAUDE.md`); `HANDOFF.md` (rubric, deliverables, dates); `docs/model_and_assumptions.md` (D4, drafted); the judging scorecard and transparency/policy-insight reports in `reports/judging/2026-10-19-0518-e31b4ed/` (gitignored, local); `docs/analysis_plan.md` D-019 to D-023 (what the ADU scenario does and what it can't say); `docs/data_availability.md`.

**Deliver (one PR):**
1. `docs/policy_scenario_comparison.md` (D6): the four required sections (comparison to baseline; drivers of differences; critical assumptions; model limitations), each with real text where it doesn't depend on numbers, and clearly marked placeholders (`[RESULT: …]`) where it does. Include a "what this model can and cannot say" box per scenario (judging finding PI) and the publishing rule (place/region only, ≥20 eligible parcels, D-015). Keep within 4 pages; `compliance_check.py` checks ≥30 words per section.
2. `docs/build/deck-outline.md`: slide-by-slide outline (title, one-sentence message, visual), ≤30 slides, for a legislator audience; and `docs/build/video-script-outline.md` (≤5 minutes).
3. No numbers that aren't already on main; every claim traceable to a doc or decision.

**Done when:** PR open with green CI; D6's compliance WARN cleared or reduced to placeholders only.
