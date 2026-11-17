# Fees rule agent: lessons register

*2026-11-17. What five states of fee coding (Oct 20 – Nov 17, 2026) taught us, written for the fees rule agent swarm
(`DESIGN.md`). Each lesson names where it came from and what the swarm does about it (→).*

**Sources read:** fee logbook fragments (`logbook.d/2026-10-20-ws-core-fees-table`, `-citations-fees`,
`2026-10-26-ws-tx-s6-fees`, `2026-10-30-ws-tx-fee-rule`, `2026-11-04-ws-or-fees`, `2026-11-09-ws-fees-*` (coverage
MN/NC/OH/TX, permits, plex-utility, phases 0–2)), `config/fees/README.md`, the five `config/fees/*.csv`,
`docs/build/manual-fee-lookups.md`, `docs/build/manual-ordinance-lookups.md`, `tx-`/`nc-fee-lookups-todo.csv`,
the ordinances README (pipeline method, second-coder results), the TX corrections sheets, the state readiness docs,
the fees causal diagram, and decisions D-034, D-065, D-066, D-069, D-073 in `docs/analysis_plan.md`.

## 0. Where the fee table stands (the baseline the swarm must beat)

| State | Rows | Places | Rows with a verbatim quote | Rows checked by a second coder (`verified_by`) |
|---|---|---|---|---|
| MN | 248 | 19 | 186 | 0 |
| NC | 307 | 20 | 241 | 0 |
| OH | 110 | 5 | 0 | 0 |
| OR | 115 | 4 | 115 | 29 |
| TX | 148 | 11 | 72 | 0 |
| **All** | **928** | **59** | **614 (66%)** | **29 (3%)** |

The biggest single weakness is not missing fees but **missing evidence**: a third of rows have no quote and 97% have
never been re-opened by an independent checker. The swarm's first job is to make every row checkable.

## 1. Retrieval: downloads, robots and bot walls

| # | Lesson | Source | → Swarm rule |
|---|---|---|---|
| R1 | Many city and utility sites answer scripts with HTTP 403 even for `robots.txt` (Fort Worth/Akamai, Houston Permitting Center/Cloudflare, durhamnc.gov, carync.gov, greensboro-nc.gov, cityofws.org, highpointnc.gov, eugene-or.gov, akronohio.gov, library.municode.com, codelibrary.amlegal.com). They usually work in a browser. | TX S6, NC fee to-do, OR fees, OH coverage, manual-ordinance-lookups | A 403 or challenge page on a host stops all automated reading of that host for the run. Emit a human task; never retry with another user agent. |
| R2 | Twice an agent was refused and then retried with plain `curl` and a browser user agent (Medford: it worked; Scott County: Cloudflare 403). That is a workaround of an access control, which the project rules forbid. | ordinances README, ADU rules notes | Retrieval uses only `lotline.io.http` (one fixed, honest user agent). Agents are told in writing that changing the user agent is a stop condition, not a fix. |
| R3 | `robots.txt` disallow is common on code hosts (SAWS catalog, Corpus Christi enCodePlus `/regs/` for AI agents). | TX fee to-do, manual-ordinance-lookups | Check `robots.txt` before the first request to a host (`fees_tool robots`); a disallow becomes a `robots_disallow` human task immediately. |
| R4 | In Cowork sessions the session proxy blocked direct downloads, so agents read pages through a web-fetch summariser. The summariser paraphrases and reflows tables, so **no quote could be matched word for word** (all 110 Ohio rows, most 2026-11-09 TX/NC rows). Columbus's "contract-area" column was read from a reflowed table and still needs checking. | 2026-11-09 coverage MN/NC/OH/TX | Amounts come only from a file downloaded into `LOTLINE_DATA_DIR` (logged in the manifest) or from a page the agent read directly. A value read only through a summariser is `quote_status = summariser` and can never be `agree`; it goes to the second coder or a human. |
| R5 | When a local copy existed, quote checks worked: 53 permit rows matched word for word against local PDF text; the plex-utility pass had a separate agent re-fetch every quote. | permits, plex-utility | `fees_tool quotecheck` matches a quote against the saved text (whitespace and dash/quote normalised). Only a match gives `quote_status = verbatim`. |
| R6 | Parallel downloads got the project's network blocked by census.gov (2026-10-19). | `lotline/io/http.py` | One request at a time per host, minimum interval, at most 12 requests per place per run. |
| R7 | Ben has local copies the agents can't fetch (`~/lotline-data/manual/nc_fees/`). | permits, plex-utility | Before fetching, the scout looks for a local copy under `LOTLINE_DATA_DIR/manual/`. |
| R8 | Wayback copies rescued several ADU rules where the live site refused scripts, but Wayback's copy may be an older schedule. | ordinances README | Wayback is allowed as evidence of a dated version only (its capture date is the evidence date). It never stands for "current" without a human check. |
| R9 | Ben will not email staff or file records requests. | memory note, 2026-11 | A source that is only available on request closes as `no_usable_source`; the swarm never emits a "call / email / request" task. |

