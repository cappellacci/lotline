"""The results bundle's `baseline` part (`results.baseline_table`, schemas 1.11).

Hand-worked: the statewide sum per draw, "all" as the per-draw sum of the size classes, percentiles taken from
the sums (not added), the D-061 window labels, coverage, and agreement with `baseline.baseline_forecast`.
"""

import numpy as np
import pandas as pd
import pytest

from lotline.config import load_params
from lotline.model import baseline, results
from lotline.schemas import validate

P = load_params("baseline")  # forecast_lead_years = 1: origin 2025 -> 2027-2031 (D-061)
SIZES = baseline.SIZE_CLASSES


def _units(rep: bool) -> list[str]:
    return [baseline.outcome_column(s, rep) for s in SIZES]


def _fake_forecast(draws_by_class):
    """A stand-in for `baseline.forecast_draws`: class -> {geoid: (horizon, n) array}."""

    def fake(panel, value, origin, *, params=None, **kw):
        size = next(s for s in SIZES if value in (f"units_{s}", f"units_{s}_rep"))
        rows, arrays = [], []
        for geoid, a in draws_by_class[size].items():
            for h in range(a.shape[0]):
                rows.append({"geoid": geoid, "horizon": h + 1})
                arrays.append(a[h])
        return pd.DataFrame(rows, columns=["geoid", "horizon"]), np.array(arrays) if arrays else np.empty(
            (0, 1)
        )

    return fake


def _panel_at_origin(units_by_place, origin=2025, state="ZZ"):
    """Origin-year rows: geoid -> units in each size class (same number in total and reported columns)."""
    rows = []
    for geoid, per_class in units_by_place.items():
        row = {"state": state, "geoid": geoid, "year": origin}
        for s, u in zip(SIZES, per_class, strict=True):
            row[f"units_{s}"] = u
            row[f"units_{s}_rep"] = u
        rows.append(row)
    return pd.DataFrame(rows)


def test_statewide_sums_by_hand(monkeypatch):
    # Two places, five years, three draws. Place A: 1-unit only, draws (1, 2, 3) every year.
    # Place B: 3-4 unit only, draws (10, 0, 5) every year. 2-unit and 5+: nothing.
    ones = np.ones((5, 1))
    a = ones * np.array([1, 2, 3])
    b = ones * np.array([10, 0, 5])
    zero = {}
    fake = _fake_forecast({"1": {"A": a}, "2": zero, "3_4": {"B": b}, "5p": zero})
    monkeypatch.setattr(baseline, "forecast_draws", fake)
    t = results.baseline_table(_panel_at_origin({"A": (4, 0, 0, 0), "B": (0, 0, 6, 0)}), "zz", 2025, P)
    t = t.set_index(["size_class", "period"])

    # Five-year totals per draw: 1-unit (5, 10, 15); 3-4 unit (50, 0, 25); all (55, 10, 40).
    # numpy-linear P10 of (10, 40, 55) = 10 + 0.2 * 30 = 16; P50 = 40; P90 = 40 + 0.8 * 15 = 52; mean 35.
    row = t.loc[("all", "2027-2031")]
    assert (row.p10, row.p50, row.p90, row["mean"]) == pytest.approx((16, 40, 52, 35))
    # Adding the classes' own P50s (10 + 25 = 35) would be wrong: "all" comes from the per-draw sums.
    assert t.loc[("1", "2027-2031"), "p50"] + t.loc[("3_4", "2027-2031"), "p50"] == pytest.approx(35)
    assert row.p50 != pytest.approx(35)
    # One year: all = (11, 2, 8) -> P50 8, mean 7.
    assert t.loc[("all", "2027"), ["p50", "mean"]].tolist() == pytest.approx([8, 7])
    assert t.loc[("2", "2031"), ["p10", "p50", "p90", "mean"]].tolist() == [0, 0, 0, 0]
    # Window and rows: 5 size classes x (1 window + 5 years).
    assert sorted({p for _, p in t.index}) == ["2027", "2027-2031", "2028", "2029", "2030", "2031"]
    assert len(t) == 30
    assert (t["places"] == 2).all() and (t["coverage_share"] == 1.0).all()
    assert (t["basis"] == "reported").all() and (t["state"] == "ZZ").all()
    validate(t.reset_index(), "results_baseline")


