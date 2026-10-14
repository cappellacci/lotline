"""Tests for lotline.parse.permit_text: every rule and every trap, on synthetic descriptions.

Each row is a description written for this test (never a real permit record) and the facts a careful
reader would take from it, checked by hand. Fields not listed in a row are expected to be None.
"""

import dataclasses

import pytest

from lotline.parse import PermitTextFacts, parse_description

N, R, T, A, D, C, B = (
    "units_new",
    "units_removed",
    "building_type_std",
    "adu_type",
    "is_demolition",
    "is_conversion",
    "building_units",
)

CASES = [
    # --- Rule 1: unit counts in front of a dwelling noun -----------------------------------------------
    ("Apartment building, 48 units", {N: 48, T: "MF5"}),
    ("New construction 48 apt units with podium parking", {N: 48, T: "MF5"}),
    ("Mixed use building, ground floor retail and 120 dwelling units above", {N: 120, T: "MF5"}),
    ("construct (3) unit multifamily", {N: 3, T: "U3_4"}),
    ("New construction of three units on one lot", {N: 3, T: "U3_4"}),
    ("Twenty-four units, wood frame over slab", {N: 24, T: "MF5"}),
    ("New 6-plex with surface parking", {N: 6, T: "MF5"}),
    ("NEW 12 UNIT APARTMENT BLDG", {N: 12, T: "MF5"}),
    ("New 4 unit apartment building", {N: 4, T: "U3_4"}),
    ("High-rise tower with 1,200 units", {N: 1200, T: "MF5"}),
    ("Building 2 - 36 units, three story walk-up", {N: 36, T: "MF5"}),
    ("Condo building with 2 HC units, 18 units total", {N: 18, T: "MF5"}),
    # --- Rule 1b: project totals vs the building on this permit -----------------------------------------
    ("Bldg 5 of Maple Court apartment complex, 240 total units", {}),
    ("Building C - project consisting of a 150 unit development in four buildings", {}),
    ("New apartment complex with 64 units, one building", {N: 64, T: "MF5"}),
    ("Two townhouse style buildings that consist of 6 units each", {N: 6, T: "MF5"}),
    ("Senior Housing Project - Building 2: a 30 unit apartment building", {N: 30, T: "MF5"}),
    # --- Rule 2: building-type words ---------------------------------------------------------------------
    ("Duplex", {N: 2, T: "U2"}),
    ("New two-family dwelling, slab on grade", {N: 2, T: "U2"}),
    ("New triplex", {N: 3, T: "U3_4"}),
    ("Construct new quadplex", {N: 4, T: "U3_4"}),
    ("New fourplex, sealed crawl", {N: 4, T: "U3_4"}),
    ("New single family dwelling, 2 car garage", {N: 1, T: "SFD"}),
    ("NSFD lot 14 slab", {N: 1, T: "SFD"}),
    ("SFD", {N: 1, T: "SFD"}),
    ("Set up manufactured home on pad", {N: 1, T: "OTHER"}),
    ("Two duplexes on one lot", {T: "U2"}),  # two buildings: no single count
    ("2-4 units, building size not decided", {T: "DTQ"}),
    ("New small multifamily building", {T: "DTQ"}),
    ("5 or more units, design pending", {T: "MF5"}),
    ("Townhouses, row of new homes", {T: "TH"}),
    ("NEW 4-UNIT TOWNHOME BLDG", {T: "TH", B: 4}),  # row size, not this permit's count
    ("Duplex with 4 units", {}),  # contradiction: no type, no count
    # --- Rule 3: accessory dwelling units ----------------------------------------------------------------
    ("ADU", {N: 1, T: "ADU", A: "unknown"}),
    ("New detached accessory dwelling unit in rear yard", {N: 1, T: "ADU", A: "detached"}),
    ("Attached ADU off kitchen wing", {N: 1, T: "ADU", A: "attached"}),
    ("Garage apartment", {N: 1, T: "ADU", A: "unknown"}),
    ("New backyard cottage", {N: 1, T: "ADU", A: "detached"}),
    ("Mother-in-law suite", {N: 1, T: "ADU", A: "unknown"}),
    ("Basement apartment with separate entrance", {N: 1, T: "ADU", A: "internal_conversion"}),
    ("ADU behind existing single family home", {N: 1, T: "ADU", A: "unknown"}),
    ("ADU - duplex permitted separately", {N: 1, T: "ADU", A: "unknown"}),
    ("New SFD with detached ADU", {}),  # two dwellings, maybe two permits: no guess
    ("Pool house with half bath, not an ADU", {}),
    # --- Rule 4: context words (existing or separately permitted buildings) ------------------------------
    ("New duplex replacing existing single family home", {N: 2, T: "U2"}),
    ("Detached garage for the new SFD on separate permit", {}),
    # --- Rule 6: alterations give 0 new units only when the text says so --------------------------------
    ("Kitchen remodel", {N: 0}),
    ("Reroof, tear off and replace shingles", {N: 0}),
    ("HVAC changeout", {N: 0}),
    ("Repair fire damage to rear wall", {N: 0}),
    ("Addition to single family home, new bedroom", {N: 0}),
    ("Remodel kitchen with new cabinets in single family home", {N: 0}),
    ("Interior renovation of 24 apartment units", {N: 0}),
    ("Remodel existing ADU bathroom", {N: 0}),  # the ADU already exists
    ("ADU renovation and new kitchen", {}),  # an ADU is named but not as existing: unit change unclear
    ("Deck add on SFD", {}),  # a house is named but nothing says new: unknown, not 1
    ("Install solar panels", {}),  # says nothing about dwellings: unknown, not 0
    # --- Rule 7: demolition ------------------------------------------------------------------------------
    ("Demo SFD", {N: 0, R: 1, T: "SFD", D: True}),
    ("Demolish existing house", {N: 0, R: 1, T: "SFD", D: True}),
    ("Demolition of duplex", {N: 0, R: 2, T: "U2", D: True}),
    ("Demo of entire 8 unit building", {N: 0, R: 8, T: "MF5", D: True}),
    ("Demo detached garage", {N: 0, R: 0, T: "OTHER", D: True}),
    ("Demo structure and garage", {N: 0, D: True}),  # the structure may be a house: removed unknown
    ("Demolition", {N: 0, D: True}),
    ("Interior demolition only, non-structural", {N: 0}),  # alteration, not a demolition
    ("New duplex. Complete DEMO-004512-2022 first", {N: 2, T: "U2"}),  # a reference to another permit
    # --- Rule 8: conversions -----------------------------------------------------------------------------
    ("Convert single family to duplex", {N: 1, R: 0, T: "U2", C: True}),
    ("Convert duplex into single family dwelling", {N: 0, R: 1, T: "SFD", C: True}),
    ("Convert garage to ADU", {N: 1, R: 0, T: "ADU", A: "unknown", C: True}),
    ("Convert basement into apartment", {N: 1, R: 0, T: "ADU", A: "internal_conversion", C: True}),
    ("Conversion of office building to 30 units", {N: 30, R: 0, T: "MF5", C: True}),
    ("Converting existing bedroom into a bathroom", {}),  # not a change in dwellings
    # --- traps: never read as unit counts ----------------------------------------------------------------
    ("New 2 story 4 bedroom single family dwelling", {N: 1, T: "SFD"}),
    ("3 bedroom units", {}),
    ("4 story building", {}),
    ("123 Main St Unit 5", {}),
    ("Apt B, 400 Oak Ave", {}),
    ("Units 101 & 102", {}),
    ("Building 5 units 101-110 electrical", {}),
    ("Permit 2024-00123 reissued", {}),
    ("Built 2024 units", {}),  # a year in front of a noun is still a year
    ("24x30 garage", {}),
    ("R-2 apt, type V-A", {}),
    ("4 new apartment buildings", {}),  # counts buildings, not units
    ("New 2 over 2 condominiums", {}),  # a stacked-flat style
    ("Lot 12 unit", {}),
    ("", {}),
    (None, {}),
]


