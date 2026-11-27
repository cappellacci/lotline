### LB-NNN · 2026-10-20 · Data: City-ordinance pipeline, batch 1 (MN top 20, Austin, Raleigh, Durham)
- **Question:** Where are each city's official ordinances, fee schedules (2016-2025), ADU programs and 2-4 unit legalization dates, and which must Ben fetch by hand?
- **What I did:** Ran the lean city-ordinance workflow (23 research agents, 23 independent checkers; robots.txt checked before any fetch, never worked around). Saved the records and wrote Ben's manual checklist.
- **Inputs:** official city, county and state web pages and documents.
- **Outputs:** `docs/research/ordinances/batch1-2026-10-20.json`, `docs/research/ordinances/README.md`, `docs/build/manual-ordinance-pdfs-batch1.md`.
- **Findings:** 168 document links (124 PDFs); 99 read; 96 need a manual download (8 robots.txt disallows, the rest 403s or bot blocks); 266 fee items, mostly from current schedules (few years before 2022); 25 ADU programs, mostly guides (2 pre-approved-plan programs, 1 loan or grant, no fee waivers found); 179 manual checklist items in all.
- **Decisions:** none.
- **AI:** Claude Code workflow (46 agents, about 3.5M subagent tokens); WS-CORE assembled the outputs.
- **Open / next:** Ben's manual downloads; converting checked records into `config/reforms` and `config/fees`.
