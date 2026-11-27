## LB-xxx · 2026-11-08 · WS-APP · One file per state, loaded when picked

**Question answered:** Can the app page carry every state if each one gets a precomputed run? Ben (2026-11-08) agreed it should load each state's results on demand rather than embed them all.

**Outputs**
- `src/lotline/app/build.py`: the page embeds only each state's `meta` and the path of its file. `build_app` writes each full bundle to `reports/app/states/<st>.js` as `LotlineState(<json>);` and removes stale state files. The new helpers are `state_file()` (it accepts two-letter codes only) and `state_script()` (escapes `</`).
- `src/lotline/app/template.html`: `loadState()` adds a `<script src>` the first time a state is picked. `show()` is async, the latest pick wins if files arrive out of order, and a missing file shows a plain message with the rebuild command.
- `scripts/build_app.py` docstring; `tests/app/test_build.py`: the fixture's bundle round-trips through its state file, stale files are removed, bad codes are refused, and a state file can't close a script tag.

**Why:** at the configured 1,000 draws, a bundle with all seven scenarios is about 2 MB (the fixture's draw rows are about 290 bytes each). With 51 states, embedding everything would make the page about 100 MB. The state files are scripts rather than JSON because `<script src>` loads from disk where `fetch` does not, so the page still needs no server.

**What Claude did and how it was checked:** Claude Code (Opus 5.5, WS-APP instance) made the change. Checked by `tests/app` (36 passed) and `compliance_check.py`. In a browser over http with four synthetic bundles, each state file loaded once when picked (network log), two quick picks in a row ended on the later one, and a deleted state file showed the message while other states still loaded. Opening from `file://` was not driven by the browser tool.

**CodeQL follow-up:** #329 merged with two CodeQL `js/xss-through-dom` alerts (a non-required check), flagging map lines that put values from the page's embedded JSON into HTML unescaped (tier numbers and colour-token names). Those values come from our own build, so they were not exploitable, but they are now escaped, together with the older alert at the factor table (`percentile` cells). Claude merged #329 without noticing the non-required failure. From now on, merges check every check, not only the required ones.
