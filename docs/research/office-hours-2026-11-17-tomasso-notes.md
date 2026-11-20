# Office hours with Amy Tomasso (mentor), 2026-11-17

Second session with Amy (first: `office-hours-2026-11-03-tomasso-notes.md`). Jacob Colombo (another participant) sat in. Shown: the app's North Carolina results (all three reforms, about 6,000 net new homes over 5 years), the ADU steps, the share of housing need, the five-state missing-middle comparison, both fee versions, Oregon's fee numbers. Transcript kept outside the repo (Granola, "ADU policy modeling and housing supply impact with Amy").

Amy's overall read: clearer than two weeks ago and on the right track. Bringing in Oregon (her suggestion on Nov 3) worked.

## What Amy said (feedback, in order)

1. **How the "pays off" step works.** She asked how the pencil-out filter is computed (a pro forma?). Ben's answer (rents and a cap rate at median rental income) satisfied her, but she had to ask.
2. **Is the ADU range big or small?** She asked what the 44 to 467 range means in proportion. The answer wandered into where ADUs are already legal and the ramp-up. She accepted it, and noted a few homes matter more in a rural place.
3. **Share of housing need.** Benchmarking against the state's own need estimate is the right move. But 4.5% to 51% shown as a table does not land. Make it a picture: where do these homes sit against the need, and how big is the gap left.
4. **Which reform first?** She wanted the page to say which lever matters most. From the screen she read fees and missing middle as roughly tied. Ben's answer: missing middle, clearly.
5. **One number.** After the five-state chart (and Texas explained as the reason the range is wide), she asked whether Ben could pick the midpoint and defend it. Ben hedged (the states are deliberately different).
6. **Tie supply to affordability.** Eric Kronberg's slides put the income level (AMI) each housing type serves on the graphic. Do the same for NC, by region: this ADU serves 60% AMI, which here is $X a year. She hedged on whether it holds up, but thinks it would be persuasive.
7. **The arc.** Demand shortfall, then the affordability gap, then how these three reforms fit both, even if the numbers are small. Other levers exist (ADU financing).
8. **Fees.** She did not answer "show the benchmark or not" directly. More interesting to her: how fees layer with the other two reforms, and that fees may be the third and weakest lever here. She did not follow why halving real fees adds so many fewer homes than halving $50,000, in NC or in Oregon; it took two explanations. She also asked why the challenge's $50,000 is so high.
9. **Per-unit fees and missing middle.** The duplex/fourplex pencil-out comparison is a core missing-middle cost argument. Ben could not find it to show (it is not in the app).
10. **Simplify.** Ben scrolled past the lower part of the page quickly. Lead with the data takeaway, the policy takeaway, and whether the added homes are enough; everything else is supplemental.
11. **States.** Do not add New York (City of Yes is a city reform; too odd). Maine legalized ADUs statewide and they are still hard to build there: a rural case worth a mention.

## Action items

Status column checked against `origin/main` at 78778f58 (2026-11-17 17:34).

| # | Action | Status today | Where it lands | Size |
|---|---|---|---|---|
| B1 | **Share of housing need as a chart.** One bar for the state's 5-year need; the three reforms' midpoints filled in from the left, a whisker for the likely range, the unfilled rest labeled as the remaining gap. Keep the per-reform rows under it. | Card exists as text plus a table. All fields already in the bundle (`need`, `AGG.shareOfNeed`). | `template.html` only | Small |
| B2 | **Say which reform does the most.** One generated sentence under the headline ranking the three by midpoint. Decide which fee version the headline uses by default: with the Handbook benchmark selected, fees look as large as missing middle, which is the misreading Amy had. | Not on the page. Fee switch exists. | `template.html`; a decision for Ben | Small |
| B3 | **Explain the fee gap in one line of arithmetic** on the fee card: this state's typical real fee in dollars beside $50,000, the dollar cut as a share of a home's cost, 3% more building per 10% cost cut (Baum-Snow and Han), times the homes built anyway. Add why a high-fee, low-building state (Oregon) still gains few homes. | Card shows both versions and says real fees are "far lower"; the state's own figure and the arithmetic are not shown. | `template.html`; state median fee from the bundle | Small |
| B4 | **Pencil-out table: house vs duplex vs fourplex, per-unit fees named.** Open since Nov 3 (A5). | Still a "pending" card on the Results page. | engine export, schemas, `template.html` | Medium |
| B5 | **Who the homes serve (AMI).** For each home type and place type: the rent the pro forma uses, the income that rent needs at 30% of income, and that as a share of area median income (HUD income limits). Labeled as context, not a model output. | Nothing yet. Needs HUD income limits as a new dataset (download script, provenance row). | new param/dataset, bundle, `template.html`, D6 | Medium to large |
| B6 | **Results order follows the arc:** the need, who is priced out, what the three reforms add, what is left. Finish the WS-RESULTS-SIMPLE "60-second test" (`docs/build/usability-check.md` does not exist yet). | Headline and range boxes done; test not run. | `template.html`, WS-RESULTS-SIMPLE | Small |
| B7 | **ADUs in proportion:** how many lots (and places) already allow an ADU today vs how many the statewide reform newly opens. Ben's own idea at the close. | Step 1 shows lots where an ADU "would become legal"; the already-legal share is not shown. | bundle field if missing, `template.html` | Small to medium |
| B8 | **New-state run.** Take a state the code has not seen through the pipeline with a new adapter only, and replace the placeholder "Add a state" steps with what that run actually took. Ben named Montana as an example; the plan of record is Wisconsin (V8). | "Add a state" page is a placeholder; `.worktrees/new-state-guide` in progress. | V8, README guide, app | Large |
| B9 | **Limitations to add (D4):** ADU financing is not modeled; statewide legalization alone may not move rural markets (Maine); New York left out on purpose. | To write. | `model_and_assumptions.md` | Small |

## Pitch fixes (no code)

- **One number:** yes, the midpoint is the best single estimate, and the range is how wrong it could be. The evidence to cite is the blind Oregon test already on the Model page (other states predicted a midpoint of 915 missing-middle buildings; 703 were built), not the diversity of the states.
- **Why the range is wide:** one sentence. Texas builds far more than its measured factors explain, and the model has to allow that a new state could be another Texas.
- **Pays off:** say "a small pro forma: local rent against the cost to build" before being asked.
- **Is it enough:** answer with the share of need, not with a caveat about persuasion.

## To check

- **Timeline.** "Two weeks left" was said in the session. The submission deadline is Dec 16 (four weeks); mentor office hours and Ben's own availability may end sooner. Plan against the earlier date.
- **NC fourplexes.** Ben said NC brought three- and fourplexes under the residential code this year. Not verified here. If so, cite it in the NC missing-middle notes as context (a building-code change, not the zoning reform the scenario models).

## Decisions (Ben, 2026-11-17, after the session)

- **B2: the headline defaults to real local fees.** The Handbook benchmark stays on the switch and in the every-state chart.
- **B1 + B5 become one card** on the Results overview: housing need, the gap, and the income each kind of home serves (AMI). Brief: `docs/build/workstreams/WS-NEED-AMI.md`.
- **B8 waits.** The new-state run is on hold while Ben reworks the data-ingestion part of the workflow.
