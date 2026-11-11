# Thread 15: The fee section of the app, from the fee prototype page (WS-APP)

**Goal:** rebuild the fee results page as the app's fee section, with a state picker and the app's story order,
without changing any number. The prototype is results page v9
(https://claude.ai/artifact/LN5G4rajXAxVi3uhEXtwDs; source `reports/fees-phase2-run/fees-phase2-results.html`).
Ben (2026-11-10): "we'll have to do some reformatting to get this to work in our final app (ie a state picker, a bit
of a different narrative structure) but I'm generally happy with this."

**Read first:** `docs/analysis_plan.md` D-073 (dose by home type), D-076 (statewide run, centred elasticity draw)
and D-077 (knobs, revenue test, revisions); `docs/build/workstreams/WS-APP.md` ("Sliders without a server");
`src/lotline/model/scenarios/fees.py` (`change_grid`); `scripts/dev/fee_knobs_export.py`.

## What exists

| Piece | Where | Notes |
|---|---|---|
| Grid of results for every knob setting | `reports/fees-knobs/grid.json` (2.2 MB) | Written by `uv run python scripts/dev/fee_knobs_export.py`; `--page <html>` puts it in a page, `--from-json` skips the run |
| Engine function | `fees.change_grid` | Tested: reproduces `fees.run` exactly at a cut and a rise of half; linear by elasticity; revenue by hand |
| Prototype page | `reports/fees-phase2-run/fees-phase2-results.html` | Plain HTML/CSS/JS, Lotline tokens, no libraries |
| Statewide run it matches | `reports/fees-statewide-run/` | D-076 |

The grid comes from a development script today. In the app it should come from the results bundle, once fees are
part of `lotline results` (`ENGINE_SCENARIOS`, a WS-ENGINE step that is not yet done). Keep the same format so the
page code carries over.

## The grid format (`grid.json`)

- `shares`: the 16 slider stops, −0.5 … 1.0 in steps of 0.1. **A stop s is a fee change of −s × each place's own
  fee**: 0.5 halves fees, 1.0 abolishes them, −0.5 raises them by half. The slider shows the fee change, so slider
  value v% means s = −v/100. One stop is stored as −0.0; compare with a tolerance, not `===`, when looking it up.
- `sizes`: `["1", "2", "3_4"]`, the Census building-permit size classes that take a dose: houses, duplexes,
  triplexes and fourplexes. Buildings of 5 or more units (`"5p"`) take none (D-073).
- `states.<ST>`:
  - `places`: places in the run (MN 944, NC 221, OH 832, TX 940).
  - `coded_places`: **don't display.** It counts `fee_source == "local"` exactly and undercounts (MN 15, where
    the run log counts 18). Fix it in the export when fees move into the bundle.
  - `baseline.<class>`: five-year (2027–2031) baseline homes, including `"5p"`.
  - `draws.<class>[stop]`: 1,000 numbers, the five-year homes added summed over the state's places, in each run.
  - `central.<class>[stop]`: the same with every assumption at its central value.
  - Revenue (a test, see below), in thousands of 2025 dollars:
    - `revenue_draws_k.<class>[stop]`: per run.
    - `revenue_central_k.<class>[stop]`: central value.
    - `revenue_today_k.<class>`: a single number, fees at today's levels on the baseline homes.

**Run i is the same world everywhere.** Run i uses the same parameter set (and the same fee draws) at every stop, in
every class and in every state. So totals are built **run by run**: add the arrays element by element over the
chosen classes and states, then take percentiles. Never add P10s or P90s together; that overstates the range.

## How the page computes (the only model arithmetic in JavaScript)

```
on     = classes the chosen policy targets
total  = Σ over states in view, Σ over on: draws[class][stop]      (element by element, 1,000 numbers)
centre = Σ over states in view, Σ over on: central[class][stop]
show   = centre, with likely range P10–P90 of total (linear interpolation, as numpy's default)
share  = centre / Σ baseline (all classes, including 5p) of the states in view
target = for each class in on: Σ central, and as a % of that class's Σ baseline
```

- **Headline = the central estimate, not the P50.** This was decided for the results page (D-073 note, D-076).
  The two differ by a few percent per state; the page says so in a note.
- **State picker:** sum only the picked state; "All four states" sums them run by run.
- **Bar scale:** fixed for each policy choice, from the biggest loss (fees up by half) to the biggest gain
  (abolished). This keeps bars growing as the slider moves, and keeps duplex-only bars visible.

## Numbers the app must reproduce (parity checks)

Five-year homes added, central estimate and likely range (P10–P90):