def test_coverage_counts_only_the_places_forecast(monkeypatch):
    # Place C permitted 30 units at the origin but is not forecast (no eligible parcels): coverage = 10 / 40.
    one = {"A": np.zeros((5, 2))}
    monkeypatch.setattr(baseline, "forecast_draws", _fake_forecast(dict.fromkeys(SIZES, one)))
    panel = _panel_at_origin({"A": (6, 0, 4, 0), "C": (0, 0, 0, 30)})
    t = results.baseline_table(panel, "ZZ", 2025, P)
    assert np.allclose(t["coverage_share"], 0.25)
    assert (t["places"] == 1).all()
    # No units anywhere at the origin: coverage is unknown, not 0 or 1.
    t0 = results.baseline_table(_panel_at_origin({"A": (0, 0, 0, 0)}), "ZZ", 2025, P)
    assert t0["coverage_share"].isna().all()


def _real_panel():
    """Three places in two counties, 2010-2025, steady counts in every size class (a real simulation)."""
    rng = np.random.default_rng(3)
    rows = []
    for geoid, county, parcels, scale in (
        ("A", "C1", 2000, 1.0),
        ("B", "C1", 800, 0.4),
        ("D", "C2", 5000, 2.0),
    ):
        for year in range(2010, 2026):
            row = {
                "state": "ZZ",
                "geoid": geoid,
                "county_geoid": county,
                "year": year,
                "eligible_parcels": parcels,
            }
            for s, base in zip(SIZES, (12, 2, 3, 20), strict=True):
                u = int(rng.poisson(base * scale))
                row[f"units_{s}"] = u
                row[f"units_{s}_rep"] = u
            rows.append(row)
    return pd.DataFrame(rows)


def test_agrees_with_the_baseline_module_on_a_real_simulation():
    panel = _real_panel()
    t = results.baseline_table(panel, "ZZ", 2025, P).set_index(["size_class", "period"])
    rep = bool(P["use_reported_only"].value)
    total_mean = 0.0
    for s in SIZES:
        f = baseline.baseline_forecast(panel, baseline.outcome_column(s, rep), 2025, params=P)
        by_year = f.groupby("year")["mean"].sum()
        assert by_year.index.tolist() == [2027, 2028, 2029, 2030, 2031]
        for year, m in by_year.items():  # statewide mean = sum of the places' means (same draws)
            assert t.loc[(s, str(year)), "mean"] == pytest.approx(m)
        assert t.loc[(s, "2027-2031"), "mean"] == pytest.approx(by_year.sum())
        total_mean += by_year.sum()
    assert t.loc[("all", "2027-2031"), "mean"] == pytest.approx(total_mean)
    w = t.xs("2027-2031", level="period")
    assert (w["p10"] <= w["p50"]).all() and (w["p50"] <= w["p90"]).all()
    assert (t["coverage_share"] == 1.0).all() and (t["places"] == 3).all()
    validate(t.reset_index(), "results_baseline")


def test_other_states_rows_are_ignored(monkeypatch):
    seen = {}

    def fake(panel, value, origin, *, params=None, **kw):
        seen["states"] = set(panel["state"])
        return pd.DataFrame({"geoid": [], "horizon": []}), np.empty((0, 4))

    monkeypatch.setattr(baseline, "forecast_draws", fake)
    panel = pd.concat(
        [_panel_at_origin({"A": (1, 0, 0, 0)}), _panel_at_origin({"X": (9, 0, 0, 0)}, state="YY")]
    )
    t = results.baseline_table(panel, "zz", 2025, P)
    assert seen["states"] == {"ZZ"}
    assert (t[["p10", "p50", "p90", "mean"]] == 0).all().all() and (t["places"] == 0).all()
    assert (t["coverage_share"] == 0.0).all()
