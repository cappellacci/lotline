"""Tests for lotline.parse.permit_text: every rule and every trap, on synthetic descriptions.

Each row is a description written for this test (never a real permit record) and the facts a careful
reader would take from it, checked by hand. Fields not listed in a row are expected to be None.
"""

import dataclasses

import pytest

from lotline.parse import PermitTextFacts, parse_description

N, R, T, A, D, C, B, X = (
    "units_new",
    "units_removed",
    "building_type_std",
    "adu_type",
    "is_demolition",
    "is_conversion",
    "building_units",
    "adu_removed",
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
    # --- ADU misreads fixed 2026-11-10 (Ben approved the parser change) -----------------------------------
    # (1) a second home on the lot called an "additional dwelling unit"; fee language is not one
    ("Additional dwelling unit behind existing house", {N: 1, T: "ADU", A: "unknown"}),
    ("New additional dwelling unit in rear yard", {N: 1, T: "ADU", A: "unknown"}),
    ("Second dwelling unit on lot, 1 bed 1 bath", {N: 1, T: "ADU", A: "unknown"}),
    ("Impact fee per additional dwelling unit", {}),
    ("Water tap charge of $1,200 for each additional dwelling unit", {}),
    ("New 12 unit apartment building, SDC assessed per additional dwelling unit", {N: 12, T: "MF5"}),
    ("Additional living quarters for pool house", {}),  # TX "ALQ": mostly pool houses, not an ADU
    # (2) Cary's utility dwelling unit (UDU), its name for an attached or internal ADU before 2025
    ("Utility dwelling unit over attached garage", {N: 1, T: "ADU", A: "unknown"}),
    ("New UDU with kitchenette and outside entrance", {N: 1, T: "ADU", A: "unknown"}),
    ("Accessory use permit - utility dwelling", {N: 1, T: "ADU", A: "unknown"}),
    ("Finish utilitydwelling unit on 2nd floor", {N: 1, T: "ADU", A: "unknown"}),
    ("Addition - UDU, screened porch and deck", {N: 1, R: 0, T: "ADU", A: "attached"}),
    ("Bonus room over garage, NOT A UDU", {}),
    # (3) an ADU created by an addition or a conversion of existing space
    ("ADU addition w/ porch", {N: 1, R: 0, T: "ADU", A: "attached"}),
    ("Addition - ADU", {N: 1, R: 0, T: "ADU", A: "attached"}),
    ("Rear ADU addition, expand footprint", {N: 1, R: 0, T: "ADU", A: "attached"}),
    ("Remodel lower level for ADU", {N: 1, R: 0, T: "ADU", A: "internal_conversion", C: True}),
    ("Basement conversion to ADU", {N: 1, R: 0, T: "ADU", A: "internal_conversion", C: True}),
    ("Converting detached garage to ADU", {N: 1, R: 0, T: "ADU", A: "detached", C: True}),
    ("Upfit unfinished space into ADU", {N: 1, R: 0, T: "ADU", A: "unknown", C: True}),
    ("Attic remodel (ADU) and porch addition", {N: 1, R: 0, T: "ADU", A: "internal_conversion", C: True}),
    ("Addition to existing ADU, new bedroom", {N: 0}),  # the ADU is already there
    ("Remodel of ADU kitchen", {}),  # work on an ADU: unit change unclear, not a new one
    ("ADU addition, repair rot at sill plate", {}),  # repair work: unclear
    ("Upfit suite 200 for ADU Inc. offices", {}),  # a company name, not a unit
    ("New SFD with ADU addition planned", {}),  # a new house and an ADU: no guess
    ("New single family home, future ADU", {}),  # a new house that mentions an ADU is not an ADU
    # (4) an ADU taken out of use is a removal, never a new ADU
    ("Removing kitchen, no longer using as ADU", {N: 0, R: 1, X: True}),
    ("Remove existing ADU and restore garage", {N: 0, R: 1, X: True}),
    ("ADU abandonment, cap plumbing", {N: 0, R: 1, X: True}),
    ("Convert ADU back to single family dwelling", {N: 0, R: 1, C: True, X: True}),
    ("Change of use from a permitted ADU to home office", {N: 0, R: 1, X: True}),
    ("Remove ADU kitchen, convert back to single family", {N: 0, R: 1, C: True, X: True}),
    ("Remove ADU deck and repair stairs", {}),  # a part of the ADU, not the ADU: no removal
    ("Garage where the ADU was, new slab", {}),  # a former ADU is context, not a new one
    ("Not to be used as an accessory dwelling unit or have cooking appliances", {}),
    ("Detached garage, not approved for use as an ADU", {}),
    ("New SFD; remove existing ADU", {N: 1, T: "SFD"}),  # the new house still counts
    ("Demolish ADU", {N: 0, R: 1, T: "ADU", A: "unknown", D: True}),  # a demolition stays Rule 7
    ("NEW ADU_New construction", {N: 1, T: "ADU", A: "unknown"}),  # an underscore no longer hides ADU
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