| Setting | Result |
|---|---|
| Every home, fees halved, by state | MN 162 (53–546) · NC 483 (125–1,982) · OH 122 (31–479) · TX 715 (174–2,738) |
| Every home, fees halved, four states | +1,482 (416–5,762), 0.09% of 1,588,691 |
| Every home, abolished | +2,969 (838–11,331) |
| Every home, raised by half | −1,450 (−5,678 to −420) |
| Duplexes only, halved | +95 (23–379), 0.3% of 36,248 duplex homes |
| Duplexes to fourplexes, halved | +142 (34–555) |
| Houses only, halved | +1,340 |
| Revenue, every home, halved | −$3.1 billion over five years, against $6.3 billion at today's fees |

The P50s in the per-state row match the D-076 run (MN P50 173, and so on). Make these a test in the app (the
parity contract in WS-APP.md).

## Ben's design calls (2026-11-10)

- **Slider direction:** cuts go left and rises go right. The ends read "Abolish", "No change" (two-thirds along),
  "Up 50%". The default is a cut of half (the D-065 scenario).
- **Home-type buttons are targeted policies**, one choice of "which homes it applies to": every home, duplexes
  only, duplexes to fourplexes, houses only. Other homes keep today's fees. The point is a bill that cuts duplex
  fees to encourage duplexes. Show the targeted type's own change: "+95 duplex homes, 0.3% more than the 36,248
  expected".
- **Plain outcome wording**, not bill-speak. Use "Fees unchanged: no homes added or lost", not "the bill does
  nothing". The section heading is "Explore other fee changes".
- **Estimated quantities are never knobs** (ε, λ, the ramp): they are the range (Ben, 2026-11-05).
- **Context before the knobs:** "What gets built today" shows a 1,000-square grid (houses 669, duplexes 23,
  triplexes and fourplexes 11, apartments 297 out of every 1,000 new homes) and a bar per state. It answered
  Ben's "our missing middle predictors didn't show that many being built".
- **Fee revenue is a test**, and Ben expects not to include it. If it stays, lead with "for each extra duplex
  home, about 1,900 that would be built anyway also get the discount". The "$1 million per extra home" figure read
  as implausible without that.
- **The builder response, in plain language** (Raleigh chain): "For each 1% a home becomes cheaper to build,
  about 0.3% more get built". Explain that it is a neighborhood-level price response (Baum-Snow and Han 2024),
  and give the range from no response to 1.75 metro-wide.

## Story order

Not decided; Ben wants "a bit of a different narrative structure". The prototype's order is:
1. headline;
2. two worlds;
3. the difference;
4. what gets built today;
5. the knobs;
6. fees as 1.6% of cost;
7. why believe it (Raleigh chain, stress test, what is checked and not);
8. the Handbook benchmark;
9. the fee rise;
10. fees per lot by type;
11. method, folded.

Keep the office-hours rules (2026-11-09): results first, two worlds side by side with the difference as the story,
ranges kept but uncluttered, method behind a click.

## Limits the section must state

- Each home type responds only to its own fee. There is no substitution from houses to duplexes when only duplex
  fees fall, and no source for a cross-response is in `docs/research/`.
- 5+ unit buildings (about 30% of the baseline) take no dose: no fees are coded for them.
- About two-thirds of each state's homes are in places using the state's median fee (coded places hold 28–33%).
  The same places hold 70–88% of the revenue.
- ADU fees are not a knob: the fee model has no ADU type. That provision belongs with the ADU scenario's toggles.
- The headline is a % of the baseline, not a share of projected household growth (office hours A2), until the
  household projection is in the bundle.
- Revenue is in 2025 dollars, not discounted. What replaces it (other taxes, less infrastructure) is not modelled.
- There is no own-data backtest of a fee cut yet (V6b, the Carthage NC test).

## Still for Ben to confirm (in D-073, D-076, D-077)

- The cost of a duplex or fourplex home: home value × unit size / house size.
- λ treated the same for a rise as for a cut.
- The lognormal form of the ε draw.
- The slider's range (abolish to +50%).
- The %-of-baseline headline.
- Whether the revenue box stays.

## Practical notes

- **Size:** the grid is 2.2 MB for 4 states (half of it revenue). With Oregon, or more stops, load it as a separate
  file rather than inline, or drop revenue if Ben drops the box.
- **Accessibility kept in the prototype:**
  - the result has `aria-live="polite"`;
  - the slider has `aria-valuetext` ("Fees cut by 50%");
  - the buttons are a radio group with visible focus;
  - the waffle has an `aria-label` with the counts.
- **Checked layouts:** desktop and 375 px phone width, with no horizontal scroll.

**Done when:** the app's fee section reads the grid from the results bundle, has a state picker, reproduces the
parity table above in a test, and keeps Ben's design calls.
