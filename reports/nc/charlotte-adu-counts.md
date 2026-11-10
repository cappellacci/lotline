# Charlotte and unincorporated Mecklenburg: ADU permits, 2010–2025

*2026-11-10 · data thread for D-072 (PR #358) · no model run*

V5 was scored and released on 2026-11-09 (D-071). This report covers four things: how many ADU-flagged permits
Charlotte (3712000) and unincorporated Mecklenburg (37119) issued each year, how good the description parser is
on them, whether Charlotte's coded ADU rules match the ordinances, and how to get the county's Accela permits
(2025 onward).

**Source:** NC's processed permit table `permits/meck_permits.parquet` (482,249 rows), built by `lotline fetch
--state NC --source meck_permits` from Ben's registered GeoPackage (`Winchester_BuildingPermits.zip`, data dated
2026-10-12). Nothing new was downloaded.

## 1. The holdout filter after the release

On `main`, `meck_permits.py` still built its query filter from every holdout, released ones included, so
Charlotte's and the county's permits from 2023-06-01 on were never read. **PR #357 (`ws/meck-release`) fixes this
and is open with green CI**: the filter uses only still-blind holdouts (`holdout.still_blind`), and both queries
become `1=1` once V5 is released. It adds tests on the blind registry (the `v5_blind` fixture) and on the
released one. I wrote the same change independently, then dropped it from this PR to avoid a conflict. **This
PR depends on #357**, and the counts below come from a store built with #357's code (2026-11-09 19:29).
Re-running the fetch on 2026-11-10 gave the same 482,249 rows, including 32,315 Charlotte and county permits
from 2023-06-01 on.

Two small things for #357 (described here, not edited):
- The adapter's `PROVENANCE` text, and so `docs/data_provenance.md`, still says held-out rows are never read.
  Add one line saying that only still-blind holdouts filter, and that V5 has been released.
- One more useful test: `load()` on the registered file under the released registry returns Charlotte's and the
  county's post-window rows (in this fixture: F2 and F3 come back, and F3 lands on 37119).

## 2. ADU-flagged permits by year

An ADU-flagged permit is a row with `building_type_std == "ADU"`: the description names an ADU on a code
101/434/438 permit (or on one with no code), and the permit is not a demolition (`meck_permits.classify`).

| Year | Charlotte flagged | Uninc. Meck flagged | Found missed (§3) | Charlotte eligible lots | Charlotte per 1,000 lots | Uninc. per 1,000 SF lots* |
|---|---:|---:|---:|---:|---:|---:|
| 2010 | 0 | 0 | 0 | 180,200 | 0.000 | 0.000 |
| 2011 | 0 | 0 | 0 | 183,775 | 0.000 | 0.000 |
| 2012 | 2 | 0 | 0 | 184,799 | 0.011 | 0.000 |
| 2013 | 2 | 0 | 0 | 185,301 | 0.011 | 0.000 |
| 2014 | 6 | 1 | 0 | 186,138 | 0.032 | 0.046 |
| 2015 | 4 | 1 | 0 | 188,081 | 0.021 | 0.046 |
| 2016 | 7 | 0 | 0 | 190,219 | 0.037 | 0.000 |
| 2017 | 9 | 0 | 1 | 192,935 | 0.047 | 0.000 |
| 2018 | 17 | 1 | 0 | 196,635 | 0.086 | 0.046 |
| 2019 | 21 | 2 | 1 | 199,911 | 0.105 | 0.092 |
| 2020 | 34 | 2 | 4 | 200,380 | 0.170 | 0.092 |
| 2021 | 23 | 1 | 1 | 201,786 | 0.114 | 0.046 |
| 2022 | 34 | 3 | 1 | 203,253 | 0.167 | 0.138 |
| 2023 | 50 | 2 | 0 | 203,204 | 0.246 | 0.092 |
| 2024 | 58 | 1 | 5 | 203,927 | 0.284 | 0.046 |
| 2025 (partial) | 43 | 1 | 1 | 203,927 (2024) | (0.211) | (0.046) |
| **2010–2025** | **310** | **15** | **14** | | | |

Eligible lots are the processed `eligible_parcels` rows (theme `adu`, rule 1.1). For Charlotte this is the ACS
one-unit-detached fallback (`acs_sf_fallback`, quality `low`), because the pre-UDO roll has zoning but no land
use. It runs to 2024, so 2025 uses the 2024 figure. As a check, NC OneMap's 2026 roll has 203,729 single-family
detached parcels in Charlotte. "Found missed" counts the 14 permits from §3 that create an ADU but are not
flagged, across both places (13 in Charlotte, 1 unincorporated in 2020).

\* **The 37119 denominator in `eligible_parcels` is wrong for this use.** It reads 275,566 lots in 2024, more than
Charlotte has. `eligible.allocate_homes` takes from the county remainder only jurisdictions that are in the BPS
universe. Charlotte and the six towns are `in_bps: False`, because BPS files their permits under 37119, so their
homes stay in the remainder. That is right for BPS outcomes. For permit-level counts it is not, because Charlotte
and the towns are counted separately: their lots would be counted twice. The last column therefore uses NC
OneMap's 21,812 single-family detached parcels in unincorporated Mecklenburg (2026 roll). With the table's
275,566, the 2021–24 rate would read 0.006 per 1,000 instead of 0.080. This is a WS-CORE / build question: for
Mecklenburg, D-072's step 2 needs a 37119 denominator that excludes the places counted separately. The PR
describes it; nothing here changes it.

**2025 is partial; 2026 is dropped.** All Charlotte permits in the legacy file fall from about 14,000–15,000 a
year (2018–2024) to 6,883 in 2025 and 991 in 2026. Within 2025, the monthly count falls from about 1,000 a month
(January–April) to under 200 by November–December as residential applications move to Accela. 2025 is roughly
half a year, so its rate is shown in brackets. The 7 Charlotte and county ADU permits issued in 2026 are not
reported.

**What the series shows:**
- Charlotte's 2021–24 rate is 0.20 per 1,000 eligible lots a year. D-072's comparison places: Durham 0.73,
  Raleigh 0.47, Durham County remainder 0.20, Greensboro 0.03.
- Flagged ADUs roughly doubled after the UDO: 28 a year in 2019–22, 54 a year in 2023–24. 2023 includes five
  pre-UDO months.
- Before about 2016 the counts rest on free text alone. The county's own work-type phrase "New. Accessory
  Dwelling Unit." first shows on a flagged permit in 2014 and is regular from 2016. It carries 260 of the 325
  flags. So 2012–2015 counts (after the 2012 rule) are likely lower bounds.

## 3. Parser hand check (30 matches, 30 non-matches)

**Sample.** Charlotte and 37119 permits, issued 2010–2025 (seed 20261110, script in the session scratchpad, not
committed). Descriptions (`permitdesc`, `workdesc`) were read from the registered file in memory only, as the
adapter does. They are not stored in the repo.
- **Matches:** 30 at random from the 325 flagged permits.
- **Non-matches:** 30 at random from a high-risk pool: 819 unflagged code 101/434/438 permits whose
  description has an ADU-like word (accessory, suite, studio, cottage, carriage, guest house, in-law, garage
  apartment, pool house, apartment, living space, ADU). A random draw from all 105,735 unflagged permits would
  find almost nothing, so it would not measure recall. "Kitchen" alone was left out of the pool: 10 of its
  5,975 permits were read, and all were kitchen remodels.
- **Plus a full pass:** all 79 unflagged permits whose description names an ADU or "accessory dwelling", of
  every code.

**Matches (30).** 25 are clearly ADUs (e.g. "ADU Construction for …", "Converting detached garage to ADU",
"Lower level"-style conversions, "Sanders Back Dwelling"). 5 are doubtful: they carry the county's "New.
Accessory Dwelling Unit." work type, but the project name says cabana, pool house (2), shed or accessory
building. Under the UDO a pool house with its own kitchen and bath is an ADU, and the county chose that work
type, so these are not clear errors.
- **Precision:** 25/30 = 0.83 strict (90% Wilson 0.70–0.92); 30/30 if the county's work type is trusted (0.92–1.00).

**Non-matches (30 from the pool).** None is clearly a missed ADU. 4 are ambiguous: "detached garage and studio",
"addition – mother-in-law suite", "master suite addition & studio bldg" and an unlabeled pool house. The rest are
owner suites, garages ("GARAGE ONLY, NO ADU"), playrooms, demolitions and apartment-complex garages.

**Full pass over the 79 that name an ADU.**
- **Correctly not flagged:**
  - 48 demolitions (codes 645/649). The county often stamps "Demolish/Move Off. Accessory Dwelling Unit." on any
    house or garage demo, so the parser's demolition rule matters here.
  - 12 garages, basements, a pool pavilion and an office that are explicitly not ADUs ("THIS IS NOT AN ADU",
    "NO ADU ALLOWED").
  - 5 others with no new unit: a repair of an existing accessory dwelling, a recreation-only garage, a mini barn,
    a scope note, and one ambiguous code-101 "New Residence … not attached to the main house".
- **Missed (14), listed in the PR:**
  - 12 code-434 permits that create an ADU but are worded as an upfit or addition: "Change room above garage to
    ADU Upfit", "Upfit … unfinished space into ADU", "Punch ADU Addition (expand footprint)" and others. The
    parser's alteration rule (rule 3) returns no type when "Upfit"/"Addition" is the work type, even when an ADU
    is named.
  - 1 code-434 "existing garage upfit" with the ADU work type.
  - 1 code-437 permit with the ADU work type (437 is not in the allowed codes).
  - None of the 14 shares a parcel with a flagged ADU permit, so none is the upfit of an ADU already counted.

**Recall.** TP = true flagged ADUs; FN = missed ADUs; recall = TP / (TP + FN).

| Case | TP | FN | Recall |
|---|---:|---:|---:|
| Central: county work type trusted; only the 14 found misses | 325 | 14 | 0.96 |
| Strict precision (0.83 × 325); 90% upper bound on clear misses in the rest of the pool (0/30 → ≤7.4% of 775) | 271 | 14 + 57 | 0.79 |
| Worst: strict precision; all 4/30 ambiguous are ADUs (≈103 of 775) | 271 | 14 + 103 | 0.70 |

For D-072's pooled k_parser = 1 / recall, Charlotte contributes **1.04 (central), up to 1.27–1.43**. Most of
Charlotte's flags come from the county's own work-type phrase, which behaves like a field flag. D-072 may prefer
to treat Charlotte from 2016 on as field-flagged and pool only its free-text flags (65 of 325) with the parser
sessions. That choice belongs in D-072, not here.

**Proposed parser fix (not made; `lotline.parse.permit_text` is shared):** when an ADU is named on an alteration
or addition permit and the description says "to ADU", "into ADU", "<name> ADU" or carries the ADU work type, and
nothing negates it, return `ADU` with `is_conversion=True`. Also allow code 437 in `meck_permits.classify`. This
recovers 14 permits, about 4%.

## 4. Charlotte's ADU rule rows in `config/reforms/nc.csv`

Sources read:
- **2012 rule:** the Zoning Committee recommendation for Petition 2012-067A (2012-06-27, 4 pp.).
- **Amendment history:** the city's text-amendment log, "Text Amendments 1992 – May 31, 2023" (17 pp.).
- **UDO rule:** the city's "Residential Accessory Structure or ADU Declaration" form (undated, file
  `permit_buildingpermitaccessorystructureudoamended.pdf`, p. 4), which quotes UDO §15.6 and §17.1.D/F.
- **Not readable:** the 2012 staff analysis PDF (it did not render). charlotteudo.org's Article 15 page shows
  only its table of contents.

**`NC-3712000-adu-2012`: no field changes; add to the notes:**
- Confirmed against the recommendation: 22 districts as coded, one ADU per lot, same owner (not owner-occupancy;
  staff advised against owner-occupancy), internal ≤35% and detached ≤50% of the principal structure, 800 heated
  sq ft cap either way, detached ADU covering ≤30% of the rear yard, 1 parking space, no separate driveway except
  corner or alley lots, no minimum lot size beyond the district's.
- The amendment log gives "Part A: 07/16/2012" and lists **no ADU amendment between then and May 31, 2023**, so
  no pre-UDO superseding row is missing. The log only lists approvals, not effective dates.
- Petition 2012-067 **deleted "elderly and disabled housing" and "guest houses and employee quarters"**, which
  the committee called ADU uses with tenant restrictions. That supports the row's note that a restricted pre-2012
  form existed. It is not coded, which is fine for a 2010 start (0 flagged in 2010–11).

**`NC-3712000-adu-2023` (UDO): confirm the fields; propose two note additions and one check:**
- Confirmed against the form's quotation of §15.6: an ADU with a single-family dwelling in any district, or with
  a duplex not on a sublot; only one per lot; same ownership; no separate driveway except corner or alley lots;
  internal ≤40% and detached ≤50% of the principal's floor area; a detached ADU no taller than the principal
  house. There is no absolute size cap (the 2012 rule's 800 sq ft cap is gone), so `adu_max_sqft` stays empty.
- **Add:** §17.1.F limits all accessory structures on a residential lot together to the heated first-floor
  area of the principal house. That is a real size cap on a detached ADU next to a small house.
- **Add:** setbacks are looser than in 2012: a detached ADU may sit in the rear or side setback, no closer than
  the district's side setback (in 2012: rear yard only, 15 ft from the rear line).
- **Parking:** §15.6 as quoted names no ADU parking requirement, but the UDO parking tables were not read, so
  `parking_min_per_unit` stays empty.
- **Check:** charlotteudo.org lists text amendment **2025-118** (approved 2026-03-23), a "maintenance text
  amendment" that "adjusts use permissions and prescribed conditions". Whether it touches §15.6 was not read.
  The form's file name ("udoamended") suggests it already reflects an amendment.

**Unincorporated Mecklenburg (37119) has no ADU rule row.** The amendment log shows the county had its own
zoning ordinance (1991-031(c)) and that zoning administration moved from the county to the city on 2005-07-01
(2005-078). Who zones unincorporated land since then, and with whose ADU rule, was not settled here. Most of it
is believed to lie in Charlotte's or a town's extraterritorial jurisdiction (ETJ). Under D-072's step 2, 37119
can't enter the fit until Ben accepts a rule row. Proposal: check the ETJ map and, if Charlotte's ETJ covers it,
code 37119 with Charlotte's rows (2012, 2023) limited to that area.

## 5. Accela permits, 2025 onward: manual download steps for Ben

The county's GIS servers answer scripts with a Cloudflare browser challenge, so this is a browser download, like
the legacy file. Don't script around it.

1. **Network.** As on 2026-10-21: from Europe, connect to a US VPN first. The county's map servers did not answer
   otherwise.
2. **Open** https://maps.mecklenburgcountync.gov/opendata-viewer in a normal browser and let the Cloudflare check
   finish.
3. **Find the dataset.** Search for "permit" and pick the building-permit dataset that the viewer describes as
   the Accela permits, the companion to "Building Permits – Winchester" (legacy). If there are several, pick the
   residential / building one, not trades (electrical, mechanical, plumbing).
4. **Before downloading, note** the dataset's exact title, its "last updated" date and any field list. Check
   that it has the issue date, a permit type or work type, a description, the parcel number and coordinates or a
   point.
5. **Download the GeoPackage** (as for Winchester), or a File Geodatabase or CSV if that is all it offers. Save it
   unchanged into `~/lotline-data/manual/meck_permits_accela/`.
6. **Register it** (from the repo, any worktree):

   ```bash
   lotline manifest register --source meck_permits_accela --url https://maps.mecklenburgcountync.gov/opendata-viewer --license "Mecklenburg County GIS public data (accuracy disclaimer; no license stated)" --vintage <the dataset's last-updated date, YYYY-MM-DD> ~/lotline-data/manual/meck_permits_accela/<file>
   ```

7. **Tell the NC data thread** the file name, the title and the date. The next step is an adapter (a new source
   `meck_permits_accela`, so `config/states/nc.yaml` needs a source entry and the registry a module), with the
   same privacy rule: owner, address and contact fields never read. Its rows would replace the legacy file from
   the Accela cut-over date on; the legacy file keeps everything before. Dedupe on permit number where the two
   overlap in 2025.

Registering under a new source id keeps the legacy adapter unchanged: `meck_permits.file_entries` already
ignores any file not named `Winchester_BuildingPermits.zip`.

## What this does not do

- No model, calibration or scenario run.
- No change to `eligible_parcels`, the parser, or `config/reforms/nc.csv`.
- No Accela download.
- The 2012 staff analysis and the UDO's own Article 15 text were not read in full.
