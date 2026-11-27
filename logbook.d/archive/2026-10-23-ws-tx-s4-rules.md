### LB-NNN · 2026-10-23 · Rules: Texas ADU and missing-middle rules, places 21-40 (Texas plan S4/S5)
- **Question:** what are the ADU and missing-middle rules, with dates, for Texas's places 21-40, and which of
  the largest places still need a hand lookup?
- **What I did:**
  - Checked robots.txt: the official code hosts block automated reading (Municode Cloudflare challenge,
    ecode360 disallows ClaudeBot, American Legal 403); the zoneomics.com mirror allows all agents.
  - One read per city (mirror index, then the chapter holding the residential rules) for 20 places; one direct
    read of Killeen's overlay page.
  - Coded what the text settled with `scripts/dev/tx_rules_21_40.py`, every row flagged for a second coder;
    wrote fill-in tables for the rest.
- **Inputs:** Texas data plan (`docs/build/tx-data-plan.md`, approved by Ben 2026-10-23); conventions of
  `scripts/dev/tx_adu_rows.py`; D-022, D-024.
- **Outputs:** 17 rows in `config/reforms/tx.csv` (10 ADU, 7 missing middle);
  `docs/research/ordinances/tx-adu-lookups-todo.csv` (14 places + second-coder line) and
  `tx-mm-lookups-todo.csv` (32 places); `scripts/dev/tx_rules_21_40.py`; ordinances README.
- **Findings:**
  - Rentable ADUs: Waco (Ord. 2023-969, 2023-11-07, owner-occupied), Denton (amended 2023-03-07), McAllen
    (2026 UDC), College Station (owner-occupied living quarters), Round Rock (attached, SF-3 only), Wichita
    Falls (2003, lots of 10,000+ sq ft). No rentable ADU: Mesquite, Midland, Sugar Land, Richardson.
  - Missing middle: one dwelling per single-family lot in Mesquite, Waco, Round Rock, Richardson, Abilene and
    Edinburg (coded `unit_cap = 1`, untreated on evidence); League City allows duplexes in its small-lot RSF-2
    district (2020). Texas's treated missing-middle places stay Austin and Houston, plus League City partly.
  - Several dates are history-note dates that may be recodifications (Denton, College Station, League City):
    marked CHECK before D-024/D-025 use them as events.
- **Decisions:** none.
- **AI:** Claude read the mirror pages through a summarising fetch tool and coded only facts the summaries quoted
  with section numbers; nothing was read from blocked hosts. All rows await a second coder.
- **Open / next:** Ben's todo tables (Corpus Christi, Pasadena, McKinney, Killeen first); second coder for 33
  flagged rows.
