"""Handbook missing-middle scenario (model/scenarios/mm.py, D-063): hand-worked checks on synthetic places."""

import numpy as np
import pandas as pd
import pytest

from lotline.config import load_params
from lotline.model.scenarios import mm

HALF, SLOPE = 0.5, 0.75


def _draws(n=20_000, theta=0.001, alpha=1e-9, units=2.0, scale=1.0):
    return pd.DataFrame({"theta": np.full(n, theta), "alpha": np.full(n, alpha), "units": np.full(n, units),
                         "teardown_scale": np.full(n, scale)})  # fmt: skip


def _place(geoid="1", eligible=1000.0, dose=0.25, band=2, f_ratio=1.2, house_share=0.6):
    return {"geoid": geoid, "eligible": eligible, "dose": dose, "band": band, "f_ratio": f_ratio,
            "house_share": house_share}  # fmt: skip


def test_log_sd_by_hand():
    s = load_params("mm_hazard")["mm_mature_hazard_ref"]
    # (ln 0.001006 − ln 0.0000325) / 3.2897 = 1.0434
    assert mm.log_sd(s) == pytest.approx(1.0434, abs=1e-4)


def test_year_shape_by_hand():
    # half 0.5, slope 0.75, ages 0.5 … 4.5: 0.5, 0.7914, 0.9350, 0.9820, 0.9952
    assert mm.year_shape(HALF, SLOPE) == pytest.approx([0.5, 0.7914, 0.9350, 0.9820, 0.9952], abs=1e-4)


def test_one_place_by_hand():
    # θ 0.001 × E 1000 × (1 − 0.25) × F 1.2 × Σ shape 4.2036 = 3.7833 buildings over five years
    res = mm.simulate(pd.DataFrame([_place()]), _draws(), HALF, SLOPE, seed=1)
    b = res.buildings.sum(1)
    assert b.mean() == pytest.approx(3.7833, rel=0.02)
    assert res.homes_gross.sum(1).mean() == pytest.approx(2 * 3.7833, rel=0.02)
    # one house lost per teardown, teardown share 0.6 × 1.0: net = 3.7833 × (2 − 0.6) = 5.2966
    assert res.homes_net.sum(1).mean() == pytest.approx(5.2966, rel=0.02)
    # year 1 carries half the mature rate: 0.001 × 1000 × 0.75 × 1.2 × 0.5 = 0.45
    assert res.buildings[:, 0].mean() == pytest.approx(0.45, rel=0.03)


def test_full_dose_adds_nothing():
    res = mm.simulate(pd.DataFrame([_place(dose=1.0)]), _draws(1000), HALF, SLOPE, seed=1)
    assert res.buildings.sum() == 0 and res.homes_net.sum() == 0


def test_teardowns_never_exceed_buildings():
    res = mm.simulate(pd.DataFrame([_place(house_share=1.0)]), _draws(2000, scale=1.0), HALF, SLOPE, seed=3)
    assert (res.teardowns <= res.buildings).all()
    assert np.array_equal(res.teardowns, res.buildings)  # every lot holds a house and the scale is 1


def test_uncoded_places_draw_their_band_dose():
    coded = [_place(geoid=f"c{i}", dose=0.2, band=2) for i in range(5)]
    small = [_place(geoid="s", dose=0.6, band=0)]  # band 0 has one coded place: under the minimum of 5
    pools = mm.dose_pools(pd.DataFrame(coded + small), min_coded=5)
    assert pools[2] == pytest.approx([0.2] * 5)
    assert sorted(pools[0]) == pytest.approx([0.2] * 5 + [0.6])  # falls back to every coded place
    unc = _place(geoid="u", dose=np.nan, band=2)
    res = mm.simulate(pd.DataFrame(coded + small + [unc]), _draws(), HALF, SLOPE, seed=1)
    row = res.places.set_index("geoid").loc["u"]
    assert row["dose_gap_mean"] == pytest.approx(0.8)


def test_no_coded_place_means_no_rule():
    res = mm.simulate(pd.DataFrame([_place(geoid="u", dose=np.nan)]), _draws(100), HALF, SLOPE, seed=1)
    assert res.places["dose_gap_mean"].iloc[0] == pytest.approx(1.0)


