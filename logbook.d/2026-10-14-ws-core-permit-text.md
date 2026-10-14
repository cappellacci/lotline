### LB-NNN · 2026-10-14 · Build: shared permit-description parser (WS-CORE)
- **Question:** Can one tested, explainable parser read unit counts, building type, ADU kind, demolition
  and conversion from free-text permit descriptions, so any state adapter can fill gaps such as Raleigh's
  2024+ multifamily permits with no unit count?
- **What I did:**
  - Wrote `parse_description(text) -> PermitTextFacts` (standard-library `re` only): named, commented
    phrase rules for counts ("48 apt units", "(3) unit", "three units", "6-plex"), type words (duplex,
    triplex, fourplex, 2-4 → DTQ, 5+ → MF5, townhouse, single-family, manufactured), ADUs and their kind,
    alteration (→ 0 new units), demolition (units removed) and conversion (net units). Every value comes
    with `evidence` (rule + matched phrase).
  - Precision over recall: traps (bedrooms, stories, years, sizes, lot/building/permit numbers, "Unit 5",
    "2 HC units", "2 over 2"), project totals on one-building-of-several permits, contradictions and
    buildings named as existing or separately permitted all return None.
  - 91 synthetic test cases in `tests/core/test_permit_text.py`, each hand-checked.
  - Read-only accuracy check on Raleigh permits 2015-2023 (new construction with a plausible recorded
    count); a narrow evaluation pull (permit number, type code, units, description fields) was fetched
    through the IO layer into `LOTLINE_DATA_DIR/raw/raleigh_permits/2026-10-14/permit_text_eval/`.
    Nothing from it is in the repo.
- **Inputs:** `docs/schemas.md` (permits contract), Raleigh adapter (WS-NC), Open Raleigh building
  permits layer (descriptions). No Charlotte or St. Paul data was read.
- **Outputs:** `src/lotline/parse/__init__.py`, `src/lotline/parse/permit_text.py`,
  `tests/core/test_permit_text.py`.
- **Findings:**
  - Raleigh 2015-2023, n = 13,058: a count is returned for 61% of records with 99.9% precision. By type
    (coverage / precision): SFD 98% / 100%; duplex 88% / 98%; 3-4 units 65% / 92% (n = 20); 5+ units
    24% / 96.5% (136 of 141); ADU 88% / 100%; manufactured 90% / 100%. Building type agrees with the
    city's code in 99.9% of the 86% of records where one is returned.
  - Raleigh 2024-2025 5+ unit permits with an empty unit field: 37 of 80 (46%) get a count from the
    description. 5+ coverage is capped by the text: 61% of descriptions are cut at 100 characters and
    many name only the project and building number.
  - Main errors: a project total read as the building's count when the text doesn't say it is one
    building of several; townhouse permits are issued one per townhouse while the text gives the row
    size (so townhouse counts go to `building_units`, not `units_new`); per-unit condo permits that
    describe the whole building. Alteration permits get a positive count in 0.35%; demolitions are
    recognised in 99% and units removed match the city's code in 95%.
- **Decisions:** Proposed: (1) adapters use the parser only to fill a missing structured value, with
  `units_confidence`/`type_confidence = "inferred"`; (2) townhouse row size is not a per-permit count.
- **AI:** Claude Code wrote the parser, tests and the evaluation script (kept outside the repo), iterated
  the rules against the Raleigh error list using only general phrase patterns, and checked every test
  expectation by hand; ruff, pytest and `compliance_check.py` pass.
- **Open / next:** wire into the Raleigh adapter (WS-NC) for 2024+ 104/105 permits (needs the description
  field added to its request; it is excluded today as free text); describe the rules in the methodology
  document; try it on other jurisdictions' descriptions.
