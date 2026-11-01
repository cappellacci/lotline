# Texas data plan (thread 12, step 1)

*WS-TX, 2026-10-23. Status: **all four decisions in §6 approved by Ben on 2026-10-23** (S1a, S1b, S1c Dallas,
S4–S6 research at about one fetch per place; Ben downloads StratMap 2026 and the four earlier vintages). Brief:
`docs/build/handoffs/12-texas-data-complete.md`. Template: `docs/build/nc-data-plan.md`.*

**Goal:** Texas runs end to end for all 1,006 jurisdictions with every input real or a labelled fallback, and,
above all, Texas adds places to the multi-state ADU (D-025) and missing-middle (D-024) estimation panels.

**What each panel needs from Texas (read from D-024 and D-025):**
- **Missing-middle panel (D-024):** the outcome is Census BPS 2–4 unit homes, which every Texas place already
  has. The panel already holds **232 Texas places of 10,000+ people**, but only **2 are treated** (Austin
  HOME 2024, Houston Livable Places 2023). Texas adds treated places through **dated rule rows**, not new
  permit data.
- **ADU panel (D-025):** the outcome is ADU permits, which BPS does not count. Texas adds places only through
  **city permit records with an ADU flag**: today that is Austin alone.

So permit sources (S1) feed the ADU panel, and rule dates (S4, S5) feed both.

## 1. What exists today (checked 2026-10-23)

I checked `main` at `f7cc92a` and the shared data folder (`~/lotline-data/processed/tx`). The brief's snapshot
is right, with the corrections and additions in bold.

| Input | What is there | Gap |
|---|---|---|
| Jurisdictions | 1,006 (952 places, 54 county remainders); tiers: 1 tier 1 (Austin), 1,005 tier 3 | Everything outside Austin is national data only. |
| Parcels | 239,626 City of Austin parcels from the TCAD 2026 roll (Travis part only, hand-registered) | **No other county.** See S2: a statewide, CC0 parcel layer exists in seven vintages. |
| Eligible parcels | Austin counted from parcels (2 rows); **1,003 jurisdictions on the ACS fallback** | D-035 now fills Austin's history from ACS scaled to the roll. |
| Permits | Austin 1971-04-27 to 2026-10-16: 151,655 permits; 3,166 ADU, 7,201 two-unit, 1,589 three-or-four-unit (8,790 two-to-four), 124,459 single-family | No other city on `main`. **Fort Worth, San Antonio and Dallas do have usable open permits** (S1). |
| ADU rules | 23 rows, **18 places** (the brief said 19), all among the 20 largest | Corpus Christi and Pasadena not coded (their lookups are written up for Ben in `docs/build/manual-ordinance-lookups.md`); McKinney (none vs partial); Killeen's overlay vote of 2026-10-20; **16 rows carry a "FLAG for second coder"** (code sites returned 403). |
| Missing-middle rules | 2 rows: **Austin HOME phase 1 (2024-02-05) and Houston Livable Places (2023-11-27) are both coded** | The other 230 panel places have no rule row, so they count as untreated by default (D-022). |
| Other reform rows | Austin HOME phase 2 lot size (2), Houston lot size (1999, 2013), Austin parking (2023); 2025 state laws SB 15, SB 840, HB 24, SB 1883; HB 852 (2019) | — |
| Fees | `config/fees/tx.csv`: 2 Austin building-permit rows (FY2024, FY2025) | **No water or sewer impact fee anywhere**, so the fee scenario uses the Handbook $50k for every place. |
| Prices | ACS, FHFA; TCAD appraised values for Austin (`value_basis = appraisal`) | Texas keeps sale prices confidential (Tax Code §22.27). Nothing to collect. |

## 2. What I checked for the gaps (2026-10-23)

Targeted requests only: one metadata or count query per source, no bulk downloads, robots.txt read first.

