# NC ADU gut check (WS-NC-GUTCHECK, 2026-11-09)

**The question.** At office hours, NC's ADU-reform result read as "a median of about 50 (range 40–301)", while
NC permits about 100–150 ADUs a year. A reform that legalizes more should not forecast less than history.

## 1. Units audit: what the number on the results page is

The NC ADU figure on the results page (run D/E, `reports/results-2026-11-09/`, the app's headline
`homes_net_statewide`) is **40 / 105 / 301 (P10 / median / P90)**. Five things separate it from "about 100 a year":

| | Results page | NC history quoted |
|---|---|---|
| Period | **5-year cumulative** (2027–2031) | one year |
| What | **added over the no-reform baseline** (the reform's effect only) | everything built |
| Unit | **net new homes**: permits × completion 0.97 × net-new share 0.65 × (1 − formalization 0.10) × (1 − displacement 0.25) ≈ 0.40 of permits | **permits** |
| Area | **statewide** | 11–13 cities whose permits flag ADUs (38% of NC's population) |
| Base | added to a baseline the page did not show for ADUs | — |

The median of **about 50 matches no exported figure**. The bundle's own medians were 126 (run B), 79 (run C) and
105 (run D/E). The 40–301 range is run D/E's P10–P90. The closest reading of "about 50" is the added *permits
a year* (259 ÷ 5 ≈ 52).

**So, part one: a units and labeling mismatch.** "Over 5 years, the reform *adds* about 105 net homes to
the ~2,000 ADUs NC would permit anyway" is a different claim from "NC would build 50 ADUs." The fix for the label
and export is the **two worlds**, both as gross ADU permits over 2027–2031:

- **without the reform:** current-rules ADUs, median **2,023** (P10–P90 1,314–4,106), about 400 a year statewide
- **with the reform:** median **2,292** (1,464–4,861)

The engine already computed both; they were never exported (`adu.run` now returns `current`; see the PR for the
proposed bundle outcomes). WS-RESULTS-SIMPLE needs exactly these two bars.

**Part two: the units hunt found a real calibration problem.** On a like-for-like comparison (the same 11
places, holdouts left out of both sides, gross permits a year), the no-reform baseline sat **well below recent
history**. That is why the hunt went on to task 2.

## 2. Baseline vs 2019–2025 history

**All housing units (BPS, reported basis):** observed 66.9k, 72.4k, 89.1k, 90.0k, 77.2k, 75.6k, 71.9k (2019–25).
The no-reform baseline's median is 70.7k in 2027, falling to 68.1k in 2031 (P10–P90 about 36–107k). That is
7% below the 2023–25 average (74.9k) and inside the range: **consistent**. Plot: `baseline_history.png`.

**ADUs, the 11 places whose permits flag ADUs (Charlotte and Mecklenburg County 37119 held out of both sides):**

| | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | forecast, a year (median, P10–P90) |
|---|---|---|---|---|---|---|---|---|
| observed ADU permits | 25 | 24 | 61 | 100 | 146 | 109 | 123 | |
| no reform, **before** the fix | | | | | | | | **78** (58–156) |
| with reform, **before** the fix | | | | | | | | **81** (59–159) |
| no reform, **after** the fix | | | | | | | | **135** (122–191) |
| with reform, **after** the fix | | | | | | | | **137** (123–196) |

**Root cause:** the observed-ADU floor (`adu_observed_first_year`–`adu_observed_last_year`, D-019) was fixed at
**2019–2022**. It is the floor on each place's current-rules hazard ("ADUs a place already builds are in its
baseline"). NC's ADU-flagging cities averaged 52 a year then and 126 a year in 2023–25, so the floor was
anchored before NC's ADU take-off. The model's own hazard (h_m × c, about 0.025% of eligible lots a year) is
below Durham's and Raleigh's recent rates, so the stale floor decided the baseline in exactly the places that
report.

The other suspects checked:
- **`[predates]` rows treated as events:** they can't move this result. Since D-048 the ADU ramp is 1 in every
  year a rule is in force, so a rule's date (and a `[predates]` date misread as a new event) doesn't change a
  forward run. The large reporting cities (Charlotte, Durham, Raleigh, Greensboro, Huntersville) are at c = 1,
  so the reform adds nothing there either way.
- **Completion factor:** 0.97 for ADUs, from Census completions (`aggregate.yaml`). It is not the driver.
- **ADU tagging:** city flags agree with the counts used on the results page (`observed.json`). See §4 for
  coverage.

**Fix (D-070, `docs/analysis_plan.md`):** the floor is now the **4 years ending at the data origin**
(`adu_observed_years`, D-019's length). A still-blind holdout's window ends before its holdout starts. For a
2022 origin (the backtests) the window is D-019's 2019–2022, unchanged.

## 3. Funnel, NC ADU scenario, 2027–2031 (after the fix; 1,000 draws)

| Stage | P10 | Median | P90 | Compared with |
|---|---|---|---|---|
| Eligible single-family parcels | 3.24M | 3.24M | 3.24M | NC OneMap / Wake / Charlotte rolls |
| **Newly legal**: eligible × (1 − c) | 509k | **624k (19%)** | 740k | 81% of lots already allow an ADU at or near the Handbook (19 S.L. 2026-59 cities at c = 1; borrowers at E[c] ≈ 0.76) |
| Newly legal that pencil out | 46k | 123k | 248k | pro forma F(PCR) |
| **ADU permits added** | 103 | **257** | 792 | uptake ≈ 0.22% of pencil-out parcels over 5 years ≈ 0.045% a year. NC's own rates: Durham 0.036%, Raleigh 0.022% of eligible lots a year (2019–22). West Coast cities run several times higher. |
| Completed (× 0.97) | 99 | 251 | 770 | Census completions |
| New homes (× net-new 0.65 × (1 − formalization 0.10)) | 54 | 140 | 427 | E039/E051/E052 |
| **Net new statewide** (× (1 − displacement 0.25)) | 40 | **104** | 301 | the page's headline |
| *No-reform ADU permits* | 1,314 | *2,023* | 4,106 | |
| *With-reform ADU permits* | 1,464 | *2,292* | 4,861 | ≥ no reform, ≥ history |

Stages are percentiles of each stage's own draws, so they do not multiply exactly at P10 or P90.

**What drives the small added number:** (1) most NC lots are already legal for ADUs, so only 19% are newly
opened; (2) NC's per-lot uptake is low, and the model matches NC's own record there; (3) the gross-to-net
factor of about 0.40. None of these is a bug. The headline is small because NC already allows most of what the
Handbook asks.

**The sentence to say aloud:** *"North Carolina has 3.2 million single-family lots. Most already allow an ADU,
so the reform newly opens about 620,000. About one in five of those pencils out, and a fraction of a percent
of those build in five years. That's about 260 extra ADU permits, roughly 100 net new homes, on top of about
2,000 ADUs NC would permit anyway over 2027–31. With the reform: about 2,300; without: about 2,000."*

## 4. Permit coverage: Census BPS vs city permits (total new units, the same place-years)

| Place | Years | City permits | BPS (reported) | City ÷ BPS | Yearly range |
|---|---|---|---|---|---|
| Raleigh | 2019–25 | 35,366 | 35,978 | 0.98 | 0.61–3.64 |
| Durham | 2019–25 | 26,746 | 24,407 | 1.10 | 0.74–1.67 |
| Greensboro | 2019–25 | 10,448 | 11,099 | 0.94 | 0.85–1.03 |

**Undercount factor: about 1.0 (0.94–1.10) over multiple years.** There is no sign that BPS undercounts total
units in these cities. Single years swing widely (timing, large multifamily permits, Raleigh's 2019 BPS rows
and its 2024–25 unit repair), so compare multi-year totals only. Charlotte/Mecklenburg can't be compared:
held out from 2023-06, and county-tagged city permits cover the unincorporated area only. BPS does not flag
ADUs, so ADU coverage specifically can't be checked this way. The ADU counts come from city flags in 11–13
places only.

**Census Master Address File:** the MAF itself is confidential under Title 13 and available only to sworn
partners (for example LUCA participants). A public by-product may give block-level counts of residential
addresses (the Census "Address Count Listing Files"). That would show net new addresses, but not ADUs. Not
verified here; it's a lead for WS-SCALE, not a source.

## 5. Guardrail

`historical_floor` (scorecard, `model/gutcheck.py`): with-reform permits a year (median) ÷ the 2023–25 observed
average, on the same places. Below 1 is **flagged** (verdict `partial`) unless
`config/historical_floor_reasons.yaml` gives a reason. NC bundle after the fix: **ADU 1.09 pass, missing
middle 1.30 pass.** Before the fix, the same arithmetic gives ADU 81 ÷ 126 = **0.64: flagged.**

## 6. TX spot check (report only; fixes go to WS-TX)

- **Units:** the same framing as NC. TX's headline is 568 / 1,351 / 3,432 net homes added over 5 years,
  statewide.
- **Baseline vs history:** the 5 ADU-flagging places show 379, 341, 389, 376, 309, **164, 79** (2019–25). The
  2024–25 drop is Austin's HOME reclassification: ADUs counted as duplexes. With this PR's trailing window, the
  Austin-area no-reform floor falls to **232 a year** (it would be about 371 on 2019–22). The headline barely
  moves (net added 1,351 vs 1,356): the added effect comes from the 4.2M newly legal lots, mostly outside
  those places.
- **Funnel:** 7.34M eligible → 4.19M newly legal (56%; TX allows far less today than NC) → 1.45M pencil out →
  3,477 permits added → 1,351 net new statewide. No-reform ADUs 3,197 vs with reform 6,765 over 5 years.
- **For WS-TX:** turn the Austin HOME fix into a documented adapter rule: tag 2024+ HOME two-unit permits on
  single-family lots as ADUs, with an assumption and a sensitivity range. The trailing floor then reads the
  real 2022–25 pace. Until then, TX's no-reform ADU baseline is understated in Austin.
- Guardrail: TX ADU 1.70 (pass, against an artifact-low 2023–25 average), missing middle 1.15 (pass).

## Files

`adu_two_worlds.csv`, `adu_funnel.csv`, `adu_observed.csv`, `baseline_total.csv`, `permit_coverage.csv`,
`adu_history.png`, `baseline_history.png`. `after/` holds the same files after the fix; the top level is
before it. Re-run: `uv run python scripts/dev/gutcheck_diagnostics.py NC [--out ...]`. CSVs are gitignored;
they are derived from the local data store.
