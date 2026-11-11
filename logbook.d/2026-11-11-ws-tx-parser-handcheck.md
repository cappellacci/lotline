### LB-NNN · 2026-11-11 · WS-TX: parser recall hand check for Fort Worth and Dallas after #376 / #380
- **Question:** after the shared parser fix, what are the parser's precision and recall, and k = 1 / recall, for
  the two Texas parser sources `fw_permits` and `dallas_permits` (D-074 step 1 as amended by D-078 §2–3, per
  source)?
- **What I did:** read the rebuilt, holdout-filtered processed permits and joined descriptions back from the
  cached 2026-11-11 raw pages (no network). Re-ran each adapter's `build()` with the `main` parser in memory
  (Fort Worth 117 flags, unchanged; Dallas 1, down from 2 now that #380 is in). Built a flagged pool and a
  near-miss pool (ADU-like words, not flagged), wrote the judging rule down before reading any sample, drew
  30 + 30 for Fort Worth with seed 20261111 and took all 1 + 18 for Dallas, and judged each by hand.
  Legalizations of existing units and new houses that name an ADU were labelled apart (Ben's rules).
- **Inputs:** `processed/tx/permits/{fw,dallas}_permits.parquet`, `raw/{fw,dallas}_permits/2026-11-11/`
  (read only).
- **Outputs:** `reports/tx/parser-handcheck-2026-11-11.md`.
- **Findings:** Fort Worth precision 0.77 (23/30), recall 0.40 (0.27–0.55), **k = 2.49 (1.83–3.66)**, a
  low-recall row under D-078 §3. Sensitivities run from 2.04 to 3.46, and precision ÷ recall gives 1.91. Its
  legalizations: 3 in the samples, and a keyword screen finds 6 of 117 flagged and 9 of 400 near-misses.
  **Dallas recall can't be estimated:** the parser finds 1 of 6 true ADUs in the whole table. The misses
  come mostly from phrasings the parser does not read ("GARAGE APT", "MOTHER IN LAW SUITE" after "SFR/",
  "2ND DWELLING UNIT", "SECOND DWELLING", "living quarters").
- **AI:** Claude Code wrote the throwaway scripts (scratch only), the rule and the report, and did the hand
  judging. The rule was fixed before any label was seen, and the parser misses were confirmed by running
  `parse_description` on the snippets. No engine, fit or scenario run, no download, no `--unblind`.
- **Open / next:** Ben to choose Fort Worth's row (1 / recall as the method says, or precision ÷ recall) and
  whether Dallas stays out or enters as a floor. A WS-CORE parser fix for the phrasings in report §4, then a
  fresh check (D-078 §3), would replace both numbers. `config/params/adu.yaml` is not edited.
