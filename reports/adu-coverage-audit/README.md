# Audit: how ADU rule rows are coded for coverage and for "no ADUs" (follow-up to D-095)

Built by `scripts/dev/adu_coverage_audit.py` from `config/reforms/*.csv` and the coverage the engine and the fit
compute (`scenarios.adu.coverage_map`, offline). Nothing is changed, fitted or scored. `rows.csv` lists every
flagged row with its text, for hand review; `summary.json` has the counts.

582 ADU rule rows. How their coverage is read: citywide 467, zone list at the 0.75 judgment 75 (+15 with a
measured lot minimum), lot minimum measured 11, limited area (0.2 judgment) 11, zones measured on parcels 3.

| Flag | Rows | In fit places | What goes wrong |
|---|---:|---:|---|
| **blank**: every rubric field blank, no `adus_per_lot` 0 | 7 | 5 rows, 5 places (Burnsville, Cottage Grove, Maplewood, Rosemount, one more MN) | Read as "ADUs allowed, every restriction unknown" (`current_rules`), though the text says "not allowed" (Rosemount) or "unknown / not settled". Their switch to a coded rule creates 4 of D-095's 10 events. |
| **zones_switch**: a place's rows alternate between a zone list and none | 55 | 34 rows, 15 places, incl. Portland, Bend, Asheville, Charlotte, Minneapolis, Raleigh | Coverage jumps between 1 (no list) and 0.75 (list, judgment) with no change in where ADUs are allowed. E.g. Charlotte's 2012 list of every single-family district reads 0.75; its 2023 "any district" text reads 1.0, a 33% step that is only coding. |
| **area_text_citywide**: text names districts or areas, read as citywide | 103 | 73 rows, 41 places | May overstate coverage. 35 rows in 20 fit places are **strong** ("only", "not allowed in", "rural", "overlay"), e.g. Forest Lake 2004 (rural districts only, read as all of the city), Durham, Medford, College Station. |

**Root cause.** Zone lists are read at 0.75 when parcels carry no zoning (most places), even where the list names
every single-family district, while a rule described as "all districts" with no list reads 1.0. And blank
placeholder rows read as allowed.
