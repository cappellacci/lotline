### LB-NNN · 2026-10-20 · Build: ADU hazard transported by price-to-cost, equity and rates (D-018)
- **Question:** How likely is an eligible single-family lot to add an ADU each year after a strong reform, here?
- **What I did:** `src/lotline/model/hazard.py`: mature hazard = anchor (4 per 1,000 lots a year, Portland)
  × share of lots where an ADU pencils (from the pro forma's price-to-cost, lognormal across lots) relative to
  the reference's, × home-equity and mortgage-rate terms (C22), × a logistic ramp after adoption; calibration
  distance and mean-preserving widening outside the reference cities' range. `config/params/hazard.yaml` (18
  parameters with sources; judgment labelled). `scripts/dev/adu_reference.py` recomputes the reference values
  from ACS 2015-19 (Portland, Seattle, Los Angeles; fetched through the IO layer) and FRED.
- **Inputs:** adu-study-design.md; two-prong design; protocol §5.5-5.8; C01, C22, C24; E038-E047, E073.
- **Outputs:** `src/lotline/model/hazard.py`, `config/params/hazard.yaml`, `tests/model/test_hazard.py`,
  `scripts/dev/adu_reference.py`, `docs/model_and_assumptions.md` (ADU hazard section, status, parameter
  table), `docs/analysis_plan.md` (D-018).
- **Findings:** Portland's ADU price-to-cost is 1.13 (Seattle 1.46, LA 1.31) at central parameters. A place at
  $1,100 rent, half Portland's home value and 2 points higher rates gets 1.42 per 1,000 lots a year.
- **Decisions:** D-018 proposed.
- **AI:** Claude designed the forms, wrote module, parameters and tests; one place worked by hand in the test;
  monotonicity checked over random parameter draws.
- **Open / next:** scenario module (`scenarios/adu.py`); fit the comparables model (protocol §5.7) to replace
  the band anchor; local construction costs for reference and target; V2.
