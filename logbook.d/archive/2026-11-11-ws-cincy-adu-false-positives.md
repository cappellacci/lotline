### LB-NNN · 2026-11-11 · WS-OH: Cincinnati ADU false positives and the one miss (D-081 item 3)
- **Question:** can the Cincinnati adapter drop the 12 false ADU flags and recover the 1 missed ADU that the
  2026-11-11 hand check found (`reports/oh/parser-handcheck-2026-11-11.md` §2, §4), with generic rules and
  without touching the shared parser?
- **What I did:** read the three cases' text in the cached 2026-11-11 raw snapshot (no network) and added
  three adapter rules to `cincy_permits.build` (adapter v1.1):
  1. **Development buildings** (`development_adus`): an ADU flag is dropped when its parcel has, in the same
     issue year, another permit for new multifamily construction (RNEW/CNEW, 3+ units), or at least
     `DEVELOPMENT_ADU_MIN` = 3 distinct ADU-flagged permits, or when its text names a master plan ("within a
     36 residential building masterplan"). The permit keeps its use-group type.
  2. **Negation** (`NOT_A_UNIT`): "not a dwelling unit" vetoes an ADU flag ("NOT A DWELLING UNIT/ADU").
  3. **House permitted separately** (`_separate_house_adu`): when the parser returns "an ADU and another
     dwelling type" and the text says the house is permitted separately, each sentence is parsed alone; if
     only ADU sentences give a type, the permit is that ADU.
  No permit ids are hard-coded. Seven synthetic tests mirror each case and its near neighbours (apartments
  another year, two ADUs on a parcel, a 3-unit alteration, an ADU beside its new house, a conflict with no
  separate permit).
- **Inputs:** `raw/cincy_permits/2026-11-11/` and `processed/oh/permits/cincy_permits.parquet` (read only).
- **Outputs:** `src/lotline/adapters/states/oh/cincy_permits.py`, `tests/states/oh/test_cincy_permits.py`,
  `docs/data_provenance.md` (cleaning step, adapter v1.1).
- **Findings:** an in-memory `build()` on the cached raw (nothing written) changes exactly 13 permits:
  the 11 masterplan carriage houses (2020P05427–5437) and the pool shed (2024P06273) leave the ADU count, and
  2026P04020 becomes a detached ADU instead of a second SFD. Flags go 29 → 18 (2020: 12 → 1, 2025: 4 → 3,
  2026: 4 → 5); the 15 true ADUs and 2 unclear permits are unchanged. One trap caught on the way: a 3-unit
  *alteration* permit (2022P04151) counted as its own multifamily neighbour, so the multifamily signal now
  takes only other, new-construction permits.
  The miss was not the "existing" veto crossing a sentence break, as the report guessed: the parser reads
  "an existing or proposed single-family dwelling that is being permitted separately" as a house built here,
  because `_CONTEXT_BEFORE` allows one word after "existing" and `_OTHER_PERMIT_AFTER` needs the
  "permitted separately" right after the type word.
- **AI:** Claude Code wrote the rules, tests and this entry, and checked the effect with the in-memory build
  above. Full `pytest` and `compliance_check.py` (0 FAIL) run. No engine, fit or scenario run, no download,
  no `--unblind`, `permit_text.py` not edited.
- **Open / next:** for the shared-parser round (D-081 item 6): negate "not a dwelling unit" in
  `_ADU_NEGATED`; read "existing or proposed <type>" and "<type> that is (being) permitted separately" as
  context. Then the adapter's rules 2–3 become no-ops and can stay as guards. Cincinnati gets its fresh hand
  check after the offline rebuild. The 11 coach units keep their use-group types (mostly UNKNOWN units,
  because the city records 0 units on the repeated rows); whether to count them as 1-unit homes is a
  separate call.
