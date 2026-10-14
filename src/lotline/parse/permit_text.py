"""Read housing facts from a building permit's free-text description.

Many permit systems record the number of new homes, the building type, or the fact that a permit is a
demolition or a conversion only in a free-text description ("NEW 4-UNIT TOWNHOME BLDG", "Demo SFD",
"convert single family to duplex"). `parse_description` reads those facts with a short list of named,
commented phrase patterns, so every state adapter fills the `permits` table the same way.

**Everything it returns is an inference.** An adapter that uses a value sets `units_confidence="inferred"`
or `type_confidence="inferred"`, and uses it only where the source's own structured field is missing.

**Precision over recall.** When the text is ambiguous the answer is `None` (unknown), never a guess:

- a count is read only when a number sits directly in front of a dwelling noun ("48 units", "(3) unit",
  "twelve apartments", "6-plex"); bedrooms, stories, square feet, years, lot, building and permit
  numbers, address units ("Unit 5", "Apt B", "Units 101 & 102") and accessible-unit subsets
  ("2 HC units") are never counts;
- two different counts in one description (a building and its project, say) give no count;
- a building type is never made finer than the text supports: "2-4 units" is `DTQ`, "5 or more" is
  `MF5`, a count of 5+ is `MF5` (never `U5_6`/`U7P`);
- contradictory signals (a duplex with 4 units, a new house *and* an ADU) give no type and no count;
- an alteration, repair, remodel, reroof, HVAC or addition gives `units_new = 0` only when the text
  says so and nothing in it adds a dwelling; text that says nothing gives `None`;
- a count that is the total of a multi-building project ("Bldg 5 ... project of 384 total units") is not
  the permit's count;
- a townhouse count ("NEW 4-UNIT TOWNHOME BLDG") describes the row building, and many places issue one
  permit per townhouse, so it goes to `building_units`, not `units_new`.

Rules, in the order `parse_description` applies them (each is a named pattern below):

1. conversion "convert X (in)to Y": net units = units of Y - units of X (an ADU adds one);
2. demolition of a whole building (not "Demo-12345" references): units_new 0, units_removed from the
   building named (a count, a type word, "house"), 0 for garages and sheds, else None;
3. alteration / repair without a new-construction cue: units_new 0 (None if an ADU is named);
4. new dwellings: one building type and one count that agree, else None. Type and count words that
   describe an existing or separately permitted building ("ADU behind existing house", "SFD - BLDR-001")
   are context and ignored.

The result's `evidence` lists each rule that fired with the phrase it matched, so any inferred value can
be traced back to the words that produced it. Standard library only (`re`); no models, no data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

__all__ = ["PermitTextFacts", "parse_description"]


@dataclass(frozen=True)
class PermitTextFacts:
    """Facts read from one description. `None` means the text does not say (never a default of 0)."""

    units_new: int | None = None
    units_removed: int | None = None
    building_type_std: str | None = None  # SFD, ADU, TH, U2, U3_4, DTQ, MF5, OTHER (manufactured home)
    adu_type: str | None = None  # attached, detached, internal_conversion, unknown
    is_demolition: bool | None = None
    is_conversion: bool | None = None
    building_units: int | None = (
        None  # units in the townhouse row the text describes (not this permit's count)
    )
    evidence: tuple[str, ...] = ()  # "rule: matched phrase", in the order the rules fired


# --------------------------------------------------------------------------------------------------------
# Numbers: digits ("48", "1,200"), parenthesised digits ("(3)"), and words up to ninety-nine ("three",
# "twenty-four", "eight (8)").
# --------------------------------------------------------------------------------------------------------
_ONES = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}  # fmt: skip
_TENS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}
_ONES_ALT = "|".join(sorted(_ONES, key=len, reverse=True))  # longest first: "seventeen" before "seven"
_WORD_NUM = rf"(?:(?:{'|'.join(_TENS)})(?:[- ](?:{_ONES_ALT}))?|{_ONES_ALT})"
NUMBER = (
    rf"(?:\(\s*\d{{1,4}}\s*\)|\b{_WORD_NUM}\b(?:\s*\(\s*\d{{1,4}}\s*\))?|\d{{1,3}}(?:,\d{{3}})+|\d{{1,4}})"
)


def _to_int(token: str) -> int:
    """'48' / '1,200' / '(3)' / 'eight (8)' / 'twenty-four' → int."""
    digits = re.search(r"\d[\d,]*", token)
    if digits:
        return int(digits.group().replace(",", ""))
    words = re.split(r"[- ]+", token.strip().lower())
    return sum(_TENS.get(w, 0) + _ONES.get(w, 0) for w in words)


# --------------------------------------------------------------------------------------------------------
# Rule 1. Unit count: NUMBER, up to three describing words, then a dwelling noun.
#   "48 units", "NEW 4-UNIT TOWNHOME BLDG", "construct (3) unit multifamily", "48 apt units",
#   "120 dwelling units", "three units", "12 condos", "6-plex".
# Words that mark a subset of the building ("2 HC units", "12 two-bedroom units") reject the count.
# --------------------------------------------------------------------------------------------------------
_QUALIFIER = (
    r"new|total|additional|residential|dwelling|apartment|apt|condo(?:minium)?|rental|multi-?\s?family|"
    r"affordable|senior|market[- ]rate|townho(?:me|use)|row\s?ho(?:me|use)|living|housing|family|style|"
    # subset markers (checked below):
    r"hc|h\.c\.|handicap(?:ped)?|accessible|ada|type\s+[a-c]|studio|efficiency|"
    r"(?:\d|one|two|three|four)\s*-?\s*(?:br|bdrm|bed(?:room)?)s?"
)
_SUBSET = re.compile(
    r"\b(?:hc|h\.c\.|handicap\w*|accessible|ada|type\s+[a-c]|studio|efficiency|br|bdrm|bed(?:room)?s?)\b",
    re.I,
)
_NOUN = (
    r"dwelling\s+units?|dwellings|du'?s|du|units?|apartments|apts|apartment\s+units?|apt\.?\s+units?|"
    r"condo(?:minium)?s|condo(?:minium)?\s+units?|townho(?:me|use)s|townho(?:me|use)\s+units?|"
    r"row\s?ho(?:me|use)s|residences|adus|accessory\s+dwelling\s+units?|plex(?:es)?"
)
COUNT = re.compile(
    r"(?:(?<![\w#.\-/:$])|(?<=\s-))"  # not inside an ID or code (R-2, #12, 3.5, 1/2, $500, 22-25); " -24" ok
    rf"(?P<num>{NUMBER})"
    r"\s*-?\s*"  # "4-unit", "4 unit", "6plex"
    rf"(?P<qual>(?:(?:{_QUALIFIER})\s*-?\s*){{0,3}}?)"
    rf"(?P<noun>{_NOUN})\b",
    re.I,
)
# A number right after one of these words is a label (Building 5, Lot 12, Unit 3, Type 2), not a count.
_LABEL_BEFORE = re.compile(
    r"\b(?:bldg|building|lot|lots|phase|section|area|type|suite|ste|floor|level|units?|apt|room|no|number|"
    r"sheet|plan|case)\.?\s*#?\s*$|#\s*$",
    re.I,
)
# Rule 1b. Project totals. A count introduced as the total of a project, complex or development ("384 total
# units", "project consisting of a 188 unit ...", "complex with (55) units") describes the whole site. When
# the same text names one building of several ("BLDG 5", "Building D", "two apartment buildings"), the
# permit is for one building and the project total is not its count.
_PROJECT_WORDS = (
    r"project|complex|development|community|site|phase|overall|consist\w*|total(?:\s+of)?|buildings|bldgs"
)
_PROJECT_WORD = re.compile(rf"\b(?:{_PROJECT_WORDS})\b", re.I)
_PROJECT_BEFORE = re.compile(rf"\b(?:{_PROJECT_WORDS})\b[^.;]{{0,40}}$", re.I)
_BUILDING_LABEL = re.compile(
    r"\b(?:bldg|bld|bdlg|building)\.?\s*(?:#\s*)?(?:\d{1,5}[a-z]?|[a-z]\d{0,4})\b", re.I
)
_ONE_OF_SEVERAL = re.compile(
    rf"{_BUILDING_LABEL.pattern}|\b(?:buildings|bldgs)\b|\b(?:phase|ph|area)\s*#?\s*\d",
    re.I,
)

# A count tied to one building: "5 units each", "building with 664 units", "24 unit ... housing building".
_EACH_AFTER = re.compile(r"^\s*(?:each|per\s+(?:building|bldg))\b", re.I)
_BUILDING_WITH_BEFORE = re.compile(
    r"\b(?:bldg|building)\s+(?:with|containing|of|has|having)\s+(?:\w+\s+)?$", re.I
)
_BUILDING_AFTER = re.compile(r"^[^.;,()]{0,40}?\b(?:building|bldg)\b", re.I)
_STACKED_BEFORE = re.compile(r"\b\d\s+over\s+$", re.I)


def _is_project_total(text: str, m: re.Match[str]) -> bool:
    """Rule 1b: is this count the total of a multi-building project rather than of one building?"""
    if _EACH_AFTER.match(text[m.end() :]) or _BUILDING_AFTER.match(text[m.end() :]):
        return False
    before = text[max(0, m.start() - 60) : m.start()]
    if _BUILDING_WITH_BEFORE.search(before):
        return False
    if "total" in m.group("qual").lower():
        return True
    project = _PROJECT_BEFORE.search(before)
    if not project:
        return False
    # "Housing Project - Building 1: a 24 unit ...": a building label after the project word scopes the count
    last = list(_PROJECT_WORD.finditer(project.group(0)))[-1]
    return not _BUILDING_LABEL.search(project.group(0)[last.end() :])


# "7 APTS BLDGS", "5 townhomes buildings": the number counts buildings ("8 unit bldg" is still a count).
_BUILDINGS_AFTER = re.compile(r"^\s*-?\s*(?:buildings?|bldgs?|structures?)\b", re.I)
# "5 UNIT 101" or "2 UNIT #4": the singular noun is followed by an address-unit number.
_ADDRESS_AFTER = re.compile(r"^\s*#?\s*\d+(?!\s*-?\s*(?:story|stories|level|bed))", re.I)

# --------------------------------------------------------------------------------------------------------
# Rule 2. Building-type words. (name, pattern, building_type_std, units implied by one such building)
# --------------------------------------------------------------------------------------------------------
TYPE_RULES: list[tuple[str, re.Pattern[str], str, int | None]] = [
    (
        "duplex",
        re.compile(r"\bduplex(?:es)?\b|\b(?:two|2)[- ]?family\b", re.I),
        "U2",
        2,
    ),
    (
        "triplex",
        re.compile(r"\btri-?plex(?:es)?\b|\b(?:three|3)[- ]?family\b", re.I),
        "U3_4",
        3,
    ),
    (
        "fourplex",
        re.compile(r"\b(?:quad(?:ru|ra)?-?plex|four-?plex)(?:es)?\b|\b(?:four|4)[- ]?family\b", re.I),
        "U3_4",
        4,
    ),
    (
        "two-to-four units",  # a lumped range: DTQ, never split into U2 / U3_4
        re.compile(
            r"\b(?:2|two)\s*(?:-|to|through|thru)\s*(?:4|four)\s*(?:-\s*)?(?:units?|family|dwellings?)\b"
            r"|\bsmall\s+multi-?\s?family\b",
            re.I,
        ),
        "DTQ",
        None,
    ),
    (
        "five or more units",  # a lumped range: MF5
        re.compile(r"\b(?:5|five)\s*(?:\+|or\s+more)\s*(?:units|family|dwellings)\b", re.I),
        "MF5",
        None,
    ),
    (
        "townhouse",
        re.compile(
            r"\b(?:new)?town\s?ho(?:me|use)s?\b(?![- ]style)|\brow\s?ho(?:me|use)s?\b"
            r"|\bsingle[- ]?family[- ]attached\b"
            r"|\bnew\s+th\b|\bth\s+(?:lots?|units?|bldg|building)\b",
            re.I,
        ),
        "TH",
        None,
    ),
    (
        "single-family house",
        re.compile(
            r"\bsingle[- ]?family(?![- ]attached)(?:\s+(?:detached|dwelling|residence|home|house))*\b"
            r"|\bn?sfd\b|\bs\.f\.d\b|\bsfr\b|\bnsf\b|\bnew\s+sf\b(?!\s+(?:of|addition))"
            r"|\bnew\s+(?:custom\s+)?(?:house|home|residence)\b",
            re.I,
        ),
        "SFD",
        1,
    ),
    (
        "manufactured home",  # Census BPS excludes these, so they are OTHER (as in the Raleigh adapter)
        re.compile(
            r"(?:\b(?:mobile|manufactured)\s+(?:home|house)\b|\b(?:single|double)[- ]wide\b)"
            r"(?![^.;]{0,30}\b(?:office|classroom|trailer)\b)",  # not a site-office trailer
            re.I,
        ),
        "OTHER",
        1,
    ),
]

# Rule 3. Accessory dwelling units, and their kind when the text says.
ADU = re.compile(
    r"(?<!\bno\s)(?<!\bnon-)(?<!\bnot\s)(?<!\bnot\san\s)\b(?:adus?|a\.d\.u\.?|dadu|aadu)\b"
    r"|\baccessory\s+(?:dwelling|apartment|residential\s+unit)"
    r"|\bgarage\s+apartment\b|\bapartment\s+(?:above|over)\s+(?:the\s+|a\s+)?(?:new\s+)?(?:detached\s+)?garage"
    r"|\bbackyard\s+cottage\b|\bcarriage\s+house\b|\bgranny\s+(?:flat|unit|pod)\b"
    r"|\b(?:mother|father)?[- ]?in[- ]law\s+(?:suite|apartment|unit|quarters)\b"
    r"|\bbasement\s+(?:apartment|unit)\b|\bsecondary\s+(?:dwelling|suite)\b",
    re.I,
)
ADU_KIND: list[tuple[str, re.Pattern[str]]] = [
    (
        "internal_conversion",
        re.compile(
            r"\b(?:basement|attic)\s+(?:apartment|unit|adu|accessory)|\b(?:internal|interior)\s+adu\b"
            r"|\badu\s+(?:within|inside|in)\s+(?:the\s+)?existing\b"
            r"|\bconver\w*\s+(?:the\s+)?(?:existing\s+)?(?:basement|attic)\b",
            re.I,
        ),
    ),
    (
        "detached",
        re.compile(
            r"\bdetached\s+(?:adu|accessory|garage\s+apartment|apartment|unit|dwelling)|\bdadu\b"
            r"|\badu\s*[(,-]?\s*detached\b|\bbackyard\s+cottage\b|\bcarriage\s+house\b"
            r"|\b(?:apartment|adu)\s+(?:above|over)\s+(?:the\s+|a\s+)?(?:new\s+)?detached\s+garage",
            re.I,
        ),
    ),
    (
        "attached",
        re.compile(r"\battached\s+(?:adu|accessory)|\baadu\b|\badu\s*[(,-]?\s*attached\b", re.I),
    ),
]

# "not an ADU" / "no ADU" anywhere: the reviewer has said the space is not a dwelling unit.
_ADU_NEGATED = re.compile(r"\b(?:not|no|non)[- ](?:an?\s+)?(?:adu|accessory\s+dwelling)\b", re.I)

# Rule 4. A type word right after one of these describes something that already exists (the house an ADU
# sits behind, the building being demolished or replaced), not what the permit builds.
_CONTEXT_BEFORE = re.compile(
    r"\b(?:existing|former|old|current|primary|principal|main|replac\w*|behind|to\s+serve|same\s+time\s+as)\s+"
    r"(?:the\s+|an?\s+)?(?:\w+\s+)?$"
    # work done on/in a building: "solar on a single family home", "deck add on SFD"
    r"|\b(?:on|in|onto|inside|within|at)\s+(?:the\s+|an?\s+)?(?:existing\s+)?(?:\w+\s+)?$"
    # a building named inside a reference to a demolition permit: "DEMO-008872-2022 (SFD)"
    r"|\bdemo\w*\W*\d[\d-]*\W*$",
    re.I,
)
# ... or a building on another permit right after it: "SFD - BLDR-001152-2023", "duplex permitted separately",
# "single family on separate case", "the single family dwelling is under Ref", "Duplex Issued 6-16-2023".
_OTHER_PERMIT_AFTER = re.compile(
    r"^\W{0,4}(?:(?:to\s+be\s+|is\s+)?(?:permitted|applied\s+for)\s+(?:separately|separate|under|on)"
    r"|(?:is\s+)?(?:on|under)\s+(?:a\s+)?(?:separate|ref\b)|separate\s+permit|also\s+in\s+review)",
    re.I,
)
# A bare permit number right after the word ("SFD - BLDR-001152-2023", "Duplex Issued 6-16-2023") also marks
# another permit's building, unless the word itself is introduced as new ("NEW SFD Demo-003862-2021").
_PERMIT_NUMBER_AFTER = re.compile(r"^\W{0,4}(?:[a-z]{2,6}-\d{3,}|issued\b|\(?\s*(?:permit|case)\s*#)", re.I)
# ... or, for single-family words, a place rather than a building right after it ("single family lot",
# "single-family zoning"); "SFD Lot 47" is a lot number and does not count.
_CONTEXT_AFTER = re.compile(
    r"^\s*(?:lots?(?!\s*#?\s*\d)|zon\w*|district|neighbou?rhood|area|subdivision|parcel)\b", re.I
)

# Rule 5. New construction of a dwelling: a verb or "new" within a few words before the dwelling phrase,
# or "new"/"construction" right after it ("Duplex - new construction", "mobile home set up").
_NEW_BEFORE = re.compile(
    r"\b(?:new|construct\w*|build|building\s+(?:an?|one)|erect\w*|set\s*-?\s*up|setup|set)\b"
    r"(?:\W+\w+){0,3}?\W*$",
    re.I,
)
_NEW_STRICT = re.compile(
    r"(?:\bnew(?:\W+\w+)?|\b(?:construct\w*|build|building\s+(?:an?|one)|erect\w*)(?:\W+\w+){0,3}?)\W*$",
    re.I,
)
_NEW_AFTER = re.compile(
    r"^\W{0,3}(?:new(?:\s+construction)?(?=\s*(?:[-,.;:)]|$))|new\s+construction\b|construction\b"
    r"|set\s*-?\s*up\b|setup\b)",
    re.I,
)
_NSFD = re.compile(r"\bnsfd\b", re.I)

# Rule 6. Work on an existing building: alteration, repair, remodel, reroof, HVAC, addition.
ALTERATION = re.compile(
    r"\b(?:alter(?:ation)?s?|remodel\w*|renovat\w*|repair\w*|re-?roof\w*|roof(?:ing)?\s+replace\w*"
    r"|replace\w*\s+(?:the\s+)?(?:existing\s+)?(?:roof\w*|windows?|siding|deck|hvac|water\s+heater|furnace)"
    r"|hvac|heat\s+pump|change[- ]?out|additions?|upfit|up-fit|fit-?up|interior\s+(?:finish|demo\w*)"
    r"|damage\w*|reinforce\w*|tenant\s+finish|int\.?\s+alt)\b",
    re.I,
)

# Rule 6b. Work on a house. For houses, duplexes and the like (not ADUs or manufactured homes), without a
# new-construction cue, a type word next to these ("SFD revision", "adding a bedroom, single family") names
# the building worked on, not a new one: units stay None.
WORK_ITEM = re.compile(
    r"\b(?:add(?:ing|s|ed)?|install\w*|solar|pool|revision|existing|work\s+(?:will|to)"
    r"|finish(?:ing|ed)?\s+(?:off\s+)?(?:the\s+|an?\s+)?(?:basement|attic|bonus|space))\b",
    re.I,
)
_CONVERT_WORD = re.compile(r"\bconver(?:t|ts|ting|ted|sion)\b", re.I)

# Rule 7. Demolition of a whole building (common misspellings included; "wreck"/"wrecking" is Minneapolis's
# word for it, WS-MN #89). "Demo" followed by a permit
# number is a reference to another permit ("Complete DEMO-001048", "Demo 45399-2020", "demo BL-158040",
# "demo permit #..."); a plain number after it is a size ("DEMO 1731 SQ FT"). Interior, partial and
# selective demolition is alteration work.
DEMOLITION = re.compile(
    r"(?<!interior\s)(?<!partial\s)(?<!selective\s)"
    r"\b(?:demo|demol\w*|deconstruct\w*|raze|razing|tear\s*-?\s*down|wreck(?:s|ed|ing)?)\b"
    r"(?!\s*[-#]\s*\d|\s*:?\s*(?:[a-z]{1,6}-)?\d+-\d|\s*:?\s*[a-z]{1,6}-\d|\s+(?:permit|case|#))",
    re.I,
)
# Structures whose demolition removes no dwelling (used only when no dwelling word is present).
NON_DWELLING = re.compile(
    r"\b(?:garage|shed|carport|deck|porch|pool|barn|fence|gazebo|outbuilding|storage\s+building"
    r"|commercial\s+building|office\s+building|warehouse|retail|restaurant|church|school)\b",
    re.I,
)
_ACCESSORY_BUILDING = re.compile(r"\baccessory\s+(?:structures?|buildings?|bldgs?)\b", re.I)
_GENERIC_BUILDING = re.compile(r"\b(?:structures?|sturctures?|buildings?|bldgs?|ho+u?se)\b", re.I)
_HOUSE = re.compile(r"\b(?:house|home|residence|dwelling|cottage|bungalow)\b", re.I)

# Rule 8. Conversion of a building or space from one use to another: "convert(ing) X (in)to Y".
# The verb may also be remodel/alter/upfit/finish/change when the sentence reads "X (in)to Y"; the rule only
# fires when Y names a dwelling, so "remodel kitchen to open plan" is not a conversion.
CONVERSION = re.compile(
    r"\b(?:conver(?:t|ts|ting|ted|sion)|remodel\w*|alter(?:ation|ing|ed)?|upfit\w*|finish\w*|chang\w*)\b"
    r"(?:\s+of)?\s+(?P<src>.{0,60}?)\s+(?:in)?to\s+(?:(?:create|make|form|become)\s+)?(?P<dst>[^.;\n]{1,60})",
    re.I,
)
_SPACE_SOURCE = re.compile(
    r"\b(?:garage|basement|attic|office|commercial|retail|warehouse|church|school|hotel|motel|storage"
    r"|bonus\s+room|barn|shed|industrial|store|bank|accessory\s+(?:structure|building))\b",
    re.I,
)
_APARTMENT = re.compile(
    r"\b(?:an?\s+|one\s+)?(?:apartment|dwelling\s+unit|living\s+unit|residential\s+unit)\b", re.I
)

_TYPE_FOR_COUNT = [(5, "MF5"), (3, "U3_4"), (2, "U2")]


def _type_for_count(n: int) -> str | None:
    """Census size class of one building with n units; a single unit could be SFD, ADU or TH, so None."""
    return next((t for lo, t in _TYPE_FOR_COUNT if n >= lo), None)


@dataclass
class _Match:
    rule: str
    text: str
    start: int
    end: int
    btype: str | None = None
    units: int | None = None
    context: bool = False  # describes something existing, not what is being built


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _counts(text: str) -> list[_Match]:
    out = []
    for m in COUNT.finditer(text):
        n = _to_int(m.group("num"))
        noun = m.group("noun").lower()
        if re.fullmatch(r"\d{4}", m.group("num")) and 1900 <= n <= 2099:
            continue  # a year
        if n < 1 or n > 2000:
            continue
        if _SUBSET.search(m.group("qual")):
            continue  # "2 HC units": accessible units within a building
        if _LABEL_BEFORE.search(text[max(0, m.start() - 15) : m.start()]):
            continue  # "Building 5 units 101-110", "Lot 12 unit"
        if noun in ("unit", "du") and _ADDRESS_AFTER.match(text[m.end() :]):
            continue  # "5 UNIT 101": a unit number, not a count
        if not noun.startswith(("unit", "dwelling unit", "du")) and _BUILDINGS_AFTER.match(text[m.end() :]):
            continue  # "7 apts bldgs": a count of buildings
        if _STACKED_BEFORE.search(text[max(0, m.start() - 12) : m.start()]):
            continue  # "2 over 2 condominiums": a stacked-flat style, not a count
        rule = "project total" if _is_project_total(text, m) else "count"
        hit = _Match(rule, m.group(0), m.start(), m.end(), _type_for_count(n), n)
        if noun.startswith(("townho", "row")):
            hit.btype = "TH"
        elif noun.startswith(("adu", "accessory")):
            hit.btype = "ADU"
        hit.context = _is_context(text, hit, other_permit=False)  # a case number after a count is not a ref
        out.append(hit)
    return out


def _is_context(text: str, hit: _Match, single_family: bool = False, other_permit: bool = True) -> bool:
    """Does this mention describe an existing or separately permitted building rather than what is built?"""
    if _CONTEXT_BEFORE.search(text[max(0, hit.start - 40) : hit.start]):
        return True
    after = text[hit.end :]
    if other_permit and _OTHER_PERMIT_AFTER.match(after):
        return True
    if _is_new(text, hit):  # "NEW SINGLE FAMILY DWELLING Demo-003862-2021": the reference is the demolition
        return False
    return bool(
        (other_permit and _PERMIT_NUMBER_AFTER.match(after))
        or (single_family and _CONTEXT_AFTER.match(after))
    )


def _types(text: str) -> list[_Match]:
    out = []
    for name, pattern, btype, units in TYPE_RULES:
        for m in pattern.finditer(text):
            plural = m.group(0).lower().endswith(("plexes", "duplexes"))
            hit = _Match(name, m.group(0), m.start(), m.end(), btype, None if plural else units)
            hit.context = _is_context(text, hit, single_family=btype == "SFD")
            out.append(hit)
    for m in ADU.finditer(text) if not _ADU_NEGATED.search(text) else ():
        hit = _Match("accessory dwelling", m.group(0), m.start(), m.end(), "ADU", 1)
        hit.context = _is_context(text, hit)
        out.append(hit)
    return out


def _is_new(text: str, hit: _Match, strict: bool = False) -> bool:
    """New construction of this dwelling? `strict` (used when the text also names alteration work) lets
    at most one word sit between "new" and the dwelling ("new custom home", not "new cabinets in home")."""
    before = text[max(0, hit.start - 50) : hit.start]
    m = (_NEW_STRICT if strict else _NEW_BEFORE).search(before)
    if m and not ALTERATION.search(m.group(0)):
        return True
    return bool(_NEW_AFTER.match(text[hit.end :]) or _NSFD.search(hit.text))


def _adu_kind(text: str) -> tuple[str, str | None]:
    for kind, pattern in ADU_KIND:
        m = pattern.search(text)
        if m:
            return kind, m.group(0)
    return "unknown", None


def _ev(rule: str, phrase: str) -> str:
    return f"{rule}: '{_clean(phrase)}'"


def _units_of(fragment: str) -> tuple[int | None, str | None, str | None]:
    """(units, building type, rule) of the dwelling a short phrase names; units 0 for non-dwelling space."""
    counts = [c for c in _counts(fragment)]
    if len({c.units for c in counts}) == 1:
        return counts[0].units, counts[0].btype, "count"
    for name, pattern, btype, units in TYPE_RULES:
        if pattern.search(fragment):
            return units, btype, name
    if ADU.search(fragment):
        return 1, "ADU", "accessory dwelling"
    if _HOUSE.search(fragment):
        return 1, "SFD", "house"
    if _SPACE_SOURCE.search(fragment):
        return 0, None, "non-dwelling space"
    return None, None, None


def _conversion(text: str) -> PermitTextFacts | None:
    """Rule 8: net units from 'convert <source> to <destination>' when both name dwellings or spaces."""
    m = CONVERSION.search(text)
    if not m:
        return None
    src_units, _, src_rule = _units_of(m.group("src"))
    dst_text = m.group("dst")
    dst_units, dst_type, dst_rule = _units_of(dst_text)
    if (
        dst_rule in (None, "non-dwelling space")
        and src_rule == "non-dwelling space"
        and _APARTMENT.match(dst_text)
    ):
        dst_units, dst_type, dst_rule = 1, "ADU", "apartment in former non-dwelling space"
    if dst_rule in (None, "non-dwelling space"):
        return None  # e.g. "convert bedroom to bathroom": not a change in dwellings
    ev = [_ev("conversion", m.group(0))]
    adu_type = None
    if dst_type == "ADU":
        kind, phrase = _adu_kind(text)
        adu_type = kind
        if phrase:
            ev.append(_ev(f"ADU kind {kind}", phrase))
    if src_units is None or dst_units is None:
        return PermitTextFacts(
            building_type_std=dst_type, adu_type=adu_type, is_conversion=True, evidence=tuple(ev)
        )
    # An ADU made from a garage, basement or part of a house adds one dwelling; else net = after - before.
    net = 1 if dst_type == "ADU" else dst_units - src_units
    return PermitTextFacts(
        units_new=max(net, 0),
        units_removed=max(-net, 0),
        building_type_std=dst_type,
        adu_type=adu_type,
        is_conversion=True,
        evidence=tuple(ev),
    )


def _demolition(text: str, demo: re.Match[str], hits: list[_Match]) -> PermitTextFacts:
    """Rule 7: a demolition-only permit. units_new 0; units_removed from what is demolished."""
    ev = [_ev("demolition", demo.group(0))]

    def out(removed: int | None, btype: str | None, *more: str) -> PermitTextFacts:
        adu_type = "unknown" if btype == "ADU" else None
        return PermitTextFacts(
            units_new=0,
            units_removed=removed,
            building_type_std=btype,
            adu_type=adu_type,
            is_demolition=True,
            evidence=(*ev, *more),
        )

    counts = [h for h in hits if h.rule == "count"]
    words = [h for h in hits if h.rule != "count"]
    if len({h.units for h in counts}) == 1:
        n = counts[0].units
        return out(n, counts[0].btype or _type_for_count(n), _ev("count", counts[0].text))
    if counts:
        return out(None, None, "conflict: several unit counts")
    if len({(h.btype, h.units) for h in words}) == 1:
        return out(words[0].units, words[0].btype, _ev(words[0].rule, words[0].text))
    if words:
        return out(None, None, "conflict: several building types")
    house = _HOUSE.search(text)
    if house:
        return out(1, "SFD", _ev("house", house.group(0)))
    other = NON_DWELLING.search(text)
    rest = _ACCESSORY_BUILDING.sub(" ", NON_DWELLING.sub(" ", text))
    if other and not _GENERIC_BUILDING.search(
        rest
    ):  # "demo structure and garage": the structure may be a house
        return out(0, "OTHER", _ev("non-dwelling structure", other.group(0)))
    return out(None, None)


def parse_description(text: str | None) -> PermitTextFacts:
    """Read units, building type, ADU kind, demolition and conversion from a permit description.

    Returns a `PermitTextFacts` whose fields are `None` wherever the text does not say. Every value is an
    inference: callers mark it `inferred` and use it only to fill a missing structured value.
    """
    if text is None or not str(text).strip():
        return PermitTextFacts()
    text = _clean(str(text))

    converted = _conversion(text)
    if converted is not None:
        return converted

    hits = _types(text) + _counts(text)
    notes: list[str] = []
    if any(h.rule == "project total" for h in hits):
        several = _ONE_OF_SEVERAL.search(text)
        if several:  # Rule 1b: this permit is one building of a larger project
            notes.append(
                _ev("project total ignored, the permit names one building of several", several.group(0))
            )
            hits = [h for h in hits if h.rule != "project total"]
        else:
            for h in hits:
                h.rule = "count" if h.rule == "project total" else h.rule
    demo = DEMOLITION.search(text)
    building = [h for h in hits if not h.context]
    alteration = ALTERATION.search(text)
    is_new = any(_is_new(text, h, strict=alteration is not None) for h in building)

    if demo and not is_new:
        return _demolition(text, demo, hits)

    convert = _CONVERT_WORD.search(text)
    if convert and building and not is_new:  # Rule 8b: a conversion we could not read in full
        if {h.btype for h in building} == {"ADU"}:  # "ADU - convert existing garage": one new ADU
            kind, phrase = _adu_kind(text)
            more = (_ev(f"ADU kind {kind}", phrase),) if phrase else ()
            return PermitTextFacts(
                units_new=1,
                units_removed=0,
                building_type_std="ADU",
                adu_type=kind,
                is_conversion=True,
                evidence=(_ev("conversion to an ADU", convert.group(0)), *more),
            )
        return PermitTextFacts(evidence=(_ev("conversion named, change in units unclear", convert.group(0)),))

    if alteration and not is_new:
        if any(h.btype == "ADU" for h in building):
            return PermitTextFacts(
                evidence=(_ev("alteration", alteration.group(0)), "ADU named: unit change unclear")
            )
        return PermitTextFacts(units_new=0, evidence=(_ev("alteration", alteration.group(0)),))

    facts = _new_building(text, building, demo, is_new)
    return replace(facts, evidence=(*facts.evidence, *notes)) if notes else facts


def _new_building(
    text: str, building: list[_Match], demo: re.Match[str] | None, is_new: bool
) -> PermitTextFacts:
    """Rules 1-3 for a permit that builds dwellings: agree on one type and one count, or say None."""
    ev = [_ev(h.rule, h.text) for h in sorted(building, key=lambda h: h.start)]
    if demo:
        ev.append(_ev("demolition mentioned alongside new construction", demo.group(0)))
    if not building:
        return PermitTextFacts(evidence=tuple(ev))

    counts = sorted({h.units for h in building if h.rule == "count"})
    count_types = {h.btype for h in building if h.rule == "count" and h.btype in ("TH", "ADU")}
    words = [h for h in building if h.rule != "count"]
    word_types = {h.btype for h in words} | count_types

    if "ADU" in word_types and len(word_types) > 1:
        return PermitTextFacts(evidence=(*ev, "conflict: an ADU and another dwelling type"))
    if len(word_types) > 1:
        return PermitTextFacts(evidence=(*ev, "conflict: several building types"))
    if len(counts) > 1:
        btype = next(iter(word_types)) if word_types else None
        return PermitTextFacts(building_type_std=btype, evidence=(*ev, "conflict: several unit counts"))

    btype = next(iter(word_types)) if word_types else None
    adu_type = None
    if btype == "ADU":
        kind, phrase = _adu_kind(text)
        adu_type = kind
        if phrase:
            ev.append(_ev(f"ADU kind {kind}", phrase))

    if counts:
        n = counts[0]
        if btype is None or btype == "DTQ":
            if btype == "DTQ" and not 2 <= n <= 4:
                return PermitTextFacts(evidence=(*ev, "conflict: count outside 2-4"))
            return PermitTextFacts(units_new=n, building_type_std=_type_for_count(n), evidence=tuple(ev))
        if btype == "MF5" and n < 5:
            return PermitTextFacts(evidence=(*ev, "conflict: count below 5"))
        if btype == "TH" and n > 1:
            # Rule 2b: a townhouse count describes the row building. Many places issue one permit per
            # townhouse, so the row size is reported apart from units_new.
            return PermitTextFacts(
                building_type_std="TH", building_units=n, evidence=(*ev, "townhouse row size")
            )
        implied = {h.units for h in words}
        if btype in ("TH", "ADU", "MF5") or implied == {n}:
            return PermitTextFacts(
                units_new=n, building_type_std=btype, adu_type=adu_type, evidence=tuple(ev)
            )
        return PermitTextFacts(evidence=(*ev, "conflict: count does not match the building type"))

    implied = {h.units for h in words}
    units = implied.pop() if len(implied) == 1 else None
    work = WORK_ITEM.search(text)
    if units is not None and btype not in ("ADU", "OTHER") and not is_new and work:
        units = None
        ev.append(_ev("work item without new-construction cue, units unclear", work.group(0)))
    return PermitTextFacts(units_new=units, building_type_std=btype, adu_type=adu_type, evidence=tuple(ev))
