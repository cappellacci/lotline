# WS-SCALE task 1: where the code is specific to one state

Finished 2026-11-17 on `ws/scale-audit` (stacked on #478). This continues the brief's § Audit
(`docs/build/workstreams/WS-SCALE.md`).

The question: where does the code branch on a state, and which adapters do more than reshape data? "Reshape"
means download, rename, map codes through a crosswalk, parse dates, attach a GEOID, validate. Anything else
in an adapter is a judgment that belongs in a named, sourced rule (task 8) or a CSV (task 7).

Method:
- `grep` over `src/lotline` for state codes, hard-coded GEOIDs and `state ==` tests;
- a read of every module in `src/lotline/adapters/states/` (TX, OH, OR and four NC files in full; the
  others with docstrings stripped, so a small inline rule there could have been missed).

## 1. State branches outside the adapters

No `if state ==` modelling branch remains in `src/` outside the adapters, except one (`mm_routes`). What is
left are state lists and hard-coded GEOIDs:

| Where | What | Kind | Suggested home |
|---|---|---|---|
| `model/scenarios/adu.py:1327` | `REFORM_STATES = ("MN","NC","OH","TX","OR")` | which states feed the shared priors | state file: `feeds_priors: true` |
| `model/estimate_mm.py:47` | `STATES = ("MN","NC","OH","TX")` | MM fit set | state file or `config/params` |
| `validation/v5.py:47`, `v5_stpaul.py:45`, `v9.py:57` | `FIT_STATES` (same four) | D-022 blank-share fit set, three copies | one list, read by all three |
| `model/mm_routes.py:40` | `if state.upper() != "OR": return LOCAL` | the only true `state ==` branch: Oregon's HB 2001 route | state file: `state_law_route` with its metro list |
| `model/estimate_mm.py:44-46`, `estimate_adu.py:764`, `mm_counts.py:57-58` | St. Paul 2758000, Charlotte 3712000, Mecklenburg 37119, Ramsey 27123 | holdout GEOIDs repeated in code | read from `cfg.holdouts` (already in the state files) |
| `validation/v5.py:39`, `v5_stpaul.py:37`, `v9.py:53` | `STATE`, reform ids, Portland/Bend GEOIDs | named validation tests | fine: a test of one place is about that place |
| `model/mm_routes.py:25` | `or_hb2001_metro.csv` (23 GEOIDs incl. 3 county remainders) | Oregon Metro list | see the note below |

**Two Metro lists disagree.**
- `or_hb2001_metro.csv` (read by `mm_routes`) has 23 GEOIDs, including the three county remainders.
- `or_metro_cities.csv` (read by `scripts/dev/or_state_reform_rows.py`) has 24 cities, no counties. It adds
  Rivergrove, Johnson City, Gladstone and Maywood Park, which the first list lacks.
- The routing model and the reform-rows script therefore use different Metro sets. This is Ben's call (it
  touches the MM routing); both files stay for now.

## 2. Adapters that do more than reshape

Most of what follows is fine as code: a text parser reading a city's permit descriptions is the adapter's
job. The question for each is whether a *number or a choice* sits in it with no name, source or range.

Grouped by kind. The "Cit" column says whether a source sits next to the value: Y = a source,
dec = a decision or hand-check note only, N = none.

### Shares and thresholds with no range (task 8 candidates)

| File:line | Value | Cit |
|---|---|---|
| `oh/franklin_permits.py:95`, `oh/montgomery_permits.py:63`, `oh/oh_parcels.py:260` | `DISTRICT_SHARE` 0.95: a taxing district maps to a jurisdiction when the parcel is missing (three copies) | N |
| `oh/oh_parcels.py:259` | `COUNTY_MIN_SHARE` 0.99 of a place's houses in one county before it gets yearly rolls | N |
| `oh/franklin_permits.py:93`, `montgomery_permits.py:62` | `ADU_REPEAT_DAYS` 730: one ADU per parcel per two years | N |
| `oh/franklin_permits.py:94` | 160 characters searched before "ADU" for a creation verb | N |
| `oh/montgomery_permits.py:67` | 100 permits a year over 2010-2025 makes a place "covered" | dec (Ben 2026-11-01) |
| `oh/cincy_permits.py:120` | 3+ ADU-flagged permits on one parcel in a year is a development, not ADUs | dec |
| `nc/durham_permits.py:91,262` | an unlocated permit goes to the city when the PIN prefix's city share is 0.5 or more | partial |
| `nc/onemap_codes.py:34-35` | tier cutoffs 0.8/0.9 **copied** from `config/params/tiers.yaml` instead of read from it | Y, but duplicated |
| `nc/onemap_parcels.py:81` | 0.5 of 2020 housing units for a place to count as covered | Y |
| `franklin_roll_diff.py`, `wake_roll_diff.py`, `mpls_roll_diff.py` | `MERGE` 0.20 acre growth = a merged lot (three copies) | N |
| `tx/fw_permits.py:126` | units over 1,000 read as missing | Y |

### Date windows and roll choices in code