## 2. Finding the schedule and parsing it

| # | Lesson | Source | → Swarm rule |
|---|---|---|---|
| P1 | Fee schedules hide in **adopted budget books** (Cary FY2026 budget appendix, Austin CBQ answers), **rate ordinances** (Portland Water Bureau Ord. 192183 Exhibit A), **utility "rules and regulations"** (El Paso Water Rules No. 7, WSFCU Utility Rules), **resolutions** (Bend Res. 3487, Arlington Res. 26-151) and **code chapters** (Toledo Ch. 1307, Columbus City Code 1137). A search for "fee schedule" finds the permit fees and misses the utility charges. | coverage passes, OR fees | The scout searches per **levying body and component**, with a fixed list of document kinds (fee schedule, rate ordinance, utility rules, budget appendix, impact-fee ordinance/CIP, SDC methodology). |
| P2 | Valuation tables ("$A for the first $L plus $r per additional $1,000") are the most common permit basis; brackets must contain the prototype's valuation or the row is not priced. | `ordinance_records.py` rule 1 | Extraction records the bracket's numbers, not the computed fee; the helper prices it at the prototype. |
| P3 | Shares of other fees (plan review = 65% of the permit fee; MN state surcharge 0.0005 × valuation) only make sense next to the fee they share. | `ordinance_records.py` | Record `basis_kind = share_of` with the parent item's id; the helper prices it after the parent. |
| P4 | Reflowed or multi-column tables mislead (Columbus contract vs non-contract columns; SAWS by elevation area; Portland meter-size rows). | OH coverage, TX S6 | The reader quotes the column header and the row label with the number. The second coder reads the table blind. |
| P5 | Scanned PDFs (Buncombe County) can't be read by text tools. | permits | A scanned PDF is a `scanned_pdf` human task unless the reader can read the page image itself; the quote is then marked `image_read`, never `verbatim`. |
| P6 | Many items were dropped because they had no quote (99 of 266 in batch 1), or were totals, escrows and minimums. | ws-core-fees-table | Escrows, deposits, minimum fees and totals are recorded as `excluded` items with a reason, so a later run doesn't re-find them. |

## 3. Taxonomy: what kind of fee is it, and who charges it

