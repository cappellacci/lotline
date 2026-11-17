# MM swarm dry run: Minnesota, 4 places (2026-11-17)

Run `dryrun-2026-11-17`, folder `$LOTLINE_DATA_DIR/rule_agents/mm/MN/dryrun-2026-11-17/` (outside the repo;
snapshots under `raw/rules_mm/dryrun-2026-11-17/`, logged in `manifest.jsonl`). Places: Minneapolis, Rochester,
Brooklyn Park, St. Louis Park, all already coded in `config/reforms/mn.csv`. St. Paul was left out because it is
the V5 holdout. No engine, scenario or model script was run; no permit or outcome data was opened.

**How it was run.** The `rules-mm-*` agent files were written in this session, so they were not yet loaded as
agent types. Each stage ran as a general-purpose subagent told to follow its agent file word for word, on the
file's model: scout haiku, coder A sonnet, coder B opus, reconciler sonnet, verifier haiku. Rochester and
Minneapolis had two blind coders; Brooklyn Park and St. Louis Park were single-coder, which tests that path and
saves tokens. Coders were blind to existing coding: the brief omits existing reform IDs, and agents were told
not to open `config/reforms/`, `docs/research/ordinances/` or `places.csv`.

## Result against the coded rows

On what the engine reads (`compare.py`: the cap in force on 1 July of each year 2010–2026, and the first year
it rises), **all 4 places match**.