**Parcels.** The TxGIO **StratMap Land Parcels** collection is **CC0 1.0** (public-domain dedication; TxGIO
DataHub API, `api.tnris.org/api/v1/collections`). Seven vintages: 2019-03 (230 counties), 2021-07, 2022-07,
2023-02 (254), 2024-02, 2025-06 and **2026-09 (253 counties, published 2026-10-01)**. Each vintage has one
statewide zip (2.0–2.8 GB; 2026: 2.7 GB) plus one zip per county. Fields include `prop_id`, `stat_land_use`
(the Comptroller's PTAD state code, which `config/crosswalks/tx_ptad_land_use.csv` already maps), `loc_land_use`,
`legal_area`, `land_value`, `imp_value`, `mkt_value`, `year_built`, `tax_year`, `county`; no unit count. The
download host (`data.geographic.texas.gov`) answers scripted requests with a CloudFront 403, so the zips are
**browser downloads for Ben**. The REST map service (`feature.geographic.texas.gov`, "most recent") has
querying turned off, so I could not count land-use coverage by county before download.

**Permits, by city** (record-level, the only kind that can flag ADUs):

| City | Source | Years | ADU flag | Units per building | License | Verdict |
|---|---|---|---|---|---|---|
| Fort Worth (4827000) | ArcGIS `CFW_Open_Data_Development_Permits_View` | 2001-06-30 to 2026-10-23; 1,620,675 rows (all trades) | No class; ~1,360 rows mention "accessory dwelling"/"ADU" in use or work text | `Units`, `Use_Type`, `Specific_Use` | CC-BY 4.0 | **Adapter (high).** Fort Worth has no rentable-ADU rule (coded none), so it joins the ADU panel as a comparison place and supports a 2–4 unit check against BPS. Has `Owner_Full_Name`: excluded by field list. |
| San Antonio (4865000) | Open Data SA CKAN, "Permits issued" 2020–2024 and 2025 on | 2020-07 to 2026 | **"Res Accessory Dwelling Permit"** type (125 in the first ~2.3 years of the 2020–2024 file) | None (permit type, area, valuation) | CC-BY | **Adapter (high).** A treated ADU place: UDC changes effective 2023-01-01 give about 2.5 years before and 3 after. robots.txt disallows `/api/` and `/datastore/` (I made one `package_show` call before reading it; nothing else there); the CSV downloads under `/dataset/` are allowed. |
| Dallas (4819000) | Socrata `e7gq-4sah` (still updated; the WS-TX brief and catalog say it stopped in 2020) | 2018-01 to 2025-12; 392,799 rows | Text only (48 rows say "accessory dwell") | `land_use`: single-family, two-family, multifamily; no unit count | **Not stated** | **Adapter (medium), license to settle first.** Dallas has no by-right ADU (comparison place). Two-family new construction is identifiable; 3–4 units are not. |
| Collin CAD (Plano, Frisco, McKinney, Allen …) | `data.texas.gov` `82ee-gbj5` | Rolling 3 years (2023 on) | "Accessory Building" (mostly sheds) | None | Not stated | **Skip for now:** no pre-period. Note that the window rolls, so older years are already gone. |
| Arlington | ArcGIS `OD_Property/MapServer/1` | Mostly 2023 on (18,715 rows) | Census class codes only | Census class 101/104/105 | Not stated | Skip: no pre-period. |
| San Marcos | ArcGIS `CoSM_BuildingPermits` | 51,731 rows (range not read) | Text | `LANDUSE` (incl. Duplex, 387) | Not read | Low: small city, rule not coded. |
| Houston | Monthly aggregates; plat reports | — | — | — | ODC-BY | No record-level permits (catalog). Houston stays in the MM panel through BPS; no ADU panel. |
| El Paso | `gis.elpasotexas.gov/.../Permit/MapServer` | — | — | — | — | The service has no layers. Stop. |

Not found in one ArcGIS Online search: Corpus Christi, Lubbock, Laredo, Plano, Garland, Irving, Amarillo,
Denton, Round Rock, Killeen, Waco, College Station. No further searching planned.

## 3. Subtasks

"Automatable" means no broad web searching: public APIs, data in the repo, or official pages I can open directly.

| # | Subtask | Feeds | Source | Automatable? | Cost | Priority | Owner |
|---|---|---|---|---|---|---|---|
| S1a | **Fort Worth permit adapter** (`fw_permits`): residential building permits only; ADU flag from `Use_Type`/`Specific_Use` and work text, validated by reading a sample; units from `Units`; D-008 check (repeated project totals across a project's permits: `Count_` and shared addresses); keep permits inside city limits at issue date (Fort Worth annexes often: compare to Census place boundaries by year, as Durham #206); owner and address fields excluded. Contract tests on a synthetic fixture. | ADU panel (comparison place, 2010–2025), 2–4 unit check vs BPS, V0 | ArcGIS REST (no robots.txt rules on services5.arcgis.com) | Yes | 4–5 h, moderate tokens; ~250k residential rows | **Panel** | Me |
| S1b | **San Antonio permit adapter** (`sa_permits`): both CSVs (2020–2024 and 2025 on) via the `/dataset/…/download` links; ADU = "Res Accessory Dwelling Permit"; combination permits share a permit number (data dictionary), so count each project once (D-008); new single-family from "Res New Building Permit"; no unit field, so 2–4 units come from BPS. | ADU panel (treated, 2023), V0 | CKAN CSV downloads (allowed by robots.txt) | Yes | 3–4 h, moderate tokens; two CSVs of a few hundred MB | **Panel** | Me |
| S1c | **Dallas permit adapter** (`dallas_permits`), **only if Ben accepts the license position** (no license on the dataset; City of Dallas open-data terms to be read once): new construction by `land_use` (single-family, two-family, multifamily); ADU from text. | ADU panel (comparison place, 2018–2025) | Socrata SODA (robots.txt allows `/resource/`, crawl-delay 1) | Yes | 3 h | Panel (medium) | Me, after **Ben** |
| S2a | **StratMap 2026 statewide parcels** (`stratmap_parcels` adapter): read the statewide zip, map `stat_land_use` with the existing PTAD crosswalk (county-specific `loc_land_use` codes where `stat_land_use` is blank), lot size from `legal_area`/`gis_area`, assign each parcel to a place or county remainder by point-in-polygon, apply the D-017 gate (counties under 90% known land use stay on ACS). **TCAD stays the source for Travis/Austin** (`single_source`); StratMap fills Austin's Williamson and Hays parts and every other county. No new dependency if the existing geo stack reads the zip (to confirm). | Eligible parcels (ADU, MM) statewide, data tiers, both panels' exposure | StratMap 2026 zip (**Ben's browser download, 2.7 GB**) | Yes, after download | Adapter + crosswalk gaps: 4–6 h; run 1–2 h unattended | Panel exposure + E2E accuracy (moves most of Texas off the ACS fallback) | Me; **Ben downloads** |
| S2b | **Earlier StratMap vintages** (2019, 2022, 2024, 2025) as extra D-035 anchors: real eligible-parcel counts in more years instead of one roll scaled by ACS. Same adapter. | Denominator history (D-035), both panels | StratMap zips (Ben, 2.0–2.8 GB each, ~10 GB total) | Yes, after download | 1–2 h after S2a | Accuracy | Me; **Ben downloads (optional)** |
| S3 | **Rebuild Texas eligible parcels and tiers** after S2a: one parcel in one jurisdiction; TCAD and StratMap never both used for Austin's Travis part; county totals vs ACS one-unit homes within a stated band; report what moved. | Every scenario's denominator | `lotline` build (exists) | Yes | 1–2 h, low tokens | **E2E** (after S2a) | Me |
| S4 | **ADU rule histories**, places with permit data first (San Antonio: confirm the 2023 row's dates; Fort Worth and Dallas: confirm "none" holds 2010–2025), then the 40 largest: Corpus Christi, Pasadena, McKinney (none vs partial), Killeen (overlay vote outcome), then places 21–40 (Mesquite to Edinburg). One direct fetch per place, no search sweeps; what I cannot open goes to `docs/research/ordinances/tx-adu-lookups-todo.csv` (NC format), largest first, together with the 16 second-coder flags. | ADU panel treatment dates, ADU scenario current rules | City pages; code hosts (municode, ecode360, amlegal return 403) | Partly | 3–4 h, token-heavy if pages are long | Panel | Me, then **Ben** for the todo CSV |
| S5 | **Missing-middle rule dates** for the 40 largest places: when, if ever, 2–4 units became legal by right on single-family lots. Expect most "never" (a row with `unit_cap` 1, so they count as untreated on evidence rather than by default). Check Austin HOME's ordinance text for its effective date (coded as the applications-open date). Same method and fetch cap as S4; shared fetches. Rest into `tx-mm-lookups-todo.csv`. | MM panel treated places (today 2 of 232), MM scenario current rules | Same | Partly | 2–3 h (shared with S4) | Panel | Me, then **Ben** |
| S6 | **Water and sewer impact fees** into `config/fees/tx.csv`: Austin Water ($4,800 water + $2,900 wastewater per service unit from 2023-10-01; city page), Fort Worth water/wastewater impact fees (city page), San Antonio SAWS (robots-blocked: into a fee todo for Ben), Dallas and Houston (one page each). | Fee scenario (local fees instead of $50k where coded) | City pages / PDFs | Partly | 2–3 h | Accuracy | Me, then **Ben** for SAWS |
| S7 | **Ben's manual items** (exact steps in §4). | S2, S4–S6 | Ben | No | 20–30 min browser time | S2a download: **E2E** | **Ben** |
| S8 | **Readiness report** `docs/build/tx-readiness.md`: coverage of every model input across the 1,006 jurisdictions (real / fallback / unknown), places Texas adds to each panel, remaining gaps and what closes each. **No model runs.** | — | Tables on `main` | Yes | 2 h | **E2E** (done-when) | Me |
| S9 | **Refresh docs:** Texas rows of `docs/data_availability.md`; catalog rows (Dallas permits continue to 2025; Fort Worth new; StratMap license CC0 and its download block; San Antonio robots rules); `config/states/tx.yaml` sources; `docs/data_provenance.md` rows for each new source. | Transparency | — | Yes | 1 h | Accuracy | Me |
| S10 | *Houston outcomes from HCAD parcel changes* (WS-TX brief) and *Collin CAD snapshot* | Houston ADU/MM outcomes | HCAD bulk | Partly | Large | Out of scope here | Later |

**Order I'd work it:** S1a → S1b (panel places first) → S4/S5 together, starting with the permit cities → S2a as
soon as Ben's download lands → S3 → S6 → S1c if approved → S9 → S8. One small PR each.

**What Texas would add to the panels if S1 and S4/S5 land:**
- ADU panel: from 1 place (Austin) to 3 (Austin, San Antonio treated; Fort Worth comparison), 4 with Dallas.
- MM panel: still 232 places; treated places rise only if S5 finds dated 2–4 unit rules beyond Austin and
  Houston. I don't expect many: most large Texas cities have not legalised 2–4 units on single-family lots.

## 4. Ben's manual items (exact steps)

**StratMap parcels (S2a, required; about 10 minutes plus download time):**

1. In a browser, open https://data.geographic.texas.gov/collection/?c=1d33dafb-6e9c-40ac-887d-f4577909ed9b
   (Land Parcels, acquired 2026-09-25).
2. Download the statewide file **stratmap26-landparcels_48_lp.zip** (2.7 GB). Direct link:
   https://data.geographic.texas.gov/1d33dafb-6e9c-40ac-887d-f4577909ed9b/resources/stratmap26-landparcels_48_lp.zip
3. Register it:

```bash
uv run lotline manifest register ~/Downloads/stratmap26-landparcels_48_lp.zip --source stratmap_parcels --vintage 2026-09 --url "https://data.geographic.texas.gov/collection/?c=1d33dafb-6e9c-40ac-887d-f4577909ed9b" --license "CC0 1.0 (TxGIO StratMap Land Parcels)"
```

4. Tell me the sha256 it prints.

**Earlier vintages (S2b, optional, ~10 GB):** the same steps for
`stratmap19-landparcels_48_lp.zip` (collection `2679b514-bb7b-409f-97f3-ee3879f34448`, `--vintage 2019-03`),
`stratmap22-landparcels_48_lp.zip` (`a6a703ba-df8b-4d1b-8d4c-ece8ae786505`, `2022-07`),
`stratmap24-landparcels_48_lp.zip` (`d0f7da13-ab09-4994-a16f-d52589e2476e`, `2024-02`) and
`stratmap25-landparcels_48_lp.zip` (`0fa04328-872e-481c-b453-126a74777593`, `2025-06`). The file link pattern
is `https://data.geographic.texas.gov/<collection>/resources/<file>`.

**Ordinance lookups (S4, S5):** Corpus Christi and Pasadena are already written up in
`docs/build/manual-ordinance-lookups.md`; the rest will be in `tx-adu-lookups-todo.csv` and
`tx-mm-lookups-todo.csv` after S4/S5, largest place first.

**SAWS impact fees (S6):** open https://apps.saws.org/business_center/Developer/ImpactFees/ in a browser and
save the current fee chart PDF; register it with `--source saws_fees`.

## 5. Risks

- **StratMap quality varies by county** (catalog: codes and schemas differ, `year_built` sparse). The D-017 gate
  keeps poor counties on ACS; the readiness report will list them.
- **No unit counts in StratMap**: multi-unit parcels are identified by PTAD code (B = multifamily), not units.
  The eligible-parcel rule only needs single-family and vacant lots, so this is acceptable.
- **ADU flags from text** (Fort Worth, Dallas) can include sheds and guest rooms: validate on a sample and
  report the share kept.
- **Comparison places with zero ADUs** add little to D-025 on their own; their value is year effects. Say so.

## 6. Decisions I need from Ben

1. **Approve S1a and S1b** (Fort Worth and San Antonio permit adapters; no new dependency).
2. **Dallas (S1c):** use a dataset with no stated license (City of Dallas open data portal), or skip it?
3. **Do the StratMap 2026 download (§4)**; and say whether you want the four earlier vintages (S2b, ~10 GB).
4. **Approve S4–S6 research** at about one direct fetch per place (no search sweeps).
