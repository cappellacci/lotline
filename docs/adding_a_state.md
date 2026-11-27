# Adding a new state to Lotline: a step-by-step guide

*Every file path, setting and command below was checked against the code on 2026-11-27.*

This guide is for an analyst with a copy of the repository who wants Lotline's ADU, missing-middle and fee
results for a state it does not cover yet. You can stop after any level in section 2. Each level after the
first narrows the ranges.

Throughout, `XX` is the new state's two-letter code in capitals (for example `WI`) and `xx` is the same code
in lower case, as file names use it.

---

## The short path (one page)

This path gives a first result with national data only (level 0 in section 2). It needs no local data and no
code. After you write the state config (step 2), one command does the rest:

```bash
uv run lotline run --state XX
```

It fetches the national data, runs all three reforms, builds the data tab and writes the page to
`reports/app/index.html`. If a data source fails, the fetch keeps going and lists the sources it skipped at the
end. `--skip-fetch` reruns the models on tables you already built, `--offline` uses only files already
downloaded, and `--draws 200` gives a quicker, rougher run.

If you want to run each part yourself, these are the same steps one at a time:

<!-- short-path:begin (generated from config/onboarding/steps.yaml) -->
1. **Write the state config** (step 2, 15 minutes).
2. **Check the state file** (step 3, 1 minute).
   ```bash
   uv run lotline onboard --state XX
   ```
3. **Fetch the national data** (step 6, about an hour, mostly waiting).
   ```bash
   uv run lotline fetch --state XX
   uv run lotline validate --state XX
   ```
4. **Run the models for the first time** (step 7, a few minutes).
   ```bash
   uv run lotline results --state XX
   ```
5. **Read the results before you show them** (step 11, an hour).
<!-- short-path:end -->

For step 2, copy `config/states/oh.yaml` to `config/states/xx.yaml` and change the state code, name, FIPS
code, Census region and ZIP prefixes (section 5, step 2). After step 7, `uv run lotline app` rebuilds the
page. Then read the confidence flags in the bundle: `meta.data_tier`, `meta.overlap_flag` and `meta.caveats`
(step 11). With national data only, the ADU ranges are wide and the bundle says "National data only". The
levels in section 2 say what each kind of local data adds.

`uv run lotline onboard --state XX` prints this checklist for your state, marks what is already done and
shows the next commands. `--json` gives the same plan to the app.

---

## 1. What you will end up with

- `config/states/xx.yaml`: the state's settings.
- `config/reforms/xx.csv`: the state's ADU and missing-middle rules, one row per rule per place.
- `config/fees/xx.csv`: the state's development fees, one row per fee per place.
- Optionally, adapters in `src/lotline/adapters/states/xx/` for local parcel and permit data, with tests in
  `tests/states/xx/` and land-use crosswalks in `config/crosswalks/xx_*.csv`.
- A results bundle at `reports/results/xx/bundle.json` with the ADU, missing-middle and fee results, and the
  state on the app's map (`reports/app/index.html`).
- A readiness report, `docs/build/xx-readiness.md`, and an `XX` section in `docs/data_availability.md`.

---

## 2. Decide how much data you will bring

More local data gives narrower and more trustworthy ranges, so decide early how far you will go. Lotline runs
at four levels of local effort. National data (Census permits, the ACS, FHFA prices, FRED rates and costs)
covers every state, so level 0 needs no local data at all.

| Level | You add | Data tier the app shows | What we know about accuracy |
|---|---|---|---|
| **0. National only** | The state config, and a reform file with the state's own ADU and middle-housing laws if it has any | Tier 3, "National data only" | **ADU: not reliable on its own.** In our leave-one-state-out test (D-075, scored under D-088), national data alone worked in Minnesota only. Oregon's median came out 8 times too low |
| **1. Coded local rules** *(recommended minimum)* | Level 0, plus the local ADU rules of the state's **20 largest places** (by eligible lots), the local middle-housing rules you can find, and fees for **at least 5 places** | Tier 3 | **ADU: passes.** The same test passed in all 4 states that could be scored: the observed total fell inside the P10–P90 range and within ×2 of the median. The ranges are wide (P90 ÷ P10 from ×4 to ×71) |
| **2. One measured city** | Level 1, plus record-level permits that flag ADUs for at least one large city | Tier 3 unless you also add parcels | ADU: also passes, and anchors the state's level to its own counts |
| **3. Local parcels** | Parcel rolls with land use, ideally with year built | Tier 2 or 1 for the places they cover | Replaces the ACS estimate of eligible lots with a real count, and lets us measure zone-limited rules |

The code applies these thresholds:

| Rule | Value | Where it is set |
|---|---|---|
| A place's parcels count as tier 2 | ≥ 90% of its parcels have a known land use | `config/params/tiers.yaml` |
| … and as tier 1 | also ≥ 80% of built parcels have a year built | `config/params/tiers.yaml` |
| A state uses its own ADU rule prior | ≥ 5 coded places (per size band, else statewide) | `adu_rule_min_coded`, `config/params/adu.yaml` |
| A state uses its own middle-housing dose prior | ≥ 5 coded places (per size band, else statewide) | `mm_rule_min_coded`, `config/params/mm.yaml` |
| A state uses its own fee prior | ≥ 5 coded places | `MIN_PLACES`, `src/lotline/model/fee_levels.py` |
| Below those minimums | Priors are borrowed from the five fitted states' coded places | same files |
| Census permit totals reconcile | place sum within 1% of the state total | `lotline validate --state XX` (V0) |

**What we do not know yet.** The missing-middle model has no data-tier result. Our D-092 accuracy run could
not test it because too few permit sources had years after a reform (`reports/mm-d092/run5-tests/README.md`).
The fee scenario has no such test either. Treat level 1 as the minimum for all three models until those tests
exist.

**What each kind of local data is worth.** We ran North Carolina four times with the same seed: once as is,
then three times with one input dropped to the fallback a state without it would get. The table shows the
change in the five-year statewide median of net new homes against the full run, and the P10–P90 range as a
multiple of the full run's range.

