### LB-NNN · 2026-11-18 · rule-agents · Which Wayback capture did a fetch actually read?

**Question.** The shared rule-agent fetch (PR #480) dropped a feature the old ADU fetcher had: recording the
URL that actually answered. A year-only Wayback link (`/web/2023/<url>`) redirects to the nearest capture,
which can be from another year, so a coder could date an ordinance by the wrong copy.

**Outputs.**
- `src/lotline/rule_agents/common/fetch.py`: `FetchResult.final_url` and `.wayback_ts`; `wayback_ts(url)`.
  The URL that answered is captured with a response hook on the HTTP client (removed afterwards), so the IO
  layer (`lotline.io.http`, WS-CORE) is unchanged.
- `src/lotline/rule_agents/common/docstore.py`: `DocRecord.served_url` and `.wayback_ts`, so a later
  store hit from any swarm reports the same capture.
- `docs/build/rule-agents/CORE.md`: fetch row updated.
- Test: `test_a_year_only_wayback_link_records_the_capture_actually_served` (2023 link served a 2022 copy).

**How Claude did it and how it was checked.** Claude (Opus 5.5) wrote the change and the test with a mock
HTTP transport that redirects; the rule-agent tests pass, ruff is clean, and the compliance check shows
0 FAIL. Raised by the ADU session while it moved onto the shared core (#471).
