# Who the new homes serve: research and method for the AMI strip (WS-NEED-AMI part B)

Written 2026-11-17 after the second Tomasso office hours (`office-hours-2026-11-17-tomasso-notes.md`, B5). Status: proposal for Ben; nothing built. Code read at `origin/main` 78778f58.

## The question
For each kind of home a reform adds, what income does a household need to live in it, and where does that sit against the area's median income? Shown as context beside the housing need and gap, not as a model output.

## What the research says

1. **What "AMI" means.** In housing programs it is HUD's Median Family Income (MFI) for an area, published every year with income limits by household size. Areas are metropolitan areas, parts of some metropolitan areas, and each non-metropolitan county. FY 2026 values came out on 2026-05-01 (a month late, because the Census delayed the 2024 ACS). The MFI is the 4-person figure; other sizes scale from it (1 person 70%, 2 persons 80%, 3 persons 90%; 8% more per person above 4).
2. **The convention for turning a rent into an AMI level** is the tax-credit one (IRC 42(g)(2)): gross rent, utilities included, is affordable at X% AMI when it is no more than 30% of the X% income limit for an assumed household of 1.5 persons per bedroom (one person for a studio). A 1-bedroom uses the average of the 1- and 2-person limits; a 2-bedroom uses the 3-person limit. Using it means our "60% AMI" is the same thing a housing official means by it.
3. **The frame Amy pointed to (Kronberg Urbanists + Architects).** As reported from a CNU session: homes affordable below 60% AMI need substantial subsidy; above 80% AMI can be delivered by zoning reform alone; 60 to 80% is the gap, which small units can reach. That gives the axis three bands to read a marker against. Source is a write-up of the slide, not the slide; cite it as such.
4. **Getting the data.** HUD publishes the limits as a downloadable file per year on its Income Limits page and through an API. The API needs a free account token and its terms ask for a notice ("This product uses the HUD User Data API but is not endorsed or certified by HUD User"). The file needs neither, so the file is the better fit for single-command setup (T3) and no keys. Federal work, public domain. **To confirm before building:** the exact FY 2026 file URL and its columns (I could not open huduser.gov from this session).

## What the engine already has (and one finding)

- **Rent.** Both the ADU and the missing-middle models take a place's ACS median gross rent (B25064, 2025 dollars). ADUs multiply it by `adu_rent_to_median_ratio` (1.0, range 0.8 to 1.2, marked as judgment in `hazard.yaml`). The plex model uses the same median rent with no premium, because any constant factor cancels in its fit (`estimate_mm.plex_price_to_cost`).
- **Place types** (core city, suburb, town) exist for ADUs (`adu_place_types.yaml`, D-088) and are in the bundle (`results_adu_place_types`).
- **Pro forma** (`model/proforma.py`): cost to build, vacancy 5%, operating costs 35%, cap rate 5.5%.
- **Finding: at the model's assumed rent, the two home types land on nearly the same AMI level,** because both rent at the place's median. They differ only through household size. A strip that shows only "rent the model assumes" would say little more than "median rent is about this share of median family income here". The method below adds a second measure that does differ by home type.

## Proposed method

For each place *j* and home type *h* (ADU = 1 bedroom, 800 sq ft; plex unit = 2 bedrooms, 1,000 sq ft; sizes from `proforma.yaml`):

1. **Two rents, both monthly gross rent in 2025 dollars.**
   - *Market rent* `R_mkt = median gross rent_j x ratio_h` (the ADU ratio from `hazard.yaml`; the plex ratio is a new parameter, 1.0 with a range, since the model has none).
   - *Break-even rent* `R_be = cost_h,j x cap rate / (12 x (1 - vacancy) x (1 - operating share))`: the rent at which the pro forma's value equals its cost, fees included. This is what a new home of that type has to rent for to get built, which is the Kronberg question. It differs by home type (cost per unit) and moves with the fee scenario.
2. **Income needed** `Y = 12 x R / 0.30`.
3. **AMI share** `S = Y / L_100(area_j, n_h)`, where `L_100` is HUD's MFI for the place's county or metro area scaled to the household size `n_h = 1.5 x bedrooms` (ADU: average of the 1- and 2-person factors, 0.75; plex unit: 3 persons, 0.90). Put MFI and rent in the same year's dollars with the engine's CPI.
4. **Roll up** to place type and state, weighting each place by the homes the reform adds there (midpoint), so the figure describes the homes the model predicts, not the average town.
5. **Ranges.** Carry the rent ratio's low and high (and, for break-even, the pro forma draws) through to P10/P50/P90. Never a share without its range (S6).

**Hand-worked example for the unit test** (round numbers, not a result): rent $1,500 a month needs 1,500 x 12 / 0.30 = $60,000 a year. With a 4-person MFI of $132,300, the 1.5-person figure is 0.75 x 132,300 = $99,225, so an ADU at that rent serves 60,000 / 99,225 = 60% AMI. The same rent for a 2-bedroom plex unit: 0.90 x 132,300 = $119,070, so 50% AMI. (The MFI is roughly Raleigh's FY 2026 value as reported second-hand; replace it with the HUD file's figure.)

