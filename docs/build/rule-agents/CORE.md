# Rule agents: the shared core

*2026-11-17. Built from the three swarms' `SHARED_CANDIDATES.md` (MM PR #469, fees #470, ADU #471). Ben's
calls that day: missing middle is the master copy because it came first; build one store for primary
documents; cut token use in searching and coding.*

The three swarms (`/rules-mm`, `/rules-adu`, `/rules-fees`) each research one rule category for one state.
Everything that is not about the category itself lives once, in `src/lotline/rule_agents/common/`, with one
command line: `uv run python -m lotline.rule_agents --help`. MM uses it now; ADU and fees move onto it after
their PRs merge (their sessions know their code best).

| Module | What it does | Came from |
|---|---|---|
| `docstore` | One store of primary documents for all swarms (below) | new; MM §10, ADU §0, fees §11 |
| `fetch` | Store first; known refusals; robots.txt for our and Claude's tokens; one try; never another user agent | MM `fetch.py` |
| `access` | Blocker classifier and code-host table (Municode, American Legal, eCode360, Legistar…) | MM `access.py` |
| `evidence` | `Evidence` (+ `doc_id`, `page`, `quote_status`), `Blocker`, `max_confidence` rule | MM `findings.py` + fees |
| `text` | What a reader sees in HTML; quote check (with pypdf word-split pass); page of a quote | MM + ADU |
| `excerpts` | Short page-cited passages for coders, by category keywords | new (token cut) |
| `budget` | Per-place limits and a spending ledger | new (token cut) |
| `handoff` | Browser tips, closed results, acceptance rule, held documents, saved-file intake | MM `handoff.py` |
| `dates`, `pdftext` | Date parsing and date-basis tags; PDF text by page | MM |

## The document store

**What it answers.** Which documents do we hold for this place, its county or its state? Which page says
this? Which coded values rest on this document? What did this fee schedule say before? Did a person already
save the file the agent could not reach?

**Identity.** A document is its bytes; its id is their sha256. The same county code fetched by the ADU swarm
for one town and by the fee swarm for another is one document, fetched once, extracted once. When a URL's
bytes change, the new document `supersedes` the old; both stay, and `history` walks the chain (fee schedules
by year, code editions).

**Layout** (under `LOTLINE_DATA_DIR`, never in the repo):

```
raw/rule_docs/<YYYY-MM-DD>/<host>/<url-hash><ext>   downloads, through lotline.io.http.fetch (manifest line)
raw/rule_docs_manual/<YYYY-MM-DD>/<file>            files a person saved, through DataStore.register
rule_docs/blobs/<sha[:2]>/<sha><ext>                hard link to the bytes: one blob per document
rule_docs/blobs/<sha[:2]>/<sha>.txt                 text, "=== page N ===" markers
rule_docs/index.jsonl                               append-only document events; latest wins, lists grow
rule_docs/citations.jsonl                           which coded value cites which document and page
rule_docs/blocks.jsonl                              refusals (403/WAF, robots, logins) and when
rule_docs/inbox/                                    drop folder for files a person saves by hand
```

**Record** (folded from the index): `doc_id`, `urls[]` (each with its retrieval date), `title`, `publisher`,
`doc_type` (code_section, code_full, ordinance, draft, minutes, agenda_packet, staff_report, fee_schedule,
rate_ordinance, budget_book, state_law, city_page, mirror, news, other), `jurisdictions[]` (GEOIDs it governs),
`states[]`, `categories[]` (swarms that used it), `pages`, `text_status` (text / scanned / none),
`draft_markers`, `label`, `adopted_date`, `effective_date`, `supersedes`, `added_by` (run or `human:<initials>`),
`may_contain_outcomes` (holdout guard), `withdrawn` (reason), `notes[]`.

