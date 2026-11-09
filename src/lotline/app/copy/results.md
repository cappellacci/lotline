# Section 1 copy: Results (draft for Ben's review)

WS-RESULTS-SIMPLE, task 1. This is the reader-facing text for Section 1, in page order. Nothing is built yet:
Ben reviews this copy first.

How to read this file:

- `{slot}` is a value filled from the results bundle at render time. The **Slots** table at the bottom says
  which bundle field each one comes from. No number is written into the copy by hand.
- Ranges always print as "low–high" from the bundle's P10 and P90; the reader only ever sees "likely range".
- Lines starting `>` are notes for the build, not page text.
- Word budget: the brief allows 300 words for all of Section 1. The page text below (one scenario's
  "can't tell you" set, slots counted as one word each) comes to **about 285 words** (308 counting this file's labels such as "Bar labels:", which are not shown).

---

## 0. Policy tabs

> One tab per policy at the top of the section, under the state picker. Each tab is a self-contained page:
> everything below (sections 1–5) describes the selected policy only. Policies are never stacked or combined
> (Ben, 2026-11-09: overlap adds too much complexity). First tab selected by default.

Tabs: **ADUs** · **Missing middle** · **Fee reduction**

> Policy not run for this state: the tab stays visible, greyed, and its page reads
> "Not run yet for {state_name}." No chart, no stand-in.

## 1. Headline chart: two worlds

**What {scenario_name} would add in {state_name}, {years}**

> One bar chart, two bars, same scale, starting at zero. Median printed on each bar; whiskers show the likely range.

Bar labels:

- **Without the reform**
- **With the reform**

Whisker key: *Bars show our estimate; the line shows the likely range.*

> Built 2026-11-09: the reform's homes are a small slice of all building (NC ADUs: about 260 on a baseline of
> about 348,000), so the two bars look alike. Under them, a strip on its own scale: **The difference, enlarged:
> homes added by the reform** (the added homes' likely range, midpoint marked).

Sentence under the chart:

> **+{added_mid} homes over 5 years** (likely range {added_low}–{added_high}). Counting only homes that are new
> to the state, about {net_mid} (likely range {net_low}–{net_high}): {need_mid}% (likely range
> {need_low}–{need_high}) of the homes the state expects to need over five years.

Reason to believe it, one line:

> When we ran this model on {backtest_years} without seeing the answer, it landed within {backtest_error}% of what
> was actually built.

> Fallback when the bundle has no backtest row for this state (never a hand-written number):
> "We have not yet checked this model against past years in {state_name}."

## 2. How we get there

> The funnel as four sentences. Step 3 is the headline's +N and step 4 is the net figure, so the sentence
> and the funnel agree. The ADU wording is shown; sentence 1 per policy lives in `copy/scenarios.yaml`.

1. The reform makes it legal to add {unit_noun} on **{legal_mid} lots**.
2. On about **{pencils_mid}** of them (likely range {pencils_low}–{pencils_high}), it pays: rent or sale value
   covers land, building and fees.
3. Most owners still don't build within five years. We expect about **{added_mid}** (likely range
   {added_low}–{added_high}) to get a building permit.
4. Some won't be finished, some won't house anyone, and some would have been built elsewhere in the state anyway.
   Without those, {state_name} gains about **{net_mid}** (likely range {net_low}–{net_high}) homes.

## 3. What this can't tell you

> Three bullets per policy, from config (S9). ADU set shown; the other sets are drafted at the end of this file.

- **Where the homes go.** It gives a statewide total, not which streets will build.
- **Rents and prices.** It counts homes, not what they will cost.
- **What cities do next.** New local rules that slow the reform would make these numbers too high.

## 4. Change the assumptions (collapsed)

Panel title: **Change the assumptions**

| Slider | Plain label | One line under it |
|---|---|---|
| uptake | How many owners build | Where it pays, the share of owners who build within five years. |
| construction cost | Building costs | Cost to build, per square foot. |
| rents/values | Rents and home prices | What the new home rents or sells for. |
| interest rate | Interest rates | The cost of borrowing to build. |

Under each slider: *Source: {param_source}. Range we tested: {param_low}–{param_high}.*
Reset link: **Back to our estimate**

## 5. Link out

**Full methodology →** (goes to "The data" and "The model")

---

## Other "can't tell you" sets (one shows per policy tab)

**Missing middle**

- **Where the homes go.** It adds up a statewide total, not which blocks will change.
- **What happens to rents and prices.** It counts homes, not what they will cost.
- **Teardowns past five years.** It counts houses replaced inside the window only.

**Fee reduction**