| # | Lesson | Source | → Swarm rule |
|---|---|---|---|
| T1 | Names don't settle the component. Texas "water impact fees" and "capital recovery fees" pay for water/sewer capacity and are coded `water_sewer`, not `impact`; Oregon "SDCs" are split by what they fund (water/sewer SDC → `water_sewer`; parks/transportation SDC → `impact`); Met Council SAC is `water_sewer`; park dedication cash-in-lieu is `impact`. | tx.csv, or.csv, mn.csv | Component = **what the fee pays for**, decided from a fixed table (`classify.py`); `fee_type` keeps the source's own name. A disagreement between the agent's label and the table is flagged, not overridden. |
| T2 | The levying body is often not the city: county (Cabarrus issues Concord's permits; Mecklenburg LUESA for Charlotte; New Hanover for Wilmington), utility (Charlotte Water, SAWS, EWEB, GCWW/MSD, NEORSD, Cleveland Water, CFPUA, WSFCU), regional (Met Council SAC), special district (Bend Park & Recreation District), state (MN 326B.148 surcharge; OR 12% surcharge; OH ORC 3781.102). | coverage passes, permits | The enumerator lists every body that can charge a new home in a place before any search. Rows stay under the place's GEOID (as today) with the body in `fee_type` and `notes`. |
| T3 | A place that has only the regional charge coded (Eagan, Eden Prairie: SAC only) looks "coded" for water/sewer, so the engine stops filling it and the total falls (Eagan $6,931). | MN coverage | The swarm reports per component whether **every** expected body was coded. A component with a missing body is listed as `partial` in the run report; the human task names the missing body. |
| T4 | Conditional fees (CUP, rezoning, variance, subdivision-only park dedication, front-footage where never assessed) are not paid by a typical infill home. | fees README, MN rows | Coded with `amount_per_unit_usd` blank and the reason in notes, as now. |
| T5 | An explicit 0 means "charges nothing" (Dallas: no utility impact fee; Portland and Salem ADU SDC waivers). A missing row means "unknown, fill from the median". Confusing the two moves totals a lot. | manual-fee-lookups, D-065 | A 0 needs a quote saying so (exemption, waiver, "no impact fee"). Otherwise no row. |
| T6 | Fee exemptions and waivers are themselves reforms (Portland's 2025–28 SDC exemption, Eugene's 100% ADU transportation reduction). | OR fees | Record them as `reform_candidates` for the reforms table; fee rows carry the full schedule. |

## 4. Dates and history

| # | Lesson | Source | → Swarm rule |
|---|---|---|---|
| D1 | `year` has meant "the year the schedule took effect" (FY2027 starting 2026-07-01 → year 2026). Fiscal years start Jul 1 (NC, OR, most utilities) or Oct 1 (TX cities). | fees README, nc.csv, tx.csv | `fees_tool` derives `year` and `effective_date` from the stated effective date, else the fiscal-year start, else the schedule label, and writes which in notes (`date_basis`). |
| D2 | Adopted ≠ effective (Apple Valley adopted 2025-11-25, effective 2026-01-01; Fort Worth's ordinance adopted 2025-06-10 with steps on 2025-10-01 and 2026-10-01). | mn.csv, TX corrections | Extraction records `adopted_date` and `effective_date` separately; the row uses effective. Step schedules are one row per step. |
| D3 | Older schedules can stay in force next to newer rows of the same component (Austin's 2023 impact fees; Bend P&RD's FY25-26 park SDC). The engine's newest-year rule dropped them until `in_force_through` (#247). | D-066 | When a body's schedule is older than another body's row for the same component, the reader confirms whether it is still current and sets `in_force_through`. |
| D4 | Plat-date cohorts (Austin, Fort Worth) and area/basin tiers (SAWS) need one central row and a range (Ben's 2026-10-30 rule). | tx-fee-rule | Encoded in `groups.py`, tested. |
| D5 | Some pages carry no effective date (Columbus sewer page). | oh.csv | `effective_date` blank, `date_basis = read_date`, flagged for the second coder. |
| D6 | Only current schedules were coded almost everywhere ("current schedules only, no 2017 vintage"). History is the hardest part: old schedules live in prior budget books and Wayback. | OR fees, MN rows 2016–2027 | History is a separate, optional pass (`--history`), budgeted per place. Default runs code the current schedule. |
| D7 | Inflation indexing: some impact fees step annually by an index. Lotline converts every row to 2025 dollars with CPI-U itself (D-066). | D-066 | Code the schedule's own dollars in `dollar_year`; note the indexing clause if the schedule has one; never pre-deflate. |

## 5. Normalising to a prototype home

| # | Lesson | Source | → Swarm rule |
|---|---|---|---|
| N1 | Prototypes are fixed in `config/params/proforma.yaml`: house 2,150 sq ft; duplex and fourplex units 1,000 sq ft; ADU 800 sq ft; $165/sq ft hard cost (house valuation $354,750). The OR pass used its own (2,000 / 800 / 1,000) and Eugene used 2,000 sq ft. | OR fees, permits | The helper reads prototypes from `proforma.yaml` only; any other size is an error. |
| N2 | Per-meter fees: one meter per unit is central; the master-meter case is the low end (D-069). | D-069 | `prototype.per_unit()` takes `meters` and `master_meter` and returns central/low/high. |
| N3 | Per-LUE/EDU/SAC-unit fees need the units per dwelling (SAC: house 1; St. Cloud fourplex 0.75; SAWS master-metered plex 0.5 EDU). | plex-utility | `units_per_dwelling` is a required extraction field with its own quote. |
| N4 | Per-bedroom (Brunswick), per drainage fixture unit (Portland BES), per trip (Eugene transportation) fees need a stated assumption. | plex-utility, OR fees | Allowed only with the assumption in `notes` and a range; the prototype table lists the default bedrooms (house 3, plex unit 2, ADU 1) and fixtures for review by Ben. |
| N5 | Fourplexes usually fall on the commercial (IBC) valuation table; per unit they can pay more permit fee than a house (Arlington, Fuquay-Varina). | permits, TX coverage | Building type is a required field; the reader codes SFD, U2, U3_4 and ADU separately whenever the schedule distinguishes them. |
| N6 | `OTHER` rows apply to every type but are priced at the house prototype; a type row for the same component replaces all `OTHER` rows of that component (so Met Council SAC as `OTHER` blocked city plex rows). | plex-utility, D-066 | The validator warns when a place mixes `OTHER` and type rows in one component. |

## 6. What second coding caught

| # | Lesson | Source | → Swarm rule |
|---|---|---|---|
| S1 | Most second-coder findings were about **dates** (wrong effective date, adoption vs effective, missing earlier version) and **which version of the text** was read (current text read as historical). | MN/NC/TX second-coder sheets, ordinances README | The second coder re-derives dates independently and must state which version of the document it read. |
| S2 | Values resting on a third-party mirror, a draft, a city guide or news were capped at "partly". | ordinances README method | Same cap for fees: only an adopted schedule, ordinance or the levying body's own rates page can give `agree`. |
| S3 | A blind re-read caught column mix-ups and paraphrased quotes; a non-blind check tends to confirm. | plex-utility, ADU browser check (74 confirmed, 2 contradicted) | The second coder gets only (place, body, component, building type) and the source list, never the first coder's values. |
| S4 | Judgment calls (which meter, which tier, whether an ADU pays) were settled by Ben, not by coders. | D-069, tx-fee-rule, Eugene D-066 | The reconciler resolves only arithmetic or transcription slips; any judgment goes to Ben's decision list. |

## 7. Process lessons

- **Dated, idempotent scripts with a rows JSON** (`coverage_fees_*_2026_11_09.py` + `_rows.json`) worked well:
  re-runnable, reviewable, validated with `load_fees` before writing. → The swarm writes a rows file and a
  proposed CSV in a run folder; a person merges into `config/fees/<st>.csv` through a PR.
- **Coverage first by population** moved state totals most (manual-fee-lookups priority 4). → Places are
  processed largest first.
- **Human lookups were vague** ("open the blocked sources") and lists drifted in prose. → One task per
  (place, body, component), with the exact fields to fill and when it counts as done (`HANDOFF_FORMAT.md`).
- **Token cost:** coverage passes ran 4–6 research subagents per state; most tokens went into re-reading long
  PDFs. → The reader extracts once into an items file; the second coder reads only the cited pages.
