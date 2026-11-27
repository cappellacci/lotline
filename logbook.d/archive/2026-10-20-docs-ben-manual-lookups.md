### LB-NNN · 2026-10-20 · Data: Ben's manual ADU ordinance lookups (Minnesota metro, plus Dayton OH)
- **Question:** When did the metro places the pipeline couldn't read allow ADUs, if ever?
- **What I did:** Ben looked up 4 places one by one (`manual-lookups.csv`: Inver Grove Heights, Dayton OH, Dayton MN, Elko New Market) and filled 32 rows of the priority table (`Minnesota-manual-lookups-todo.csv`, from the blank `manual-lookups-todo.csv`). WS-CORE reviewed them: 12 adoptions dated within 2016–2025, 9 "not allowed" answers (mostly unsourced), 7 left unknown (ambiguous answers, or Brooklyn Center, whose link is Brooklyn Park's page).
- **Inputs:** official city sites, codes and agendas, and some secondary sources (local news, citizenportal.ai), as noted per row.
- **Outputs:** `docs/research/ordinances/manual-lookups.csv`, `docs/research/ordinances/manual-lookups-todo.csv`, `docs/research/ordinances/Minnesota-manual-lookups-todo.csv`.
- **Findings:** Many answers came from AI search summaries; unsourced "not allowed" answers are coded with a flag for a second check.
- **Decisions:** coding rules approved by Ben (2026-10-20): dated adoptions with his source; unsourced fields blank (D-022 draws them); unsourced "none" flagged; ambiguous rows stay unknown.
- **AI:** Ben's lookups (some via AI search); WS-CORE structured and reviewed them.
- **Open / next:** WS-MN codes them into `config/reforms/mn.csv`; WS-OH checks Dayton OH; then the one-time D-023 run.
