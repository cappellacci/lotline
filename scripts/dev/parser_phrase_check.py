"""Phrase-coverage check of the shared ADU description parser (`lotline.parse.permit_text`).

Scores "new ADU or not" on two sets of short phrases:

- `SET_376`: the 42 phrases #376 scored (32 quoted in the 2026-11-10 NC scout reports, 10 written to match
  their findings), with #376's labels.
- `SET_1111`: phrases quoted in the 2026-11-11 hand checks (`reports/tx/parser-handcheck-2026-11-11.md` §3-4,
  `reports/nc/parser-handcheck-2026-11-11.md` §1 and §4, `reports/oh/parser-handcheck-2026-11-11.md` §2),
  shortened and with addresses removed as the reports print them, plus negatives written to guard
  precision (fee language, negations, legalizations, new houses that name an ADU).

Labels follow the reports' judging rules with D-080 item 2 (a legalization of a built ADU is not new) and
D-081 item 2 (an in-law suite with no kitchen named is not an ADU). Phrases marked `nk` are kitchenless
in-law suites: the no-kitchen sensitivity counts them as ADUs.

This is a check of phrase coverage, not a measured recall: the reports' hand checks are the measure, and
they are re-run on the rebuilt tables after this change. No permit data is read.

    python scripts/dev/parser_phrase_check.py            # the parser in this checkout
    python scripts/dev/parser_phrase_check.py <src dir>  # another copy (e.g. main, for "before")
"""

from __future__ import annotations

import sys
from pathlib import Path

# (phrase, new ADU under the central rule, kitchenless in-law suite)
SET_376: list[tuple[str, bool]] = [
    ("ACCESSORY USE PERMIT - UTILITY DWELLING", True),
    ("ADDITION - ADU", True),
    ("Addition - UDU, Screen Porch, & Deck", True),
    ("Attic remodel (ADU) and porch addition", True),
    ("Converting detached garage to ADU", True),
    ("DWELLING UNIT ADDITION & DECK", True),
    ("FINISH UTILITYDWELLING UNIT ON 2ND FLOOR", True),
    ("Finishing area over garage for a utility dwelling", True),
    ("NEW ADU_New construction", True),
    ("Punch ADU Addition (expand footprint)", True),
    ("Remodel Lower Level for ADU", True),
    ("ADU ADDITION W/ PORCH", True),
    ("Change room above garage to ADU Upfit", True),
    ("Upfit unfinished space into ADU", True),
    ("SFR - 1BR 1BA - ADU", True),
    ("additional dwelling unit", True),
    ("Build additional dwelling unit behind house", True),
    ("detached garage with upstairs apartment", True),
    ("new garage with apartment", True),
    ("acc use dwelling", True),
    ("Basement conversion to ADU", True),
    ("Convert garage into ADU", True),
    ("Accessory Dwelling Unit to Single Detatched", False),
    ("All work to take place at Accessory Dwelling Unit - repairs to existing deck", False),
    ("Demolish/Move Off. Accessory Dwelling Unit.", False),
    ("GARAGE ONLY, NO ADU", False),
    ("NO ADU ALLOWED", False),
    ("NOT A UDU", False),
    ("Not to be used as an ADU", False),
    ("Not to be used as an accessory dwelling unit/have cooking appliances", False),
    ("THIS IS NOT AN ADU", False),
    ("no longer using as ADU", False),
    ("Single Family Home with ADU", False),
    ("Two-family dwelling (SFD with attached ADU)", False),
    ("ADU to be permitted separately", False),
    ("garage where the ADU was", False),
    ("change of use from a permitted ADU", False),
    ("Remove ADU kitchen, convert back to single family", False),
    ("Impact fee per additional dwelling unit", False),
    ("Addition to existing ADU", False),
    ("Renovate existing ADU", False),
    ("New single family home, future ADU", False),
]

