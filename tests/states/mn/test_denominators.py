"""MN denominators: one parcel source per jurisdiction before the shared eligible-parcel rule."""

import pandas as pd

from lotline.adapters.states.mn import denominators as d
from lotline.build import eligible as elig
from lotline.config import load_state

MPLS, STP, EDINA = "2743000", "2758000", "2718188"


def _parcels() -> pd.DataFrame:
    rows = [
        # Minneapolis appears in two sources: only the assessor rows count
        ("1", MPLS, 2023, "SF_DETACHED", 1, "mpls_assessor_parcels"),
        ("2", MPLS, 2023, "SF_DETACHED", 1, "mpls_assessor_parcels"),
        ("1", MPLS, 2023, "SF_DETACHED", None, "metc_parcels"),
        ("2", MPLS, 2023, "SF_DETACHED", None, "metc_parcels"),
        ("3", MPLS, 2023, "SF_DETACHED", None, "metc_parcels"),
        # suburban Ramsey in two sources: only Met Council counts
        ("4", STP, 2023, "SF_DETACHED", 1, "metc_parcels"),
        ("4", STP, 2023, "SF_DETACHED", 1, "ramsey_parcels"),
        ("5", EDINA, 2023, "DUPLEX", 2, "metc_parcels"),
        ("6", EDINA, 2023, "SF_DETACHED", None, "metc_parcels"),
    ]
    df = pd.DataFrame(
        rows, columns=["parcel_id", "jurisdiction_geoid", "vintage", "land_use_std", "units", "source"]
    )
    return df.assign(state="MN", lot_sqft=6000.0, units=df["units"].astype("Int64"))


JURIS = pd.DataFrame(
    {
        "geoid": [MPLS, STP, EDINA],
        "name": ["Minneapolis city", "St. Paul city", "Edina city"],
        "kind": "place",
        "county_geoid": ["27053", "27123", "27053"],
        "pop_2020": [429954, 311527, 53494],
        "data_tier": 1,
    }
)


def _eligible() -> pd.DataFrame:
    return elig.from_parcels(elig.single_source(_parcels(), load_state("MN").parcel_sources), JURIS)


def test_mn_config_picks_one_source_per_jurisdiction():
    choice = load_state("MN").parcel_sources
    assert choice == {"2743000": "mpls_assessor_parcels", "*": "metc_parcels"}
    kept = elig.single_source(_parcels(), choice)
    assert set(kept.loc[kept.jurisdiction_geoid == MPLS, "source"]) == {"mpls_assessor_parcels"}
    assert set(kept["source"]) == {"mpls_assessor_parcels", "metc_parcels"}
    assert len(kept) == 5


def test_eligible_counts_use_the_chosen_source():
    e = _eligible().set_index(["jurisdiction_geoid", "theme"])
    assert e.loc[(MPLS, "adu"), "eligible_parcels"] == 2  # not 5: Met Council's copy is left out
    assert e.loc[(STP, "adu"), "eligible_parcels"] == 1
    assert e.loc[(EDINA, "adu"), "eligible_parcels"] == 1  # the duplex isn't eligible
    assert e.loc[(MPLS, "adu"), "denominator_quality"] == "high"
    assert e.loc[(EDINA, "adu"), "denominator_quality"] == "low"  # units unknown: an assumption


def test_compare_with_acs():
    e = _eligible()
    acs = e.assign(eligible_parcels=[4, 4, 1, 1, 2, 2], denominator_source="acs_sf_fallback")
    c = d.compare_with_acs(e, acs, JURIS, year=2023, largest=2).set_index("geoid")
    assert list(c.index) == [MPLS, STP]
    assert c.loc[MPLS, "ratio"] == 0.5