- `tx/stratmap_parcels.py:114`: `ROLLS = ("2019-03","2025-06")`. Y.
- `nc/wake_realestate.py:66`: Wake rolls. dec.
- `mn/metc_parcels.py:93`: Metro rolls and their order. dec (Ben 2026-10-19).
- `mn/mpls_assessor_parcels.py:51,163`: years 2017-2026, with the file layout switching by year.
- `oh/franklin_permits.py:92`: snapshots.
- `oh/oh_parcels.py:247`: Franklin rolls.
- `oh/columbus_variances.py:56`: vintage pinned.
- `tx/fw_permits.py:22`: issue year = filing year.
- Floors on what counts as a valid date or year:
  - Austin: issue dates before 1970 dropped (stated in its provenance).
  - Franklin: issue dates outside 1970-today dropped.
  - Montgomery: issue dates outside 1990-today dropped.
  - Year built: under 1700 or 1800 dropped, in several files.

### Rules specific to one place

| File:line | Rule | Cit |
|---|---|---|
| `tx/austin_adu_roll.py:46-49,139-171` | HOME rule: from 2024-02-05, classes 101/102/103/436 count as an added building; a demolition within 3 years cancels it; 103 excluded (D-074) | Y / dec |
| `build/permit_theme.py:74-127` | `austin_home_two_unit`: an Austin U2 "TWO UNIT RES" permit from 2024-02-05 adding one home is an ADU (D-092 §6). All or nothing, not a share | Y |
| `tx/sa_permits.py:169-171` | "ETJ" in the address or council district 0 → Bexar remainder | Y |
| `or/mwvcog_permits.py:84` | Only Salem kept; other COG cities dropped as incomplete | dec |
| `oh/oh_parcels.py:915-933` | Franklin, Montgomery and Warren county paths | N |
| `oh/franklin_permits.py:369` | Columbus rows dropped (Columbus's own permits cover them) | N |
| `oh/columbus_permits.py:286-309` | Franklin Auditor ADU flags override Columbus permits | Y |
| `mn/ramsey_parcels.py:45` | St. Paul site-city handling | Y |
| `nc/clt_v5.py:42-49` | six Mecklenburg town GEOIDs in a dict | N |
| `mn/metc_parcels.py:287` | seven Metro county GEOIDs in code | N |

### One permit split into two rows (house + ADU)

Three adapters split one combined permit into two rows, each its own way:
- `or/portland_permits.py:152-206`: a new house with 2+ units becomes a house (n-1) and an ADU (1);
- `or/medford_permits.py:244-253`: "#house" and "#adu" rows;
- `mn/mpls_permits.py:261-279`: one unit moves from the house to an ADU row.

`mn/rochester_permits.py` does the same for code 103. The same idea in four spellings is a candidate for one
shared helper.

### Text parsers (fine as adapter code; listed for completeness)

These classify permit text with regular expressions. Each is the adapter's own reading of one city's free
text, and most were checked by hand:
- `oh/cle_permits.py`, `oh/cincy_permits.py`, `oh/franklin_permits.py`, `oh/montgomery_permits.py`,
  `oh/columbus_variances.py`;
- `nc/asheville_permits.py`, `nc/cary_permits.py`, `nc/chapel_hill_permits.py`,
  `nc/wilmington_permits.py`, `nc/raleigh_permits.py`;
- `mn/mpls_permits.py`, `tx/austin_permits.py`;
- `nc/onemap_codes.py` (about 40 rules for county land-use labels).

Five have no source note (N): Cleveland, Chapel Hill, Columbus variances, Montgomery, Cincinnati's word lists.

### Units derived from type (fine; already one column per crosswalk)

- `austin_permits.py:103-117`;
- `cstx_permits.py`;
- `columbus_permits.py:87`;
- `durham_permits.py:124`;
- `stpaul_permits.py:73`;
- `rochester_permits.py:132`;
- `mwvcog_permits.py:86`;
- `cle_permits.py:88`.

After task 7, the building-type crosswalk's `derived_units` column is the place for these.

## 3. What this means for tasks 7, 8 and 12

- **Task 7 (crosswalks):** the hard-coded code→type dicts are the next files to move into the
  building-type format:
  - Austin, Medford, Bend, Chapel Hill, Minneapolis occupancy;
  - Rochester codes, Columbus BPS codes.
- **Task 8 (rules as data):** the first block of § 2 is the list. Start with the values that are copied
  across files, because one rule then replaces three constants:
  - `DISTRICT_SHARE` 0.95;
  - `ADU_REPEAT_DAYS` 730;
  - `MERGE` 0.20;
  - the onemap tier cutoffs.
- **Austin:** the brief's "share of 2024+ duplex permits counted as ADUs" is today a yes/no rule
  (`permit_theme.austin_home_two_unit`) plus a measured share (`mm_counts.two_unit_adu_share`, D-092 §6). Giving
  it a low/high range is a method change (Ben's call; the MM owner's model reads it).
- **Task 12 (WI):** a new state needs none of the above. Every item is inside one state's own adapters.
  The pieces a new state does touch are the five state lists in § 1, and task 0 already made the first one
  optional ("borrow only").