**Rules.** Append-only files written under a lock, so swarms that run at the same time never clash and none
assumes another has run. Nothing is deleted; a wrong document is withdrawn with a reason and `withdraw` lists
every citation to re-check. A place GEOID does not contain its county, so `find --geoid G --county C` takes the
county from `places.csv`. State law (tagged with the two-digit state GEOID) matches every place in the state.

**A person in the loop.** The lookup sheet lists the documents already held for each place, so nobody
downloads them again. A person who opens a blocked page saves the file into `rule_docs/inbox/` and writes its
name in `saved_file`; `ingest` registers it (manifest + blob + text) as `human:<initials>` and the evidence
cites its `doc_id`. Older hand-saved folders can be imported once with `docs backfill DIR`.

**For judges.** `docs/research/rule_docs_catalog.csv` is committed and holds no document text: id, URL,
retrieval date, title, type, places, categories. Anyone can re-fetch a document and check it by its hash.

**First use.** The three Sunfish Lake PDFs that had been committed under `docs/research/ordinances/source-pdfs/`
(against the no-committed-data rule) were registered in the store and removed from git.

## Cutting token use

The 2026-11-17 dry runs spent ~370k tokens a place (MM) and ~200k (ADU): 20–35M for a 100-place state. Where
it went: each subagent loading ~70k of context; coders reading whole code books and packets; second coders on
every place; searching for sources that were never online.

| Change | Where | Expected effect |
|---|---|---|
| Store first: a document any swarm holds costs no fetch and no robots read | `fetch.get`, scout step 0 | Second and third categories in a state reuse the first's documents |
| A host that refused any swarm in the last 30 days is not asked again | `DocStore.recent_block` | No repeat bot-wall attempts (also the politeness rule) |
| Coders read page-cited passages, not documents | `excerpts`, `outline`, `docs text --page` | Sunfish Lake code book: 655k characters whole vs ~3k of ADU passages, with the 1,200 sq ft cap in them |
| Quote checks by machine, by page, no network | `docs quote` / `mm quote DOC` | Verifier reads only failing pages |
| Second coder only for events, below-high confidence and a 1-in-10 audit | `mm select-b` | ~40% of tokens in the ADU dry run went to the second coder |
| Per-place budget; when spent, open fields become `budget_spent` tasks for a person | `budget`, `ledger status` | Caps the long tail of searching for sources that are not online |
| Subagent prompts carry only RUN, GEOID, COUNTY | `/rules-mm` | Less pasted context |

Not done here, for the next dry run to measure: trimming each agent file to a one-page rules card and
restricting tools per agent (the ~70k fixed load per subagent).

## Passages: how `excerpts` picks text

1. Split the stored text into pages, each page into blocks (paragraphs; section headings where a page is one
   block; long blocks cut with overlap).
2. Score a block by weighted category words (`KEYWORDS`: "accessory dwelling" 3, "duplex" 3, "impact fee"
   3, …; supporting words 1–2), counted as whole words; date and enactment words add to a block's score only
   when it has a strong topic word. "Parking" or "square feet" alone is not ADU evidence.
3. A strong block brings the next five blocks on its page at a slightly lower score, so a heading
   ("1207.12 ACCESSORY DWELLING UNITS") comes with its lettered standards ("D. Maximum size … 1,200 square
   feet").
4. Keep the best blocks above 30% of the top score until the character budget (default 6,000), in page
   order, each tagged `[doc p.N]`.

The keyword lists are search aids, not model parameters: they change which passages a coder sees first,
never a coded value, and a coder can always ask for any page.

## Moving ADU and fees onto the core (after their PRs merge)

Each session replaces its own copy with `common`: fetch and robots (`fetch.get(url, "<cat>", run)`), the
classifier, quote checks, `Evidence`/`Blocker` (keep category fields in the finding model), the shared
hand-off pieces (keep the category's answer columns), and reads documents through `excerpts`. ADU's first-pass
scoring and MM's `select-b` should become one shared rule once both use `max_confidence`. The fee swarm's
schedule history uses `supersedes` and `history`.
