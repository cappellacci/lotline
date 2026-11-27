### LB-NNN · 2026-11-11 · WS-CORE: second shared-parser round (D-081 item 6)
- **Question:** can the shared ADU parser read the misses the 2026-11-11 hand checks listed (TX §4, NC
  findings (a) and (b), OH §4) while keeping its precision, and apply D-080 item 2 and D-081 item 2?
- **Decided by:** Ben, 2026-11-11 (approved this round as D-081 item 6).
- **What I did:**
  - `src/lotline/parse/permit_text.py`:
    - new ADU names: "GARAGE APT", "garage with (upstairs) apartment", "in-law apt", "2ND DWELLING UNIT",
      "second dwelling"; "living quarters" only when detached, over a garage or in a separate building
      (Rule 3d); a floor area between "addition of" and the ADU name; "to create a mother-in-law suite";
    - D-081 item 2: an in-law suite or quarters with no kitchen named is not an ADU (tag `NO_KITCHEN_TAG`);
      `parse_description(text, in_law_suite_needs_kitchen=False)` gives the no-kitchen sensitivity;
    - D-080 item 2: an ADU the text says was already built ("built without a permit", "work has been
      done", "into compliance", "legalize") is not new (tag `LEGALIZATION_TAG`, `units_new` 0);
    - Asheville (a): a house named by its own permit number after the ADU ("ADU (SFR 16-…)") or after
      "ref." is context (Rule 4b), and a leading "SFR/" is a use label (Rule 4c); administrative notes
      ("RECD AMENDMENT TO CHANGE HVAC CONTRACTOR") are dropped before the rules run;
    - Asheville (b): "new stick-built / site-built house" is a new house;
    - Ohio: "NOT A DWELLING UNIT/ADU" and "may not be used as a 2nd dwelling" are negations; "existing or
      proposed single-family dwelling" and "dwelling (existing or proposed) is permitted separately" are
      context;
    - repairs: "replace 1 exterior door" and "upgrade" are alteration words.
  - `asheville_permits.NEW_HOUSE` also matches "new … house/home/residence" (not guest, carriage, pool,
    tiny or coach houses, and not "new ADU next to house"), a leading "residence" and "new build
    structure". `meck_permits.classify` accepts code 437.
  - `scripts/dev/parser_phrase_check.py`: the 42-phrase set from #376 (recovered from that session's log)
    and a 63-phrase set from the three reports plus written precision guards.
- **Outputs:** the files above; tests in `tests/core/test_permit_text.py`,
  `tests/states/nc/test_asheville_permits.py`, `tests/states/nc/test_meck_permits.py`.
- **Findings (phrase coverage, not measured recall):**

  | Set | Before (recall / precision) | After |
  |---|---|---|
  | #376 set (42) | 0.82 / 0.95 | 0.95 / 0.95 |
  | 2026-11-11 set (63), central | 0.37 / 0.43 | 0.85 / 1.00 |
  | 2026-11-11 set, kitchenless in-law suites as ADUs | 0.41 / 0.61 | 0.88 / 0.94 |

  Still missed: "ADDITION PORCH/GARAGE/2ND DWELLING UNIT", "Garage addition, Add Second Story. ADU",
  "demolish the garage and rebuild with a second level ADU", "convert garage to guest house", "DWELLING
  UNIT ADDITION". Still a false positive: "Accessory Dwelling Unit to Single Detatched".
- **How it was checked:** full `pytest` (2052 passed, 2 skipped), `ruff`, `python compliance_check.py`
  (0 FAIL). No permit data was read; test strings are written for the tests after the reports' quoted
  phrasings. No engine, scenario or fit script was run and nothing was downloaded.
- **AI:** Claude Code wrote the patterns, tests and phrase-check script.
- **Open / next:** the offline rebuild (`lotline fetch --offline`, #382), then fresh hand checks for the
  sources whose counts move. Greensboro and Mecklenburg in-law-suite flags and Fort Worth's no-stove
  suites drop out under D-081 item 2. "Upgrade" and door replacement now read as alterations for every
  building type, so a few house permits filled from text may move too. The Cincinnati carriage-house fix
  and its separately-permitted SFD stay with the Cincinnati session.