| Input dropped | Fallback | ADU median | ADU range | Middle housing median | Middle housing range | Fees |
|---|---|---|---|---|---|---|
| Parcels | ACS count of one-unit homes, scaled (D-056); tier 3 | −4% | ×0.97 | −18% | ×0.79 | +3%, ×1.03 |
| Zoning rules (`config/reforms/nc.csv`) | Rule priors borrowed from the other coded states | +251% | ×4.9 | +51% | ×1.5 | unchanged |
| Permits | No observed ADU floor | +4% | ×1.01 | unchanged | unchanged | unchanged |

Coded local rules matter most. Without them, North Carolina's places take the other states' rule mix, the ADU
median rises 3.5-fold and its range widens almost 5-fold. This suggests that North Carolina's own ordinances
allow ADUs less often than the borrowed mix (we did not check this rule by rule). It is why level 1 is the
recommended minimum.

Parcels move the middle-housing median by about a fifth, but they do not widen the range. The ACS fallback
gives a smaller eligible count, so the range narrows with it. The D-056 factor's own uncertainty is in the
fallback, but here it is smaller than the change in the count.

Permits barely move the scenario totals. Their job is to supply the observed ADU counts and the tests, not the
forecast.

These numbers come from one state, one seed and 1,000 draws. A state whose own rules are looser than the
borrowed mix would move the other way. To rerun the test, use
`uv run python scripts/dev/missing_input_matrix.py --state NC --out <folder>`. It runs offline, writes nothing
to the data directory and keeps holdouts hidden.

---

## 3. What the code does for a new state

A new state runs without any change to the code. `tests/model/test_new_state_runs.py` proves this by building
a full bundle for a made-up state with national data only, no permits and no reforms file.

1. **You don't add the state to `REFORM_STATES`.** That list (`src/lotline/model/scenarios/adu_rule_inputs.py`)
   holds the five fitted states whose coded rules feed the shared priors. A state outside it borrows from them
   and feeds nothing back, so no other state's results move.
   - `config/reforms/xx.csv` is optional. Without it the state has no coded rules, and every place takes the
     borrowed priors. With it, the state's rules apply to its own places.
   - Adding a state to `REFORM_STATES` is part of pooling it into the calibration (step 14). That is a method
     decision, because the state's coded rules would then shift every other state's priors.
2. **A state with no permit table runs.** A missing permit table is read as empty: there is no observed ADU
   floor and no `adu_permits` rows in the bundle's `observed` part.
3. **No test pins the list of states.** `tests/core/test_config.py` checks that the five fitted states are
   present, not that they are the only ones.

**What the new state reads from other states.** The ADU rule priors and field counts it borrows are saved in
`config/params/adu_rule_priors.csv` and `config/params/adu_field_counts.csv`, one block per origin year from
2016 to 2025. The calibration step `adu_rule_priors` writes them. For ADUs, your run reads only your own
state's tables, and an origin year outside 2016–2025 stops with an error that names the step to rerun.

The missing-middle model is different. A new state with no coded missing-middle rule of its own borrows its
dose from the five fitted states' coded places, by size band (`borrowed_pool` in
`src/lotline/model/scenarios/mm.py`). That pool is built at run time from their reform files in `config/` and
from their `jurisdictions` tables (and parcels, for zone-limited rules) in your data folder. So unless your
state has at least one coded missing-middle rule, build those tables once:

```bash
uv run lotline fetch --source jurisdictions
```

With no `--state`, this builds the `jurisdictions` table of every configured state, including yours.

---

## 4. Before you start

1. **Set up the repository** as the README's Setup section says (`uv sync`).
2. **Copy `.env.example` to `.env`** and fill in:
   - `CENSUS_API_KEY`, free from the Census Bureau. The ACS, decennial and County Business Patterns adapters
     need it.
   - `LOTLINE_DATA_DIR`, which defaults to `~/lotline-data`, outside the repository.
   - Optionally `SOCRATA_APP_TOKEN`, if a city portal you use runs on Socrata.
3. **Work on a branch** of your own, for example `ws/xx`, so your changes stay apart from `main`.
4. **Decide now whether the state will be a blind test.** If you want to predict the state before you see its
   outcomes (as we did for Oregon in V9), its holdouts must be in the config *before the first fetch*. The
   project maintainers add and release holdouts. Never pass `--unblind`.
5. **Watch for state codes that are Python keywords.** Oregon's package is `adapters/states/or/`, and `or` is a
   Python keyword. Indiana (`in`) has the same problem. The registry imports such a package by name and that
   works, but tests must import its modules with `importlib`. See `tests/states/or/test_package.py`.

---

## 5. The steps

The table lists every step. Under **Ways to do it**, *manual* means you follow this guide, *built-in* means
`lotline onboard` and the app show the commands to run, and *agent* means the rule agents can propose the
table for you ([adding local rules with the agents](adding_local_rules_with_agents.md)). **Done when** names
the check `lotline onboard` runs.

<!-- steps-table:begin (generated from config/onboarding/steps.yaml) -->
| Step | Level | Time | Ways to do it | Done when |
|---|---|---|---|---|
| 1. Look at what the state publishes | 0 national | about half a day | manual | docs/build/xx-assessment.md exists |
| 2. Write the state config | 0 national | 15 minutes | manual | config/states/xx.yaml loads |
| 3. Check the state file | 0 national | 1 minute | manual, built-in | the state file agrees with the repository |
| 4. Code the state's ADU and middle-housing rules | 1 rules | 1 to 3 days for 20 places | manual, agent | config/reforms/xx.csv loads and passes the reforms schema |
| 5. Code fees for at least 5 places | 1 rules | 1 to 2 days | manual, agent | config/fees/xx.csv covers at least 5 places |
| 6. Fetch the national data | 0 national | about an hour, mostly waiting | manual, built-in | the six national tables are built |
| 7. Run the models for the first time | 0 national | a few minutes | manual, built-in | reports/results/xx/bundle.json exists |
| 8. Add local parcels | 3 parcels | 1 to 3 days per source | manual | a parcels table is built |
| 9. Add local permits | 2 permits | 1 to 2 days per source | manual | a permits table is built |
| 10. Rebuild the derived tables | 2 permits | about 10 minutes | manual, built-in | every GEOID in your data is a jurisdiction |
| 11. Read the results before you show them | any | an hour | manual | you have read the confidence flags (a person decides) |
| 12. Write it up | any | half a day | manual, built-in | docs/build/xx-readiness.md exists |
| 13. Run the checks | any | 15 minutes | manual, built-in | tests and compliance_check.py pass (a person decides) |
| 14. Pool the state into the calibration (optional) | any | a method decision | manual | an analysis_plan.md entry records the decision before any run (a person decides) |
<!-- steps-table:end -->

