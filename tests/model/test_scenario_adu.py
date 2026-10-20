"""Handbook ADU scenario (model/scenarios/adu.py): one place by hand end to end, levers off, one ADU per
parcel,
monotone in profit, increment over current rules, additionality. Synthetic inputs only."""

import math

import numpy as np
import pandas as pd
import pytest

from lotline.model.scenarios import adu

P = adu.central_params()


def _places(**cols):
    base = {
        "geoid": ["X"],
        "eligible_parcels": [2000.0],
        "rent": [1100.0],
        "home_value": [P["adu_ref_home_value_usd"] / 2],
        "mortgage_rate": [P["adu_ref_mortgage_rate"] + 2],
        "rule_class": ["none"],
        "rule_age": [np.nan],
        "observed_rate": [np.nan],
    }
    base.update({k: v if isinstance(v, list) else [v] for k, v in cols.items()})
    n = max(len(v) for v in base.values())
    return pd.DataFrame({k: v * n if len(v) == 1 else v for k, v in base.items()})


def test_one_jurisdiction_year_by_hand():
    """2,000 eligible parcels; rent $1,100, half the reference home value, rates +2 points; no ADU rule today.
    Mature hazard 0.0014219 (test_hazard: worked by hand). Year 1: ramp(1) = 1 / (1 + e^(4/3)) = 0.20861, so
    the
    Handbook hazard is 0.0014219 × 0.20861 = 0.00029662 and gross ADU permits = 2,000 × 0.00029662 = 0.5933.
    Current rules give none, so all 0.5933 are added. Homes = 0.5933 × 0.65 (net-new) × (1 − 0.10)
    (formalization) = 0.3470. Year 2: pool 2,000 − 0.5933; ramp(2) = 0.5; 1,999.407 × 0.0014219 × 0.5 =
    1.4215."""
    out = adu.central_path(_places())
    ramp1 = 1 / (1 + math.exp(4 / 3))
    year1 = 2000 * 0.0014219229 * ramp1
    assert out["mature_hazard"][0] == pytest.approx(0.0014219229, rel=1e-6)
    assert out["handbook"][0, 0] == pytest.approx(year1, rel=1e-6)
    assert out["current"][0, 0] == 0.0
    assert out["added"][0, 0] == pytest.approx(0.5933, abs=1e-4)
    assert out["homes"][0, 0] == pytest.approx(year1 * 0.65 * 0.9, rel=1e-6)
    assert out["homes"][0, 0] == pytest.approx(0.3470, abs=1e-4)
    assert out["added"][0, 1] == pytest.approx((2000 - year1) * 0.0014219229 * 0.5, rel=1e-6)
    assert out["added"][0, 1] == pytest.approx(1.4215, abs=1e-4)


def test_all_levers_off_equals_the_baseline():
    places = _places(rule_class=["none", "partial", "handbook"], rule_age=[np.nan, 6.0, 1.0])
    off = adu.central_path(places, enabled=False)
    assert np.all(off["added"] == 0) and np.all(off["homes"] == 0)
    np.testing.assert_array_equal(off["handbook"], off["current"])
    yearly, totals = adu.run(places, 2025, draws=50, enabled=False)
    for name in ("adu_permits_added", "additional_homes"):
        cols = [f"{name}_{s}" for s in ("mean", "p10", "p50", "p90")]
        assert (yearly[cols] == 0).all().all() and (totals[cols] == 0).all().all()


def test_at_most_one_adu_per_parcel():
    """Even with a 90% yearly hazard, cumulative ADUs never exceed the eligible parcels, under either rule."""
    paths = adu.pool_paths([100.0], [0.9], [np.nan], [0.0], [np.nan], 0.5, 0.5, 5)
    assert paths.handbook.sum() <= 100.0 + 1e-9
    assert paths.current.sum() <= 100.0 + 1e-9
    assert np.all(paths.handbook >= 0)
    hm = adu.pool_paths([100.0], [1.0], [np.nan], [0.0], [np.nan], 0.5, 0.5, 5)
    assert hm.handbook.sum() == pytest.approx(100.0, rel=1e-3)  # every parcel used once, never twice


