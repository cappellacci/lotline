# Why the ADU anchor misses: a look before any new modifier (exploratory)

*2026-11-03, WS-ENGINE, after D-040's results, at Ben's request. Nothing is fitted or changed here: the
figures describe the D-039 fit set and test set, the D-039 fit (`fit.csv`) and the permit tables. Per-place
inputs: `diagnose_places.py` (run from the repo root with an output path). Not pre-registered; every grouping
below was chosen after seeing D-039 and D-040.*

## 1. Austin's "ADUs" are mostly a different product
- All 2,545 come from one permit class, `R-102 Secondary Apartment | New`.
- **66% were issued in the same year as a new single-family house on the same parcel** (67% within a year).
  These are builders putting two new homes on one lot, not owners adding a unit behind an existing house.
- They are large: median 1,310 sq ft, against 600–850 in San Antonio, Durham, the Mecklenburg towns and
  Greensboro. In Raleigh and Durham, 12–15% are issued alongside a new house.
- Austin alone is 70% of the ADUs in the fit. Without the co-built units, Austin is 864 permits in 8 years, or
  **0.72 per 1,000 eligible parcels a year**, close to Durham (0.73) and Raleigh (0.52).

## 2. Minnesota's suburbs are counted by a survey that undercounts
- 40 of the 42 MN places rely only on Met Council's annual survey, where each city reports its own ADUs.
- Where the two overlap, Met Council records about half of Minneapolis's own ADU permits. Examples: 2017,
  22 vs 30; 2019, 18 vs 35; 2023, 8 vs 14.
- The number of suburbs reporting any ADU rose from 1 (2016) to 25 (2025). That rise mixes real uptake with
  cities starting to report.
- So many of the 21 MN places at zero over their whole window may be "not reported", not "not built".

## 3. The market term points the wrong way across places
- The model expects more ADUs where rents and home values are high. Its market multiplier (`h1`) is 0.9–1.2 in
  the outer suburbs and 0.3–0.8 in the big cities.
- Observed rates run the other way:
  - log rate vs log `h1`: correlation −0.13;
  - the fitted place effect vs log `h1`: −0.22.
- The pro forma answers "would an ADU pay off for this owner", but that is not what separates high-uptake
  places from low ones in our data.

## 4. Rule age and rule type add little
- The place effect correlates −0.24 with the ramp: places with long-standing rules have not produced more.
- Nearly every place is coded with a restricted rule (partial), Austin included. The rule coding has little
  variation to explain anything with.

## 5. Many places carry almost no information
- 18 places enter with 1–3 years and ramps of 0.1–0.4, with expected counts under 2.
- In D-040, "MN" is 42 small suburbs and "TX" is two large cities, so leaving one state out compares unlike
  sets.

## What it suggests (for Ben's decision; nothing done)
1. **Count the same thing everywhere first:**
   - Decide whether Austin's co-built secondary apartments count as ADUs for the scenario. If not, exclude
     them by a rule written down in advance.
   - Measure Met Council's undercount, e.g. a reporting factor from the Minneapolis overlap, or use only places
     with their own permit records.
2. **Then re-check whether the market term carries any signal across places.** If it still doesn't, the
   cross-place driver is something we don't yet model: city ADU programmes, lot and alley layout, or builders'
   business models.
3. **Only then** consider a place-type modifier. Some of the city-vs-suburb gap in D-040 is likely items 1 and 2.
