# Thread 16: ADU model, what we tried and what worked (D-079 to D-090)

**Why this exists:** Ben asked on 2026-11-14 for a short record for the ADU thread. It covers what was tried to
make one ADU model fit all five states (MN, NC, OH, TX, OR), what worked, and what is still open. Use it to
look for a better way, not to repeat these steps. Details are in `docs/analysis_plan.md` under each D-number.

## The problem

The joint refit (D-079) fits five states with one mechanism: rate θ × transport (price to cost) × rules ×
a gamma place effect u. That model (Form A) passes no claim tier in any state. Its places spread far more
than the transport explains: α, the place-effect variance, was 1.9–2.7 depending on the fit set. Ben's reading (2026-11-14): "we
still don't have a model that explains or accounts for the variability across 5 states".

## What we tried

| D | Idea | Result | Kept? |
|---|---|---|---|
| D-079 | Joint refit, Form A vs Form B (dose) | A kept. No tier passes anywhere; test C passes in all 5 states | A, as the base |
| D-082 | Observed floor over 3 years, matching test C | Fixed 41 of test C's 43 failures, which were a window mismatch | Yes |
| D-083 | Screen place effects against unused place factors | Two narrow passes: owner share (β −0.71, Holm p 0.08) and pre-1960 housing (+0.59, p 0.10). New houses per lot and others showed nothing | Screen only |
| D-084 | Owner share as a place term (A′) | Small held-out gain; the rule picked A′, but Ben deferred adoption | Superseded by D-088 |
| D-085 | Calendar-year trend, plus test D (fit 2016–20, forecast 2021–25) | No trend kept. The in-sample trend is mostly Oregon. **Carry-forward beat every model form on test D** | No |
| D-086 | Code each place's rule history to estimate a rule-change effect | Only 6 events in 2 states, so the effect can't be estimated | No (a second coder wouldn't change this) |
| D-087 | Housing age as a second term (A″) | The rule keeps A. No held-out gain on top of owner share | No |
| D-088 | Place types shared across states (core city / suburb / town) | **Adopted.** Core cities ×3.3 (×1.7–×6.7). Held-out log score +7.2 against a bar of 6.1. Observed ÷ forecast ratios move closer to 1 (TX 5.9 → 2.4, NC 2.7 → 1.6, OR 3.6 → 2.0). Still no claim tier | **Yes, Form A + P** |
| D-089 | Profile each state against the fit's evidence; a prior for towns | 63–93% of each state's lots are unlike any fitted place, mostly cheaper or bigger. Towns yield 1–5% of ADUs. Town prior sd 0.729 | Yes (prior and label) |
| D-090 | Within-state forecast test (another session) | Own history isn't enough (useful in 1 of 4 states). **Persistence is within ×2 in all 4.** Ranges are far too narrow (about ±9%) | No |
| Engine | Wire A + P into the scenario (#432) | Added homes at P50 rise ×1.8–4.1 in MN, NC, OH and TX. Types and the new θ make most of the rise in OH and TX; m_x 0.4 makes most of it in MN and NC (partial rules count less today, so the reform adds more) | Yes, pending merge |

## What worked, and what didn't

- **Worked: a coarse, national segment.** Core city vs suburb uses only OMB metro areas and ACS housing units.
  It is defined the same way in every state and is where a new state's data already exists. It is the only
  change that passed the held-out rule.
- **Didn't: more place covariates.** Owner share and housing age help in-sample, but the gain doesn't survive
  held-out scoring once types are in. About 70% of the spread between places is still between places that look
  alike on every measure we have.
- **Didn't: time and rule-change terms.** The trend is one state (Oregon). Rule changes are too few to
  estimate.
- **The strongest predictor of a place we've seen is its own recent rate.** Carry-forward beat every model
  form on test D, and persistence passed D-090 in all 4 states. The model's value is for places with no ADU
  counts, which is most of each state (D-089).
- **Where the evidence is thin:**
  - lower-priced suburbs, mostly in OH and TX; every fitted suburb has a home value of $228k or more;
  - towns, where no place is in the fit;
  - Texas's biggest cities, which are bigger than anything fitted.

## Ideas for a better way

1. **Split the job.** Where a place has ADU counts, forecast from its own rate with a drift term: shrink to
   persistence, widened for period-to-period change. Use the type model only where there are no counts. The
   engine already uses the observed rate as a floor; this would make it the centre.
2. **Add a drift term.** D-090's ranges are about ±9% because u is fixed over time. A random walk on log u
   (one variance, fitted on test D's split) would fix that without adding place covariates.
3. **Find counts for cheap suburbs** in OH and TX from open permit portals. Records requests and emails to
   staff are ruled out. This is the data the forecasts lean on most and have never seen.
4. **Look at counting source.** Source explains about as much of the spread as state or type (23% vs 26%;
   D-088 Part 1). It is tangled with state (every survey place is in MN). A residual source effect could mean
   the undercount k table is off for some sources.

## Where things stand (2026-11-14)

- **Open PRs, all stacked:**
  - #427 (D-088), #428 (D-089), #431 (config), #432 (engine);
  - an anchor-slope recompute for the A + P fit, still running;
  - earlier ones: #420–#426 (D-085, D-086 coding, D-087) and #429 (D-090).
- **Results pages:**
  - D-088: https://claude.ai/artifact/F8JER4WdEHK6GUn581E4J3
  - D-089: https://claude.ai/artifact/GoxSAAjVEv2szddSuRSJEb
  - engine switch: https://claude.ai/artifact/Wn5ktV2Hvo26TQdTEseNci
- **Rules that still hold:**
  - St. Paul (V5) is blind;
  - Oregon is read only through the V9 holdout filters;
  - pre-register before counting;
  - fitted values go to config only with Ben's approval.
