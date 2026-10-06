# Lotline — Theme 1: ADU natural-experiment study design (draft, 2026-09-30)

Goal: measure how much ADU production real reforms caused, using older reforms (long post-periods) and comparison areas that did not reform, to calibrate Lotline's ADU scenario (one detached/semi-detached ADU ≥600 sf per single-family parcel, no added parking).

## What the evidence already says
- **No rigorous causal study of ADU production exists.** The published record is before/after counts, cross-sections, and papers that use the reforms to study property values. HUD-funded UCLA/UC Irvine parcel studies were pending as of 2025. A controlled design fills a real gap (scores on Policy Insight and Methodological Soundness).
- **Strong reforms in high-cost markets:** permits rose roughly 4x–30x over the pre-period — LA ~30x within 1–2 years (2017), California statewide ~15–20x over 5–6 years, Portland ~20x over 6 years, Seattle ~3–4x, Austin ~3x (pre-trend already rising). Treat these as upper bounds: they also include housing booms and formalization of existing unpermitted units.
- **Partial reforms did little:** Washington DC <30/yr, Minneapolis ~20/yr before 2021, New Hampshire 0.1–1.5 per 1,000 houses/yr.
- **Working calibration band (inference, uncertain):** about 2–5 ADU permits per 1,000 single-family lots per year at maturity for a strong reform in a high-cost city (Portland ≈ 4); about 1–3% of lots with an ADU after 5–10 years. Weak markets or partial reforms ≈ 10x lower.
- **Lag:** immediate where cheap conversions and pent-up demand exist (LA garages); 2–3 years to plateau for detached units (Seattle ~3 yrs; Portland kept rising ~6 yrs). Completions trail permits by ~6 months–2 years.
- **What drives uptake:** home/land values and rents; parking waivers; no owner-occupancy rule; fee cuts (Portland SDC waiver); ministerial approval and pre-approved plans (Seattle 80 vs 133 days); lot size and existing garages. Financing is the persistent limit (Portland: 62% cash, 2% construction loans). HOAs suppress uptake.

## Measurement constraints
- **Census BPS and ACS cannot identify ADUs** (detached ADUs are counted as 1-unit permits). Outcome data must come from sources that flag ADUs.
- **California HCD APR Table A2** is the only open, multi-jurisdiction, parcel-level dataset that tags ADUs (2018 onward; APN errors, duplicates; ~96% geocodable).
- City ADU datasets: Portland (PortlandMaps ADU report, address/taxlot, multi-year), Seattle (AADU/DADU layers, 2005–present), Austin (ADU permits dataset), Raleigh (2020+), Los Angeles (permit text 2013+), Salt Lake City (2019–22 reports), Massachusetts ADU tracker (2025+).
- Unpermitted ADUs are common (San José: ~3.6 unpermitted per permitted, 2016–20), so part of any jump is formalization. Record conversions vs new builds separately.
- Commercial Shovels.ai classifies ADUs nationally but is unvalidated and paid; the Rules allow paid data only with a free access path for end users, so prefer open city data for anything the tool depends on.

## Recommended designs (oldest and cleanest first)
| # | Treated | Reform | Post-period | Controls | Data | Main threats |
|---|---|---|---|---|---|---|
| 1 | **Portland, OR** | SDC fee waiver 2010 (made permanent 2018); state SB 1051 2018 | ~15 yrs | Vancouver / Clark County WA, clean to ~2017 | Portland ADU report (address-level); Clark County permit pull | Many overlapping Portland reforms; Clark County reformed 2018 |
| 2 | **Los Angeles + California cities** | State ADU laws 2017 and 2020 | 6–9 yrs | Dose design: cities restrictive before 2020 vs already permissive; out-of-state Phoenix / Las Vegas (untreated to ~2024) | APR A2 parcel-level 2018+; LA permit text 2013+; old APR second-unit counts pre-2018 | No untreated CA city; COVID; 2022 rate shock; SB 9 (2022) |
| 3 | **Seattle** | 2019 ordinance (2 ADUs/lot, no owner-occupancy or parking) | ~6 yrs | Puget Sound cities, clean until HB 1337 bites ~2025 | Seattle 2005–present; controls need city permit pulls | Tacoma reformed 2019; Seattle MHA upzoning 2019 |
| 4 | Weak-reform contrast | NH SB 146 (2017), Minneapolis 2014 (owner rule until 2021), DC 2016 | 6–12 yrs | — | Sparse local data | Low volume; used to show what *partial* reforms yield |
| — | Deprioritized | Connecticut PA 21-29 opt-in vs opt-out (68% opted out) | ~3 yrs | Self-selected | No ADU series | Too short; endogenous opt-out |

**Method:** staggered difference-in-differences / event study (e.g., Callaway–Sant'Anna) with pre-trend checks; synthetic control for single-city cases (Portland, Seattle); within-city eligibility contrasts where rules differ by parcel (e.g., LA transit-parking waiver). Outcome: ADU permits and completions per 1,000 single-family lots, split conversion vs new.

**Output for Lotline:** an uptake curve (years since reform → ADUs per 1,000 SF lots) with a range, scaled by local home value/rent so it transfers to data-sparse states.

## Sources
Terner Center 2020 (https://ternercenter.berkeley.edu/wp-content/uploads/pdfs/Reaching_Californias_ADU_Potential_2020.pdf) · Marantz, Elmendorf & Kim 2023, Cityscape 25(2) (https://www.huduser.gov/portal/periodicals/cityscape/vol25num2/ch5.pdf) · Sightline LA 2019 (https://www.sightline.org/2019/04/05/la-adu-story-how-a-state-law-sent-granny-flats-off-the-charts/) · Urban Institute 2020 (https://www.urban.org/sites/default/files/2023-08/Land%20Use%20Reforms%20for%20Housing%20Supply.pdf) · Seattle OPCD ADU report 2024 (https://seattle.gov/documents/departments/opcd/ongoinginitiatives/encouragingbackyardcottages/opcd-aduannualreport2024.pdf) · Mercatus NH 2023 (https://www.mercatus.org/research/policy-briefs/new-hampshire-adu) · Jo et al., JAPA (https://dho.stanford.edu/wp-content/uploads/JAPA.pdf) · Oregon DEQ ADU survey 2014 (https://www.oregon.gov/deq/FilterDocs/ADU-surveyinterpret.pdf) · CA APR data (https://data.ca.gov/dataset/housing-element-annual-progress-report-apr-data-by-jurisdiction-and-year) · Portland ADU report (https://www.portlandmaps.com/reports/index.cfm?action=accessory-dwelling-unit) · Seattle DADU layer (https://data-seattlecitygis.opendata.arcgis.com/datasets/SeattleCityGIS::detached-accessory-dwelling-units-dadus/about) · Austin ADU permits (https://data.austintexas.gov/Building-and-Development/Building-Permits-Issued-for-Accessory-Dwelling-Uni/687g-qcqy) · Desegregate CT opt-out findings (https://accessorydwellings.org/wp-content/uploads/2024/06/ae3e0-publicact21-29initialfindings-desegregatect28129.pdf)
