# ADU rule coding: lessons register

What six weeks of coding ADU rules (MN, NC, OH, TX, OR; Oct 20 – Nov 16, 2026) taught us, written for the
agent swarm that replaces the ad-hoc agents. Each lesson has an ID; the design (`DESIGN.md`), the agent files
(`.claude/agents/rules-adu-*.md`) and the helper code (`src/lotline/rule_agents/adu/`) cite these IDs.

Sources read: the ADU logbook fragments in `logbook.d/` (the WS-MN/NC/OH/TX/OR rules fragments,
metro-adu-adoption, v9-adu-own-history, ws-adu-rules*, adu-uncoded-rules, adu-coverage-*, nc-adu-rule-rows,
ws-nc-second-coder, ws-mn-13-readiness and others), LOGBOOK LB-068, -071, -096, -097, -098, the HANDOFF
decisions log, `docs/analysis_plan.md` (D-0xx), `docs/build/manual-*.md`, the state data plans and readiness
notes, `docs/research/adu-study-design.md`, and `docs/research/ordinances/` (README, research issues,
second-coder sheets and decisions, corrections, source checks, `or-state-law-check-2026-11-05.csv`). Fragment
names below drop the `logbook.d/` prefix.

## R. Retrieval

| ID | Lesson | Evidence |
|---|---|---|
| L-R1 | The official code publishers block scripts: Municode (Cloudflare challenge, script-only viewer), American Legal's code library (403 even where robots.txt allows), eCode360 (robots.txt disallows ClaudeBot), encodeplus `/regs/` (disallows AI agents), civicweb and destinyhosted (disallow all). Treat them as human hosts from the first refusal. | `2026-10-23-ws-tx-s4-rules`, `-ws-mn-4-adu-rules`, `-ws-oh-4-adu`; ordinances README |
| L-R2 | City sites often refuse scripts too: 25 of 40 NC city homepages answered 403; in the first MN metro run 110 of 162 places stayed unknown, mostly behind blocked hosts. | `2026-10-21-ws-nc-4-rules-research`, `2026-10-20-docs-metro-adu-adoption-records` |
| L-R3 | Hosts that did serve scripts: the Legistar API (St. Paul, Columbus, Cincinnati, Winston-Salem; 1,742 Columbus ordinances in 2 pages), Municode's PDF blob (`mcclibrary.blob.core.usgovcloudapi.net`), American Legal's `files.amlegal.com` PDFs, city-hosted PDFs, and the Wayback Machine (past code versions; pages whose live host refuses scripts). | `2026-10-30-ws-oh-12-columbus-adu-recall`, LB-071, NC rows |
| L-R4 | The Zoneomics mirror allows all agents and carried most of TX places 21–40, but a mirror-only value is at most "partly": it counts as agreed only when someone confirms it on the official code. | `2026-10-23-ws-tx-s4-rules`; README WS-ADU-RULES conventions 2–3 |
| L-R5 | Robots violations happened: three Charlotte UDO PDFs fetched from a host whose robots.txt disallows all crawling (deleted unread). | `2026-10-20-ws-nc-4-adu-rules` |
| L-R6 | Never work around a block. In Medford an agent retried a refused PDF with curl and another user agent; in Scott County one curl with a browser user agent was tried. Both were process incidents. A block becomes a human task, full stop. | README process incidents; `2026-11-12-ws-adu-rules` |
| L-R7 | Scanned PDFs mislead: Cincinnati was first coded from a summary because the enacted text was a scan (Ben's signed copy moved the date); a misaligned text layer gave a wrong League City reading. | LB-071, `2026-10-30-ws-tx-ben-lookups` |
| L-R8 | Size and rate limits: Euclid's code page exceeded the 2 MB fetch cap; Abilene's code is 362,000 characters (use tables lost columns); Bend rate-limited. Fetch the section, not the whole code. | `2026-10-26-ws-oh-7-rules`, `2026-11-05-v9-adu-own-history` |
| L-R9 | Search budgets ran out mid-state (NC's shared 200-search budget; about 24 MN lookups and 9 Oregon counties left undone only for budget). Budget per place, not per run. | `2026-10-20-ws-nc-4-adu-rules`, `manual-adu-adoption-dates.md` |

## D. Dates

| ID | Lesson | Evidence |
|---|---|---|
| L-D1 | Effective date beats adoption date. Record announced, adopted and effective separately. In the 2026-11-13 date check, 9 of 11 same-event disputes moved from the vote to the later effective date. | `oh-lookups-brief-2026-11-01.md`, `adu-rules-source-check-dates-2026-11-13.csv` |
| L-D2 | Never compute an effective date (Columbus "+30 days" gave 12-25, the notice said 12-24; Cincinnati's emergency passage was not its effective date). If only adoption is known, code adoption and say so. | `2026-10-26-ws-oh-7-rules`, LB-071 |
| L-D3 | A code edition, recodification, "current through" or rewrite date is not a first-allowed date. Most NC "no" verdicts were exactly this. A row dated only by a rewrite is never a reform event (`[predates]` rule, HANDOFF 2026-11-01; D-092). | `2026-11-01-ws-nc-second-coder`, `mn-research-issues-2026-11-02.md` |
| L-D4 | Tags carry date quality: `[predates]` (in force at window start; first date unknown), `[earliest-known]` (earliest dated source, not a confirmed first date), `DATE UNCONFIRMED` (no signed ordinance or effective-date record). D-025 reads them; firm-dates sensitivities drop the weak ones. | README; D-025 |
| L-D5 | Dateless or unknown-type rows are dangerous: a row with no date enters the estimator as an early adopter. Skip it (East Bethel, Westerville) rather than guess. | `2026-10-20-ws-mn-5-adu-histories`, `2026-10-26-ws-oh-7-rules` |
| L-D6 | Treatment date can differ from effective date (Austin HOME effective 2023-12-18, coded 2024-02-05 when applications opened; still open). Code the effective date; note the treatment date. | LB-068, README "still open" |
| L-D7 | State law is coded per covered place, never as a statewide row (NC S.L. 2026-59 statewide row was replaced; Oregon SB 1051 per city > 2,500 and county > 15,000, strict inequalities; HB 2001 from 2020-01-01). Signature dates are absent from enrolled texts: `adoption_date` blank. Population tiers near a threshold follow the state's certified estimates (3 Oregon cities were in the wrong tier). | `2026-11-04-ws-or-state-law`, `-ws-or-statelaw-validation`; D-068 |
| L-D8 | Local rules often predate or exceed state law (Portland since 1998, Salem 2017, Medford and Bend dropped parking before HB 2001). Always ask "was the local rule there first, and stricter or looser?" | `2026-11-04-ws-or-local-rules` |
| L-D9 | Dates that belong to another ordinance: Hastings's matched St. Paul's Ord. 23-43; Stillwater's 2017 ordinance was short-term rentals; Medina's 2024 was a height rule; Denton's 2023 an unrelated amendment. The quote must be about ADUs. | `2026-10-20-ws-mn-5-adu-histories`, `2026-11-02-ws-mn-13-readiness` |
| L-D10 | Superseded versions end on the successor's effective date; when a year moves the `reform_id` must be renamed once (renames ran twice and re-renamed a reused id). | `2026-11-13-ws-adu-rules-config`, `2026-10-30-ws-tx-wrapup` |

## F. Fields

| ID | Lesson | Evidence |
|---|---|---|
| L-F1 | "No ADUs" is an explicit row: `adus_per_lot = 0`, `by_right = False`, notes prefix `NO ADU RULE`. It includes non-rentable guest, family or servants' quarters and units allowed only by rezoning, SUP or board case (Fort Worth convention; Orono, New Brighton decided by Ben). | `2026-10-20-ws-tx-5-adu-rules`, `2026-11-16-adu-uncoded-rules`, README Ben calls |
| L-F2 | Uncoded is not "none": 15 NC places read as none only because nobody coded them; 7 blank placeholder rows read as "allowed" and made 4 of D-095's 10 events. Code the pre-reform state too. | `2026-10-20-ws-nc-4-adu-rules`, `2026-11-15-ws-adu-coverage-audit` |
| L-F3 | Blank means not found, never "no restriction" (D-022). Don't infer `adus_per_lot = 1` or owner occupancy from a handout (Bloomington stays blank). | README; D-022 |
| L-F4 | A moratorium is an in-force "no ADUs" row tagged `[moratorium]`, not `status = suspended` (every engine filter drops suspended rows; Blaine read as uncoded). | `2026-11-16-adu-uncoded-rules` (reverses README provisional convention 2) |
| L-F5 | Size: code an absolute cap only. A "% of the house" cap is blank with a note; a "greater of X or Y%" X is a floor, blank (College Station 400, Austin HOME 2,300, St. Paul 800). "Less than 960" codes 960. | README convention 5; `2026-11-13-ws-adu-rules-config` |
| L-F6 | `by_right` is true when any qualifying ADU type is staff-approved; tag `[detached-conditional]` when detached ADUs need a CUP/SUP/IUP (18 rows). By-right was wrongly coded false 11 times in the value check. | README convention 1; source-check values CSV |
| L-F7 | Parking: code the ADU's increment, not the lot total; "1 per bedroom" or a transit waiver is `depends` with a blank number; a citywide zero-minimum parking reform settles a blank ADU parking field (`with_parking`). | value check; `lotline.model.scenarios.adu.with_parking` |
| L-F8 | Lot minimums often apply to detached ADUs only (Ramsey's acre); then `min_lot_sqft` is blank with a note. 13 of 43 value-check changes were `min_lot_sqft`. | value check; README "still open" |
| L-F9 | Coverage: free-text coverage is ignored by the classifier; zone lists read 0.75 vs "citywide" 1.0, so a list naming every single-family district must be cleared to citywide (17 rows) and subset rules need lists (12 rows) (D-021, D-096). | `2026-11-15-ws-adu-coverage-audit`, `2026-11-15-adu-coverage-fix` |
| L-F10 | Overlays and sub-areas: Raleigh's 2 per lot only in Frequent Transit Areas; Hopkins owner occupancy only in N1/N2. Code the citywide rule; put the overlay in notes or `coverage_zones`. | value check; README |
| L-F11 | What is not an ADU: temporary family health-care dwellings (Grant), two-family principal uses, accessory-structure footprint caps (Hopkins 2024), farm manufactured homes. A garage apartment is detached. | MN second-coder decisions |
| L-F12 | Wrong place: same-name towns (Thomasville NC/GA, Newbern TN, Canton OH/GA), a Brooklyn Center link to Brooklyn Park's page, a chapter that was cable TV. Check state and GEOID on every source. | `2026-11-01-ws-nc-second-coder`, `2026-10-21-ws-nc-4-rules-research` |
| L-F13 | County remainders: 18 Ohio county remainders are zoned by many townships and cannot be one rule; code a remainder only where one code governs most homes. | `2026-11-16-adu-uncoded-rules` |
| L-F14 | Tag matching is literal: "not [predates]" or "tag [predates]" in notes created false tags. Notes must never contain a tag string except as the tag. | `2026-11-10-nc-adu-rule-rows`, `2026-11-02-ws-mn-13-readiness` |

## S. Second coding and checks

| ID | Lesson | Evidence |
|---|---|---|
| L-S1 | Second coding caught real errors at every pass: NC 66 rows (8 yes, 44 partly, 14 no); MN 109 rows (8 yes, 92 partly, 9 no); WS-ADU-RULES 153 rows (88 agree, 11 adjudicated, 54 single); the source check overturned 43 values and 35 dates. | second-coder sheets; README |
| L-S2 | Disagreement categories, most to least common: recodification vs first-allowed date; floor vs cap; detached-only lot minimum; by-right vs attached/detached permit path; parking increment vs total; overlay coded citywide; mirror- or summary-only evidence; wrong document or town. | value/date checks; MN/NC decisions |
| L-S3 | A check that could not read the source is not agreement: 74 of 80 TX flagged rows were "could not confirm" and stayed single-coder. Agreement on secondary evidence only is not agreement. | `2026-10-30-ws-tx-wrapup` |
| L-S4 | The second coder errs too (wrong-place citations; overwrote the sheet's columns; one recommendation would have overwritten Ben's own lookup). Its output is a proposal; the verifier re-opens sources. | `2026-11-01-ws-nc-second-coder`, `2026-11-02-ws-mn-13-readiness` |
| L-S5 | Missing versions are the costliest miss (Cornelius allowed → removed 2021 → re-allowed 2023; Rochester 2023 was an expansion, not a first rule). Coders list every version 2016–2025 plus the prior state; an era only one coder found is a disagreement. | README conflicts; value check |
| L-S6 | Same-model second coders are not fully independent (Oregon); a blind coder must not see the first coder's output, and a different model is preferred when available. Ben (D-088): a second coder may not change results much; weigh cost. | `2026-11-04-ws-or-state-law`; D-088 |
| L-S7 | Judgment calls go to Ben, not to the coders: coders settle clear-cut corrections only, with reasons in the notes. | README "decisions made without Ben" |

## H. Human lookups

| ID | Lesson | Evidence |
|---|---|---|
| L-H1 | Ben does not email staff or file records requests. "Records request only" closes as no usable source. | memory note; README |
| L-H2 | Lookups that got done were ranked largest place first, with what is already known and where to start (e.g. "Westerville §1175.06"). | LB-096; `2026-10-26-ws-oh-7-rules` |
| L-H3 | One row per place/question with a small fixed set of cells to fill worked; long free-form sheets did not (the NC, OH and MN to-do sheets were never filled in place; rows closed elsewhere and the sheets were not updated). | `*-adu-lookups-todo.csv` |
| L-H4 | Answers without a link (search-engine summaries, citizenportal.ai) could not be used; every answer needs URL + quote. | `2026-10-20-docs-ben-manual-lookups`, `2026-10-30-ws-tx-ben-lookups` |
| L-H5 | Never-finished lookups pile up (Pasadena, 74 TX rows, Killeen/Lewisville/Denton ordinance numbers, 10 Oregon counties, 9 manual_needed pages). Each task needs an estimate and a "done when". | `2026-11-01-ws-tx-handoff`, README |
| L-H6 | Downloaded PDFs go under `~/lotline-data/manual/...` with sha256 in a manifest; never in the repo. | `2026-11-02-ws-mn-13-readiness`; `manual-ordinance-pdfs-batch1.md` |

## O. Other must-dos

| ID | Lesson | Evidence |
|---|---|---|
| L-O1 | Holdouts: code rules of holdout places, but open no permit counts, dashboards, staff reports with activity numbers, refits or `reports/`. Leaks came from search snippets (Bend), a staff report (St. Paul) and ordinance findings with counts (Portland). | `2026-11-04-ws-or-local-rules`, README incident, `2026-11-05-v9-adu-own-history` |
| L-O2 | No model, engine or scenario runs in rule-coding threads. | `2026-11-10-nc-adu-rule-rows`; memory |
| L-O3 | Rows are proposals: written to a CSV, applied by a dated, idempotent script after Ben accepts. | `2026-10-30-ws-tx-wrapup`; README |
| L-O4 | After rows land: check `current_rules` at several dates, rerun the coverage audit, confirm every coded place has a live rule at the 2025 origin. | `2026-11-16-adu-uncoded-rules` |
| L-O5 | Cost: 12.5M subagent tokens for 162 MN places found only 52 statuses. Rank by predicted impact (population, eligible lots) and stop early on blocked places. | `2026-10-20-docs-metro-adu-adoption-records` |
| L-O6 | Verbatim quotes of at most 25 words with a section number; cite only URLs actually opened; https sources (Wayback https for http-only pages). | `2026-11-12-ws-adu-rules`, `2026-11-13-ws-adu-rules-config` |