- **Who pays instead.** Lower fees mean less money for pipes and roads; it does not say how cities make that up.
- **What happens to rents and prices.** It counts homes, not what they will cost.
- **Builders' other costs.** If land or labor costs rise, the gain shrinks.

---

## Slots

Every slot comes from the state's results bundle (`reports/results/<st>/bundle.json`) or build-time config.
"5-yr" means the bundle's five-year `period` (e.g. `2027-2031`).

| Slot | Bundle field |
|---|---|
| `state_name` | `src/lotline/app/us_tiles.yaml` name for `meta.state` |
| `years` | `totals.period` for the 5-yr window, printed "2027–2031" (`AGG.windowLabel`) |
| `scenario_name` | `build.SCENARIOS[scenario][0]` (Handbook names) |
| Without-reform bar | `baseline` row `size_class == "all"`, 5-yr: `p50`, whiskers `p10`/`p90` |
| With-reform bar | **gap, see Q1** |
| `added_mid/low/high` | `totals` row, scenario, 5-yr, outcome **see Q2**: `p50`, `p10`, `p90` |
| `need_mid` | `need` row with `is_headline`, scenario: `share_p50` × 100 |
| `backtest_years`, `backtest_error` | **gap, see Q3** (a `scorecard` row) |
| `legal_mid` | `funnel` stage `legal`, `p50` |
| `pencils_mid/low/high` | `funnel` stage `pencils` |
| `built_mid/low/high` | `funnel` stage `built` |
| `net_mid` | `totals` outcome `homes_net_statewide`, 5-yr, `p50` |
| `unit_noun` | ADU: "a backyard cottage or basement apartment"; missing middle: "a duplex, triplex or fourplex"; fees: n/a (fees sentence 1 reads "Lower fees change the math on {legal_mid} lots where building is already legal.") |
| `param_*` | `build.knobs()`, resolved from `config/params/` |

## Open questions for Ben

> The first build (2026-11-09, Ben asked for it to QC on Pages) takes the leaning answer to each question below
> and marks it **Built as**. Any of them can change.

**Q1. The "with reform" range needs per-draw baseline.** The bundle has the baseline as P10/P50/P90 only. Adding
the scenario's P10 to the baseline's P10 overstates the spread. Proposed contract change (WS-CORE/WS-ENGINE):
either per-draw baseline totals, or a `totals` outcome `with_reform` computed in the engine. Until then the page
can draw the with-reform bar as baseline median + added range and say so.
**Built as:** with-reform bar = baseline shifted by the median added homes; the added homes' own range is the
enlarged strip.

**Q2. Which count is the headline: permits or net homes?** The baseline counts *permits* (Census BPS). To keep
the two bars comparable, the headline should be `permits_added`. The funnel then ends on net homes (step 4), so
the sentence number and step 4 will differ. Alternative: headline in net homes and the bars shift by the net
gain. I lean permits for the bars and sentence, with step 4 explaining the gap.
**Built as:** permits in the bars and the bold +N; the same sentence then gives net homes and share of need.

**Q3. Backtest line needs a scorecard row.** No bundle has a "within X% on 2019–23" row yet. Proposed: a
`scorecard` row `check_id` for the blind backtest, `metric` = absolute percent error of the 5-yr total,
`label` naming the years. Until it lands the page uses the fallback line.
**Built as:** the page reads a scorecard row with `metric: abs_pct_error_5y` (value a share, label the years);
no bundle has one yet, so every state shows the fallback.

**Q4. Sliders.** The brief asks for uptake, construction cost, rents/values and interest rate. Only uptake is a
factor the browser can move today; the other three feed the pro forma, which the brief's "no model arithmetic in
the browser" rule keeps server-side. Options: (a) pre-computed low/mid/high grid for those three in the bundle,
(b) one "Share of lots where it pays" slider standing in for all three. I lean (a).
**Built as:** the existing five engine-factor sliders, unchanged, inside the collapsed panel.

**Q5. Where the "can't tell you" bullets live.** The brief says config. Proposed home:
`config/scenarios/limits.yaml` (owned by WS-CORE? or by this workstream). The drafts above move there once agreed.
**Built as:** `src/lotline/app/copy/scenarios.yaml` (app-owned), with funnel sentence 1 per policy; the build
refuses a number written into it.

**Q6. Policy tabs, no combined view (decided, Ben 2026-11-09).** Each policy gets its own tab; the page never
stacks or combines policies, so there is no overlap correction on this page. This drops the brief's "scenario
comparison small multiples, combined scenario with the overlap correction" task. Fees are still in
`meta.scenarios_pending`, so its tab shows "Not run yet" until the engine fills it. The pair and `combined`
scenarios stay in the bundle contract but Section 1 does not show them.