| Place | Swarm row | Coded row | Field differences | Who is right? |
|---|---|---|---|---|
| Minneapolis 2743000 | cap 3, by right, adopted 2019-11-08, effective 2020-01-01, `dated`, prior cap 1; zones **R1;R1A**; `single_coder` | same cap and dates; zones **R1;R1A;R2;R2B**; `agree` | Zones: the swarm left out R2/R2B as two-family districts (LESSONS M-4); the coded row includes them. | **A decision for Ben.** R2/R2B went from 2 to 3 homes, and M-4 says that is not MM. If kept, the coverage share changes. |
| St. Louis Park 2757220 | cap 3, by right, N-1;N-2, adopted 2025-03-03, effective **2025-03-18** (computed from the draft's §90), `unconfirmed`, confidence low | effective **2025-03-28** (published date) | Effective date. Both are before 1 July 2025, so the event year is the same. The prior cap was handed off. | Coded row (its date is the published effective date, from the signed ordinance). The swarm correctly refused to call its computed date `dated`. |
| Rochester 2754880 | none row (cap 1 after reconcile), R-1, adopted 2022-09-07, effective 2023-01-01; the **verifier blanked the cap** | none row, cap 1, R-1, same dates, `[predates]` | The verifier was over-strict: a none row's evidence is an empty table cell, and it rejected the legend quote. It also counted "Adoption Draft" on the cover of a compiled code as a draft. | Coded row. The agent prompts were fixed (below). With a blank cap the engine reads cap 1 anyway, so the event reading is unchanged. |
| Brooklyn Park 2707966 | none row, zones **UR;R-1;R-2**, effective 2024-07-29 (council approval of the 2024 code), `earliest_known` | none row, zone **R-1**, 2010-01-01 placeholder | Zones and date (a none row is a control, so no effect on events). | **Worth a look.** The 2026-11-02 second coding narrowed the coded row to R-1 because R-2 allowed duplexes. The swarm read the 2024 Land Usage Code, where the two-family row is "NP" in UR, R-1 and R-2. Either the 2024 code changed R-2, or one reading is wrong. |

Agreement between the two blind coders, where both ran:
- **Rochester:** same rule. Two minor diffs (adoption date blank vs 2022-09-07; `earliest_known` vs `dated`), settled from coder B's city-page quote.
- **Minneapolis:** coder A was blocked everywhere (LIMS, Municode) and coded nothing rather than code from news. Coder B found a Wayback copy of the city's "Recently Adopted" page and coded the rule. That is `single_coder`, as LESSONS S-2 requires.

## Hand-offs

13 tasks in `out/human-lookups.csv` / `.md`:

| Blocker kind | Tasks |
|---|---|
| ambiguous source | 4 |
| dead link | 3 |
| robots.txt disallows | 2 |
| 403 / bot wall | 2 |
| code host (Municode, American Legal) | 2 |

11 are priority 1 (they hide a date or a cap). Each has a direct start URL, a host tip, a look-for line naming
the ordinance or table, and closed answer columns. The Minneapolis LIMS task, for example, asks for ordinance
2019-00217's council action, mayor approval and publication dates, and the adopted Table 546-1 rows for R1/R1A.

## What the dry run caught in the swarm (all fixed in this branch, with tests)

1. **Classifier false positive:** a St. Louis Park city page loading an Akamai script looked like a bot wall.
   The page was also truncated at 20 KB, before its body text. Challenge words now count only in visible text,
   read from the whole page (`test_classify_ignores_challenge_words_in_scripts`).
2. **Quote check against raw HTML:** Minneapolis's date quote spans markup, so `quote` failed and the verifier
   blanked the dates. Quotes are now matched against visible text (`test_verify_quote_across_markup`).
3. **Verifier blanked a required date,** which made the file invalid. The verifier now keeps the effective date,
   sets `date_basis` to `unconfirmed` and adds a hand-off.
4. **Draft rule too broad:** it fired on a city "recently adopted" page and on a compiled code's cover. It now
   applies only to date evidence from ordinance or code documents.
5. **None-row evidence:** a none row is evidenced by an empty cell. Coders now quote the row and legend and name
   the cell; the verifier accepts that.
6. **Prior cap blocked:** St. Louis Park's predecessor code was unreadable, and `check` refused the event. A
   Blocker naming `prior_cap` now satisfies the check (`test_prior_cap_check`).
7. **Two none rows with different dates** were "major" diffs. They are now minor, since a none row is never an
   event (`test_reconcile_none_rows_dates_minor`).
8. **No blocker kind for timeouts,** so the reconciler mapped a Laserfiche timeout to `not_found`. Added
   `unreachable`.
9. **Sidecars:** agents may not write under `raw/`, so PDF text sidecars moved to `<RUN>/text/`.
10. **`doc_id` was missing from fetch output** (an edit hit a reformatted line); fixed.
11. **Compare:** "no event" vs "no event" was counted as a mismatch; fixed (`test_compare_two_none_places_match`).
12. **Stray tool calls:** two haiku subagents tried a session hand-off tool (denied, no effect). The registered
    agent files restrict tools to Read, Write, Bash and WebSearch, so this cannot happen once they are loaded.

## Politeness

Every fetch went through `python -m lotline.rule_agents.mm fetch` (robots first, one try). Refusals were
recorded, not retried:
- Municode: robots disallow.
- American Legal: robots disallow.
- Minneapolis LIMS: robots.txt answers 403.
- Rochester: an alerts page answered 403; Laserfiche timed out.

No records requests, emails or forms.

## Cost

About 1.5M subagent tokens for 4 places, roughly 370k per place:

| Stage | Agents | Tokens |
|---|---|---|
| Scouts | 4 | ~340k |
| Coders | 6 | ~700k |
| Reconcilers | 2 | ~150k |
| Verifiers | 3 | ~270k |

That is above the 150k-per-place estimate in DESIGN §8. Each subagent spends ~70k tokens just loading context;
agent types with restricted tools would cut that.

Missing PDF tooling cost time: coders used Swift PDFKit and system pypdf ad hoc because poppler and pypdf are not
installed. A 100-place state would cost ~35M tokens at this rate. A single-coder first pass with the second
coder only on dated events would be ~15M.

## Not run

- Verifier on St. Louis Park (single-coder, low confidence).
- The optional browser stage.
- Ingest of real answers (covered by tests only).
