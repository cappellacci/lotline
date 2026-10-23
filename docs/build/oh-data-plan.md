# Ohio data plan (thread 11, step 1)

*WS-OH, 2026-10-23. Status: **draft, waiting for Ben's approval** (§6). Brief:
`docs/build/handoffs/11-ohio-data-complete.md`. Template: `docs/build/nc-data-plan.md`.*

**Goal:** Ohio can run end to end through the baseline, the ADU scenario (D-025), the missing-middle scenario
(D-024), the fee scenario and the county and state totals, for all 952 Ohio jurisdictions, with every input
either real or a labelled fallback. Above all, Ohio should **add places to the multi-state ADU and
missing-middle estimation panels**.

## 1. What exists today (checked 2026-10-23)

I checked `main` at `f7cc92a` and the shared data folder (`~/lotline-data/processed/oh`). The brief's snapshot
is right, with the corrections and additions in bold.

| Input | What is there | Gap |
|---|---|---|
| Jurisdictions | 952 (567 places, 297 townships, 88 county remainders); tiers 826 / 126 (tier 2 / 3) | No tier 1: the statewide roll has no year built. |
| Parcels | 6,093,278 parcels, all 88 counties. **Export dates run from 2023-06 to 2023-12 for 86 counties; Summit and Clinton are 2026 exports.** | One roll per county. Land use unknown for more than 10% of parcels in **Summit (100%), Meigs (100%), Muskingum (100%: code 999), Lucas (55%), Warren (44%), Coshocton (28%), Hocking (27%), Hardin (25%), Fairfield (20%), Cuyahoga (13%)**. Almost all of these are blank codes, so the fix is a county file, not a crosswalk. No year built or units. |
| Eligible parcels | 825 jurisdictions counted from parcels (2023), 6 from the 2026 rolls, 121 on the ACS fallback (2010–2024). 6 of 5,282 rows rated `high`. | **The table was built before D-035 (#208) merged, so parcel-counted places still have no history rows** (no `parcels_scaled_acs`). **7 of the 20 largest places are on the ACS fallback because of the D-017 gate:** Cleveland (24% unknown), Toledo (65%), Akron (100%), Dayton (19%), Hamilton (11%), Cuyahoga Falls (100%), Middletown (15%). |
| Permits | Columbus 2010–2026 (29,157 new-building and demolition permits) and Cincinnati 2010–2026 (8,190). **2–4 units, permits (units): Columbus 446 two-unit (892) and 432 three-or-four-unit (1,261), plus 905 townhouse permits; Cincinnati 37 (74) and 39 (130).** ADU: Cincinnati 26, Columbus 0. | **Columbus's 0 ADUs are missing data, not zeros** (no description field), so Columbus would enter the ADU panel as a place that never builds ADUs. Its layer does have `B1_ALT_ID`, the permit number, which the Franklin County Auditor's permit file also carries *with* a work description (S1). Cleveland: 201,961 permits since 2015 with work descriptions and use groups, ODbL. **Dayton, Toledo, Akron, Cuyahoga Falls, Hamilton, Lakewood and Dublin: one ArcGIS search each found no open permit layer.** Canton has a "Building and Development" layer, not opened. |
| ADU rules | 20 rows, 15 places | Uncoded among the 20 largest: Akron, Parma, Canton, Lorain, Cuyahoga Falls (amlegal returns 403). Dayton: Ben's lookup (Ord. 31991-22A, 2022-09-21) vs the coded row (Ord. 32038-23 inferred, 2023-05-10). **Franklin County suburbs (Westerville, Grove City, Hilliard, Upper Arlington, Gahanna, Reynoldsburg …): no rows, so they can't join the panel even once S1 gives them ADU counts.** |
| Missing-middle rules | 1 row (Cincinnati Connected Communities, 2024-07-01) | **Euclid's Ord. 120-2024 (two-family dwellings permitted in U1, passed 2024-10-07) is noted in Euclid's ADU row but not coded as a missing-middle row.** Columbus Zone In is coded `other` (corridor apartments, not 2–4 units on single-family lots), which is right. Others unknown. |
| Fees | none (`config/fees/oh.csv` does not exist) | Columbus water and sewer capacity charges (catalog: $335–397 water for a small meter); Cincinnati and Cleveland water and sewer |
| Market, demand | ACS, FHFA, FRED, demand index: statewide | — |
| Engines on `main` | Baseline, ADU, missing-middle, fee, combine | — (not run here: data thread) |

**Already on disk and unused:** the Franklin County Auditor's current `Permit.xlsx` (362,049 permits,
2021–2026, 122 taxing districts, with free-text descriptions) and `Dwelling.xlsx` (year built `YRBLT`, living
units `LIVUNITS`, one row per dwelling *card*), downloaded 2026-10-18 for a research scan. A text search of the
permit file finds 113 records naming an ADU or carriage house (74 in Columbus, the rest in suburbs), many of
them trade permits pointing back to one building permit. The host has no robots.txt rules (404).

## 2. What the estimation panels need from Ohio

