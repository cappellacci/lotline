### LB-XXX · 2026-11-17 · WS-APP · Method card names the headline's units

**Question:** Does the Model tab's Method card describe the number the headline shows?

**Output:** `src/lotline/app/template.html` (Method card, "The question").

**What happened:** The missing-middle gut-check (Missing Middle Analysis session, 2026-11-17) found the card asked how many more homes would be *permitted*, while the headline counts net new homes (completions after teardowns and displacement, about 39% of extra permits for missing middle). Ben approved the fix. The card now says "gain" and defines net new housing. The second proposed fix (a 2031 pace beside "about X a year") had no target: the only per-year line on main is the no-reform card, which PR #466 removes, and the no-reform forecast is not back-loaded.

**Claude's part and checks:** Claude (ADU session) made the edit from the MM session's approved wording; app tests pass.
