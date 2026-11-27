### LB-NNN · 2026-10-20 · Policy analysis: WS-MN metro ADU rule histories for D-023
- **Question:** Which Twin Cities metro places have dated ADU rules, so the D-023 staggered-adoption estimator has
  enough adopters within 2016-2025?
- **What I did:**
  - Coded `config/reforms/mn.csv` rows (schemas 1.7 citation columns) from the city-ordinance pipeline records
    (`docs/research/ordinances/metro-adu-adoption-2026-10-20.json`: only entries with a read link and a quote;
    `verified_by = pipeline-checker`, checker verdict not stored), Ben's `manual-lookups.csv` (Inver Grove Heights,
    Dayton MN, Elko New Market) and Ben's filled rows in `Minnesota-manual-lookups-todo.csv` under his rules
    (dated adoptions with unsourced fields blank; unsourced "not allowed" as `adus_per_lot = 0` needing a second
    check; seven places left unknown).
  - Ran `uv run python scripts/dev/estimate_adu.py --smoke` before and after.
- **Inputs:** the three files above; `src/lotline/model/estimate_adu.py`.
- **Outputs:** `config/reforms/mn.csv` (43 → 105 rows, 57 more places), `tests/states/mn/test_reforms.py`.
- **Findings:** Smoke panel grows from 21 to 77 places; treated places 12 → 32; adopters within 2016-2025 6 → 25;
  never treated in the window 45; 108 places still lack a dated rule. 21 quoted pipeline entries have no date and
  are not coded. Hastings's date and ordinance number (2023-10-18, Ord. 23-43) match St. Paul's Ord. 23-43 exactly:
  likely a mix-up, flagged for a second check.
- **Decisions:** East Bethel (no detached, attached unknown, no date) not coded: a dateless row of unknown type would
  enter D-023 as a 2010 adopter.
- **AI:** Claude wrote the coding script and tests and ran the smoke check; rows are single-coder
  (`pipeline+ben` / `ben`).
- **Open / next:** second checks of Ben's unsourced "not allowed" rows and Hastings; dates for the 21 undated quoted
  entries.