- **ADU panel (D-025):** a place enters if it is in a permit source with an ADU flag, has a dated ADU rule (a "no
  ADUs allowed" row counts) and has eligible parcels. Today Ohio offers **one usable place, Cincinnati**
  (adopted 2023-10-02, 26 ADU permits). Columbus would enter with false zeros. Toledo (2025-09) and
  Lakewood (2023-11) have dated rules but no permits.
- **Missing-middle panel (D-024):** the outcome is Census BPS 2–4 unit permits, so every Ohio place over
  10,000 people with a BPS row is already in. What Ohio adds is **treated places with dated rules**; today
  that is Cincinnati only. City permit data matters less here.

So for the ADU panel the lever is **permit records with ADU flags across many places at once**, which is what
the Franklin County file gives. For missing middle the lever is **rule dates**.

## 3. Subtasks

Costs are my wall-clock time and whether the work is token-heavy. "Automatable" means no broad web
searching: public APIs, files already on disk, or official pages I can open directly.

| # | Subtask | Feeds | Source | Automatable? | Cost | Priority | Owner |
|---|---|---|---|---|---|---|---|
| S1 | **Franklin County permits adapter** (`franklin_permits`): read the auditor's permit file; flag ADUs from the description (accessory dwelling, ADU, carriage house with kitchen or living space; one building permit per project, trade permits that cite it folded in); flag new two-, three- and four-family buildings; place each permit by parcel ID through `oh_parcels` (Columbus and the county's suburbs and townships). Then give Columbus permits an ADU flag by joining `B1_ALT_ID` to the auditor's permit number. **Check the monthly archives for permit files from 2014–2020** (one listing request per year folder) so the panel has pre-adoption years. Every hand rule gets a test on synthetic rows; a sample of 50 flagged and 50 unflagged descriptions is read by hand and the hit rate reported. | ADU panel (Columbus with real counts; Franklin suburbs as places with no ADU rule or later adopters); baseline checks vs BPS | Franklin County Auditor (on disk; archives) | Yes | 4–6 h, moderate tokens | **Panel (top)** | Me |
| S2 | **Rule rows for the places S1 covers:** the Franklin County cities and villages with permits (Westerville, Grove City, Hilliard, Upper Arlington, Gahanna, Reynoldsburg, Worthington, Whitehall, Bexley, Grandview Heights, New Albany, Canal Winchester, Groveport, Obetz …) plus the townships with zoning. Dublin is coded. One direct fetch of each official code page; what won't open goes to `oh-adu-lookups-todo.csv` and `oh-mm-lookups-todo.csv`. | ADU panel (a place with no dated rule is left out), MM rules | City code pages (many on amlegal or Municode, which often block bots) | Partly | 3–4 h, token-heavy if pages are long; about one fetch per place | **Panel (top)**, with S1 | Me, then **Ben** for the todo CSVs |
| S3 | **Rebuild eligible parcels on today's `main`** so D-035's scaled history exists for Ohio's 831 parcel-counted jurisdictions; report what moved and check each parcel sits in one jurisdiction. Again after S5 or S6. | Every scenario's denominator, every panel row (the panel uses the nearest roll) | `lotline build` (exists) | Yes | 1 h, low tokens | **E2E** | Me |
| S4 | **ADU and missing-middle rules, permit places and the 40 largest:** Dayton (reconcile Ben's 31991-22A with the coded row: one fetch of the city's legislation page), Euclid (code Ord. 120-2024 as a missing-middle row if the ordinance text opens), Akron, Parma, Canton, Lorain, Cuyahoga Falls (to the todo CSV: amlegal blocks), then places 21–40 (Mansfield, Mentor, Strongsville, Cleveland Heights, Fairfield, Delaware, Findlay, Warren, Lancaster, Marion, Lima, Brunswick, North Ridgeville, Mason …). Confirmed rows into `config/reforms/oh.csv` with the schemas 1.7 citation fields; unread stays blank (D-022). | ADU and MM scenarios' current rules; MM panel events | Official city pages; Legistar where the city uses it | Partly | 4–5 h, token-heavy; about one fetch per place | Panel (MM events) and accuracy | Me, then **Ben** |
| S5 | **Land use for Summit, Lucas and Cuyahoga** (Akron, Cuyahoga Falls, Toledo, and Cleveland's 24% unknown): one probe each for an open county parcel layer with a land-use code (Summit Fiscal Office, Lucas County AREIS, the Cuyahoga open-data hub in the catalog), robots.txt first; if open, a small adapter or a land-use join onto `oh_parcels` by parcel ID. Muskingum, Meigs, Warren and the smaller counties: probe only if the first three work. | Eligible parcels for 4 of the 10 largest cities (moves them off the ACS fallback); D-021 coverage | County GIS / auditor open data | Yes, if open | Probes 30 min; each adapter 2–3 h | Accuracy (high) | Me |
| S6 | **A real second roll year:** (a) Franklin County shapefile and CSV archives (2002 on, monthly since 2014) with `YRBLT` and `LIVUNITS` from `Dwelling.xlsx`: real history and **tier 1 for Franklin County** (year built), plus a check on D-035's scaled history; (b) the token-gated 2022 statewide vintage: an access request to OGRIP (Ben, §4). D-035 already gives every place a history, so this is a check and a quality gain, not a blocker. | Eligible history, V1 backtests, tier 1 for Columbus and suburbs | Franklin Auditor archives; OGRIP | (a) Yes; (b) No | (a) 3–4 h, downloads ~1 GB; (b) one email | Accuracy | Me (a), **Ben** (b) |
| S7 | **Cleveland permits** (`cle_permits`, ODbL: fetched at run time, derived tables never redistributed): new one-, two- and three-family buildings from `USE_GROUP_1` and the work description; ADU flag from the description (12 mention a carriage house). Cleveland allows no ADUs, so it joins the ADU panel as a place with no rule, and the FBC pilot areas (2024) get permit counts. | ADU panel (one untreated big city), FBC descriptive check | ArcGIS REST (ODbL) | Yes | 3 h, moderate tokens | Accuracy (medium) | Me, after **Ben's OK on ODbL** |
| S8 | **Fees:** Columbus water and sewer system capacity charges (city PDF in the catalog), Cincinnati (Greater Cincinnati Water Works, MSD) and Cleveland Water tap and capacity fees, from official PDFs I can open; rows in `config/fees/oh.csv` (thread 2 format). Others keep the $50k Handbook prior (D-034). | Fee scenario's "real fees" variant | City PDFs | Partly | 2–3 h, token-heavy (PDF tables) | Accuracy | Me |
| S9 | **Ben's manual items** (§4). | S2, S4, S6, S7 | Ben | No | 30–60 min of lookups, one email | As the items they feed | **Ben** |
| S10 | **Readiness report** `docs/build/oh-readiness.md`: coverage of every input across the 952 jurisdictions (real, fallback, unknown), the number of places Ohio adds to each panel, and what closes each gap. Refresh the OH rows of `docs/data_availability.md` and the catalog's Cleveland and Franklin rows. **No model runs.** | Transparency | — | Yes | 2 h, moderate tokens | **E2E** (done-when) | Me |

**Order I'd work it:** S3 now (cheap, confirms the table) → S1 → S2 → S4 → S5 probes → S10 draft → S6a → S7
(if approved) → S8 → S10 final. One small PR each. Week of 2026-10-26.

**What Ohio would add if S1, S2 and S4 land:** ADU panel from 1 place (Cincinnati) to roughly 15–25
(Columbus with real counts, the Franklin suburbs that have dated rules, Cleveland if S7). Missing-middle
events from 1 to 2–4 (Cincinnati, Euclid if confirmed, any found in S4). These are estimates; the readiness
report gives the real counts.

## 4. Ben's manual items (exact steps)

1. **ADU and MM fill-in tables** (after S2 and S4 write them): open
   `docs/research/ordinances/oh-adu-lookups-todo.csv` and `oh-mm-lookups-todo.csv`, largest place first. For
   each row, open the city's code (link given), and fill in the date ADUs (or 2–4 units) became allowed, the
   ordinance number and by right yes/no; leave a row blank if the code doesn't say. About 5 minutes a place.
   Akron, Parma, Canton, Lorain and Cuyahoga Falls are on amlegal, which blocks me.
2. **Dayton:** if my one fetch of Dayton's legislation page can't settle it, look up Ord. 31991-22A's
   *effective* date (Dayton ordinances usually take effect 30 days after passage, so likely 2022-10-21) and
   whether 32038-23 (2023-05-10) changed the ADU rules. I then replace the coded row.
3. **Statewide 2022 parcels (S6b), one email** to OGRIP (the contact listed on the Ohio Geographically
   Referenced Information Program site, ogrip.oit.ohio.gov):

   > We are building an open, public-interest housing model and use the Ohio Statewide Parcels public view.
   > Could we get read access (or a one-time export) of the 2022 statewide parcel vintage
   > (maps.ohio.gov Statewide_Parcels_2022), which currently needs a token? We need only parcel ID, county,
   > land-use code and land area; no owner names.

4. **Cleveland ODbL (S7):** say yes or no to fetching Cleveland permits at run time under ODbL, on the terms
   already in WS-OH (never commit or publish derived tables; results cite the source and the license).

## 5. Out of scope

`model/*` and `model/scenarios/*` (no engine changes and no engine, scenario or development runs), the demand
index, statewide sales (88 different auditor systems; WS-OH gotcha), and the National Zoning Atlas (license).

## 6. Decisions I need from Ben

1. **Approve S1** (Franklin permits adapter from the auditor's file; no new dependency) and its archive check
   (a few listing requests and, if found, about 6 permit files of ~20 MB).
2. **Approve S2 and S4 research** at about one direct fetch per place, no search sweeps.
3. **Approve S6a downloads** (Franklin archives, ~1 GB in `~/lotline-data`).
4. **S7:** fetch Cleveland under ODbL, yes or no?
5. Do §4's items 1–3 when the tables are ready.
