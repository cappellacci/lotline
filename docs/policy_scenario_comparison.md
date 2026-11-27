# Lotline: Policy Scenario Comparison

<!-- Rules §7a(6): max 4 pages, single-spaced, non-technical. Every section below is required. -->

Lawmakers need to know how many homes a reform would add, and how sure they can be. We compare three
reforms from the Challenge Handbook with no reform, in 6 states, over the five years 2027–2031. All numbers
come from the published results, release `app-2026-11-27`, which the interactive tool shows.

## How each scenario compares with the baseline

The baseline is "no reform". It keeps every city's own rules, including laws already passed that take effect
by the end of 2027, so a reform is never credited with homes that current law will produce anyway. Each
number below is what a reform adds on top of that baseline.

The reforms follow the Handbook's definitions:

- **ADUs:** one backyard home (accessory dwelling unit) allowed on every lot with a house, at least 600 sq ft,
  with no parking required.
- **Missing middle:** 2–6 homes, up to three stories, allowed on lots now zoned for one house.
- **Fee cut, Challenge benchmark:** development fees cut from $50,000 to $25,000 per home.
- **Fee cut, real local fees:** each city's own fees cut in half. We added this second version because real
  fees are far below $50,000 in most places we checked.

We count net new housing: permits that get finished and add a home someone can live in, minus the homes that
would have been built elsewhere in the state anyway. Every result is a range. Our model runs 1,000 times,
each time with different plausible values for everything it is unsure about. The table shows the midpoint of
those runs in bold and, in brackets, the middle 80% of them (P10 to P90).

**Net new homes added over 2027–2031, compared with no reform**

| State | ADUs | Missing middle | Fee cut, benchmark | Fee cut, real local fees |
|---|---|---|---|---|
| Minnesota | **230** (122–505) | **1,240** (178–7,800) | **443** (119–1,720) | **84** (22–349) |
| North Carolina | **169** (75–448) | **2,110** (327–13,100) | **2,370** (635–9,140) | **360** (92–1,500) |
| Ohio | **345** (164–886) | **1,850** (268–11,300) | **883** (241–3,460) | **89** (23–362) |
| Oregon | **5** (2–19) | **178** (23–1,170) | **223** (60–870) | **55** (14–227) |
| Texas | **2,310** (1,190–5,310) | **8,390** (1,150–53,200) | **5,560** (1,510–21,700) | **500** (126–2,090) |
| Wisconsin | **192** (73–583) | **514** (68–3,380) | **606** (165–2,380) | **92** (23–381) |

Numbers are rounded to the nearest 10 at or above 1,000 and to the nearest 100 at or above 10,000.

Missing middle has the largest upside and the widest range. Its midpoint is the largest of the three reforms
in Minnesota, Ohio and Texas. In North Carolina, Oregon and Wisconsin the benchmark fee cut has a slightly higher
midpoint, but missing middle's upper end is still the highest in every state.

The benchmark fee cut adds 4 to 11 times as many homes as cutting real local fees in half. The benchmark assumes
a $50,000 fee everywhere. Real fees are much lower, so halving them is a much smaller cut.

ADUs add the fewest homes of the three reforms in every state, and their range is the narrowest. Oregon's ADU
result is close to zero because state law has required most Oregon cities to allow an ADU with every house since
2018, so the reform adds little over current rules.

Wisconsin is a test of a state the model was not fitted on. We built the model on Minnesota, North Carolina,
Ohio, Texas and Oregon, and ran it for Wisconsin with national data only, borrowing local rules from the five
states by place size.

## Drivers of the differences

The reforms differ in size because they work on different numbers of lots and through different people.

Missing middle opens every single-family lot to small multi-home buildings. That is a very large pool, so even
a small share of lots used adds many homes. Builders tend to put these buildings up in clusters (a row of
duplexes, or a build-to-rent community), so a place's count depends on whether one big project lands in the
five years. That is why the range is so wide.

ADUs depend on homeowners, one lot at a time, and owners add them slowly. Many cities already allow ADUs in
some form, so the reform adds only the homes current rules don't already allow.

Fee cuts lower the cost of every new home in a building of 1–4 homes. How many extra homes that brings depends
on how strongly building responds to cost, and on the size of the cut compared with the cost of a home.
Buildings with 5 or more homes get no fee cut in our model, because the fee reform is meant to encourage small
buildings.

States differ mostly by the size of their building market. Texas builds far more homes than any other state
here, so every reform adds the most homes there.

## Critical assumptions

Every result is a range. For each reform we measured how much of that range each uncertain assumption
explains on its own, using the 1,000 runs behind the published results.

In Minnesota, our benchmark state:

| Reform | How wide the range is (P90 ÷ P10) | What drives it |
|---|---|---|
| Missing middle | about ×43 | How readily owners and builders use a new 2–4 home allowance (the uptake rate fitted to places that already allow it): 93% |
| Fee cut (the Challenge's $50,000 → $25,000) | about ×14 | How strongly building responds to lower fees (the elasticity): 93%. How much of the cut landowners capture: 4% |
| Fee cut (half of real local fees) | about ×16 | The elasticity: 92%. How much of the cut landowners capture: 5% |
| ADUs | about ×4 | How fast owners add ADUs once allowed (fitted uptake rate): 40%. How much a partial ADU rule already counts: 32% (these two overlap, because one is refitted for each value of the other). Legalized or replacement units: 10%. Homes that would be built elsewhere in the state anyway: 5% |

The other states look much the same.
- The missing-middle uptake rate explains 89–93% in every state.
- The fee elasticity explains 92–93% in every state, for both fee cuts.
- For ADUs, more of the range comes from place-to-place differences and which local rules apply: 28–34%
  in Ohio, Texas and Oregon. In Wisconsin, 49% comes from these and from the extra spread we allow for a
  state the model was not fitted on.

What this means for a decision:
- The missing-middle estimate rests almost entirely on one number: how much 2–4 home allowances get used
  where they already exist. A state adopting this reform should watch early permit counts closely. Those
  counts will narrow the range faster than anything else.
- For fee cuts, the evidence on how builders respond to cost changes matters far more than the fee amounts
  themselves.
- Assumptions about construction costs, completion rates and how much new housing simply moves between
  places matter much less: under 10% each.

Each share is the assumption's effect on its own. We did not separate out effects that come only from two
assumptions combining.

## Model limitations

These are limits we could not address. A reader should keep them in mind next to every number above.

- Missing middle counts buildings of 2–4 homes only. National permit data put 5–6 home buildings in with large
  apartments, so we can't measure them. The result is a floor for the Handbook's 2–6 home reform.
- The benchmark fee cut is not a forecast of a realistic local fee cut. The Handbook's $50,000 fee is far above
  real fees in most places we checked, so the real-local-fees column is the better guide to what a fee bill
  would do.
- The evidence on fees is weak. Studies of how fees change the amount of building mostly find small or no
  effects, and the share of a cut that landowners capture is uncertain.
- Many places have no usable parcel data. There we count houses from the Census survey instead of lots, with no
  zoning and no vacant land.
- We place every home with 2025 city boundaries, so annexations are not modelled.
- Construction costs are national: the same cost per square foot applies everywhere.
- The model predicts how many homes a reform adds, not who will live in them or what they will rent for.
- Wisconsin was not used to fit the model, so its ranges are wider and less tested.

The full list of limits, with the evidence for each, is in the
[Model and Assumptions Overview](model_and_assumptions.md#limitations-and-edge-cases).
