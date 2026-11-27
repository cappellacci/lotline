### LB-NNN · 2026-11-15 · ADU · How are coverage and "no ADUs" coded across rule changes? (audit)

- **Question:** D-095 found reforms that read as tightenings. Ben: "Yes, check coverage".
- **Outputs:** `scripts/dev/adu_coverage_audit.py`; `reports/adu-coverage-audit/` (rows.csv for hand review,
  summary.json, README).
- **Result:** three coding patterns, none changed yet:
  - blank placeholder rows read as allowed (7 rows, 5 fit places; 4 of D-095's 10 events);
  - zone lists read at 0.75 judgment while "all districts" text reads 1, so coverage steps with no real change
    (34 rows in 15 fit places, including six of the largest core cities);
  - text naming limited areas read as citywide (35 strong rows in 20 fit places).
- **What Claude did:** traced coverage from `coverage_map` through `current_rules` and `PlaceData.cr`, wrote the
  audit, ran it offline, and read the flagged rows for the event places and the core cities.
- **How it was checked:** flagged rows read by hand for the 10 D-095 events and six core cities; the counts
  come from the script; ruff passes.
