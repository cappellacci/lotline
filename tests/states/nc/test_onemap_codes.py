"""Crosswalk drafter on synthetic code inventories (no network): the keyword rules, field choice and flags."""

import pandas as pd
import pytest

from lotline.adapters.states.nc import onemap_codes as oc


@pytest.mark.parametrize(
    "code, std",
    [
        ("1 Family Residential", "SF_DETACHED"),
        ("SINGLE FAMILY", "SF_DETACHED"),
        ("Modular", "SF_DETACHED"),  # a modular house is a house (Gaston's hand crosswalk)
        ("Single Family Attached Townhome", "SF_ATTACHED"),
        ("TWINHOME", "SF_ATTACHED"),
        ("Duplex/Triplex/Quadraplex", "TRI_QUAD"),
        ("2 Family Residential", "DUPLEX"),
        ("3 or more Family Residential", "MULTIFAMILY_5P"),  # "3 or more" includes 5+: never read as 3-4
        ("1.06-MF Dwellings", "MULTIFAMILY_5P"),
        ("Res Multiple Homes", "SF_DETACHED"),  # "multiple" is not "multifamily"
        ("DOUBLE WIDE MH", "MOBILE_HOME"),
        ("Mult-Sect Manufactured", "MOBILE_HOME"),
        ("Automobile Sales", "COMMERCIAL"),  # "automobile" is not "mobile"
        ("Warehouse", "INDUSTRIAL"),  # "warehouse" is not "house"
        ("4.01-Light Manuf", "INDUSTRIAL"),
        ("Residential Vacant Lot", "VACANT_RESIDENTIAL"),
        ("CLASS: RESIDENTIAL - VAC", "VACANT_RESIDENTIAL"),  # Vance
        ("03-MFR-CONST(04-COND/TWN/DUP-SFR)", "SF_ATTACHED"),  # Pitt: condo/townhouse/duplex, not a house
        ("warehouse condo", "COMMERCIAL"),
        ("BUILDERS LOT", "VACANT_RESIDENTIAL"),
        ("Vacant", None),  # a bare "vacant" could be any use: unknown, as in the hand crosswalks
        ("Vacant 10 Acres & Up", None),  # "acres" is not "res"
        ("93.00-Vacant Com", "COMMERCIAL"),
        ("95.00-Vacant Indus", "INDUSTRIAL"),
        ("94.00-Vacant Inst", "INSTITUTIONAL"),
        ("Owners Association Common Area", "OTHER"),
        ("Parking Lot", "OTHER"),
        ("1.12-Other Res", "OTHER"),
        ("Exempt Religious", "INSTITUTIONAL"),
        ("Public Utilities", "OTHER"),
        ("GENERAL FARM - PRESENT US", "AGRICULTURAL"),
        ("Eating Place-Consumption", "COMMERCIAL"),
        ("958", None),  # a bare numeric code has no label to read
        ("", None),
    ],
)
def test_keyword_rules(code, std):
    assert oc.classify(code)[0] == std


def inventory(rows):
    return pd.DataFrame(rows, columns=["field", "code", "n", "n_improved", "n_structyear", "truncated"])


def test_specific_field_first_free_text_and_unlabelled_fields_skipped():
    inv = inventory(
        [
            ("parusecode", "RES", 900, 850, 840, False),
            ("parusecode", "COM", 100, 90, 0, False),
            ("parusecd2", "10", 800, 790, 0, False),  # numeric codes: nothing to classify
            ("parusecd2", "18", 200, 150, 0, False),
            ("parusedsc2", "1 Family Residential", 700, 690, 0, False),
            ("parusedsc2", "Single Family Attached Townhome", 150, 150, 0, False),
            ("parusedsc2", "Duplex", 50, 50, 0, False),
            ("parusedsc2", "Business", 100, 90, 0, False),
            ("parusedesc", "free text", 1000, 900, 0, True),  # truncated by the server
        ]
    )
    d = oc.draft(inv)
    assert d.fields == ("parusedsc2", "parusecode")  # three residential types beat one
    assert set(d.rows["field"]) == {"parusedsc2", "parusecode"}
    assert d.vacant_when_unimproved  # 690 of 700 single-family parcels carry a building value
    assert d.built_signal == "improvval"
    assert d.land_use_share == pytest.approx(1.0)


def test_no_building_values_uses_structyear_and_no_vacant_flag():
    inv = inventory(
        [
            ("parusedesc", "SINGLE FAMILY", 900, 0, 880, False),
            ("parusedesc", "COMMERCIAL", 100, 0, 90, False),
        ]
    )
    d = oc.draft(inv)
    assert d.built_signal == "structyear" and not d.vacant_when_unimproved


def test_tiers_follow_d016_thresholds():
    rows = [("parusedesc", "SINGLE FAMILY", 950, 900, 850, False), ("parusedesc", "x7", 50, 0, 0, False)]
    d = oc.draft(inventory(rows))
    assert d.data_tier == 1  # 95% classified, 850/900 built with a year
    rows = [("parusedesc", "SINGLE FAMILY", 950, 900, 10, False), ("parusedesc", "x7", 50, 0, 0, False)]
    assert oc.draft(inventory(rows)).data_tier == 2
    rows = [("parusedesc", "SINGLE FAMILY", 600, 500, 500, False), ("parusedesc", "x7", 400, 0, 0, False)]
    assert oc.draft(inventory(rows)).data_tier == 3


def test_county_without_codes_has_no_fields():
    inv = inventory(
        [(f, "", 1000, 900, 0, False) for f in ("parusecode", "parusedesc", "parusecd2", "parusedsc2")]
    )
    d = oc.draft(inv)
    assert d.fields == () and d.data_tier == 3 and d.rows.empty