## What the card shows

One row per home type; a 0 to 150% AMI axis with the three bands (under 60% usually needs subsidy; 60 to 80%; above 80%); a filled marker at the market-rent share with its range and the dollar income beside it ("about $60,000 a year"); a hollow marker at the break-even share. Where the hollow marker sits right of the filled one, the home does not pay for itself at local rents, which is the same story the "pays off" step tells. Optional third row for contrast: a new single-family house for sale (needs a down payment share, tax and insurance rate: three more sourced parameters). Without it the strip has no "compared with what"; with it the card is larger. Ben's call.

## Limits to state on the card and in D4

- The model predicts how many homes, not their rents. Market rent here is an assumption the model already makes, shown in a new unit.
- New homes usually rent above the median of existing homes; the ratio's range covers some of that, and its source is judgment.
- AMI is family income for the whole area, owners included; the median renter earns less.
- Many ADUs are not rented at market (family, home office), so "serves" is about what they could rent for.
- Shares for towns rest on county-level MFI and small-sample ACS rents.

## What it needs

| Piece | Where | Note |
|---|---|---|
| HUD income limits adapter | `adapters/national/` (WS-CORE path) | file download through the IO layer; provenance and availability rows |
| Parameters | new `config/params/affordability.yaml` | 30% rule, bedrooms per home type, 1.5 persons per bedroom, HUD size factors, plex rent ratio, band edges; each with its source |
| Calculation | new `model/affordability.py` | pure function; unit test on the worked example |
| Bundle table | `results.py`, `docs/schemas.md` | `affordability`: home type, place type, rent kind, rent, income, AMI share (P10/P50/P90); schema bump, `contract-change` issue |
| App strip | `template.html` | under the need chart |

## Decisions for Ben

1. Show break-even rent as well as market rent (recommended; it is the only part that differs by home type), or market rent only.
2. HUD MFI by file download (recommended) rather than ACS median household income.
3. Household size by the 1.5-persons-per-bedroom convention (recommended; replaces the 2- and 3-person suggestion in the brief).
4. Include the single-family contrast row or not.

## Sources

- HUD, Statement on FY 2026 Median Family Income Estimates and Income Limits: https://www.huduser.gov/portal/datasets/il/il26/Statement-on-FY-2026-Income-Limits.pdf
- HUD Office of Native American Programs, PG 2026-01 (areas and method of the FY 2026 MFI): https://www.hud.gov/sites/default/files/PIH/documents/ONAP-PG-2026-01-FY26-IHBG-Income-Limits.pdf
- HUD User API documentation and terms: https://www.huduser.gov/portal/node/8148 ; https://huduser.gov/portal/node/9108
- IRS Guide for Completing Form 8823, calculation methods (1.5 persons per bedroom, 30% of the limit): https://gocodebook.com/library/us/federal/us-irs-pub5913-form8823-guide-2024-01/f.7.-calculation-methods
- National Housing Law Project on LIHTC rents: https://www.nhlp.org/?p=2071
- CNU, "Housing choice can make cities more affordable and resilient" (Kronberg's spectrum of affordability): https://cnu.org/node/7911
- Raleigh-Cary FY 2026 4-person 50% limit, second-hand: https://grantsights.com/blog/north-carolina-section-8

## Decisions (Ben)

- 2026-11-19: **show both market rent and break-even rent** (decision 1: yes).
- 2026-11-19: **include the single-family contrast row** (decision 4: yes). Method: the monthly cost of owning a new house (mortgage at `market.yaml`'s forecast rate, property tax, insurance) held to the same 30% of income, for a 3-bedroom household (4.5 persons). Down payment, tax and insurance rates are new sourced parameters. The break-even definition for a for-sale house is to be proposed in the build PR.
- Decisions 2 and 3 (HUD file; 1.5 persons per bedroom) stand as recommended unless Ben says otherwise.
- Build handoff: `docs/build/handoffs/16-need-ami-part-b.md`.
- 2026-11-19: **HUD file downloaded by hand.** huduser.gov answers every scripted request (the page and the file links) with an AWS WAF bot challenge, so the file is saved in a browser and registered with `lotline manifest register --source hud_income_limits` (the Wake roll pattern); no API, no key. Without it `lotline fetch` still runs and the strip is empty.
- 2026-11-19: **Break-even leaves out land and profit for all three home types** (value = construction + soft costs + fees + interest while building; house price = that cost / (1 − selling costs)), as in the models' own price-to-cost. It is a floor, and the card says so.
- 2026-11-19: **The hollow marker sits at today's local fees**; a line under each row follows the fee switch (real local fees cut in half, or the Handbook benchmark). ADU fees are $0 in the model, so the ADU row does not move.
- Build notes (2026-11-19, not decisions): the AMI share's household-size factor is the HUD file's own `l50_n / l50_4` ratio; plex units are priced as the pro forma's duplex (residential code); places are weighted by the ADU scenario's median added ADUs (ADU row) and the missing-middle scenario's mean net homes (plex and house rows), equal weights where a reform adds none.