@pytest.mark.parametrize(("text", "expected"), CASES, ids=[repr(c[0])[:50] for c in CASES])
def test_parse_description(text, expected):
    facts = parse_description(text)
    got = {f.name: getattr(facts, f.name) for f in dataclasses.fields(facts) if f.name != "evidence"}
    want = {name: expected.get(name) for name in got}
    assert got == want, facts.evidence


def test_every_value_is_traceable_to_evidence():
    facts = parse_description("New construction 48 apt units with podium parking")
    assert facts.evidence == ("count: '48 apt units'",)
    facts = parse_description("Demo SFD")
    assert facts.evidence == ("demolition: 'Demo'", "single-family house: 'SFD'")


def test_unknown_is_none_never_zero():
    assert parse_description("Lot 7, Oak Hill subdivision") == PermitTextFacts()
    assert parse_description("   ") == PermitTextFacts()


def test_result_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        parse_description("Duplex").units_new = 3  # type: ignore[misc]


@pytest.mark.parametrize(
    ("text", "removed"),
    [
        ("Wrecking a single family dwelling", 1),  # Minneapolis's wording (WS-MN #89): was read as a NEW SFD
        ("WRECK existing duplex", 2),
        ("wrecked single-family house and detached garage", 1),
    ],
)
def test_wrecking_is_demolition_not_new_construction(text, removed):
    facts = parse_description(text)
    assert facts.is_demolition is True and facts.units_new == 0 and facts.units_removed == removed