### Step 1. Look at what the state publishes (about half a day)

A short assessment before any code tells you which levels are within reach. `docs/build/or-assessment.md` is
the model. Answer these questions:

- Does the state have a **statewide ADU or middle-housing law**? Note its effective dates, which places it
  covers (often by population), and whether it reaches small towns.
- **Local rules**: which of the 20 largest places have their own ADU or middle-housing ordinances, and where
  is the official code text?
- **Fees**: where do the six largest places publish their fee schedules (water and sewer connection, impact,
  building permit and plan review)?
- **Permits**: which cities publish record-level permits, and do any flag ADUs?
- **Parcels**: is there a statewide or county parcel layer with land use and year built?
- **Licenses**: what are the published terms of every candidate source? Use only sources whose terms allow
  use in an Apache-2.0 public pipeline. The National Zoning Atlas does not, for example.

Search `docs/research/lotline-data-catalog.csv` first, since we scouted some states early on.

### Step 2. Write the state config (15 minutes)

This one file is all the code needs to know about a state. Create `config/states/xx.yaml` by copying
`config/states/oh.yaml` and changing the values. The loader rejects any key it does not know.

```yaml
state: XX                 # required, two capital letters, must match the file name
name: Statename           # required
fips: "55"                # required, two-digit state FIPS code, in quotes
bps_region: Midwest Region  # required: Northeast Region, Midwest Region, South Region or West Region
township_permits: false   # true where townships issue building permits (MN, OH, WI, MI, PA...)
zip3_ranges: [[530, 549]] # needed: the state's USPS 3-digit ZIP prefixes, inclusive; FHFA's ZIP index fails without it
holdouts: []              # set by the project maintainers; see section 4
sources: []               # one entry per local adapter you add (steps 8 and 9)
```

Add these optional keys later, when they apply:

- `adu_state_law_rows_complete: true`, only if you generate a state-law row for **every** place the state's ADU
  law covers, as Oregon does (D-068). A place without a row is then read as outside the law.
- `parcel_sources`, needed only when two parcel sources cover the same jurisdiction.
- `local_jurisdictions`, for governments the Census permit survey has no row for (it files their permits
  under a county) but that your own permit or parcel data reports separately. Write them as
  `"GEOID": "Name"`. Minnesota lists 23 townships and North Carolina 196 towns. The jurisdictions list is the
  survey's places, these governments and the holdouts. It never reads your data, so it needs no rebuild when
  you add a source. After adding a permit or parcel source, run `uv run lotline unlisted --state XX`. It
  prints every GEOID your data uses that the list lacks. Add the real governments among them here.
- `data_tiers`, to override a place's tier by hand.

Saving this file registers the state everywhere the code calls `all_states()`, including the app.

### Step 3. Check the state file (1 minute)

```bash
uv run lotline onboard --state XX
```

Step 3 of its list checks the state file against the rest of the repository. Every GEOID in it must belong to
the state, the files it names must exist, and `parcel_sources` must name real sources. The same checks run in
`tests/config/test_state_schema.py`.

### Step 4. Code the state's ADU and middle-housing rules (1 to 3 days for 20 places)

Coded local rules move the results more than any other input (section 2), so this step makes level 1 pass.
The rule agents can propose this file for you
([adding local rules with the agents](adding_local_rules_with_agents.md)). To code it by hand, create
`config/reforms/xx.csv` and copy the header line exactly from `config/reforms/or.csv`:

```
reform_id,state,jurisdiction_geoid,theme,component,status,announced_date,adoption_date,effective_date,end_date,supersedes,by_right,owner_occ,unit_cap,far_cap,max_stories,min_lot_sqft,adu_max_sqft,adu_detached_allowed,adus_per_lot,lot_split,parking,parking_min_per_unit,fee_change_usd,dollar_year,coverage,coverage_zones,source_url,source_section,source_quote,verified_by,verified_date,coder,coder_2,coder_agreement,coding_notes
```

Code the places in this order:

1. **The state law**, if there is one.
   - ADU: a row whose `jurisdiction_geoid` is the 2-digit state FIPS applies to every place.
   - Middle housing: a 2-digit row is **not** applied to places. Write one row per covered place instead.
     When coverage depends on population (as with Oregon's HB 2001), generate the rows with a script like
     `scripts/dev/or_state_reform_rows.py`, and mark generated rows `GENERATED` in `coding_notes`.
2. **Local rules for the 20 largest places by eligible lots.** After step 6 you can list the places with
   `eligible_parcels` from the data store. Until then, use 2020 population.
3. **Any other place that changed its rules** in the last ten years.

Record a place that does **not** allow ADUs too, with `adus_per_lot` = 0. Leaving it out means "unknown", and
the model then borrows a rule from similar places.

Fill the main columns like this:

| Column | What to write |
|---|---|
| `jurisdiction_geoid` | 7-digit Census place GEOID, or 5-digit county GEOID for an unincorporated remainder, or 2-digit state FIPS for a statewide ADU law |
| `theme` | `adu` or `missing_middle` (also `parking` for a citywide parking change) |
| `status` | `in_force`, `suspended`, `repealed`, `opted_out` or `pending`. The models read `in_force` rows only |
| `adoption_date`, `effective_date` | ISO dates (YYYY-MM-DD). The model treats a rule as in force from the year it is in force on 1 July |
| `supersedes` | the `reform_id` of the earlier row this one replaces; blank fields are then filled from it |
| `by_right` | `True` if approved without a public hearing, `False` otherwise |
| `owner_occ` | `True` if the owner must live on the lot |
| `adu_detached_allowed` | `True` or `False` |
| `adu_max_sqft` | the size cap in square feet |
| `adus_per_lot` | `0` means ADUs are not allowed |
| `parking`, `parking_min_per_unit` | the parking rule as written, and the minimum spaces per ADU |
| `unit_cap` | middle housing: homes allowed per lot (2, 3, 4…). `1` codes a "not allowed" control row |
| `coverage` | `citywide`, or words naming the limited area |
| `coverage_zones` | the zones it applies in, separated by `;` (measured against parcels' zoning where you have it) |
| `min_lot_sqft` | the smallest lot it applies to |
| `source_url`, `source_section`, `source_quote` | the official code page, the section number, and the deciding words (≤ 300 characters) |
| `coder`, `coder_2`, `coder_agreement` | who coded it, who checked it, and `agree`, `adjudicated` or `single_coder` |
| `coding_notes` | free text, plus these tags where they apply: `[predates]` (in force since before the data starts; never an event), `[earliest-known]` (the first date you could find, not a confirmed adoption date), `DATE UNCONFIRMED`, `[standards]` (a standards-only reform) |

Booleans are `True`, `False` or blank. **Blank means unknown, never "no restriction".**

This is how a rule becomes a model input:

- **ADU.** The ADU model checks each rule against the Handbook test. A rule fails the test if it needs a
  hearing (`by_right` False), requires the owner to live on the lot, bans detached ADUs, caps ADUs below
  600 sq ft or requires parking. Where several rules apply, the most permissive one wins (`current_rules` in
  `src/lotline/model/scenarios/adu_rules.py`).
- **Missing middle.** The rule's "dose" is units grade × approval grade × coverage
  (`src/lotline/model/mm_rates.py`). The units grade is 1/3 for 2 homes per lot, 2/3 for 3 and 1 for 4 or more.
  The approval grade is 1 by right and 0.333 otherwise.

Read rules from the official code, not from memory, and have a second person check every dated row. Every
other state's rows meet that standard.

To check the file, add `tests/states/xx/__init__.py` and `tests/states/xx/test_reforms.py`, copied from
`tests/states/oh/test_reforms.py`. That test reads the CSV as text, so a typo like "Ture" fails instead of
becoming blank. It checks every row against the `reforms` schema and lists the 20 largest places it expects to
see. Then run:

```bash
uv run pytest tests/states/xx -q
```

### Step 5. Code fees for at least 5 places (1 to 2 days)

With 5 coded places the state gets its own fee prior instead of the pooled median of all states. The rule
agents can propose this file too (`/rules-fees XX`). By hand, create `config/fees/xx.csv` following
`config/fees/README.md` and `docs/build/manual-fee-lookups.md`. The main steps are:

1. Take the **largest places by 2020 population**, about six. Five is the minimum for the state's own prior.
   With fewer, every uncoded place takes the pooled median of all states.
2. Open each place's **official fee schedule**. Write one row per fee component and building type for the
   water and sewer connection or capacity fee, impact fees, and the building permit and plan review fees.
   Use building types `SFD`, `ADU`, `U2` and `U3_4` (and `OTHER` for a fee that applies to any type). Skip
   buildings of 5 or more units.
3. Copy the fee **exactly** into `amount_usd`. Convert it to one home in `amount_per_unit_usd`, and say how in
   `notes`. For valuation-based fees, use the prototype house: 2,150 sq ft, valued at about $355,000.
4. **Fees that vary by area or tier:** put the median on one row and the range in
   `amount_per_unit_low_usd` and `amount_per_unit_high_usd`.
5. For duplex and fourplex water fees, one meter per unit is the central case. The master-meter case goes in
   the range (D-069).
6. **If you can't find a fee, leave the row out. Never write 0**, because 0 means the place charges nothing.
   Leave `amount_per_unit_usd` blank for fees that don't apply to a typical infill home (rezoning, variances,
   per-acre charges).

The required columns are:

- `state`, `jurisdiction_geoid`, `year`;
- `fee_component`: `water_sewer`, `impact`, `permit`, `planning` or `other`;
- `fee_type`: the schedule's own name for the fee;
- `building_type_std`;
- `basis`: `per_unit`, `per_sqft`, `per_lue`, `pct_of_value`, `flat` or `other`;
- `amount_usd`, `amount_per_unit_usd`, `dollar_year`;
- `source`: the schedule's URL.

Add `source_section`, `source_quote`, `verified_by` and `verified_date` when you can.

The model fills gaps this way. A coded place missing its water and sewer or permit fee has that fee filled
from the state's other places. A coded place missing impact, planning or other fees counts them as zero. A
place with no rows takes the state's median, or the pooled median if the state has fewer than 5 places. The
Handbook's $50,000 is never used as a fallback.

To check the file, add `"XX"` to the `parametrize` list of `test_committed_fee_tables_validate` in
`tests/core/test_ordinance_records.py` (about line 209), then run:

```bash
uv run pytest tests/core/test_fees_config.py tests/core/test_ordinance_records.py -q
```

### Step 6. Fetch the national data (about an hour, mostly waiting)

```bash
uv run lotline fetch --state XX
```

This downloads into `LOTLINE_DATA_DIR` and records every file in `manifest.jsonl`. If one source fails, the
fetch keeps going and lists the skipped sources at the end. Each error is one plain line, and
`uv run lotline --debug fetch --state XX` shows the full traceback. The fetch builds:

- `acs_geo_year`: rent, home value, homes by type and households;
- `bps_place_year`: Census permits by building size, per place and township;
- `market_geo_year`: FHFA prices, FRED rates and costs, and the demand index;
- `jurisdictions`: every permit-issuing place, with its tier;
- `eligible_parcels`: eligible lots from the ACS (one-unit detached homes) where there are no parcels;
- `place_inputs` (last): one row per place and year with every input the models share (eligible lots for
  ADUs and middle housing, rent and value, observed ADUs, permits by size, place type, price index). Its
  `models` column says which models read the place, and `models_note` says why it is left out of the others.
  Open it to see exactly what the models will see for your state.

Then check the national data:

```bash
uv run lotline validate --state XX
```

This runs check V0 and writes `reports/xx/V0-national.md`. It checks that the Census place permits add up to
the state total within 1%. Read it, and note any places Census imputed. `uv run lotline validate` with no
flags lists every check and blind test, and `--step V1` runs the baseline backtest.

If your state has no coded missing-middle rule yet, also run `uv run lotline fetch --source jurisdictions`
once, so the model can borrow the five fitted states' doses (section 3).

### Step 7. Run the models for the first time (a few minutes)

```bash
uv run lotline results --state XX
uv run lotline app
```

`lotline results` runs the ADU, missing-middle and fee scenarios and writes `reports/results/xx/bundle.json`.
Each scenario draws 1,000 times from origin year 2025 (`config/params/aggregate.yaml`). With national data
only, it labels the state `national_only`, scales the ACS eligible-lot count by the D-056 factor with that
factor's uncertainty, and adds the caveat "National data only". `lotline app` then rebuilds the page.
`uv run lotline run --state XX --skip-fetch` does both in one go.

If the missing-middle step stops on a missing `jurisdictions` table for another state, run
`uv run lotline fetch --source jurisdictions` (section 3).

### Step 8. Add local parcels (optional, level 3; 1 to 3 days per source)

Parcels replace the ACS estimate of eligible lots with a real count. Each source plugs in through a small
adapter that turns it into the same table every state uses.

1. **Write an adapter**, `src/lotline/adapters/states/xx/<name>_parcels.py`, using
   `src/lotline/adapters/states/or/rlis_parcels.py` as the template. The registry picks up a module
   automatically if it defines these four names (`src/lotline/registry.py`):
   - `SOURCE`: a source id, unique across all sources;
   - `TABLE`: `"parcels"`;
   - `PROVENANCE`: title, landing URL, table, cleaning steps, limitations;
   - `load(state, store, *, refresh=False)`, which returns the canonical table.

   Existing adapters also set `ADAPTER` and `VERSION`, and yours should too. An adapter that reads another
   table from the store (most parcel adapters read the jurisdictions list through `geo.known_geoids`) sets
   `READS = ("jurisdictions",)`, so a plain `lotline fetch` builds that table first
   (`registry.fetch_order`). Add `src/lotline/adapters/states/xx/__init__.py`.
2. **Download through the IO layer** (`lotline.io`: `fetch`, `arcgis` or `socrata` into `store.raw(...)`) so
   the file lands in the manifest. For a file you can only download in a browser, register it:
   ```bash
   uv run lotline manifest register ~/lotline-data/manual/xx/file.zip --source <name>_parcels --url <page> --license "<terms as published>"
   ```
3. **Fill the required parcel columns**: `state`, `parcel_id`, `vintage`, `jurisdiction_geoid`, `lot_sqft`,
   `land_use_std`, `land_use_raw` and `source`. Add `year_built`, `units` and `zoning_raw` when the source has
   them. **Never request owner names or addresses.** List those fields in a `PERSONAL` set and test that they
   are never requested, as the Ohio and North Carolina adapters do.
4. **Tag each parcel with its jurisdiction** using `lotline.geo`, not your own lookup:
   - For a source covering one city, set `jurisdiction_geoid` to that city's GEOID as a constant.
   - Otherwise, call `geo.place_or_township(lon, lat, state, store)` for each point. It uses the Census
     TIGER/Line 2025 boundaries of incorporated places and county subdivisions. Then call
     `geo.resolve(steps, geo.known_geoids(state, store))`, where `steps` is your rule as an ordered list, for
     example `[("place", place), ("county_remainder", county_geoid, False)]`. The first step that gives a GEOID
     in the jurisdictions table wins (`False` keeps the value even if it is not in the table), and every row
     gets a `how` label saying which step placed it. `resolve_jurisdictions` in
     `src/lotline/adapters/states/nc/onemap_parcels.py` is a three-line example.
   - For a source that names its city or uses a code ("TC" for Cary), put each name or code in
     `config/crosswalks/xx_aliases.csv` (`source,field,raw,geoid,notes,source_url`), read it with
     `geo.aliases("XX", "<source>", "<field>")` and use the result as a resolver step. `nc_aliases.csv` is the
     example.
5. **Map land uses** with a crosswalk, `config/crosswalks/xx_<source>_land_use.csv`.
   - Every source code maps to one of `SF_DETACHED`, `SF_ATTACHED`, `DUPLEX`, `TRI_QUAD`, `MULTIFAMILY_5P`,
     `MOBILE_HOME`, `CONDO_UNIT`, `VACANT_RESIDENTIAL`, `MIXED_USE`, `COMMERCIAL`, `INDUSTRIAL`,
     `AGRICULTURAL`, `INSTITUTIONAL`, `OTHER` or `UNKNOWN`.
   - Use the land-use format, `field,code,description,land_use_std,notes,source_url`, and read it with
     `lotline.adapters.crosswalks.read(path, "land_use")`. The reader checks the header and that every
     `land_use_std` is in the list above. `config/crosswalks/oh_dte_luc.csv` is a simple example.
   - Labels that vary by county are matched with ordered rules instead of exact codes. Leave `code` blank and
     add a `pattern` column (a regular expression; the first match wins), plus `county` if a rule holds in one
     county only (`mn_land_use.csv`, `or_rlis_land_use.csv`).
6. **Call** `holdout.apply(...)` on the rows before returning them, then `validate(df, TABLE)`.
7. **Add a `sources:` entry** in `config/states/xx.yaml` with name, URL, license, access, cadence and notes.
8. **Name your judgments.** A share, threshold, date or label your adapter applies to the data beyond
   reshaping it goes in the state file's `rules:` block, not in code. An example is "a taxing district maps
   to a city when 95% of its parcels are in that city". Give each rule `value`, `unit`, `what`, `assumption`,
   `source` and `used_by` (the modules that read it), plus `low` and `high` when you know a sensitivity range.
   Read it with `lotline.config.state_rule("XX", "<rule id>")`. `config/states/oh.yaml` has three examples
   and `tx.yaml` two.

### Step 9. Add local permits (optional, level 2; 1 to 2 days per source)

A city's own permits that flag ADUs tie the state's level to its own counts. The pattern is the same as in
step 8. Use `src/lotline/adapters/states/or/bend_permits.py` as the template and `"permits"` as the table.

- **Required permit columns:** `state`, `permit_id`, `jurisdiction_geoid`, `issue_year`, `issue_date`,
  `date_precision`, `building_type_std`, `type_confidence`, `units_new`, `units_removed`, `units_confidence`,
  `is_demolition`, `is_conversion` and `source`.
- **Building types:** `SFD`, `ADU`, `TH`, `U2`, `U3_4`, `U5_6`, `U7P`, `DTQ`, `MF5`, `OTHER` or `UNKNOWN`.
  Never guess a finer type. Set `type_confidence` to `inferred` or `unknown` instead.
- **Shared helpers:** `src/lotline/adapters/common.py` has the size-class rules several permit adapters share.
  `multi_type(n)` gives the Census class of a building of 2 or more units (`U2`, `U3_4`, `MF5`, else None),
  `size_class(n)` does the same but returns `UNKNOWN` below 2 units or with no count, and
  `units_fit(fits, btype, n)` checks a reported unit count against your adapter's `FITS` table. Use them
  instead of writing your own.
- **Map permit types** with a building-type crosswalk,
  `field,code,description,building_type_std,role,derived_units,notes,source_url`
  (`config/crosswalks/nc_gso_occupancy.csv` is the example), read with
  `crosswalks.read(path, "building_type")`. `role` is what the permit does in your adapter's terms
  (dwelling, multi, demolition and so on). `derived_units` is the unit count to record when the source gives
  none.
- **ADUs:** mark them `building_type_std = ADU` (or fill `adu_type`). A permit that builds a house and an ADU
  together is split into two rows (D-041).
- **Hand-check the flag.** If ADUs come from reading descriptions, check 30 flagged and 30 unflagged permits
  by hand (D-074). The undercount factor for the source then goes in `adu_flag_undercount` in
  `config/params/adu.yaml`. Without a row, the factor is 1.

Once a source flags ADUs, the ADU model uses that city's own recent counts as its no-reform rate.

### Step 10. Rebuild the derived tables (about 10 minutes)

The national build steps read whatever local tables exist when they run, so rebuild them after adding
sources, in this order:

```bash
uv run lotline unlisted --state XX
uv run lotline fetch --state XX --source jurisdictions
uv run lotline fetch --state XX --source eligible
uv run lotline fetch --state XX --source demand
uv run lotline fetch --state XX --source place_inputs
```

`unlisted` lists the GEOIDs your new data uses that are not jurisdictions yet. Add any real government among
them to `local_jurisdictions` (step 2) and rerun the adapter. `jurisdictions` then picks up each place's tier
from its parcels, the one thing it still reads from local data. `eligible` swaps the ACS estimate for the
parcel count where parcels exist. `place_inputs` goes last, since it reads every other table. Then rerun
step 7.

A state with local data that is not in any fit (the usual case) should be labelled a transfer state:

```bash
uv run lotline results --state XX --role transfer
```

### Step 11. Read the results before you show them (an hour)

A number quoted without its confidence flags can mislead a lawmaker, so read these first. Open
`reports/results/xx/bundle.json`, or rebuild the page with `uv run lotline app`, and check:

- **`meta.overlap_flag`**: whether the state's places sit inside the range of places the model learned from.
  Outside means low confidence. Say so wherever you quote the number.
- **`meta.caveats` and `meta.data_tier`.**
- **The state effect.** A state outside the ADU fit gets a random state multiplier drawn from the spread of
  the fitted states (D-043, D-044). Its ADU ranges are wider for that reason. This is intended, not a bug.
- **Places with no rent or home value** in the ACS. They are dropped from the bundle, so count them.
- **Where the fees come from.** The app's fee card lists each place with coded fees and marks any fee filled
  from the state's other places. Every place without rows takes the state median, or the pooled median below
  5 coded places (step 5).

### Step 12. Write it up (half a day)

1. Write **`docs/build/xx-readiness.md`** in the shape of `docs/build/or-readiness.md`. It needs a coverage
   table for each input (jurisdictions, eligible lots, parcels, permits, ADU flags, rules, fees, market,
   demand, holdouts), what is blind, and the remaining gaps and what would close each.
2. Add **an `XX` section to `docs/data_availability.md`**. For each data need, say what exists, what Lotline
   uses and why the rest is not used.
3. Regenerate the **provenance** document:
   ```bash
   uv run lotline provenance --write
   ```
   This rebuilds `docs/data_provenance.md` from the manifest. It fails if any built table has no manifest
   entry.
4. Add a row to **`docs/disclosures.md`** for any new host the adapters call.

### Step 13. Run the checks (15 minutes)

The checks show that your state's files and adapters meet the same standard as the five fitted states. Run:

```bash
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
uv run lotline schemas
uv run lotline provenance
python compliance_check.py
python compliance_check.py --run
```

All must pass, and `compliance_check.py` must show 0 FAIL.

**Every new adapter ships with `tests/states/xx/test_<source>.py`.** Tests run on small rows written in the
test, never on downloaded data and never over the network. Each one checks that:

- the output conforms to the schema (`assert_conforms(build(raw), "permits")`);
- the classification rules hold and the right rows are dropped;
- no personal fields are requested;
- `load()` keeps holdouts hidden.

**Contributing the state back (optional).** To add your state to the public Lotline, open a pull request
with the files from steps 2, 4, 5, 8, 9 and 12. Describe in it any method choice you made.

### Step 14. Pool the state into the calibration (optional)

Up to step 13, the new state *uses* the fitted models but does not change them. Adding its data to the fits is
a separate method decision. It must be recorded in a `docs/analysis_plan.md` entry before any run, as Oregon's
was (D-053 for ADUs, D-092 for missing middle). If the state might later be a blind test, freeze its
prediction first.

- **ADU:**
  1. Add the state to `STATES` in `src/lotline/calibrate/adu/adu_fit_set.py`. Its places enter by rule: a
     coded rule in force, eligible lots and a permit source that flags ADUs (`fit_set`, D-079).
  2. Rerun the ADU chain in the order `uv run lotline calibrate --list` prints: `adu_joint`,
     `adu_partial_share_grid`, `adu_anchor_slopes`, `adu_calibration_range`, `adu_town_prior_sd`,
     `adu_new_rule`, `adu_state_effect`, `adu_drift` and `adu_ramp_share`. Use
     `uv run lotline calibrate --run --step <name>` to compare, then add `--write` to update config and the
     lock. `adu_state_effect` adds `adu_state_effect_fitted__XX` to `config/params/adu_state_effect.yaml`.
- **Shared rule priors:** add the state to `REFORM_STATES` in `src/lotline/model/scenarios/adu_rule_inputs.py`,
  so its coded rules feed the priors other states borrow. Then rerun the `adu_rule_priors` step
  (`--run --step adu_rule_priors`, then `--write`) so the saved borrowed priors include it. Record the
  before and after bundles.
- **Missing middle:**
  1. Add the state to `STATES` in `src/lotline/calibrate/mm/mm_fitsets.py` (and to `SPREAD_STATES` if its
     uncoded places should count toward φ).
  2. Rerun `mm_units_per_project`, `mm_year_spread`, `mm_c4` and `mm_fast_ramp` the same way (`--run`, then
     `--run --write`).
  3. D-092's §7 accuracy tests are archived in `scripts/archive/mm_tests_d092.py` as the record of how D-092
     was scored. They have no `lotline calibrate` step, and rerunning one is a method decision for the
     project maintainers.
- **Validation:** decide whether the state joins `FIT_STATES` in `src/lotline/validation/v5.py`,
  `v5_stpaul.py` and `v9.py`.

---

## 6. Reference: what each model needs from a state

### ADU (`src/lotline/model/scenarios/adu.py`)

| | Input | Where from |
|---|---|---|
| **Required** | State config | step 2 |
| | `jurisdictions`, `eligible_parcels` (theme `adu`), `acs_geo_year` (rent B25064, value B25077, homes by type B25024), `market_geo_year` (CPI) | step 6 |
| **Used if present** | Coded local ADU rules: each place's rule type and how long it has been in force | step 4 |
| | Parcels: real eligible-lot counts; measured coverage of zone-limited rules | step 8 |
| | Permits that flag ADUs: the place's own recent rate becomes its no-reform rate, with drift (D-091, D-093) | step 9 |
| | `adu_flag_undercount` row for the source | step 9 |
| **Fallback** | No rule row: borrowed from coded places in the same size band (≥ 5), else the state. A state outside `REFORM_STATES` reads the five fitted states' saved priors | `rule_priors`, `config/params/adu_rule_priors.csv` |
| | Blank rule field: the state's share of restrictive values (≥ 5 known), else pooled, else 0.5. A new state reads the pooled counts from `config/params/adu_field_counts.csv` | `field_probabilities` |
| | No parcels: ACS one-unit detached homes, scaled by D-056 if the whole state is on the ACS | `eligible_proxy.py` |
| | No ADU-flagging permits: the hazard from the fitted model (pro forma × θ × place type) | |
| | State not in the fit: a random state multiplier from the fitted states' spread | D-043, D-044 |
| | Place type (core city, suburb, town): national data only (ACS, CBSA) | D-088 |

### Missing middle (`src/lotline/model/scenarios/mm.py`)

The scenario applies the hazard already fitted in `config/params/mm_hazard.yaml` (fitted on MN, NC, OH, TX and
OR). It reads no permits.

| | Input | Where from |
|---|---|---|
| **Required** | `jurisdictions`, `eligible_parcels` (theme `missing_middle`), `acs_geo_year` (rent, value, households), `market_geo_year` (CPI, construction-input prices, mortgage rate) | step 6 |
| **Used if present** | Middle-housing rule rows: the dose per place | step 4 |
| | Parcels: share of eligible lots with a house on them, zone coverage, single-family-only zoning | step 8 |
| **Fallback** | No rule row: dose drawn from coded places in the same size band (≥ 5), else the state | `mm.yaml` |
| | Nothing in a new state coded: dose drawn from the five fitted states' coded places by size band. This needs their `jurisdictions` tables in your data folder (section 3) | `borrowed_pool` |
| | Blank `by_right` or `unit_cap`: the share pooled over the five fitted states | `mm_rates.blank_shares` |
| | No parcels: ACS one-unit detached homes, house share 1, no D-056 scaling | `build/eligible.py` |
| | Missing rent: the state median price-to-cost ratio | |
| | Pro forma costs, cap rate, margins: national values only (`config/params/proforma.yaml`) | |

### Fees (`src/lotline/model/scenarios/fees.py`)

| | Input | Where from |
|---|---|---|
| **Required** | `jurisdictions`, `acs_geo_year` (home value), `market_geo_year` (CPI), the BPS baseline | step 6 |
| | At least one fee for each place, coded or filled from a prior. The run stops if a place has none | step 5 |
| **Used if present** | `config/fees/xx.csv` | step 5 |
| | Parcels with ≥ 20 feasible lots: the pro forma feasibility route instead of the elasticity route | step 8 |
| **Fallback** | Missing water and sewer or permit fee: filled. Missing impact, planning or other: zero. No rows: the state median (≥ 5 places), else pooled | `fee_levels.py`, D-065 |
| | Pass-through (λ 0.5) and elasticity (ε 0.3, lognormal): national | `config/params/fees.yaml` |

---

## 7. Reference: state lists written into the code

| Where | What it is | Change it when |
|---|---|---|
| `src/lotline/model/scenarios/adu_rule_inputs.py` `REFORM_STATES` | States whose rules feed shared priors | Only when pooling (step 14) |
| `config/params/adu_rule_priors.csv`, `adu_field_counts.csv` | The priors a new state borrows | Rewritten by the `adu_rule_priors` step when pooling |
| `tests/core/test_ordinance_records.py` ≈ line 209 | States whose fee CSVs are validated | When you add a fee file |
| `src/lotline/calibrate/mm/panel.py` `STATES` | D-024 missing-middle panel | Only when refitting |
| `src/lotline/calibrate/adu/adu_fit_set.py` `STATES` | ADU fit set | Only when pooling (step 14) |
| `config/params/adu_state_effect.yaml` | `adu_state_effect_fitted__XX` | Generated when pooling |
| `src/lotline/calibrate/mm/mm_fitsets.py` `STATES`, `SPREAD_STATES` | Missing-middle fit sets | Only when pooling (step 14) |
| `src/lotline/validation/v5.py`, `v5_stpaul.py`, `v9.py` `FIT_STATES` | Validation fit sets | Only if the state joins a fit |
| `config/params/housing_need.yaml` `*_xx` keys | Housing-need context | Optional |
| Scripts in `scripts/dev/` and `scripts/archive/` with their own `STATES` tuples | Research and page scripts | Only if you rerun that script |

These are not hard-coded, so there is nothing to change in them: the CLI, the BPS adapter (it reads region
and FIPS from the config), the app build and the map (`src/lotline/app/us_tiles.yaml` lists every state), the
dashboard and `compliance_check.py`.

---

## 8. Reference: what a state with no reform history borrows

Most states have passed no ADU or middle-housing reform, so they have no uptake history of their own. Lotline
does not need one. The rule is the same for every such state. **The uptake parameters come from the reformed
states the model was fitted on, adjusted to the new state's own market, and the range widens by how much
states differ from each other.**

| What | Borrowed from | Adjusted to the new state by | Extra width for a new state |
|---|---|---|---|
| ADU uptake rate θ | The fit on the reformed states (`config/params/hazard.yaml`) | The state's own rents, home values and mortgage rates (`model/hazard.py`, D-043) | A state multiplier exp(τz) drawn per draw, τ from its fitted profile (D-044, `config/params/adu_state_effect.yaml`), plus the extrapolation widening for places outside the fitted range (D-030) |
| ADU rule probabilities for uncoded places | The coded places of the five fitted states, saved in `config/params/adu_rule_priors.csv` and `adu_field_counts.csv` (section 3) | The place's size band | None beyond the prior's own spread |
| Missing-middle dose and blank shares | The same states' coded places, pooled at run time (`borrowed_pool`) | Size band | None beyond the prior's own spread |
| Fee levels for places with no fee file | The coded places of every state, pooled (`model/fee_levels.py`, below 5 own places) | None | The pooled prior's spread |
| Eligible lots with no parcels | The ACS count of one-unit detached homes | The D-056 scaling factor | The factor's log-sd |

A borrowed parameter never changes for the states it came from. The new state feeds nothing back until it is
pooled (step 14).

**Is this allowed?** The Rules and Handbook (read 2026-11-17) do not ask for causal identification. Neither
page uses the words "causal", "identification" or "counterfactual". The Handbook calls the challenge
"methodology-agnostic" and accepts assumptions when they are "clearly described and justified". Under Policy
Insight (§8), the Rules judge work applied to "states with less complete data" more favorably. A borrowed
parameter is acceptable when it is written down, sourced and carried with its range, which is what the table
above and `config/params/` do.

**What a borrowed parameter cannot say.** It assumes the new state's builders and owners respond to a reform
the way owners did in the fitted states, once rents and prices are accounted for. Its range covers how much
the fitted states differed from each other. It cannot cover a way the new state differs from all of them. The
bundle's `overlap_flag` says when a place sits outside the fitted range, and step 11 asks you to report it.

## 9. Adding a scenario (a new reform)

A new reform, such as parking, is **one new module** in `src/lotline/model/scenarios/` plus its parameters in
`config/params/`. You do not edit `results.py`, `schemas.py` or the bundle code. The module is found the same
way a state's data sources are (the scenario contract in `scenarios/__init__.py`).

The module defines:

| Name | What it is |
|---|---|
| `NAME` | the reform's id, lower case, for example `"parking"` |
| `LABELS` | `{"title": ..., "definition": ..., "handbook": ...}`: a plain-language title, a one-line definition and the Handbook text it follows (None if none) |
| `VARIANTS` | the runs it adds, `{bundle name: variant}`; most reforms have one, for example `{"parking": "handbook"}` |
| `run(inputs, variant)` | returns a `ScenarioRun`: per draw, the funnel's first stage by data tier, θ, the pencil-out and net-new shares, the added homes by completion class, and each year's share of the five years |
| `ORDER` (optional) | where it sits in the bundle; new reforms go after the built-in ones (90) so their draws stay the same |
| `TABLES`, `extra_tables(run)` (optional) | extra bundle parts it fills, such as the fee section's `fee_types` |

`inputs` carries the state, the data store, the origin year, the number of draws and the state's place table
(`inputs.places`). `lotline results --state XX` then runs the new reform with the others. It gets its own rows
in `results_draws`, `results_funnel`, `results_totals` and `results_need`, and a row in `meta.scenarios` with
its labels.

The test `tests/model/test_scenario_contract.py` proves this with a toy reform
(`tests/fixtures/scenarios/toy.py`, one home per 100 eligible lots). Registered with nothing else edited, the
toy reform shows up in the bundle, and the built-in reforms' draws do not change. Every parameter a new
reform reads still needs a cited source in `config/params/`, and each equation needs a hand-worked test
(`CLAUDE.md`).