def test_more_profit_never_lowers_uptake():
    rents = list(np.linspace(600, 3500, 60))
    out = adu.central_path(_places(rent=rents))
    total = out["added"].sum(axis=1)
    assert np.all(np.diff(total) >= 0)


def test_handbook_equivalent_rules_add_nothing():
    out = adu.central_path(_places(rule_class="handbook", rule_age=0.5))
    assert np.all(out["added"] == 0)
    assert out["current"].sum() > 0  # the recent reform still ramps up under current rules


def test_partial_rules_get_the_increment_only_by_hand():
    """A long-standing partial rule (age 50 years, ramp ≈ 1): current hazard = 0.3 × h_m. Handbook year 1:
    0.3 h_m + 0.7 h_m × ramp(1). Added in year 1 = 2,000 × 0.7 × h_m × 0.20861 (same pool in year 1)."""
    out = adu.central_path(_places(rule_class="partial", rule_age=50.0))
    hm = out["mature_hazard"][0]
    assert out["current"][0, 0] == pytest.approx(2000 * 0.3 * hm, rel=1e-6)
    assert out["added"][0, 0] == pytest.approx(2000 * 0.7 * hm / (1 + math.exp(4 / 3)), rel=1e-6)


def test_observed_adus_are_never_counted_as_added():
    """If a place already builds ADUs at or above the Handbook hazard, nothing is added (additionality)."""
    hm = adu.central_path(_places())["mature_hazard"][0]
    out = adu.central_path(_places(observed_rate=hm * 1.5))
    assert np.all(out["added"] == 0)
    half = adu.central_path(_places(observed_rate=hm / 2))
    assert 0 < half["added"].sum() < adu.central_path(_places())["added"].sum()


def test_run_ranges_are_ordered_and_flag_extrapolation():
    places = _places(rent=[1100.0, 1800.0], home_value=[260_000.0, 600_000.0], mortgage_rate=[5.0, 5.0])
    yearly, totals = adu.run(places, 2025, draws=200)
    for t in (yearly, totals):
        assert (t["additional_homes_p10"] <= t["additional_homes_p50"]).all()
        assert (t["additional_homes_p50"] <= t["additional_homes_p90"]).all()
    assert totals["outside_calibration"].tolist() == [True, False]
    assert len(yearly) == 2 * 5 and set(yearly["year"]) == set(range(2026, 2031))
    assert "eligible_parcels" in yearly  # denominator kept beside the units


def _reforms(rows):
    cols = [
        "reform_id",
        "jurisdiction_geoid",
        "theme",
        "status",
        "effective_date",
        "end_date",
        "supersedes",
        *adu.RUBRIC,
    ]
    df = pd.DataFrame([tuple(r) + (None,) * (len(cols) - len(r)) for r in rows], columns=cols)
    for c in ("effective_date", "end_date"):
        df[c] = pd.to_datetime(df[c])
    return df


def test_current_rules_classes_amendments_and_state_laws():
    reforms = _reforms(
        [
            # A: owner-occupancy rule, then an amendment that drops it (other fields inherited)
            (
                "A1",
                "100",
                "adu",
                "in_force",
                "2015-01-01",
                None,
                None,
                True,
                True,
                True,
                800,
                "no minimum",
                0,
            ),
            ("A2", "100", "adu", "in_force", "2021-01-01", None, "A1", None, False, None, None, None, None),
            # B: parking required
            (
                "B1",
                "200",
                "adu",
                "in_force",
                "2020-01-01",
                None,
                None,
                True,
                False,
                True,
                900,
                "one space",
                1,
            ),
            # C: nothing local, state law later than the date
            ("S1", "27", "adu", "in_force", "2030-01-01", None, None, True, False, True, 800, "none", 0),
        ]
    )
    out = adu.current_rules(reforms, ["100", "200", "300"], "27", pd.Timestamp("2025-12-31")).set_index(
        "geoid"
    )
    assert out.loc["100", "rule_class"] == "handbook" and out.loc["100", "rule_id"] == "A2"
    assert out.loc["100", "rule_age"] == pytest.approx(
        (pd.Timestamp("2025-12-31") - pd.Timestamp("2021-01-01")).days / 365.25
    )
    assert out.loc["200", "rule_class"] == "partial" and "parking required" in out.loc["200", "rule_note"]
    assert out.loc["300", "rule_class"] == "none" and "S1" in out.loc["300", "rule_note"]
    early = adu.current_rules(reforms, ["100"], "27", pd.Timestamp("2018-06-30")).set_index("geoid")
    assert early.loc["100", "rule_class"] == "partial"  # owner-occupancy rule in force then


