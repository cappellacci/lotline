# Thread 16: Who the new homes serve (the AMI strip, WS-NEED-AMI part B)

**Goal:** under the housing-need chart on the Results page, show for each kind of home what income a household
needs to live in it and where that sits against the area's median income (AMI): an ADU, a unit in a duplex to
fourplex, and a new single-family house for contrast. Two markers per row: the rent (or price) the model assumes,
and the break-even rent (or price) at which the home pays for itself. Context beside the need and the gap, not a
forecast. Ben's decisions, 2026-11-17 and 2026-11-19, are at the end of the method doc.

**Read first:** `docs/research/lotline-ami-method.md` (the method; where it and the brief differ, it wins);
`docs/build/workstreams/WS-NEED-AMI.md` part B; `docs/research/office-hours-2026-11-17-tomasso-notes.md` (B5);
`docs/build/handoffs/README.md` (shared rules); `src/lotline/model/proforma.py`, `model/hazard.py` (ADU rent),
`model/estimate_mm.py` (`plex_price_to_cost`), `model/results.py`.

## Before anything else
1. **Four files are not on `main` yet.** They sit untracked in the main checkout (`~/Engineering/lotline`):
   `docs/research/lotline-ami-method.md`, `docs/research/office-hours-2026-11-17-tomasso-notes.md`,
   `docs/build/workstreams/WS-NEED-AMI.md`, `logbook.d/2026-11-17-cowork-office-hours-amy.md`, plus this file.
   Copy them into your worktree unchanged and commit them first, so they land with your first PR.
2. **Part A is on `origin/ws/app-need-ami`** (703b19cb: need chart, which reform adds the most, real local fees by
   default; tests in `tests/app/test_need_card.py`). It was not on `main` at 294f786a (2026-11-18). If it has
   merged, branch from `origin/main`; if not, ask Ben whether to branch from it or wait. The strip goes under
   that chart, so don't build against the old need table.
3. **Open a `contract-change` issue** for the new bundle table and the new national adapter (WS-CORE paths) before
   editing them. Schemas were at 1.17 on 2026-11-18; take the next free number at merge time.
4. **Confirm the HUD file.** Find the FY 2026 Section 8 income limits file on
   https://www.huduser.gov/portal/datasets/il.html (no account or token needed for the file; do not use the API).
   Record its exact URL, columns and area codes in the provenance row. It could not be reached from the Cowork
   session, so nothing about its layout is confirmed. If the site blocks the download, stop and tell Ben.

## What exists
| Piece | Where | Notes |
|---|---|---|
| Place median gross rent, home value | ACS B25064, B25077 via `adapters/national/acs.py`; `place_inputs` (schemas 1.16) | 2025 dollars |
| ADU rent | `hazard.yaml` `adu_rent_to_median_ratio` (1.0, 0.8 to 1.2, judgment) | rent = median x ratio |
| Plex rent | `estimate_mm.plex_price_to_cost` | uses the median rent; no ratio exists (it cancels in the fit) |
| Pro forma | `model/proforma.py`, `proforma.yaml` | rental and for-sale tenures; vacancy, operating share, cap rate; fee levels are arguments |
| Place types | `adu_place_types.yaml`, `results_adu_place_types` | core city, suburb, town (D-088) |
| Mortgage rate | `market.yaml` `mortgage_rate_forecast` (6.60%) | for the house row |

## Build, in this order (small PRs)
1. **Adapter + provenance.** HUD income limits through the IO layer and manifest; rows in
   `docs/data_provenance.md` and `docs/data_availability.md`; place to HUD area by the place's main county.
2. **Parameters** in a new `config/params/affordability.yaml`, each with a source: the 30% rule; bedrooms per home
   type (ADU 1, plex unit 2, house 3); 1.5 persons per bedroom; HUD's household-size factors (take them from the
   file's own columns where possible instead of hard-coding); a plex rent ratio (1.0 with a range; say it is
   judgment); band edges at 60% and 80% AMI; and for the house row a down payment share, a property tax rate and
   an insurance rate. Find a public source for each of the last three (candidates: ACS median real estate taxes
   over median value for the tax rate; a national home-buyer survey for the down payment). Don't invent values:
   if no source is found, mark the parameter as judgment with a wide range and flag it in the PR.
3. **`model/affordability.py`**, pure functions, each with a hand-worked test:
   - rent to income: `12 x rent / 0.30`; test: $1,500 a month gives $60,000.
   - income to AMI share: income / (MFI x size factor); test: MFI $132,300, 1 bedroom (factor 0.75) gives 60%;
     2 bedrooms (0.90) gives 50%.
   - break-even rent: the rent at which the pro forma's value equals its cost, fees included, per home type; it
     must move when the fee scenario changes. Test against a hand-worked pro forma.
   - house row: monthly cost of owning (mortgage at the forecast rate, tax, insurance) to income at the same 30%,
     for the market price and for the break-even price. Propose the break-even definition for a for-sale house
     (how land enters) in the PR for Ben before wiring it.
   - roll-up to place type and state, weighted by the homes the reform adds in each place (midpoint).
4. **Bundle table** `affordability` (home type, place type, rent kind = market or break-even, monthly rent or
   price, income needed, AMI share, each P10/P50/P90) in `results.py` and `docs/schemas.md`.
5. **App strip** in `template.html` under the need chart: one row per home type; a 0 to 150% AMI axis with the
   three bands labeled in plain words; a filled marker at the market value with its range and the dollar income
   beside it; a hollow marker at break-even. One sentence above, one "what this is not" line below (the model
   predicts how many homes, not their rents). Every number from the bundle; no midpoint without its range.
6. **D4 limitations** (`docs/model_and_assumptions.md`): the five limits listed in the method doc.

## Don't
- Don't present the strip as a result of the reform scenarios, and don't show anything below place type (S10).
- Don't use the HUD API or add a key. Don't add a dependency without Ben's OK.
- Don't change the ADU or plex rent the models use; this thread only reads them.

## Done when
`lotline results` writes the table for every state with a bundle; the strip renders for NC and for the fixture
bundle; tests, `compliance_check.py` and the params table check pass; logbook fragment written; each PR names the
`contract-change` issue.
