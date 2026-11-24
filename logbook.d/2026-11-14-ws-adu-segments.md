### LB-NNN · 2026-11-14 · ADU model · Can the ADU data be split another way, so the model works across all five states?

- **Question:** D-084 and D-085 left no ADU form passing any data tier, and a place's own past rate forecast
  better than the model. Ben asked whether the data can be characterized or segmented another way (2026-11-14).
  He also stopped D-086 at the first coding: a second coder would not change the 6-events-in-2-states count.
- **Output:** D-088 (proposed) in `docs/analysis_plan.md`. It has two parts:
  - **Part 1**, a descriptive breakdown of the place effects by state, by place type and by counting source,
    with a reading rule;
  - **Part 2**, Form P: place types (core city, suburb, town) from national data, shared across states, scored
    on D-075's leave-one-state-out tiers, tests A–B and D-085's test D under a fixed decision rule.
- **Numbering:** D-088, because Ben has a D-087 running in another session.
- **What Claude did:** drafted the entry before any type, count or fit was made.
  - Claude first suggested measuring ADUs per new home built. It then found that D-083's X4 (new houses per lot)
    had already come out flat, so the entry records that idea as considered and not used.
- **How it was checked:** the entry's numbers were checked against D-083's screen table and the D-084 and D-085
  entries; `compliance_check.py`.
