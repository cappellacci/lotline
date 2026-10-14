"""Jurisdiction × year panel (protocol §5.1): numerator and denominator side by side, never a rate."""

import pandas as pd
import pytest

from lotline.build import panels
from lotline.io import DataStore
from lotline.schemas import validate
from lotline.validation.holdout import HoldoutLeak

ZERO = {f"{p}_{s}": 0 for p in ("bldgs", "units") for s in ("1", "2", "3_4", "5p")}


def _bps(rows):
    """rows: (bps_id, geoid, county, year, units_1, units_2, imputed)."""
    out = []
    for bps_id, geoid, county, year, u1, u2, imputed in rows:
        r = ZERO | {"units_1": u1, "units_2": u2, "bldgs_1": u1}
        r |= {f"{k}_rep": v for k, v in r.items() if k.startswith("units_")}
        out.append(
            r
            | {
                "state": "NC",
                "bps_id": bps_id,
                "geoid": geoid,
                "county_geoid": county,
                "name": bps_id,
                "year": year,
                "months_reported": 12,
                "imputed": imputed,
            }
        )
    return validate(pd.DataFrame(out), "bps_place_year")


BPS = _bps(
    [
        ("37000100", "3700001", "37001", 2023, 10, 2, False),
        ("37000100", "3700001", "37001", 2024, 12, 0, False),
        ("37000200", "3700002", "37001", 2024, 3, 0, False),  # same place filed under two BPS IDs...
        ("37000300", "3700002", "37003", 2024, 4, 2, True),  # ...in two counties: summed
        ("37001000", "37001", "37001", 2024, 50, 0, False),  # rest of county: county GEOID
        ("37009900", None, "37001", 2024, 7, 0, False),  # no GEOID: can't be matched, left out
    ]
)


def _eligible():
    rows = []
    for geoid, year, n in [("3700001", 2023, 1000), ("3700001", 2024, 1010), ("37001", 2024, 20000)]:
        for theme in ("adu", "missing_middle"):
            for rule in ("1.0", "0.9"):
                rows.append(
                    {
                        "state": "NC",
                        "jurisdiction_geoid": geoid,
                        "year": year,
                        "theme": theme,
                        "rule_version": rule,
                        "eligible_parcels": n
                        + (1 if theme == "missing_middle" else 0)
                        + (5 if rule == "0.9" else 0),
                        "data_tier": 3,
                        "denominator_source": "acs_sf_fallback",
                        "denominator_quality": "low",
                    }
                )
    return validate(pd.DataFrame(rows), "eligible_parcels")


MARKET = pd.DataFrame(
    {
        "geo": ["national:US", "national:US", "county:37001", "county:37001", "state:37", "state:37"],
        "year": [2023, 2024, 2023, 2024, 2023, 2024],
        "cpi_u": [304.70, 313.70, None, None, None, None],
        "mortgage_rate": [6.81, 6.72, None, None, None, None],
        "ppi_resid_inputs": [310.0, 315.2, None, None, None, None],
        "hpi": [None, None, 400.0, 410.0, 300.0, 305.0],
        "hpi_base2000": [None, None, 200.0, 205.0, 150.0, 152.5],
    }
)


def _panel(**kw):
    return panels.build(BPS, _eligible(), MARKET, theme="adu", rule_version="1.0", **kw).set_index(
        ["geoid", "year"]
    )


def test_numerator_sums_bps_rows_per_jurisdiction():
    """3700002 in 2024: units_1 = 3 + 4 = 7, units_2 = 0 + 2 = 2, two BPS rows, imputed if either was."""
    p = _panel()
    row = p.loc[("3700002", 2024)]
    assert (row["units_1"], row["units_2"], row["units_1_rep"], row["n_bps_rows"]) == (7, 2, 7, 2)
    assert bool(row["imputed"])
    assert p.loc[("37001", 2024), "units_1"] == 50
    assert len(p) == 4  # the GEOID-less row is not in the panel


