### LB-NNN · 2026-11-10 · WS-CORE: shared permit parser ADU misreads (D-074/D-075 k_parser)
- **Question:** can the shared permit-description parser read the four ADU phrasings the NC/MN/OH/TX/OR count
  sessions found it misreading, without losing precision?
- **What I did:**
  - Changed `src/lotline/parse/permit_text.py` (Ben approved editing this WS-CORE file on 2026-11-10):
    1. "additional / second dwelling unit" (and "additional unit on/behind ...") reads as an ADU, except when
       the text talks about fees or "per/each" units;
    2. Cary's "utility dwelling unit" / "UDU" / "accessory use dwelling" read as an ADU ("not a UDU" is negated);
    3. an alteration or addition permit that creates the ADU it names ("ADU addition", "Addition - ADU",
       "Remodel lower level for ADU", "upfit space into ADU", "Attic remodel (ADU)") gives one new ADU; repairs,
       "addition to (existing) ADU", "remodel of ADU" and company names ("ADU Inc.") do not;
    4. new Rule 0: an ADU taken out of use ("no longer using as ADU", "remove ADU", "ADU abandonment",
       "convert ADU back to single family", "change of use from a permitted ADU") gives `units_new` 0,
       `units_removed` 1, new field `adu_removed=True`, and **no** building type, so no adapter counts it.
  - Also: wider negation ("not to be used/approved as an ADU"), "the ADU was" as context, underscores read as
    spaces ("NEW ADU_New construction"), ADU kinds for lower-level/attic conversions, detached-garage
    conversions and ADU additions, and "convert <unknown space> to ADU" now gives one unit.
  - Added 40 synthetic test rows to `tests/core/test_permit_text.py` (each case plus negatives).
  - Adapters were not changed (their own rules differ, e.g. Cary types a bare UDU as attached).
- **Inputs:** sibling session notes; phrases quoted in `reports/nc/*-adu-scout.md`, `reports/nc/charlotte-adu-counts.md`
  and the MN/OH/TX/OR undercount reports. No downloaded data was read.
- **Outputs:** `src/lotline/parse/permit_text.py`, `tests/core/test_permit_text.py`.
- **Findings:** on a 42-phrase check set (32 phrases quoted in the reports, 10 written to match their
  findings; labelled "new ADU or not" by Claude following the reports' hand-check verdicts), recall went
  0.18 → 0.82 and precision 0.40 → 0.95. This is a phrase check, not a re-run of any hand-check sample: the
  hand-check labels are not committed as fixtures, and real permit text was not read (holdouts untouched).
- **Decisions:** proposed in the PR: parser sources re-measure k_parser = 1/recall on their next rebuild, since
  parser recall changed.
- **AI:** Claude Code wrote the patterns and tests and ran pytest, ruff and `compliance_check.py`. Every test
  string is hand-written.
- **Open / next:** remaining misses: "SFR - 1BR 1BA - ADU", "garage with (upstairs) apartment", "DWELLING UNIT
  ADDITION"; "Remove ADU deck and rebuild" still reads as a new ADU (no alteration word).
