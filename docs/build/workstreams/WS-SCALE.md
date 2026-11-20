# WS-SCALE · One settings file per state, one input dataset, simple geography (Priority 2)

**Start:** after WS-NC-GUTCHECK's root-cause finding (task 3), so the fix isn't fighting a refactor (that
finding is on `main`: #352). **Branch:** `ws/scale` from `origin/main`.

**Owns:**
- This is a **shared-contract change**. Open a `contract-change` issue for WS-CORE first and agree the schema
  there.
- Then:
  - `config/states/*.yaml` schema;
  - `src/lotline/config/`, `src/lotline/geo.py`;
  - `src/lotline/build/` (new `geography.py`, `place_inputs.py`);
  - `src/lotline/adapters/` (shared resolver, rule docs);
  - `config/crosswalks/` formats;
  - `docs/adding_a_state.md`;
  - `tests/config/`, `tests/build/`.
- **Model code is not this workstream's.** `scenarios/adu.py` and `scenarios/mm.py` each have one owning
  session (ADU: "ADU statewide prediction methodology"; MM: "Missing Middle Analysis refresh").
  - WS-SCALE writes the shared input table and its tests.
  - Each model's owner switches that model to read it. Hand over; never edit both sides at once.

**Source:**
- `docs/research/office-hours-2026-11-09-greg-miller-notes.md`, action items 8–11;
- Ben, 2026-11-17: "one consolidated dataset feed all 3 models, making the process of tagging and identifying
  regions as simple as possible, and keeping the schema and structure as straightforward as possible";
- HANDOFF decisions 2026-10-28 (general-purpose transfer) and 2026-11-06 (50-state gate, D-053).

## The problem
Replicability & Scalability is 25%. A reviewer worried that parts of the work are too bespoke to each state (for
example, the Austin HOME fix). A state should be able to bring its own data, including better private data, by
editing one file. The model should still run, with wider ranges, when parcel, permit or zoning data is missing.

An audit on 2026-11-17 (§ Audit) found the pipeline is less tidy than its nine canonical tables suggest:
- **No shared input table.** Each model builds its own place frame from the canonical tables, with copied
  helpers.
- **The models disagree on the same quantities**, in ways that change results.
- **Seven ways to tag a record with its jurisdiction.**
- **20 crosswalk formats** across 73 files.
- **A new state can't run** without code edits.

## Target
- **One file per state** (`config/states/<st>.yaml`) controls:
  - which adapter feeds each input (parcels, zoning rules, permits, prices/rents, costs, fees, housing need)
    and the fallback for each;
  - state-specific adapter rules;
  - parameter overrides with sources.
  
  The code holds no state names or state-specific branches.
- **One geography table per state** (`geography`): one row per jurisdiction with every tag the models use,
  built once at fetch time. It comes with two long side tables, county shares and aliases (§ Design).
- **One input table per state** (`place_inputs`), keyed (state, geoid, year), feeding all three models and the
  baseline:
  - every shared quantity is computed once, by one function, with one rule for missing values;
  - model-specific and parameter-dependent quantities stay in the models.
- **Each calculation is its own module** with one entry point (e.g. eligible, pencil, uptake, completion,
  aggregate). The run order is declared, not hidden.
- **A data-tier ladder per input**: full local data → partial → national proxy (ACS/BPS) → borrowed parameter
  from reformed states. Each step down widens the range by a documented, tested amount.
- **A small schema.** New tables replace recomputation; they do not add a parallel set. Any column no code reads
  is dropped. Versions are logged in `schemas.py` as now.

## Audit (2026-11-17, read-only, `main` at `770c8d07`)

### A. Each model builds its own inputs

| Quantity | ADU (`adu.places_from_store`) | MM (`mm.places_from_store`) | Fees (`scripts/dev/fee_dev_run.py`) | Baseline (`panels.load`) |
|---|---|---|---|---|
| Places in the run | Places with ADU-eligible parcels; places with no ACS rent or value **dropped** (`results.py:520`) | Places with MM-eligible parcels; a place with no rent **kept**, its share of lots that pencil out filled with the state median (`mm.py:303`) | Every BPS geoid (D-076); missing home value **filled and flagged** | BPS geoids |
| Parcel roll used | Nearest roll to origin (inline, `adu.py:1479`) | `_nearest`, a copy | — | `carry_forward` (forward only) |
| Overlap removal (D-020) | `non_overlapping` | calls `adu.non_overlapping` + `adu._county_shares` | none | none |
| D-056 ACS scaling (tier 3) | applied | **not applied**, with no decision recorded | — | — |
| Parcel stats vintage | latest roll, **no origin cap** (`_sf_parcels`) | latest roll, **no origin cap** (`house_shares`) | ≤ origin + 1 (`parcel_inputs`) | — |
| ACS geo key, rent, value | `acs_values` | copies the key; calls `adu.acs_values` | copies the key twice; calls `adu.acs_values` | — |
| Size band, place type | `apply_priors`; `adu_types` | `adu.size_band` | — | — |

- The scenario totals and the baseline therefore **do not cover the same places**.
- Fees are not in `lotline results` at all (`ENGINE_SCENARIOS`, `results.py:50`).
- `DataStore.read` has no cache. One `lotline results` run reads `jurisdictions` from disk about 19 times and
  the reform CSVs 10 times.

### B. Geography is tagged seven ways
- **Hard-coded constant:** 20 adapters (a city's own file). This is fine and stays.
- **Constant plus a local flag:** 1 (San Antonio ETJ).
- **TIGER point-in-polygon, else the county:** 9 (`geo.place_or_township`).
  - The "known GEOID, else county" step is written five times: `metc_parcels.py:317`,
    `onemap_parcels.py:351`, `stratmap_parcels.py:298`, `oh_parcels.py:794`, `rlis_parcels.py:214`.
  - The loader for the jurisdictions table is written several more times.
- **Own city polygon with annexation dates:** 1 (Durham).
- **Source field plus a name lookup:** 3. Written three ways: metc `ctu_lookup`, rlis `city_lookup`, the
  mwvcog dicts.
- **Crosswalk CSV:** 3, each with its own header (Wake, TCAD, Mecklenburg).
- **Join to another source's parcels:** 2 (Franklin, Montgomery).

Tags computed on every run and never stored:
- `acs_geo`: the prefix map is rebuilt in at least 8 places;
- the market geography chain;
- size band: county remainders have no `pop_2020` and fall into the smallest band through `fillna(0)`;
- place type: `place_types.py` and `adu_types.py` are near-duplicates;
- county shares for places that cross county lines: built from the Census API in five places.

Other problems:
- **Circular build.** `jurisdictions.local_geoids` reads the permit and parcel tables, and those adapters read
  `jurisdictions` to decide what is known. That is why the jurisdictions build has to be rerun by hand.
- **Two rules for a county remainder's homes.** `eligible.allocate_homes` uses shares; `units_table` in
  `place_types.py` and `adu_types.py` subtracts places from their primary county only.
- **Two permit sources for one place** (Met Council and Minneapolis) are settled only inside
  `observed_adu_counts`.
- **Unused pieces:** `or_metro_cities.csv` is read by nothing; schema kind `region` is never produced.

### C. Crosswalks
- 73 files with 20 distinct headers.
- 49 already share one format: `field,code,description,land_use_std,notes,source_url` (NC, read through the
  `nc_land_use_counties.csv` registry).
- The other 24 are:
  - MN ordered regex rules (6);
  - permit type → building type (4, each keyed differently);
  - jurisdiction maps (5, each with its own header);
  - one-off code lists (6);
  - registries (2);
  - the Charlotte UDO file (1).

### D. A new state can't run (`docs/adding_a_state.md` §3)
1. `REFORM_STATES` (`scenarios/adu.py:1308`) must list it, or ADU and MM raise a `KeyError`.
2. A state with no permit adapter crashes: `store.read(st, "permits")` returns None, and that None is used
   without a check at `adu.py` ≈1509 and `results.py` ≈571.
3. `tests/core/test_config.py:8` pins the five states.

Outside the adapters, `src/` has no `if state ==` branches. The state-specific code is these tuples, the fit
sets (`estimate_mm.STATES`, `FIT_STATES` in `validation/`) and hard-coded holdout GEOIDs in `estimate_mm.py`
and `mm_counts.py`.

## Design (draft for the `contract-change` issue)

**`geography`.** Extends `jurisdictions` (same key, same file, schema version bump), so there is still one
geography table.
- New stored columns:
  - `acs_geo`;
  - `market_geo` (county → cbsa → state_noncbsa → state);
  - `size_band`, with a `pop_2020` for county remainders from the decennial remainder count;
  - `place_type`, with `place_type_vintage`;
  - `is_holdout`;
  - `parcel_source`, moved here from the yaml's GEOID lists;
  - `permit_sources`, in precedence order.
- Built in one pass after the adapters, from their *raw* GEOIDs. Adapters no longer read `jurisdictions`, which
  breaks the circular build.
- Side tables, long form:
  - `place_county_share` (place, county, homes share), replacing every `geoparts.county_shares` call;
  - `place_township_share`.

**Aliases.** One `config/crosswalks/xx_aliases.csv` per state: `source,raw,geoid,notes,source_url`, mapping
a source's city name or code to a GEOID. It replaces:
- the Wake, Mecklenburg and TCAD jurisdiction CSVs;
- the mwvcog dicts and the Cary dict;
- the metc `ctu_lookup`, the rlis lookup, the Wilmington `DISTRICTS`;
- `or_metro_cities.csv`.

**One shared resolver** in `geo.py`: point → place, else township, else county; then alias; then keep only
known GEOIDs. Every row records a `how` value. It replaces the five `resolve*` copies. Adapters with one city
keep their constant.

**Two crosswalk formats.**
- Land use: the NC format, plus an optional `pattern` column for regex rules (covers MN and OR).
- Building type: `field,code,building_type_std,role,derived_units,notes,source_url`.

Registries move into the state yaml.

**`place_inputs`.** Built once per state at fetch time, from `geography` and the canonical tables.
- **Key:** (state, geoid, year), for every BPS geoid and every local-only place. A `models` flag says which
  models a place feeds and why it is out of the others.
- **Columns (and the function that fills each today):**
  - BPS units by size class, `imputed` (`panels.numerator`);
  - `eligible_parcels_adu` and `eligible_parcels_mm`, net of overlap, with `overlap_removed_*` (`_nearest` +
    `non_overlapping`, once);
  - `denominator_source`, `denominator_quality`, `data_tier`;
  - rent and home value in 2025 dollars, `acs_end_year`, `sf_detached_homes` (`acs_values`);
  - `cpi_u`, cost index, HPI;
  - `house_share` (`mm.house_shares`);
  - `new_home_value` (`fees.parcel_inputs`);
  - `observed_adu_per_year` (holdout-stopped);
  - `eligible_proxy`.
- **Not in it** (model-specific or parameter-dependent): ADU rule probabilities and priors, the MM dose,
  fee levels, lot-value arrays, baseline forecasts.
- **One missing-value rule per column**, written in the schema and the guide.

## Tasks
- [x] **0. Blockers (do first).** Done 2026-11-17: "borrow only" (Ben). The three in § Audit D. The `REFORM_STATES` fix is a method choice: put it to
      Ben in plain words (memory: raise decisions in chat). A state listed there feeds the rule priors that every
      other state's uncoded places borrow.
- [x] **1. Audit, finish.** Done 2026-11-17: `docs/build/ws-scale-audit.md`. Every place the code branches on a state, or a file in `adapters/` does more than
      reshape data. Start from § Audit and write the full list to the PR.
- [x] **2. Schema.** Issue #455; Ben agreed 2026-11-17, then chose the straight-line build (tags in
      `place_inputs`, `local_jurisdictions` in the state file). All 5 states checked by
      `tests/config/test_state_schema.py`.
  - A draft of the state settings schema, `geography`, the aliases format and `place_inputs`, in the
    `contract-change` issue.
  - Validate all 5 states against it (`tests/config/test_state_schema.py`).
- [x] **3. Geography.** #459 (resolver, 43.3M rows unchanged), #463 (list without adapter output), #467
      (aliases), tags in `place_inputs` (#465).
  - The shared resolver, with synthetic tests: point inside a place, in a township, outside both, on a
    border, and an alias hit.
  - The aliases files.
  - The geography build, with the side tables.
  - Move the five parcel adapters' `resolve*` onto the resolver, then the name-lookup adapters.
  - **Check:** every adapter's `jurisdiction_geoid` column is unchanged on cached raw data, row for row
    (`--offline`). Any difference is listed and explained.
- [ ] **4. `place_inputs`, behavior-preserving.** Built, registered, schema 1.16, checked (#461, #465, and
      the fetch-step PR); owners' switch-over PRs still to do.
  - Build the table and a `DataStore` read cache.
  - Hand each model's owner a switch-over PR that reads it.
  - **Check:** `lotline results --all` bundles are identical before and after (same seed). The fee dev run's
    output is identical too.
- [ ] **5. Fix the disagreements, one at a time** (§ Audit A), each as its own `analysis_plan.md` entry and Ben's
      call, with before/after bundles:
  - one place universe for scenarios and baseline;
  - D-056 scaling for MM in tier-3 states;
  - one parcel-vintage rule;
  - one missing-ACS rule.
- [ ] **6. Fees in the bundle.** Add `fees` to `ENGINE_SCENARIOS`, reading `place_inputs`. This is the fee
      model's owner's call.
- [x] **7. Crosswalks.** Done 2026-11-17 (all 18 loaders unchanged); registries stay CSVs; `or_metro_cities.csv`
      kept (a dev script reads it). Convert the 24 odd files to the two formats; delete `or_metro_cities.csv`. **Check:**
      every adapter's `land_use_std` and `building_type_std` columns are unchanged row for row.
- [ ] **8. Adapter rules as data.** Started 2026-11-17: `rules:` block and five rules (OH three, TX two), values
      unchanged; onemap tier cutoffs read from params. No ranges set yet (Ben). The rest of the audit list is open. Move state quirks into named, documented rules in the state file (`rules:`
      with id, what it does, assumption, sensitivity range, source). First case: TX `austin_home_adu_share`, the
      share of 2024+ duplex permits on single-family lots counted as ADUs, with low and high values.
- [ ] **9. Missing-input matrix.** For each of parcels, zoning and permits missing, run NC with that input
      dropped to its fallback. Record how far the median moves and how much the range widens, as a plain table
      in `docs/adding_a_state.md` §2.
- [ ] **10. Borrowed parameters.** Document the rule for states with no reform history: take the uptake
      parameters from reformed states, with the D-043 transport. Check the Rules/Handbook on whether causal
      identification is expected; quote it.
- [x] **11. Bring-your-own-state guide.** Short path added 2026-11-17, generated from the steps file (task 13);
      kept current with each task. `docs/adding_a_state.md` exists (written 2026-11-17, before this
      work). Keep it current as each task lands, and add a one-page "short path" at its top: copy a template
      state file, point to your data, run one command, read the confidence flag.
- [ ] **12. Proof.** Onboard the unseen state (WI, V8) using only a new state file, aliases and adapter, with no
      engine edits. If an engine edit is needed, the abstraction is wrong; fix the abstraction, not WI.
- [ ] **13. Onboarding as data, for the app** (added 2026-11-17, Ben: "wire it up into the app so a user can
      follow the step by step instructions either by themselves, through built in functions to grab data, or to
      launch agent swarms"). Steps file, function interface and `lotline onboard` built; app UI not started (see
      § Task 13 design).

## Task 13 design: onboarding steps as data

**One source.** `config/onboarding/steps.yaml` lists the steps of `docs/adding_a_state.md`, in order. Each step
has:
- `id`, a plain-language `title`, `time`;
- `level`: the data level it belongs to (section 2 of the guide), or null for every level;
- `inputs`, `outputs`;
- `modes`: any of `manual`, `built_in`, `agent`;
- `commands` (built-in steps; `XX` is replaced by the state code);
- `check`: a named function that says whether the step is done;
- `done_when`: the same in plain words;
- `agent`: the brief, its owner and a note (agent steps).

**The guide renders from it.** `tests/core/test_onboarding.py` fails if:
- a guide step heading does not start with the step's title, in order;
- the guide's two generated blocks (the short path at the top, the step table in section 5) differ from
  `uv run python -m lotline.onboarding`.

The guide's prose stays hand-written; titles, order, short path, times and checks cannot drift.

**Three modes per step.**
- *Manual:* the guide section with the same number.
- *Built-in:* the app runs `onboarding.commands(step, state)` (lotline fetch for national sources,
  validate, results, provenance). Nothing in `onboarding` runs a command itself, so the app decides how
  to run and show it.
- *Agent:* the app's rule agents, a service the user switches on (Ben 2026-11-17,
  `docs/build/rule-agents/PRINCIPLES.md` on `ws/rule-agents-core`).
  - They propose a table: `reforms` rows for the `rules` step, `fees` rows for the `fees` step. The table
    uses the existing CSV header, keyed by GEOID, with a citation for every value.
  - The user reviews it and imports it (`onboarding.import_action`: the schema, the target file, the
    check). The imported file passes the same check as a hand-made one; the reforms check validates the
    schema.
  - The agents never write config, never produce model rates, and never open outcome data for
    held-back places.
  - Only `rules` and `fees` are agent steps. Adapter writing (`parcels`, `permits`) is manual.

**Function interface for the app** (`src/lotline/onboarding.py`):
- `steps()`: the validated steps;
- `commands(step, state)`: argument lists;
- `import_action(step, state)`: the review-and-import action of an agent step;
- `check(step, state, store)`: a `Status(done, detail)`. It looks at config files and which processed tables
  exist. It downloads nothing and reads no holdout outcomes;
- `plan(state, store)`: the whole checklist for one state as JSON-ready dicts;
- `config_problems(state)`: what is wrong with a state file;
- `lotline onboard --state XX [--json]`: the same plan on the command line.

**Stops here.** The app UI belongs to the "UI/UX Workflow" session; it reads `plan()` (or
`lotline onboard --json`). Running commands from the app, and launching agents from a step, are that
session's and the swarm session's to build.

## Not in scope
- The ADU/Missing-Middle substitution model stays as is (reviewer: not worth the complexity for scoring).
- Oregon's role (calibration source vs test state) is a Ben decision; ask, don't assume.
- Rewriting the 20 single-city adapters: a constant GEOID is already the simplest tagging.
- Any refit. Tasks 3, 4 and 7 must not move a result. Task 5 moves results only through approved entries.

## Order and risk
- The submission deadline is Dec 16. Tasks 0, 3 and 4 give the most simplicity for the least risk, because
  each has a zero-difference check.
- Do 5 and 6 only with time left before the final runs.
- If time is short, ship 0, 3 and 4. Leave 7–8 as written plans in the guide.

## Done when
- All 5 states plus WI run from their state files alone, with no `if state ==` in `src/`.
- All three models and the baseline read `place_inputs`.
- Geography is resolved in one place.
- Crosswalks use two formats.
- The missing-input table exists.
- Tests and compliance pass.
- Logbook fragment written; HANDOFF decision proposed in the PR description.