SET_1111: list[tuple[str, bool, bool]] = [
    # --- Texas misses (Fort Worth, Dallas), new ADUs
    ("DETACHED GARAGE APT", True, False),
    ("DETACHED LIVING QUARTER", True, False),
    ("New garage on 1st floor/Living quarters on 2nd floor; separate building from residence", True, False),
    ("ADD BATHROOM TO DETACHED GARAGE//REVISE TO CONVERT GARAGE TO GUEST HOUSE", True, False),
    ("to be construct second dwelling onto first existing floor", True, False),
    ("CONSTRUCT DETACHED GARAGE WITH SECOND DWELLING", True, False),
    ("2ND DWELLING UNIT", True, False),
    ("ADDITION OF 400SF ACCESSORY DWELLING UNIT(BDA CASE)", True, False),
    ("ADDITION PORCH/GARAGE/2ND DWELLING UNIT", True, False),
    ("Finish work on revoked permit, 2nd dwelling approved by bda", True, False),
    # --- Texas flagged, new ADUs
    ("CONVERT GARAGE TO APARTMENT", True, False),
    ("Garage converted to ADU. New bathroom, small kitchen", True, False),
    ("DETACHED MOTHER IN LAW SUITE - Not allowed separate service, kitchenette", True, False),
    ("ADU APPROVED BY BOA", True, False),
    # --- in-law suites with no kitchen named: not ADUs (D-081 item 2), ADUs in the sensitivity
    ("SFR/ NEW DETACHED MOTHER IN LAW SUITE/", False, True),
    ("NEW ADDITION TO EXISTING GARAGE TO CREATE A MOTHER-IN-LAW SUITE WITH NO STOVE", False, True),
    ("NEW 2 BEDROOM 1 BATH MOTHER IN LAW SUITE", False, True),
    ("ADDITION - MOTHER-IN-LAW SUITE", False, True),
    ("turning basement into mother-in-law suite", False, True),
    ("ADDITION OF 'MOTHER-IN-LAW SUITE'", False, True),
    # --- in-law suites with a kitchen named (written)
    ("NEW DETACHED MOTHER IN LAW SUITE WITH KITCHEN", True, False),
    ("Mother-in-law suite with full kitchen and bath", True, False),
    # --- Texas not new
    ("Accessory Dwelling 924 square feet, already built without permit", False, False),
    ("CONVERTING GARAGE INTO APARTMENT (WORK HAS BEEN DONE)", False, False),
    ("PERMITTING EXISTING GUEST HOUSE", False, False),
    ("GARAGE APARTMENT/REPLACE 1 EXTERIOR DOOR", False, False),
    ("Remodel of existing mother-in-law suite", False, False),
    ("New Barndo with attached garage and mother-in-law suite", False, False),
    ("LOFT OR IN-LAW SUITE ABOVE", False, True),
    ("300 SQ FT IN LAW SUITE PREVIOUS PERMIT PB22-01234", False, False),
    ("CAN NOT BE USED AS SECOND DWELLING UNIT", False, False),
    ("NEW CONSTRUCTION OF GUEST HOUSE", False, False),
    # --- NC: Mecklenburg and Asheville misses, new ADUs
    ("Garage addition, Add Second Story. ADU", True, False),
    ("attached garage w/ mother-in-law apt", True, False),
    ("garage apartment, ref. new house permit 14-01234", True, False),
    ("accessory dwelling unit (SFR 16-04567)", True, False),
    ("Detached ADU over garage. RECD AMENDMENT TO CHANGE HVAC CONTRACTOR", True, False),
    ("Change of Use - Garage to Dwelling Unit 828 SF", True, False),
    ("demolish the existing 2 car garage and rebuild with a second level ADU", True, False),
    ("create a detached ADU", True, False),
    # --- NC not new
    ("new stick built house with ADU in basement", False, False),
    ("apartment made previously with no permits", False, False),
    ("bring existing ADU in basement into compliance", False, False),
    ("upgrade existing studio/apartment above detached garage", False, False),
    ("not to be used as ADU", False, False),
    # --- Ohio (Cincinnati)
    ("NEW DETACHED GARAGE WITH ADU ON SECOND FLOOR", True, False),
    ("985SF ADU AT BASEMENT LEVEL", True, False),
    (
        "NEW DETACHED GARAGE WITH ACCESSORY DWELLING UNIT ABOVE. THE EXISTING OR PROPOSED SINGLE-FAMILY "
        "DWELLING IS PERMITTED SEPARATELY",
        True,
        False,
    ),
    ("POOL SHED - NOT A DWELLING UNIT/ADU", False, False),
    ("NEW SINGLE FAMILY DWELLING, ADU IN BASEMENT REMOVED FROM PROJECT SCOPE", False, False),
    ("CARRIAGE HOUSE ALTERATION", False, False),
    ("REPAIR CARRIAGE HOUSE", False, False),
    # --- precision guards (written)
    ("IMPACT FEE PER 2ND DWELLING UNIT", False, False),
    ("SECOND DWELLING UNIT FEE", False, False),
    ("STORAGE BUILDING MAY NOT BE USED AS A 2ND DWELLING", False, False),
    ("New single family home with second dwelling unit", False, False),
    ("NEW SFD WITH GARAGE APT", False, False),
    ("2ND DWELLING UNIT ALREADY BUILT WITHOUT PERMIT", False, False),
    ("garage apartment built without a permit", False, False),
    ("Addition of living quarters to house", False, False),
    ("Remodel existing detached living quarters", False, False),
    ("NEW SFD. RECD AMENDMENT TO CHANGE HVAC CONTRACTOR", False, False),
    ("new pool house", False, False),
]


