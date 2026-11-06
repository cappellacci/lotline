# Missing-middle uptake after by-right reforms: outside evidence, a plausibility check for D-038 (2026-11-03)

**Status:** plausibility check only (D-037 amendment, Ben 2026-11-03: "we need to be rolling our own"). The
values in `config/params/mm_hazard.yaml` are fitted on our four states (D-038, `reports/mm-d038/`; replaced on 2026-11-06
by D-054's refit, adopted under D-055, `reports/mm-d054/`). This table is what D-038's fit was compared against: the implied mature rates, 0.07–0.76 per 1,000 at each fit place's own dose
and price-to-cost, fall inside it. The table was compiled before any missing-middle fit or scenario number.
Sources are rows of `lotline-evidence-register.csv` (E-numbers).

**What is compared.** D-037 builds the missing-middle effect as eligible parcels (rule 1.1, D-014) × the
share that pencil (pro forma) × an uptake hazard × a ramp. The hazard is the yearly chance that an eligible
parcel gets a new 2–6 unit building once the reform has matured, at the reference place's market. Its unit here
is **projects (buildings) per 1,000 eligible parcels per year**, the fit's unit. Units per project are a separate parameter.

**Held out.** Minneapolis, Durham, Durham County and Raleigh are D-037 out-of-sample test places, so their
outcomes did not set any value (Minneapolis is shown for context from sources already in the register). Charlotte,
Mecklenburg County and St. Paul outcomes were not read.

## The common-unit table

D = derived here (arithmetic shown in the notes); S = stated by the source.

| Place, reform | Source | Denominator | Units / 1,000 parcels / yr | Projects / 1,000 / yr | Ramp | Used for |
|---|---|---|---|---|---|---|
| **Portland OR**, RIP (Aug 2021), RIP2 (Aug 2022) | E022 (city report, Jan 2025) | 148k lots in single-dwelling zones (S) | 2023: ≈2.9 (D); RIP2 year 1: 3.5 (D, 514 units); 2021–24 average 1.87 (D from zone rates); R2.5 4.3, R5 2.0, R7 0.5, R10 0.1 (S, annual) | 2023: ≈0.85 (D); average ≈0.55 (D) | Flat in year 1, near plateau in year 2 | Main comparison (full-dose, strong market) |
| **Houston TX**, 1998 Inner Loop, 2013 citywide lot-size cut | E105 (Furman Center 2023) | 282,770 single-family parcels outside block-vote areas (S) | 1.35 (D, 2007–20 average) | 0.35 (D, average); ≈0.5–0.7 (D, 2015 peak, read from a chart) | About 15 years to peak; recessions in between | Comparison (lot-split townhouses); slow ramp |
| **Auckland NZ**, Unitary Plan (Nov 2016), MHS and MHU zones | E001 (JUE 2023), E107 (WP 012) | Upzoned parcels; count not published; MHS 146.8 km², MHU 74.6 km² (S) | +45 dwellings per 1,000 upzoned parcels over non-upzoned in 2022 (S: 0.045 per parcel; greenfield included) | ≈10 (D, at 3–5 dwellings per site; assumption) | Rising every year 2016–22; half-way ≈ year 4 | Upper bound (extreme market); slow ramp |
| **Lower Hutt NZ**, PC43 (2017–20) | E004 | No parcel count | ≈+23 per 1,000 existing dwellings in 2022 (D) | — | Rose 2018–22, fell 2023 | Context: a single-city upzoning can be large |
| **California**, SB 9 (2022) | E026, E027, E028, E110 | 6.1M eligible parcels (S, Terner simulation) | ≈0.02 (D, 140 units in 2023) | ≈0.01–0.02 (D) | Flat near zero | Lower bound (restricted rule) |
| **Oregon HB 2001 cities** | E024, E108 | Not published | — | — | Many cities near 0; Eugene flat ≈100 units a year | Selection: Portland is not typical |
| **Spokane WA**, BOCA (2022–23) | E025, E109, E113 | Not published | — | — | Middle share (ADUs included) 3–4% → 8% → 10% → 17% (2025): still rising in year 3 | Ramp shape only |
| **Arlington VA**, EHO (Jul 2023) | E106 | Not published | — | 22–23 zoning permits a year under a 58 cap; 8 reached a building permit | Cut off by litigation | Frictions (caps, litigation) |
| **Austin TX**, HOME (2024) | E111 | Not found | — | — | 436 units in year 1 | Context (secondary source) |
| **Edmonton AB**, 2024 bylaw | E112 | Not published | — | — | Row housing 8× its prior average in year 1 | Fast-ramp case |
| *Minneapolis MN*, 2040 Plan (2020): test place, not used | E021 | ≈72.5k lots (unverified) | 0.87 (D, 2023) | 0.33 all 2–4-plexes, 0.15 on former single-family lots (D, 2023) | Peak in year 4 | Not used here (D-037 test place) |

## Notes on the derivations

- **Portland.** The report's per-lot rates are annual: p.25 says "Each year…", and the chart axis reads "Annual avg.
  MH units permitted per 1,000 lots". Lots by zone are printed under the chart: R2.5 26k, R5 74k, R7 32k, R10 13k,
  R20 3k, total 148k.
  - Lot-weighted average: (4.3×26 + 2.0×74 + 0.5×32 + 0.1×13) / 148 = 277 / 148 = 1.87 units per 1,000 a year.
  - Mature year: 2023 units read from the p.13 chart are about 430 (fourplex ≈225, cottage ≈95, duplex ≈37,
    triplex ≈30, attached ≈30, sixplex ≈12), so 430 / 148 = 2.9. RIP2's first year (Aug 2022–Jul 2023) is stated:
    514 units, so 514 / 148 = 3.5.
  - Projects are not published. Dividing each type by its units (cottage clusters at 4) gives about 125 projects
    in 2023, 3.4 units per project, so 0.85 per 1,000 a year. The 2021–24 average is 1.87 / 3.4 = 0.55.
  - "Middle housing" here includes attached houses (townhomes) and cottage clusters and excludes ADUs. The
    counts are permits, not completions. "Lot" is not defined.
  - Market: mortgage rates rose from about 3% to 7% over 2021–23. System development charges are exempt for
    for-sale homes under a price cap. An expedited lot-division path (Oregon 2021) means over half of new
    middle units sit on divided lots.
- **Houston.** 1,392 projects / 282,770 parcels / 14 years (2007–20) = 0.35 per 1,000; 5,359 / 282,770 / 14 =
  1.35 units. 96.6% of projects lie inside the Loop, so the citywide denominator understates the Inner Loop
  rate. Counts are completions (tax-record parcel links); subdivisions before 2005 are missed. Most Houston
  townhouses were built on non-single-family land and are not in this count.
- **Auckland.** The 0.045 coefficient is consents (dwellings) per parcel over non-upzoned parcels, all
  development; the authors report infill effects smaller and greenfield effects up to 0.19. Market: nominal
  prices up about 350% 2001–18, price-to-income about 9. MHS and MHU allow 3 dwellings per existing parcel by
  right, with no minimum lot size.
- **SB 9.** 140 units / 6.1M parcels = 0.023 per 1,000 a year. The 6.1M denominator is Terner's simulated
  eligible set; the 140 is a self-reported statewide count reported by an advocacy group.

## What the evidence says, in one paragraph

Where a 2–6 unit building is allowed by right on ordinary single-family lots in a strong US market, mature
uptake runs about **0.3–0.9 projects (1–3.5 homes) per 1,000 eligible lots a year** (Houston, Portland). It is
higher where the allowance is generous and land is dear (Portland R2.5 ≈1.3 projects; Auckland far higher),
lower on large-lot zones (Portland R7 ≈0.15, R10 ≈0.03) and close to zero where the rule carries owner-occupancy
or fee frictions (SB 9). Uptake reaches its plateau in about two years in Portland but keeps rising for six
years in Auckland and over a decade in Houston. The best-documented places are the successes; the other Oregon
cities, Eugene and Arlington show that a typical adopter does less.

## Gaps worth closing later

- Portland's yearly counts are read from charts; the city's permit series by zone and year would replace them.
- Auckland parcel counts by zone (LINZ parcels joined to Unitary Plan zones) would replace the area-based guess.
- A published eligible-lot count for Spokane, Eugene or another HB 2001 city would add a second US denominator.
- *Missing No Longer?* (E028) could not be fetched (HTTP 403); its SB 9 table was not re-read.
