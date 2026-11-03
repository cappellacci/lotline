# Panel counts on the four-state data (thread 14, task 2)

Counts only, no estimate. Built on 2026-11-02 from the processed tables in `LOTLINE_DATA_DIR`, with Ohio's and
Texas's `eligible_parcels` rebuilt after #252, and with the rule date tags read by `model/rule_tags.py` (#264).
Commands:

```bash
uv run python scripts/dev/estimate_mm.py --smoke
uv run python scripts/dev/estimate_pooled_adu.py --smoke
```

## D-024 missing middle (BPS 2–4 unit homes, 2010–2025, places of 10,000+ plus every coded place)

| | MN | NC | OH | TX | All |
|---|---|---|---|---|---|
| Places | 100 | 56 | 172 | 232 | **560** |
| Treated (a by-right rule; any year) | 3 | 14 | 4 | 6 | 27 |
| Adopting inside 2010–2025 | 3 | 10 | 2 | 5 | **20** |

- Place-years with an outcome: 8,763 (197 missing BPS rows stay missing). 73% of place-years are zero; 140
  places never permit a 2–4 unit home (3 treated). Holdouts excluded: Charlotte and St. Paul (and every
  Mecklenburg reporter).
- Treated place-years by event-time bin: 0–1 years 37, 2–3 years 26, 4+ years 148.
- Treated before the window: Apex, Asheboro, Goldsboro, New Bern, Grove City (coded 1979) and El Paso (T =
  1990, where the adoption-year search starts) and Dayton (T = 2007). Asheboro and Goldsboro are `[predates]`;
  Apex, New Bern and El Paso are earliest-known rows dated on or before 2010-01-01, the data threads' "allowed
  before the window" placeholder, which `rule_tags` now reads like `[predates]` (fix found by these counts,
  on #264).
- In-window adopters (T = first year the rule is in force on 1 July): MN Minneapolis 2020, Richfield 2023,
  St. Louis Park 2025; NC Durham city and county 2020, Burlington 2020, Garner 2023, Mooresville 2022,
  Morrisville 2014, Raleigh 2022, Sanford 2019, Wake Forest 2014, Wilson 2013; OH Cincinnati 2024, Euclid
  2025; TX Austin 2024, Houston 2024, League City 2021, Lewisville 2023, Lubbock 2024.
- **Firm dates only** (the one tag sensitivity): 8 places leave the panel, all in NC: Burlington, Garner,
  Monroe, Mooresville, Morrisville, Sanford, Wake Forest, Wilson. That gives 552 places, 20 treated, 13
  adopting in the window. Without `[earliest-known]` alone the set is the same; without `DATE UNCONFIRMED`
  alone nothing drops (no D-024 event carries it).

**Against the readiness reports:**

| | Readiness | Panel | Difference |
|---|---|---|---|
| MN places / events | 100 / 3 | 100 / 3 | none |
| NC places / events | 55 (+ Durham County if remainders are in) / Durham, Raleigh firm, 8 earliest-known | 56 / 10 adopters | Durham County's remainder is in. Monroe's 2022 rule is by right only in RH (special-use permit in RMD), so it is an event but not a by-right adopter. The firm-dates sensitivity drops exactly the report's 8 places |
| OH places / events | 156 / 2 | 172 / 2 | 16 townships of 10,000+ issue permits and are in the panel; the report counted places only |
| TX places / events | 232 / 5 | 232 / 5 | none |

No remaining difference points to a bug.

## D-025 ADU (pooled hierarchical negative binomial)

Sample (amendment of 2026-11-02 in `docs/analysis_plan.md`): Twin Cities places with Met Council permits
2016–2025 (as before) plus Texas's four record-level cities, each over the years its source counts ADUs in
full.

| | Places | Place-years | Treated | Adopting in the panel years | Never treated | No ADU in any year | ADU permits |
|---|---|---|---|---|---|---|---|
| **Main** | 80 (MN 76, TX 4) | 791 | 31 | 21 | 49 | 53 | 3,192 |
| Firm dates only | 71 (MN 67, TX 4) | 701 | 27 | 17 | 44 | 47 | 3,178 |

- Adopters in the panel years: 2016 1, 2018 2, 2020 2, 2021 1, 2022 2, 2023 5, 2024 3, 2025 5.
- ADU permits a year: MN 26–39; TX 239–386 a year through 2023 (Austin about 85% of them), then 73 and 68 (San
  Antonio and Fort Worth only).
- Texas years: Austin 2016–2023, San Antonio 2021–2025, Fort Worth 2016–2025, Dallas 2016–2023.
- **Austin's ADU flag breaks with HOME (February 2024):** R-102 ADU permits go 243 (2023), 90 (2024), 9
  (2025) while two-unit permits rise to 384 in 2025. HOME lets the second home be permitted as a dwelling unit,
  so the drop is a change in coding, not in building. Austin's 2024–2025 years are out of the panel.

**Against the MN readiness report:** 76 places = the report's 43 places with an in-window change + 28 "no
ADUs" controls + 5 places with a coded rule and no in-window event (Apple Valley, Baytown Township, Denmark
Township, Savage, Stillwater), which the report didn't count. The 4 MN event places outside the panel are St.
Paul (holdout) and Duluth, Rochester and St. Cloud (no Met Council permits). Matches.

**Not in this sample:** North Carolina (8 places with an in-window change) stays out of sample for the
transport test (Raleigh, Durham). Ohio's 15 places stay out: their counts are lower bounds from ADU-only files.
Both are open questions for Ben in the amendment entry.