def test_denominator_is_its_own_column_for_the_chosen_theme_and_rule():
    p = _panel()
    assert p.loc[("3700001", 2024), "eligible_parcels"] == 1010  # adu, rule 1.0 (not 1011 or 1015)
    assert p.loc[("37001", 2024), "eligible_parcels"] == 20000  # rest of county joins on the county GEOID
    assert p.loc[("3700001", 2024), "denominator_quality"] == "low"
    assert pd.isna(p.loc[("3700002", 2024), "eligible_parcels"])  # no denominator: missing, never 0
    mm = panels.build(BPS, _eligible(), MARKET, theme="missing_middle", rule_version="0.9")
    assert mm.set_index(["geoid", "year"]).loc[("3700001", 2023), "eligible_parcels"] == 1006


def test_panel_never_stores_a_rate():
    cols = set(panels.build(BPS, _eligible(), MARKET, theme="adu", rule_version="1.0").columns)
    suspicious = {c for c in cols if ("rate" in c or "per_" in c or "share" in c) and c != "mortgage_rate"}
    assert not suspicious
    assert {"units_1", "eligible_parcels"} <= cols


def test_unknown_theme_or_rule_version_raises():
    with pytest.raises(ValueError, match="theme='fees'"):
        panels.build(BPS, _eligible(), MARKET, theme="fees", rule_version="1.0")


def test_market_covariates_national_and_hpi_fallback():
    """3700002's BPS county (first by bps_id) is 37001, which has an HPI; with ('county', 'state') a
    jurisdiction in a county without one would fall back to state:37."""
    p = _panel()
    assert p.loc[("3700001", 2024), "cpi_u"] == pytest.approx(313.70)
    assert p.loc[("3700001", 2023), "mortgage_rate"] == pytest.approx(6.81)
    assert p.loc[("3700001", 2024), "hpi"] == pytest.approx(410.0)
    assert p.loc[("3700001", 2024), "hpi_geo"] == "county:37001"

    no_county = MARKET[MARKET["geo"] != "county:37001"]
    only_county = panels.build(BPS, _eligible(), no_county, theme="adu", rule_version="1.0")
    assert only_county["hpi"].isna().all()
    both = panels.build(
        BPS, _eligible(), no_county, theme="adu", rule_version="1.0", hpi_levels=("county", "state")
    )
    row = both.set_index(["geoid", "year"]).loc[("3700001", 2024)]
    assert (row["hpi"], row["hpi_base2000"], row["hpi_geo"]) == (305.0, 152.5, "state:37")


def _store(tmp_path, bps):
    store = DataStore(tmp_path)
    for table, name, df in [
        ("bps_place_year", "bps", bps),
        ("eligible_parcels", "eligible", _eligible()),
        ("market_geo_year", "fred", MARKET.drop(columns=["hpi", "hpi_base2000"])),
        ("market_geo_year", "fhfa", MARKET[["geo", "year", "hpi", "hpi_base2000"]]),
    ]:
        path = store.processed("NC", table, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path)
    return store


def test_load_reads_every_market_file(tmp_path):
    """FRED and FHFA files share national:US rows; both sources' columns survive the read."""
    p = panels.load("NC", _store(tmp_path, BPS), theme="adu", rule_version="1.0").set_index(["geoid", "year"])
    assert p.loc[("3700001", 2024), "cpi_u"] == pytest.approx(313.70)
    assert p.loc[("3700001", 2024), "hpi"] == pytest.approx(410.0)


def test_load_refuses_held_out_outcomes(tmp_path):
    """Charlotte (3712000) 2024 is a V5 holdout in config/states/nc.yaml: a leaked row stops the build."""
    leaked = pd.concat([BPS, _bps([("37120000", "3712000", "37119", 2024, 1, 0, False)])], ignore_index=True)
    with pytest.raises(HoldoutLeak):
        panels.load("NC", _store(tmp_path, leaked), theme="adu", rule_version="1.0")