def test_state_total_is_the_sum_of_places_run_alone():
    a, b = _place(geoid="a"), _place(geoid="b", eligible=3000.0, dose=0.0)
    d = _draws(500, alpha=2.0)
    both = mm.simulate(pd.DataFrame([a, b]), d, HALF, SLOPE, seed=9)
    one = mm.simulate(pd.DataFrame([a]), d, HALF, SLOPE, seed=9)
    two = mm.simulate(pd.DataFrame([b]), d, HALF, SLOPE, seed=9)
    assert np.array_equal(both.buildings, one.buildings + two.buildings)
    assert np.array_equal(both.homes_net, one.homes_net + two.homes_net)


def test_current_dose_takes_the_strongest_live_rule():
    rows = pd.DataFrame(
        {"reform_id": ["r1", "r2", "r3"], "unit_cap": [2, 4, 4], "by_right": ["True", "False", "True"],
         "effective_date": pd.to_datetime(["2020-01-01", "2021-01-01", "2026-06-01"]),
         "end_date": pd.to_datetime([None, None, None])}
    )  # fmt: skip
    # r1: 1/3 × 1 = 0.3333; r2: 1 × (0 + 1 × 1/3) = 0.3333 at coverage 1, 0.1667 at 0.5; r3 not yet live
    d = mm.current_dose(rows, pd.Timestamp("2025-12-31"), {"r2": 0.5}, (0.5, 1 / 3), 1 / 3)
    assert d == pytest.approx(1 / 3)
    assert mm.current_dose(rows.iloc[:0], pd.Timestamp("2025-12-31"), {}, (0.5, 1 / 3), 1 / 3) == 0.0


def test_current_dose_on_the_d064_date_counts_a_2026_rule():
    """D-064: forward runs read the dose on `baseline.rules_as_of(2025)` = 2027-12-31. r3 (four units, by
    right, coverage 1) is in force from 2026-06-01: dose 1 × (1 + 0) × 1 = 1, the strongest, so the place's
    dose is 1 and the Handbook scenario adds 1 − 1 = 0 there. On 2025-12-31 it was 1/3."""
    from lotline.model import baseline

    rows = pd.DataFrame(
        {"reform_id": ["r1", "r3"], "unit_cap": [2, 4], "by_right": ["True", "True"],
         "effective_date": pd.to_datetime(["2020-01-01", "2026-06-01"]),
         "end_date": pd.to_datetime([None, None])}
    )  # fmt: skip
    as_of = baseline.rules_as_of(2025)
    assert as_of == pd.Timestamp("2027-12-31")
    assert mm.current_dose(rows, as_of, {}, (0.5, 1 / 3), 1 / 3) == pytest.approx(1.0)
    assert mm.current_dose(rows, pd.Timestamp("2025-12-31"), {}, (0.5, 1 / 3), 1 / 3) == pytest.approx(1 / 3)


def test_summarize_has_every_measure_and_period():
    res = mm.simulate(pd.DataFrame([_place()]), _draws(200), HALF, SLOPE, seed=1)
    s = mm.summarize(res)
    assert set(s["measure"]) == {"buildings", "homes_gross", "teardowns", "homes_net"}
    assert set(s["period"]) == {"five_years"} | {f"year_{j}" for j in range(1, 6)}
    five = s[(s["measure"] == "buildings") & (s["period"] == "five_years")].iloc[0]
    assert five["p10"] <= five["p50"] <= five["p90"]


def test_draw_params_centres_on_the_config():
    d = mm.draw_params(20_000, 5)
    sp = mm.specs()
    assert np.median(d["theta"]) == pytest.approx(sp["mm_mature_hazard_ref"].value, rel=0.05)
    assert d["units"].between(sp["mm_units_per_project"].low, sp["mm_units_per_project"].high).all()
    assert d["teardown_scale"].between(0.5, 1.0).all()


def test_house_share_by_hand():
    parcels = pd.DataFrame(
        {"land_use_std": ["SF_DETACHED"] * 3 + ["VACANT_RESIDENTIAL", "COMMERCIAL"],
         "lot_sqft": [8000.0] * 5, "units": [1, 1, 1, np.nan, np.nan], "sf_only_zoned": [True] * 5}
    )  # fmt: skip
    # 3 houses and 1 vacant lot are eligible; the commercial parcel is not -> 0.75
    assert mm.house_share(parcels) == pytest.approx(0.75)
    assert np.isnan(mm.house_share(parcels.iloc[4:]))
