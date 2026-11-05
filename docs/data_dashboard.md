# Data dashboard

A single page that shows what Lotline has collected, for every state in the build at once or one state at a
time. It exists to **check the data** (are the parcel rolls, reforms and permits complete and consistent?) and
to **show the work** behind the model. It is not a model output: every number is a count or share of data the
adapters have already processed.

```bash
python scripts/build_data_dashboard.py            # every configured state; writes reports/data_dashboard/
python scripts/build_data_dashboard.py --fetch    # also downloads Census population estimates if missing
python scripts/build_data_dashboard.py --state MN # one state
```

Open `reports/data_dashboard/index.html` in a browser (it needs internet access for d3 and the county map;
see `docs/disclosures.md`). The folder is gitignored: it holds aggregates of downloaded data. The summary is
also written as `summary.json` beside the page.

## What is on the page

| Panel | Shows | Source |
|---|---|---|
| Headline tiles | Population covered, jurisdictions and counties with a parcel roll, parcels on file, eligible parcels, coded reforms (share second-coded) | processed tables, `config/reforms/` |
| Coverage map | Counties colored by one of six measures (population covered, parcels, roll year, reforms, housing growth minus population growth, best data tier); a dot per municipality and township, filled when it has parcels. Click a county to filter the page | the same, plus TIGERweb place/township boundaries (dot positions) and the us-atlas county shapes |
| Parcels by land use | Standardized land-use mix of the parcels on file, for the scope or a clicked county | processed `parcels` |
| Parcel sources | Every processed parcel file: parcels in its latest rolls, how many are used, counties, roll years, share with a zoning code | processed `parcels` |
| Ordinance timeline | Every coded reform by place and date, colored and shaped by theme; hollow marks are single-coded; reforms per year above | `config/reforms/<st>*.csv` |
| Housing vs population growth | Population, ACS housing units and "2010 stock + units permitted since", indexed to 2010 = 100 | Census PEP, ACS B25024, BPS |
| Units permitted per year | BPS units by building size (1, 2, 3–4, 5+) | processed `bps_place_year` |
| Data checks | Automatic checks with a level (ok / note / warn) | all of the above |
| Jurisdictions | Searchable, sortable table of every jurisdiction with a CSV download | all of the above |

## Rules

The rules live in the docstring of `src/lotline/dashboard/summarize.py`, and each has a hand-worked test in
`tests/dashboard/test_dashboard.py`. In short:

- **Latest roll per jurisdiction.** Each parcel source is cut to its latest vintage *per jurisdiction*, since
  rolls arrive county by county and some places are kept only in older rolls (St. Paul, under the V5 snapshot
  rule).
- **One source per jurisdiction.** Where sources overlap, the one named in `parcel_sources` in the state config
  wins if it has parcels there; otherwise the largest. Counts are never added across sources.
- **Population covered.** A jurisdiction counts as covered if its chosen source has at least one parcel. Population is the
  2020 Census count; an unincorporated county area gets the county's 2020 estimate less the other listed
  jurisdictions in that county (floored at zero, marked with *).
- **Nothing is dropped silently.** Parcels outside any listed jurisdiction, counties with no jurisdiction in the
  table and reform GEOIDs that match no jurisdiction all show up as data checks.
- **Holdouts.** Only processed tables are read, and those already exclude held-out outcomes.
- **Precision.** Outputs are jurisdiction or county counts; no parcel-level record is shown (Official Rules PDF
  review, point N-series: avoid parcel-level precision).

## Growth panel caveats

- ACS 5-year housing units are labeled by the survey's end year, so each point averages five years and lags.
- Population estimates splice two vintages: 2010–2019 from vintage 2020, then 2020 on from vintage 2025. The
  2020 seam changes the Census base and is marked on the chart.
- "2010 stock + permits" adds every unit permitted since 2010 to the 2010 ACS count. It ignores demolitions and
  permits that were never built, so it runs above the ACS line; the gap is a rough sense of both.
- County "housing growth minus population growth" compares ACS 2010 with ACS 2024 against estimates for the
  same years. Small counties have wide ACS margins.

## Adding a state

Nothing in the dashboard names a state. A fifth state shows up once it has `config/states/<st>.yaml`, a built
`jurisdictions` table and whatever else its adapters have produced. Missing pieces show up as empty panels or
data checks, never as errors. The end-to-end test builds a made-up state from config and processed tables only.
