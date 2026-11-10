"""Cleveland permits adapter on synthetic rows (no real data): building type and units from the work and use
group, the ADU description rule and its vetoes, house + ADU permits, parcel IDs, and the schema."""

import pandas as pd
import pytest

from lotline.adapters.states.oh import cle_permits as cp
from lotline.schemas import validate

MS_2021 = 1_620_000_000_000  # 2021-05-03


def _raw(rows):
    cols = ["OBJECTID", "PERMIT_ID", "PERMIT_TYPE", "PERMIT_SUBTYPE", "PERMIT_CATEGORY", "JOB_DESCRIPTION",
            "USE_GROUP_1", "WORK_DESCRIPTION", "JOB_VALUE", "ISSUE_DATE", "PARCEL_NUMBER", "SIZE_OF_BUILDING",
            "DW_Form_Based_Code_Area"]  # fmt: skip
    out = []
    for i, (pid, work, use, text, issued) in enumerate(rows):
        out.append([i, pid, "Building Permit", "Residential", "New", work, use, text, 1000.0, issued,
                    "104-14-018", "", None])  # fmt: skip
    return pd.DataFrame(out, columns=cols)


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("ERECT 2 STORY FRAME GARAGE W/ IN-LAW SUITE ABOVE PER BOZA 20-138", "detached"),
        ("ERECT REAR 2 STORY FRAME SINGLE FAMILY IN-LAW SUITE CARRIAGE HOUSE PER PLAN", "detached"),
        ("CONVERT BASEMENT TO ACCESSORY DWELLING UNIT", "internal_conversion"),
        ("ERECT 20 X 32 2 STORY ATTACHED ADDITION FOR MOTHER-IN-LAW SUITE", "attached"),
        ("NEW ADU PER PLAN", "unknown"),
        ("ESTABLISH ADULT DAY CARE USE", None),  # "adult" is not "ADU"
        ("INSTALL NEW WIRING FOR KITCHEN (NOT FOR IN-LAW SUITE)", None),
        ("MAKE INTERIOR ALTERATIONS TO 942 SF CARRIAGE HOUSE PER APPROVED PLANS", None),
        ("EXISTING CARRIAGE HOUSE INTERIOR ALTERATION", None),
        ("DEMOLISH CARRIAGE HOUSE", None),
        ("REROOF GARAGE", None),
        (None, None),
    ],
)
def test_adu_rule(text, kind):
    assert cp.adu_from_text(text) == kind


def test_house_and_adu():
    assert cp.builds_house_too(
        "CONSTRUCT A NEW 2 STY SINGLE FAMILY RESIDENCE W/ DET GARAGE AND IN-LAW SUITE ABOVE"
    )
    assert cp.builds_house_too(
        "ERECT A 2 STY 3,708 S.F. SINGLE FAMILY RESIDENCE W/IN-LAW SUITE ABOVE ATTACHED GARAGE"
    )
    assert cp.builds_house_too(
        "CONSTRUCT A NEW 2 STY 3101 SF WOOD FRAME SINGLE FAM RES W/ DET GARAGE AND IN-LAW SUITE"
    )
    assert not cp.builds_house_too("ERECT 2 STORY FRAME GARAGE W/ IN-LAW SUITE ABOVE")
    assert not cp.builds_house_too(
        "ERECT REAR 2 STORY FRAME SINGLE FAMILY IN-LAW SUITE CARRIAGE HOUSE WITH GARAGE BELOW"
    )
    assert not cp.builds_house_too(
        "ERECT NEW 2 STORY FRAME SINGLE FAMILY RESIDENCE IN-LAW SUITE ON SECOND FLOOR OF EXISTING GARAGE"
    )


def test_build_types_units_and_adus():
    raw = _raw(
        [
            ("B1", "New Construction", "One Family", "ERECT NEW SFD", MS_2021),
            ("B2", "New Construction", "Two Family", "ERECT 2 FAMILY", MS_2021),
            ("B3", "Demolition", "Two Family", "RAZE 2 FAMILY", MS_2021),
            ("B4", "Demolition", "Accessory Use", "RAZE GARAGE", MS_2021),
            ("B5", "Fence-Garage-Deck-Pool", "Accessory Use", "ERECT GARAGE W/ IN-LAW SUITE ABOVE", MS_2021),
            ("B6", "New Construction", "One Family",
             "CONSTRUCT A NEW SINGLE FAMILY RESIDENCE W/ DET GARAGE AND IN-LAW SUITE ABOVE", MS_2021),
            ("B7", "Alteration", "R-2 Residential - Permanent Housing", "RENOVATE CARRIAGE HOUSE",
             MS_2021),
            ("B8", "Alteration", "One Family", "KITCHEN REMODEL", None),  # never issued: dropped
        ]
    )  # fmt: skip
    out = cp.build(raw).set_index("permit_id")
    assert len(out) == 7
    assert out.loc["cle-B1", ["building_type_std", "units_new"]].tolist() == ["SFD", 1]
    assert out.loc["cle-B2", ["building_type_std", "units_new"]].tolist() == ["U2", 2]
    assert out.loc["cle-B3", "units_removed"] == 2 and out.loc["cle-B3", "is_demolition"]
    assert out.loc["cle-B4", "units_removed"] == 0
    assert out.loc["cle-B5", ["building_type_std", "adu_type", "units_new"]].tolist() == [
        "ADU",
        "detached",
        1,
    ]
    assert out.loc["cle-B6", ["building_type_std", "adu_type", "units_new"]].tolist() == [
        "SFD",
        "detached",
        1,
    ]
    assert pd.isna(out.loc["cle-B7", "adu_type"]) and out.loc["cle-B7", "building_type_std"] == "OTHER"
    assert out.loc["cle-B1", "parcel_id"] == "3903510414018"
    assert out.loc["cle-B1", "jurisdiction_geoid"] == cp.CLEVELAND_GEOID
    validate(out.reset_index(), "permits")


def test_no_personal_fields_requested():
    assert not cp.PERSONAL & set(cp.OUT_FIELDS)
    with pytest.raises(AssertionError):
        cp.build(_raw([]).assign(PRIMARY_ADDRESS=[]))


def test_registered():
    from lotline import registry

    assert registry.sources_for("OH")["cle_permits"].module.TABLE == "permits"
