# WS-NEED-AMI · One card for housing need, the gap, and who the homes serve

**Start:** part A now; part B once Ben settles the two open decisions below. **Branch:** `ws/app-need-ami` from `origin/main`.
**Owns:** the "Share of housing need" card in `src/lotline/app/template.html` and its tests in `tests/app/`. Part B also touches `src/lotline/model/results.py`, `docs/schemas.md`, a new params file and a new national adapter: those are WS-CORE and WS-ENGINE paths, so open a `contract-change` issue first and coordinate in the PR.
**Source:** `docs/research/office-hours-2026-11-17-tomasso-notes.md` (B1, B2, B5, B6) and Ben's decisions of 2026-11-17 recorded there.

## The problem
The mentor could not read the share of housing need from a table (4.5% to 51% did not land), read fees and missing middle as tied, and asked for supply to be tied to affordability: what income each kind of home serves. Ben's decision: one card on the Results overview that shows the need, the gap and who the homes serve together.

## Part A: fee default and the need chart (app only, no contract change)
- [ ] **Real local fees are the default.** `UI.fee` starts as `fees_local_half`; when a bundle has no `fees_local_half` run, fall back to `fees` (today the fallback goes the other way). The Handbook benchmark stays one click away on the same switch, and stays in the every-state chart and the fee card (S1 comparability). Check the headline note, `IN_NOTE` and the share of need all follow the switch.
- [ ] **Replace the need table with a chart** (plain SVG, `docs/build/identity/` tokens): one horizontal bar for the state's need over the five years; the three reforms' net new homes filled in from the left at their midpoints, one colour per reform; a whisker for the likely range of the three together; the rest of the bar labeled as the gap that remains. One sentence above it: "[State] needs about N homes by 2031. These three reforms together add a to b of them." Keep the per-reform rows beneath, and the "if the need is x to y instead" line.
- [ ] One generated sentence saying which reform adds the most (ranked by midpoint, with ranges).
- [ ] Both need kinds keep their labels (household growth; shortage); never mix them in one bar. Ohio's projected household growth is negative: the chart must use the headline kind the bundle marks, as the card does today.
- [ ] Tests: every number in the card traces to a bundle field; no midpoint without its range (S6); renders with the fixture bundle and with a bundle that has no need rows.

## Part B: who the homes serve (needs new data)
**Method and research:** `docs/research/lotline-ami-method.md` (read it first; where it and this brief differ, it wins: two rents, market and break-even, and household size at 1.5 persons per bedroom).

For each kind of home (ADU; a unit in a duplex to fourplex) in each place type (core city, suburb, town), show three numbers: the monthly rent the model's pro forma assumes, the yearly income a household needs for that rent to be 30% of income, and that income as a share of area median income, with the dollar figure ("about 60% of area median income, $X a year here").

- [ ] **Rent:** the same rent the engine already uses, so the card and the model agree: ACS median gross rent (B25064) times `adu_rent_to_median_ratio` for ADUs, and the pro forma's rent for a plex unit. Aggregate places to place types weighted by the homes the reform adds there.
- [ ] **Income (open decision 2).** Add the source as a dataset: fetch script through the IO layer, manifest entry, row in `docs/data_provenance.md` and `docs/data_availability.md`, parameters (30% rule, household size per home type) in `config/params/` with sources.
- [ ] **Bundle:** a new `affordability` table (state, home type, place type, rent, income needed, share of area median income, each with P10/P50/P90 where the rent varies across draws). Schema version bump; `docs/schemas.md` updated.
- [ ] **Card:** a small strip under the need chart, one row per home type, a marker on a 0 to 150% of area median income axis, the dollar income beside it.
- [ ] **Label it as context, not a forecast.** The model predicts how many homes, not what they rent for; new homes often rent above the median. Say so on the card and in D4 limitations.
- [ ] Unit test for the rent to income to share arithmetic against a hand-worked example; app tests as in part A.

## Open decisions (Ben)
1. **What "the gap" is measured against.** Today the share of need divides the reforms' net new homes by the whole need, with no credit for homes built anyway. A gap chart can show (a) need, reforms, remainder, as today; or (b) need, homes expected with no change, reforms on top, remainder. (b) is the more honest picture of a shortfall but needs a no-change total for all building sizes in the bundle, and makes less sense for the shortage kind of need, which is a backlog on top of normal building. Recommendation: (a) for the shortage kind, (b) for household growth if the all-sizes no-change total is already exported.
2. **Which "area median income".** HUD income limits (the definition practitioners mean by AMI; by county and metro, by household size; a new federal dataset, public domain) or ACS median household income (B19013; one more table on the adapter we already have, but not what "60% AMI" means in housing programs). Recommendation: HUD, with a 2-person household for an ADU and a 3-person household for a plex unit.

## Done when
A reader can say from the card alone: how many homes the state needs, how much of that the three reforms cover, which reform covers the most, and what income a household needs to live in each kind of home. Tests and `compliance_check.py` pass; logbook fragment written.

## Note (2026-11-19)
The "What it takes to pencil out" placeholder card was removed from the Results page (Ben): the AMI section's break-even rows (what each home must earn to cover building it, with the fee cut) and the fee card's per-place fee table cover it. A place-by-place pencil-out view, if wanted, belongs on the Model page (nothing below place type on Results, S10).
