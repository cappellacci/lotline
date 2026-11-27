### LB-NNN · 2026-11-11 · Validation: fresh Cincinnati parser hand check after #388 and #389 (D-081 items 1, 3, 6)
- **Question:** after the Cincinnati adapter fix (#388) and the second parser round (#389) moved Cincinnati from
  29 to 18 ADU flags (#391), what is its k_parser = precision ÷ recall, and are the #384 errors gone?
- **What I did:**
  - Wrote and committed the judging rule first (commit `a83064d2`): the #384 labels plus NOKITCHEN (D-081 item 2)
    and DEV (development coach units, item 3), new seeds 20261121–23, simulated k range from Jeffreys beta draws.
  - Read all 18 flags and the full near-miss net of 70 (a census; the seeded 30 reported too), shuffled together
    and shown without flags. Labels were locked before unblinding.
- **Inputs:** rebuilt `processed/oh/permits/cincy_permits.parquet` (#391) and the 2026-11-11 raw combo snapshot in
  `LOTLINE_DATA_DIR`, read-only. Nothing downloaded; Ohio has no holdouts; no `--unblind`.
- **Outputs:** `reports/oh/parser-handcheck-2026-11-11b.md`, with a proposed `adu_flag_undercount` row.
- **Findings:**
  - Precision 14/18 = 0.78 (4 bare "carriage house" flags unclear); recall 14/14 inside the download net
    (0 misses in 70). **k = 0.78, 90% range 0.61–1.31** across the readings of 6 unclear permits.
  - No-kitchen sensitivity adds one flag (a mother-in-law suite): k 0.79.
  - The 11 development carriage houses and the negated shed are unflagged; the #384 miss (2026P04020) is caught.
  - Reading two of the unclear flags as #384 did gives k = 0.89 (0.74–1.02): the result turns on those permits.
- **Decisions:** proposed in the PR: the `cincy_permits` row (k 0.78, 0.61–1.31), replacing #384's 1.07.
  `config/params/adu.yaml` not edited.
- **AI:** Claude Code (Opus 5.5) wrote the rule, the throwaway draw and score scripts, the hand labels and the
  report. Checks: the flag count matches #391 (18; no-kitchen 19); the parser's no-kitchen run adds exactly the
  one permit labelled NOKITCHEN; the five checks in report §5 each traced by permit number. No engine, fit,
  scenario or dev-run script was run.
- **Open / next:** Ben accepts or adjusts the row; optional second reader for the 4 unclear flags; widening
  `COMBO_WORDS` would need a new fetch.