def _flag(parse, text: str) -> bool:
    f = parse(text)
    return f.building_type_std == "ADU" and bool(f.units_new) and not f.is_demolition


def _score(rows, parse, *, show: bool) -> tuple[int, int, int, int]:
    tp = fp = fn = tn = 0
    for text, label in rows:
        got = _flag(parse, text)
        tp += got and label
        fp += got and not label
        fn += (not got) and label
        tn += (not got) and not label
        if show and got != label:
            print(f"    {'FN' if label else 'FP'}  {text}")
    return tp, fp, fn, tn


def _line(name: str, c: tuple[int, int, int, int]) -> str:
    tp, fp, fn, tn = c
    rec = tp / (tp + fn) if tp + fn else float("nan")
    prec = tp / (tp + fp) if tp + fp else float("nan")
    return f"| {name} | {tp} | {fp} | {fn} | {tn} | {rec:.2f} | {prec:.2f} |"


def main(src: str | None = None) -> None:
    root = Path(src) if src else Path(__file__).resolve().parents[2] / "src"
    sys.path.insert(0, str(root))
    import inspect

    from lotline.parse.permit_text import parse_description

    def sens_parse(text: str):
        # the D-081 item 2 sensitivity switch exists only after this round; before it, the parser read every
        # in-law suite as an ADU anyway
        if "in_law_suite_needs_kitchen" in inspect.signature(parse_description).parameters:
            return parse_description(text, in_law_suite_needs_kitchen=False)
        return parse_description(text)

    central = [(t, lab) for t, lab, _ in SET_1111]
    sens = [(t, lab or nk) for t, lab, nk in SET_1111]
    print(f"parser from {root}")
    print("| set | TP | FP | FN | TN | recall | precision |\n|---|--:|--:|--:|--:|--:|--:|")
    rows = [
        ("#376 set (42)", _score(SET_376, parse_description, show=False)),
        (f"2026-11-11 set ({len(central)}), central", _score(central, parse_description, show=False)),
        ("2026-11-11 set, in-law suites as ADUs", _score(sens, sens_parse, show=False)),
    ]
    for name, c in rows:
        print(_line(name, c))
    print("\nWrong, #376 set:")
    _score(SET_376, parse_description, show=True)
    print("Wrong, 2026-11-11 set (central):")
    _score(central, parse_description, show=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