def test_rule_restrictions_size_cap_and_unknowns():
    fails, unknown = adu.rule_restrictions({"by_right": True, "owner_occ": False, "adu_max_sqft": 500})
    assert fails == ["size cap under 600 sq ft"]
    assert set(unknown) == {"adu_detached_allowed", "parking"}


def test_observed_counts_take_the_larger_source_not_the_sum():
    permits = pd.DataFrame(
        {
            "jurisdiction_geoid": ["M"] * 5 + ["S"],
            "source": ["metc", "metc", "city", "city", "city", "metc"],
            "issue_year": [2020] * 6,
            "building_type_std": ["ADU", "ADU", "ADU", "ADU", "ADU", "SFD"],
            "adu_type": [None] * 6,
        }
    )
    out = adu.observed_adu_counts(permits, 2019, 2022).set_index("geoid")["adu_permits"]
    assert out["M"] == 3 and out["S"] == 0
    assert adu.adu_share_of_one_unit(permits, 2020, 2020) == (5, 6)


def test_forward_runs_draw_the_rate_path_and_backtests_use_the_given_rate():
    """No rate given -> each draw uses mortgage_rate_forecast (market.yaml), so the central run equals a run
    given the central forecast rate; a given (historical) rate is used as is, never replaced."""
    no_rate = _places().drop(columns="mortgage_rate")
    forecast = _places(mortgage_rate=P["mortgage_rate_forecast"])
    assert adu.central_path(no_rate)["added"] == pytest.approx(adu.central_path(forecast)["added"])
    _, t_forward = adu.run(no_rate, 2025, draws=300)
    assert t_forward["mortgage_rate_central"].iloc[0] == P["mortgage_rate_forecast"]
    _, t_hist = adu.run(_places(mortgage_rate=3.0), 2018, draws=300)
    assert t_hist["mortgage_rate_central"].iloc[0] == 3.0
    _, t_fixed = adu.run(forecast, 2025, draws=300)
    spread = lambda t: t["adu_permits_added_p90"].iloc[0] - t["adu_permits_added_p10"].iloc[0]  # noqa: E731
    assert spread(t_forward) > spread(t_fixed)  # drawing the rate widens the range


def test_an_explicit_no_adu_row_is_none_and_a_state_law_still_wins():
    # "adus_per_lot = 0": the city's code allows no ADUs. It must read as "none", not as a partial rule.
    reforms = _reforms(
        [
            ("N1", "400", "adu", "in_force", "2010-01-01", None, None, True, False, True, 800, "none", 0, 0),
            ("S1", "27", "adu", "in_force", "2024-01-01", None, None, True, False, True, 800, "none", 0, 1),
        ]
    )
    before = adu.current_rules(reforms, ["400"], "27", pd.Timestamp("2020-06-30")).set_index("geoid")
    assert before.loc["400", "rule_class"] == "none" and before.loc["400", "rule_id"] == "N1"
    assert "no ADUs allowed" in before.loc["400", "rule_note"] and pd.isna(before.loc["400", "rule_age"])
    after = adu.current_rules(reforms, ["400"], "27", pd.Timestamp("2025-12-31")).set_index("geoid")
    assert after.loc["400", "rule_class"] == "handbook" and after.loc["400", "rule_id"] == "S1"
