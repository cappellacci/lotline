# Adding a new state to Lotline: a step-by-step guide

*Written 2026-11-17 against `main` at `770c8d07`. Every file path, setting and command below was checked in the
code at that commit. The steps were not run end to end on a new state: that is the V8 unseen-state test
(`docs/research/lotline-validation-plan.md`). Where the code does not yet do what this guide needs, the step
says so under **Known blockers** (section 3).*

This guide is for a person who has a copy of the repository and wants Lotline's ADU, missing-middle and fee
results for a state it does not cover yet. You can stop after any level in section 2. Each level after the
first narrows the ranges.

Throughout, `XX` is the new state's two-letter code in capitals (e.g. `WI`) and `xx` is the same code in lower
case (file names use lower case).

---

## The short path (one page)

For a first result with national data only (level 0 in section 2), with no local data and no code:

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
   uv run python scripts/dev/fee_dev_run.py --state XX --statewide --out reports/xx/fees-statewide.csv
   ```
5. **Read the results before you show them** (step 11, an hour).
<!-- short-path:end -->

Step 2 means: copy `config/states/oh.yaml` to `config/states/xx.yaml` and change the state code, name, FIPS
code, Census region and ZIP prefixes (section 5, step 2). Then read the confidence flag in the bundle:
`meta.data_tier`, `meta.overlap_flag` and `meta.caveats` (step 11). With national data only, the ADU ranges are
wide and the bundle says "National data only"; the levels in section 2 say what each kind of local data adds.

`uv run lotline onboard --state XX` prints this checklist for your state, marks what is already done, and
shows the next commands. `--json` gives the same plan to the app.

---

## 1. What you will end up with

- `config/states/xx.yaml`: the state's settings.
- `config/reforms/xx.csv`: the state's ADU and missing-middle rules, one row per rule per place.
- `config/fees/xx.csv`: the state's development fees, one row per fee per place.
- Optionally, adapters in `src/lotline/adapters/states/xx/` for local parcel and permit data, with tests in
  `tests/states/xx/` and land-use crosswalks in `config/crosswalks/xx_*.csv`.
- A results bundle at `reports/results/xx/bundle.json` (ADU and missing middle), a fee run, and the state on
  the app's map (`reports/app/index.html`).
- A readiness report, `docs/build/xx-readiness.md`, and an `XX` section in `docs/data_availability.md`.

---

## 2. Decide how much data you will bring

Lotline runs at four levels of local effort. National data (Census permits, the ACS, FHFA prices, FRED rates
and costs) covers every state, so level 0 needs no local data at all.

| Level | You add | Data tier the app shows | What we know about accuracy |
|---|---|---|---|
| **0. National only** | The state config. A reform file with the state's own ADU and middle-housing laws, if it has any | Tier 3, "National data only" | **ADU: not reliable on its own.** In the leave-one-state-out test (D-075, scored under D-088 on 2026-11-15), national data alone was useful in Minnesota only; Oregon's median came out 8 times too low |
| **1. Coded local rules** *(recommended minimum)* | Level 0, plus the local ADU rules of the state's **20 largest places** (by eligible lots), the local middle-housing rules you can find, and fees for **at least 5 places** | Tier 3 | **ADU: passes.** The same test passed in 4 of the 4 states that could be scored (observed total inside the P10–P90 range and within ×2 of the median). The ranges are wide (P90 ÷ P10 from ×4 to ×71) |
| **2. One measured city** | Level 1, plus record-level permits that flag ADUs for at least one large city | Tier 3 unless you also add parcels | ADU: also passes, and anchors the state's level to its own counts |
| **3. Local parcels** | Parcel rolls with land use (and ideally year built) | Tier 2 or 1 for the places they cover | Replaces the ACS estimate of eligible lots with a real count, and lets zone-limited rules be measured |

**Thresholds the code applies:**

| Rule | Value | Where it is set |
|---|---|---|
| A place's parcels count as tier 2 | ≥ 90% of its parcels have a known land use | `config/params/tiers.yaml` |
| … and tier 1 | also ≥ 80% of built parcels have a year built | `config/params/tiers.yaml` |
| A state uses its own ADU rule prior | ≥ 5 coded places (per size band, else statewide) | `adu_rule_min_coded`, `config/params/adu.yaml` |
| A state uses its own middle-housing dose prior | ≥ 5 coded places (per size band, else statewide) | `mm_rule_min_coded`, `config/params/mm.yaml` |
| A state uses its own fee prior | ≥ 5 coded places | `MIN_PLACES`, `src/lotline/model/fee_levels.py` |
| Below those minimums | Priors are pooled from the other states' coded places | same files |
| Census permit totals reconcile | place sum within 1% of the state total | `lotline validate` (V0) |

**What is not known yet.** The missing-middle model has no data-tier result: the D-092 accuracy run skipped
that test because too few permit sources had years after a reform (`reports/mm-d092/run5-tests/README.md`).
The fee scenario has none either. Treat level 1 as the minimum for all three models until those tests exist.


**What each kind of local data is worth (task 9, North Carolina, 2026-11-17).** NC was run four times with
the same seed: as is, then with one input dropped to the fallback a state without it would get. Five-year net
homes statewide, change in the median against the full run, and the P10-P90 range as a multiple of the full
run's range:

| Input dropped | Fallback | ADU median | ADU range | Middle housing median | Middle housing range | Fees |
|---|---|---|---|---|---|---|
| Parcels | ACS count of one-unit homes, scaled (D-056); tier 3 | −4% | ×0.97 | −18% | ×0.79 | +3%, ×1.03 |
| Zoning rules (`config/reforms/nc.csv`) | Rule priors borrowed from the other coded states | +251% | ×4.9 | +51% | ×1.5 | unchanged |
| Permits | No observed ADU floor | +4% | ×1.01 | unchanged | unchanged | unchanged |

How to read it:
- **Coded local rules matter most.** Without them, NC's places take the other states' rule mix. The ADU
  median rises 3.5-fold and its range widens almost 5-fold, which suggests NC's own ordinances allow ADUs
  less often than the borrowed mix (not checked rule by rule). This is why level 1 (coded rules) is the
  recommended minimum.
- **Parcels move the middle-housing median by about a fifth.** They do not widen the range: the ACS
  fallback gives a smaller eligible count, so the range narrows with it. The D-056 factor's own uncertainty
  is in the fallback, but here it is smaller than the change in the count.
- **Permits barely move the scenario totals.** Their job is the observed ADU counts and the tests, not the
  forecast.
- **One state, one seed, 1,000 draws.** The numbers are NC's. A state whose own rules are looser than
  the borrowed mix would move the other way.
- **Rerun:** `uv run python scripts/dev/missing_input_matrix.py --state NC --out <folder>` (offline;
  writes nothing to the data directory; holdouts stay hidden).

---

## 3. Known blockers (cleared by WS-SCALE task 0, 2026-11-17)

Three things used to stop `lotline results` for a new state. They are fixed; this section says what changed so
you know what the code now does for you. Tested in `tests/model/test_new_state_runs.py`, which builds a full
bundle for a synthetic national-data-only state with no permits and no reforms file.

1. **You no longer add the state to `REFORM_STATES`.** A state not in that list (`scenarios/adu.py`) is added
   to the run on the fly (`adu.reforms_with`). It **borrows** the listed states' rule priors, field
   probabilities and blank shares, and **feeds nothing back**, so no other state's results move ("borrow
   only", Ben 2026-11-17).
   - `config/reforms/xx.csv` is optional: without it the state has no coded rules, and every place takes the
     borrowed priors. With it, its rules apply to its own places.
   - Putting a state *into* `REFORM_STATES` is now part of pooling it into the calibration (step 14), a
     method decision, because then its coded rules shift every state's priors.
2. **A state with no permit table runs.** `adu.observed_adu_counts` treats a missing permit table as empty: no
   observed ADU floor, and no `adu_permits` rows in the bundle's `observed` part.
3. **No test pins the list of states.** `tests/core/test_config.py` checks that the five states are present,
   not that they are the only ones.

Also needed, but not a code change: `rule_inputs` reads the built `jurisdictions` table of **every** state in
`REFORM_STATES`, since those feed the priors your state borrows. Your data directory must hold those states'
tables too. Run
`uv run lotline fetch --source jurisdictions` once with no `--state` to build them all.

---

## 4. Before you start

1. **Set up the repository** as the README's Setup section says (`uv sync`).
2. **Copy `.env.example` to `.env`** and fill in:
   - `CENSUS_API_KEY` (free from the Census Bureau; the ACS, decennial and County Business Patterns adapters
     need it);
   - `LOTLINE_DATA_DIR` (default `~/lotline-data`, outside the repository).
   - Optionally `SOCRATA_APP_TOKEN`, if a city portal you use runs on Socrata.
3. **Work on a branch in its own worktree** (CLAUDE.md, "Working in parallel"), e.g. `ws/xx`.
4. **Decide now whether the state will be a blind test.** If you want to predict the state before seeing its
   outcomes (as Oregon was in V9), the holdout must be in the config *before the first fetch*. Only Ben adds or
   releases holdouts. Never pass `--unblind`.
5. **Watch for state codes that are Python keywords.** Oregon's package is `adapters/states/or/`, and `or` is a
   Python keyword. Indiana (`in`) has the same problem. The registry imports such a package by name and that
   works, but tests must import its modules with `importlib`. See `tests/states/or/test_package.py`.

---

## 5. The steps

Every step at a glance. **Ways to do it:** *manual* is this guide; *built-in* means `lotline onboard` and the
app show the commands to run; *agent* means a coding agent can do it from a brief. **Done when** names the check
`lotline onboard` runs.

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
| 13. Run the checks and open the pull request | any | 15 minutes | manual, built-in | tests and compliance_check.py pass (a person decides) |
| 14. Pool the state into the calibration (optional; Ben's call) | any | a method decision | manual | Ben approves an analysis_plan.md entry (a person decides) |
<!-- steps-table:end -->

### Step 1. Look at what the state publishes (about half a day)

Fill in a short assessment before writing any code. `docs/build/or-assessment.md` is the model. Answer:

- Does the state have a **statewide ADU or middle-housing law**? Its effective dates, which places it covers
  (often by population), and whether it reaches small towns.
- **Local rules**: which of the 20 largest places have their own ADU or middle-housing ordinances, and where
  the official code text is.
- **Fees**: where the six largest places publish their fee schedules (water and sewer connection, impact,
  building permit and plan review).
- **Permits**: which cities publish record-level permits, and whether any flag ADUs.
- **Parcels**: whether there is a statewide or county parcel layer with land use and year built.
- **Licenses**: for every candidate source, its published terms. Only use sources whose terms allow use in an
  Apache-2.0 public pipeline (the National Zoning Atlas does not, for example).

Search `docs/research/lotline-data-catalog.csv` first: some states were scouted early on.

### Step 2. Write the state config (15 minutes)

Create `config/states/xx.yaml`. Copy `config/states/oh.yaml` and change the values. The loader rejects any key
it does not know.

```yaml
state: XX                 # required, two capital letters, must match the file name
name: Statename           # required
fips: "55"                # required, two-digit state FIPS code, in quotes
bps_region: Midwest Region  # required: Northeast Region, Midwest Region, South Region or West Region
township_permits: false   # true where townships issue building permits (MN, OH, WI, MI, PA...)
zip3_ranges: [[530, 549]] # needed: the state's USPS 3-digit ZIP prefixes, inclusive; FHFA's ZIP index fails without it
holdouts: []              # Ben only; see section 4
sources: []               # one entry per local adapter you add (steps 9-10)
```

Optional keys, added later when they apply:

- `adu_state_law_rows_complete: true`: only if you generate a state-law row for **every** place the state's ADU
  law covers (as Oregon does, D-068). A place without a row is then read as outside the law.
- `parcel_sources`: needed only when two parcel sources cover the same jurisdiction.
- `local_jurisdictions`: governments the Census permit survey has no row for (it files their permits under
  a county) but your own permit or parcel data reports separately, as `"GEOID": "Name"`. Minnesota lists 23
  townships, North Carolina 196 towns. The jurisdictions list is the survey's places, these, and the
  holdouts; it never reads your data, so it needs no rebuild when you add a source. After adding a permit
  or parcel source, run `uv run lotline unlisted --state XX`: it prints every GEOID your data uses that the
  list lacks. Add the real governments among them here.
- `data_tiers`: to override a place's tier by hand.

Saving this file registers the state everywhere the code calls `all_states()`, including the app.

### Step 3. Check the state file (1 minute)

```bash
uv run lotline onboard --state XX
```

Step 3 of its list checks the state file against the rest of the repository:
- every GEOID in it belongs to the state;
- the files it names exist;
- `parcel_sources` names real sources.

The same checks run in `tests/config/test_state_schema.py`. The blockers that used to sit here are cleared
(section 3).

### Step 4. Code the state's ADU and middle-housing rules (1 to 3 days for 20 places)

**File:** `config/reforms/xx.csv`. Copy the header line exactly from `config/reforms/or.csv`:

```
reform_id,state,jurisdiction_geoid,theme,component,status,announced_date,adoption_date,effective_date,end_date,supersedes,by_right,owner_occ,unit_cap,far_cap,max_stories,min_lot_sqft,adu_max_sqft,adu_detached_allowed,adus_per_lot,lot_split,parking,parking_min_per_unit,fee_change_usd,dollar_year,coverage,coverage_zones,source_url,source_section,source_quote,verified_by,verified_date,coder,coder_2,coder_agreement,coding_notes
```

**Which places, in order:**

1. **The state law**, if there is one.
   - ADU: a row whose `jurisdiction_geoid` is the 2-digit state FIPS applies to every place.
   - Middle housing: a 2-digit row is **not** applied to places. Write one row per covered place instead.
     When coverage depends on population (as Oregon's HB 2001 does), generate the rows with a script like
     `scripts/dev/or_state_reform_rows.py`. Mark generated rows `GENERATED` in `coding_notes`.
2. **Local rules for the 20 largest places by eligible lots.** This is what makes level 1 pass. After step 6 you
   can list the places with `eligible_parcels` from the data store. Until then, use 2020 population.
3. **Any other place that changed its rules** in the last ten years.

Record a place that does **not** allow ADUs too, with `adus_per_lot` = 0. Leaving it out means "unknown", and
the model then borrows a rule from similar places.

**How to fill the main columns:**

| Column | What to write |
|---|---|
| `jurisdiction_geoid` | 7-digit Census place GEOID, or 5-digit county GEOID for an unincorporated remainder, or 2-digit state FIPS for a statewide ADU law |
| `theme` | `adu` or `missing_middle` (also `parking` for a citywide parking change) |
| `status` | `in_force`, `suspended`, `repealed`, `opted_out` or `pending`. The models read `in_force` rows only |
| `adoption_date`, `effective_date` | ISO dates (YYYY-MM-DD). The model treats a rule as in force from the year it is in force on 1 July |
| `supersedes` | the `reform_id` of the earlier row this one replaces; blank fields are then filled from it |
| `by_right` | `True` if approved without a public hearing; `False` otherwise |
| `owner_occ` | `True` if the owner must live on the lot |
| `adu_detached_allowed` | `True` / `False` |
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

**How a rule becomes a model input:**

- **ADU.** The ADU model checks each rule against the Handbook test. A rule fails it if any of these hold:
  - it needs a hearing (`by_right` False);
  - it requires the owner to live on the lot;
  - it bans detached ADUs;
  - it caps ADUs below 600 sq ft;
  - it requires parking.
  
  Where several rules apply, the most permissive one wins (`scenarios/adu.py`, `current_rules`).
- **Missing middle.** The rule's "dose" is units grade × approval grade × coverage (`estimate_mm.py`).
  - Units grade: 2 per lot is 1/3, 3 is 2/3, 4 or more is 1.
  - Approval grade: by right is 1, otherwise 0.333.

Read rules from the official code, not memory, and have a second person check every dated row. That is the
standard every other state's rows meet.

**Check the file:** add `tests/states/xx/__init__.py` and `tests/states/xx/test_reforms.py`, copied from
`tests/states/oh/test_reforms.py`. That test reads the CSV as text, so a typo like "Ture" fails instead of
becoming blank. It checks every row against the `reforms` schema and lists the 20 largest places it expects to
see. Then run:

```bash
uv run pytest tests/states/xx -q
```

### Step 5. Code fees for at least 5 places (1 to 2 days)

**File:** `config/fees/xx.csv`. Follow `config/fees/README.md` and `docs/build/manual-fee-lookups.md`. In short:

1. Take the **largest places by 2020 population**, about six. Five is the minimum for the state to get its own
   fee prior. With fewer, every uncoded place takes the pooled median of all states.
2. Open each place's **official fee schedule**. For each of these, write one row per component and building
   type:
   - the water and sewer connection or capacity fee;
   - impact fees;
   - the building permit and plan review fees.
   
   Use building types `SFD`, `ADU`, `U2` and `U3_4` (also `OTHER` for a fee that applies to any type). Skip
   buildings of 5 or more units.
3. Copy the fee **exactly** into `amount_usd`. Convert it to one home in `amount_per_unit_usd`, and say how in
   `notes`.
   - For valuation-based fees, use the prototype house: 2,150 sq ft, valued at about $355,000.
4. **Fees that vary by area or tier:** put the median on one row and the range in
   `amount_per_unit_low_usd` / `amount_per_unit_high_usd`.
5. Duplex and fourplex water fees: one meter per unit is the central case. The master-meter case goes in the
   range (D-069).
6. **If you can't find a fee, leave the row out. Never write 0:** a 0 means the place charges nothing.
   - Leave `amount_per_unit_usd` blank for fees that don't apply to a typical infill home (rezoning,
     variances, per-acre charges).

**Required columns:**

- `state`, `jurisdiction_geoid`, `year`;
- `fee_component`: `water_sewer`, `impact`, `permit`, `planning` or `other`;
- `fee_type`: the schedule's own name for the fee;
- `building_type_std`;
- `basis`: `per_unit`, `per_sqft`, `per_lue`, `pct_of_value`, `flat` or `other`;
- `amount_usd`, `amount_per_unit_usd`, `dollar_year`;
- `source`: the schedule's URL.

Add `source_section`, `source_quote`, `verified_by` and `verified_date` when you can.

**Fallbacks the model applies:**

- A coded place missing its water/sewer or permit fee has that fee filled from the state's other places.
- A coded place missing impact, planning or other fees counts them as zero.
- A place with no rows takes the state's median, or the pooled median if the state has fewer than 5 places.

The Handbook's $50,000 is never used as a fallback.

**Check the file:** add `"XX"` to the `parametrize` list in `tests/core/test_ordinance_records.py`
(`test_committed_fee_tables_validate`, about line 208), then run:

```bash
uv run pytest tests/core/test_fees_config.py tests/core/test_ordinance_records.py -q
```

### Step 6. Fetch the national data (about an hour, mostly waiting)

```bash
uv run lotline fetch --state XX
```

This downloads into `LOTLINE_DATA_DIR`, records every file in `manifest.jsonl`, and builds:

- `acs_geo_year`: rent, home value, homes by type and households;
- `bps_place_year`: Census permits by building size, per place and township;
- `market_geo_year`: FHFA prices, FRED rates and costs, and the demand index;
- `jurisdictions`: every permit-issuing place, with its tier;
- `eligible_parcels`: eligible lots from the ACS (one-unit detached homes) where there are no parcels;
- `place_inputs` (last): one row per place and year with every input the models share (eligible lots for
  ADUs and middle housing, rent and value, observed ADUs, permits by size, place type, price index) and a
  `models` column saying which models read the place and, in `models_note`, why it is left out of the others.
  Open it to see exactly what the models will see for your state.

Then check the national data:

```bash
uv run lotline validate --state XX
```

This writes `reports/xx/V0-national.md`. It checks that the Census place permits add up to the state total
within 1%. Read it, and note any places Census imputed.

```bash
uv run lotline fetch --source jurisdictions
```

With no `--state`, this builds the other states' jurisdiction tables too, if your data directory lacks them
(section 3).

### Step 7. Run the models for the first time (a few minutes)

```bash
uv run lotline results --state XX
uv run python scripts/dev/fee_dev_run.py --state XX --statewide --out reports/xx/fees-statewide.csv
```

- **`lotline results`** runs the ADU and missing-middle scenarios. It writes `reports/results/xx/bundle.json`.
  - With national data only, it sets the role to `national_only`. It scales the ACS eligible-lot count by the
    D-056 factor, with that factor's uncertainty, and adds the caveat "National data only".
  - Each run draws 1,000 times from origin year 2025 (`config/params/aggregate.yaml`).
- **The fee scenario** is not in the bundle yet (the bundle lists it under `scenarios_pending`). The dev script
  prints five-year totals (P10, P50, P90 and the mean of added homes) for each size class, and `--out` writes
  them to the CSV.

If the results run stops with a `KeyError` naming another state, that state's `jurisdictions` table is missing
from your data directory (see the note at the end of section 3).

### Step 8. Add local parcels (optional, level 3; 1 to 3 days per source)

1. **Write an adapter**, `src/lotline/adapters/states/xx/<name>_parcels.py`, using
   `src/lotline/adapters/states/or/rlis_parcels.py` as the template. A module is picked up automatically if it
   defines these four names (`src/lotline/registry.py`):
   - `SOURCE`: a source id, unique across all sources;
   - `TABLE`: `"parcels"`;
   - `PROVENANCE`: title, landing URL, table, cleaning steps, limitations;
   - `load(state, store, *, refresh=False)`, which returns the canonical table.
   
   Existing adapters also set `ADAPTER` and `VERSION`; keep that convention. An adapter that reads another
   table from the store (most parcel adapters read the jurisdictions list through `geo.known_geoids`) sets
   `READS = ("jurisdictions",)`, so a plain `lotline fetch` builds that table first
   (`registry.fetch_order`). Add `src/lotline/adapters/states/xx/__init__.py`.
2. **Download through the IO layer** (`lotline.io`: `fetch`, `arcgis` or `socrata` into `store.raw(...)`) so
   the file lands in the manifest. For a file you can only download in a browser, register it:
   ```bash
   uv run lotline manifest register ~/lotline-data/manual/xx/file.zip --source <name>_parcels --url <page> --license "<terms as published>"
   ```
3. **Required parcel columns:**
   - `state`, `parcel_id`, `vintage`, `jurisdiction_geoid`;
   - `lot_sqft`;
   - `land_use_std`, `land_use_raw`;
   - `source`.
   
   Add `year_built`, `units` and `zoning_raw` when the source has them. **Never request owner names or
   addresses.** List those fields in a `PERSONAL` set and test that they are never requested, as the Ohio and
   North Carolina adapters do.
   **Tag each parcel with its jurisdiction** using `lotline.geo`, not your own lookup:
   - a source covering one city: set `jurisdiction_geoid` to that city's constant GEOID;
   - otherwise: `geo.place_or_township(lon, lat, state, store)` for the point, then `geo.resolve(steps,
     geo.known_geoids(state, store))`, where `steps` is your rule as an ordered list, e.g.
     `[("place", place), ("county_remainder", county_geoid, False)]`. The first step that gives a GEOID in the
     jurisdictions table wins (`False` keeps the value even if it is not in the table), and every row gets a
     `how` label saying which step placed it. `src/lotline/adapters/states/nc/onemap_parcels.py`
     (`resolve_jurisdictions`) is a three-line example.
   - a source that names its city or uses a code ("TC" for Cary): put each name or code in
     `config/crosswalks/xx_aliases.csv` (`source,field,raw,geoid,notes,source_url`) and read it with
     `geo.aliases("XX", "<source>", "<field>")`; use the result as a resolver step. `nc_aliases.csv` is the
     example.
4. **Map land uses** with a crosswalk, `config/crosswalks/xx_<source>_land_use.csv`.
   - Every source code maps to one of: `SF_DETACHED`, `SF_ATTACHED`, `DUPLEX`, `TRI_QUAD`, `MULTIFAMILY_5P`,
     `MOBILE_HOME`, `CONDO_UNIT`, `VACANT_RESIDENTIAL`, `MIXED_USE`, `COMMERCIAL`, `INDUSTRIAL`,
     `AGRICULTURAL`, `INSTITUTIONAL`, `OTHER` or `UNKNOWN`.
   - Use the land-use format, `field,code,description,land_use_std,notes,source_url`, and read it with
     `lotline.adapters.crosswalks.read(path, "land_use")`. The reader checks the header and that every
     `land_use_std` is in the list above. `config/crosswalks/oh_dte_luc.csv` is a simple example.
   - Labels that vary by county are matched with ordered rules instead of exact codes: leave `code` blank and
     add a `pattern` column (a regular expression; the first match wins), plus `county` if a rule holds in one
     county only (`mn_land_use.csv`, `or_rlis_land_use.csv`).
5. **Call** `holdout.apply(...)` on the rows before returning them, then `validate(df, TABLE)`.
6. **Add a `sources:` entry** in `config/states/xx.yaml` with name, URL, license, access, cadence and notes.
7. **Name your judgments.** A share, threshold, date or label your adapter applies to the data, beyond
   reshaping it (for example "a taxing district maps to a city when 95% of its parcels are in that city"),
   goes in the state file's `rules:` block, not in code:
   - give it `value`, `unit`, `what`, `assumption`, `source` and `used_by` (the modules that read it), plus
     `low` and `high` when you know a sensitivity range;
   - read it with `lotline.config.state_rule("XX", "<rule id>")`;
   - `config/states/oh.yaml` has three examples, `tx.yaml` two.

### Step 9. Add local permits (optional, level 2; 1 to 2 days per source)

Same pattern as step 8. Use `src/lotline/adapters/states/or/bend_permits.py` as the template and `"permits"` as
the table.

- **Required permit columns:**
  - `state`, `permit_id`, `jurisdiction_geoid`;
  - `issue_year`, `issue_date`, `date_precision`;
  - `building_type_std`, `type_confidence`;
  - `units_new`, `units_removed`, `units_confidence`;
  - `is_demolition`, `is_conversion`;
  - `source`.
- **Building types:** `SFD`, `ADU`, `TH`, `U2`, `U3_4`, `U5_6`, `U7P`, `DTQ`, `MF5`, `OTHER` or `UNKNOWN`.
  Never guess a finer type: set `type_confidence` to `inferred` or `unknown` instead.
- **Map permit types** with a building-type crosswalk,
  `field,code,description,building_type_std,role,derived_units,notes,source_url`
  (`config/crosswalks/nc_gso_occupancy.csv` is the example), read with
  `crosswalks.read(path, "building_type")`. `role` is what the permit does in your adapter's terms
  (dwelling, multi, demolition, ...); `derived_units` is the unit count to record when the source gives none.
- **ADUs:** mark them `building_type_std = ADU` (or fill `adu_type`). A permit that builds a house and an ADU
  together is split into two rows (D-041).
- **Hand-check the flag:** if ADUs come from reading descriptions, check 30 flagged and 30 unflagged permits
  by hand (D-074). The undercount factor for the source then goes in `adu_flag_undercount` in
  `config/params/adu.yaml`. Without a row, the factor is 1.

Once a source flags ADUs, the ADU model uses that city's own recent counts as its no-reform rate.

### Step 10. Rebuild the derived tables

The national build steps read whatever local tables exist when they run, so rebuild them after adding
sources, in this order:

```bash
uv run lotline unlisted --state XX
uv run lotline fetch --state XX --source jurisdictions
uv run lotline fetch --state XX --source eligible
uv run lotline fetch --state XX --source demand
uv run lotline fetch --state XX --source place_inputs
```

`unlisted` lists GEOIDs your new data uses that are not jurisdictions yet; add any real government to
`local_jurisdictions` (step 2) and rerun the adapter. `jurisdictions` then picks up each place's tier from its
parcels (the one thing it still reads from local data). `eligible` swaps the ACS estimate for the parcel count
where parcels exist. `place_inputs` goes last, since it reads every other table. Then rerun step 7.

When the state has local data but is not in any fit (the usual case), label it a transfer state:

```bash
uv run lotline results --state XX --role transfer
```

### Step 11. Read the results before you show them

Open `reports/results/xx/bundle.json`, or rebuild the page with `uv run python scripts/build_app.py`, and check:

- **`meta.overlap_flag`**: whether the state's places sit inside the range of places the model learned from.
  Outside means low confidence. Say so wherever you quote the number.
- **`meta.caveats` and `meta.data_tier`.**
- **The state effect.** A state outside the ADU fit gets a random state multiplier drawn from the spread of the
  fitted states (D-043, D-044). Its ADU ranges are wider for that reason; this is intended, not a bug.
- **Places with no rent or home value** in the ACS are dropped from the bundle. Count them.
- **The fee run's `fee_source` column:** how many places use their own fees and how many use a prior.

### Step 12. Write it up

1. **`docs/build/xx-readiness.md`**, in the shape of `docs/build/or-readiness.md`:
   - a coverage table for each input: jurisdictions, eligible lots, parcels, permits, ADU flags, rules, fees,
     market, demand, holdouts;
   - what is blind;
   - the remaining gaps and what would close each.
2. **An `XX` section in `docs/data_availability.md`**: for each data need, what exists, what Lotline uses, and
   why the rest is not used.
3. **Provenance:**
   ```bash
   uv run lotline provenance --write
   ```
   This regenerates `docs/data_provenance.md` from the manifest. It fails if any built table has no manifest
   entry.
4. **`docs/disclosures.md`**: add a row for any new host the adapters call.

### Step 13. Run the checks and open the pull request

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
test, never on downloaded data and never over the network. Each one checks:

- the output conforms to the schema (`assert_conforms(build(raw), "permits")`);
- the classification rules and the rows dropped;
- no personal fields are requested;
- `load()` keeps holdouts hidden.

Write a logbook fragment in `logbook.d/<date>-ws-xx.md`, open the PR, and propose any HANDOFF decision in its
description.

### Step 14. Pool the state into the calibration (optional; Ben's call)

Up to step 13, the new state *uses* the fitted models but does not change them, apart from the shared rule
priors (section 3). Adding its data to the fits is a separate method decision, made in an
`docs/analysis_plan.md` entry before any run, as Oregon's was (D-053 for ADUs, D-092 for missing middle). If the
state might later be a blind test, freeze its prediction first.

- **ADU:**
  1. Add its fit places and years to `scripts/dev/calibrate_adu.py` (`FOUR_STATE` / `OREGON_FIT`, about lines
     300–311, and `STATES`).
  2. Rerun with `--draw-terms` (regenerates `config/params/adu_anchor.yaml`).
  3. Rerun with `--state-effect-config` (regenerates `config/params/adu_state_effect.yaml`, adding
     `adu_state_effect_fitted__XX`).
  
  A place-year enters only with a coded rule in force and a source that flags ADUs.
- **Shared rule priors:** add the state to `REFORM_STATES` (`scenarios/adu.py`), so its coded rules feed the
  priors other states borrow. Record the before/after bundles.
- **Missing middle:**
  1. Add the state to `STATES` in `scripts/dev/calibrate_mm_d092.py`.
  2. Rerun it and `scripts/dev/mm_tests_d092.py` (marked "only with Ben's go-ahead").
  3. Update `config/params/mm_hazard.yaml`.
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
| **Fallback** | No rule row: borrowed from coded places in the same size band (≥ 5), else the state, else all states | `rule_priors` |
| | Blank rule field: the state's share of restrictive values (≥ 5 known), else pooled, else 0.5 | `field_probabilities` |
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
| **Fallback** | No rule row: dose drawn from coded places in the same size band (≥ 5), else the state. **If nothing in the state is coded, dose is 0 (the full Handbook gap)** | `mm.yaml` |
| | Blank `by_right` or `unit_cap`: the share pooled over all `REFORM_STATES` | `estimate_mm.blank_shares` |
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
| **Fallback** | Missing water/sewer or permit fee: filled. Missing impact, planning or other: zero. No rows: the state median (≥ 5 places), else pooled | `fee_levels.py`, D-065 |
| | Pass-through (λ 0.5) and elasticity (ε 0.3, lognormal): national | `config/params/fees.yaml` |

---

## 7. Reference: state lists written into the code

| Where | What it is | Change it when |
|---|---|---|
| `src/lotline/model/scenarios/adu.py` `REFORM_STATES` | States whose rules feed shared priors | Only when pooling (step 14) |
| `tests/core/test_ordinance_records.py` ≈ 208 | States whose fee CSVs are validated | When you add a fee file |
| `src/lotline/model/estimate_mm.py:47` `STATES` | D-024 missing-middle panel | Only when refitting |
| `scripts/dev/calibrate_adu.py` ≈ 300–311, 537 | ADU fit set | Only when pooling (step 14) |
| `config/params/adu_state_effect.yaml` | `adu_state_effect_fitted__XX` | Generated when pooling |
| `scripts/dev/calibrate_mm_d092.py:52` | Missing-middle fit set | Only when pooling |
| `src/lotline/validation/v5.py`, `v5_stpaul.py`, `v9.py` `FIT_STATES` | Validation fit sets | Only if the state joins a fit |
| `config/params/housing_need.yaml` `*_xx` keys | Housing-need context | Optional |
| About 30 scripts in `scripts/dev/` with their own `STATES` tuples | Research and page scripts | Only if you rerun that script |

Not hard-coded, so nothing to change:

- the CLI;
- the BPS adapter (it reads region and FIPS from the config);
- the app build and the map (`src/lotline/app/us_tiles.yaml` lists every state);
- the dashboard;
- `compliance_check.py`.

---

## 8. Reference: what a state with no reform history borrows (WS-SCALE task 10)

Most states have passed no ADU or middle-housing reform, so they have no uptake history of their own. Lotline
does not need one. The rule is the same for every such state: **the uptake parameters come from the reformed
states the model was fitted on, moved to the new state's own market, and the range widens by how much states
differ from each other.**

| What | Borrowed from | Moved to the new state by | Extra width for a new state |
|---|---|---|---|
| ADU uptake rate θ | The fit on the reformed states (`config/params/hazard.yaml`) | The state's own rents, home values and mortgage rates (`model/hazard.py`, D-043) | A state multiplier exp(τz) drawn per draw, τ from its fitted profile (D-044, `config/params/adu_state_effect.yaml`), plus the extrapolation widening for places outside the fitted range (D-030) |
| ADU rule probabilities for uncoded places | The coded places of the states in `REFORM_STATES` ("borrow only", section 3) | The place's size band | None beyond the prior's own spread |
| Missing-middle dose and blank shares | The same coded places, pooled | Size band | None beyond the prior's own spread |
| Fee levels for places with no fee file | The coded places of every state, pooled (`model/fee_levels.py`, below 5 own places) | None | The pooled prior's spread |
| Eligible lots with no parcels | The ACS count of one-unit detached homes | The D-056 scaling factor | The factor's log-sd |

A borrowed parameter never changes for the states it came from: the new state feeds nothing back until Ben
pools it (step 14).

**Is this allowed?** The Rules and Handbook (read 2026-11-17) do not ask for causal identification. Neither
page uses the words "causal", "identification" or "counterfactual".
- The Handbook calls the challenge "methodology-agnostic".
- The Handbook accepts assumptions when they are "clearly described and justified".
- The Rules score the opposite of a data requirement. Under Policy Insight (§8), work applied to "states
  with less complete data" is judged more favorably.

So a borrowed parameter is acceptable when it is written down, sourced, and carried with its range. That is
what the table above and `config/params/` do.

**What a borrowed parameter cannot say.** It assumes the new state's builders and owners respond to a reform
the way owners did in the fitted states once rents and prices are accounted for. Its range covers how much
the fitted states differed; it cannot cover a way the new state differs from all of them. The bundle's
`overlap_flag` says when a place sits outside the fitted range, and the guide's step 11 asks you to report it.
