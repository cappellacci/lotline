"""Adoption routes for missing middle's ramp (D-100): hand-worked checks."""

import numpy as np
import pytest

from lotline.model import calibrate_mm as cal
from lotline.model import mm_routes as mr
from lotline.model.hazard import ramp


def test_route_of_by_hand():
    metro = {"4159000", "4121250", "41005"}
    assert mr.route_of("OR", "4159000", 652_503, metro) == mr.STATE_REQUIRED  # Portland, Metro
    assert mr.route_of("OR", "4105800", 99_178, metro) == mr.STATE_REQUIRED  # Bend, 10,000+
    assert mr.route_of("OR", "4119600", 3_000, metro) == mr.LOCAL  # a small town outside Metro
    assert mr.route_of("OR", "4121250", 1_944, metro) == mr.STATE_REQUIRED  # Durham, small but in Metro
    assert mr.route_of("OR", "41005", None, metro) == mr.STATE_REQUIRED  # Clackamas unincorporated
    assert mr.route_of("MN", "2758000", 311_527, metro) == mr.LOCAL  # St. Paul


def test_metro_csv_lists_portland_and_three_counties():
    g = mr.metro_geoids()
    assert {"4159000", "41005", "41051", "41067"} <= g and len(g) == 23


def test_shift_ages_matches_a_faster_ramp():
    # ramp(age + d, h) = ramp(age, h − d): d = 3, h = 4 -> a local half-way point of 1
    age = np.array([0.5, 1.5, 2.5])
    assert ramp(age + 3.0, 4.0, 0.75) == pytest.approx(ramp(age, 1.0, 0.75))


def _place(g, y, age):
    n = len(y)
    return cal.Place(geoid=g, name=g, T=2020, beta=0.0, years=np.arange(2020, 2020 + n),
                     y=np.array(y, float), g=np.ones(n), kr=np.full(n, 1000.0), age=np.array(age, float),
                     eligible=np.full(n, 1000.0))  # fmt: skip


def test_shift_ages_moves_only_local_places():
    a, b = _place("a", [1, 2], [0.5, 1.5]), _place("b", [1, 2], [0.5, 1.5])
    out = mr.shift_ages([a, b], {"b"}, 2.0)
    assert out[0].age.tolist() == [0.5, 1.5] and out[1].age.tolist() == [2.5, 3.5]


def test_fit_routes_recovers_fast_local_and_slow_state_ramps():
    # θ = 0.01 per lot-year at maturity, kr 1000: mature mean 10 a year. State places follow half 4, local
    # places half 1 (means set exactly to the ramp, so the best pair is the truth).
    ages = np.array([0.5, 1.5, 2.5, 3.5, 4.5, 5.5])
    slow = 10 * ramp(ages, 4.0, 0.75)
    fast = 10 * ramp(ages, 1.0, 0.75)
    places = [_place(f"s{i}", np.round(slow * 20), ages) for i in range(3)]
    places += [_place(f"l{i}", np.round(fast * 20), ages) for i in range(3)]
    places = [cal.replace(p, kr=p.kr * 20) for p in places]
    rf = mr.fit_routes(places, {"l0", "l1", "l2"}, halves=(1.0, 2.0, 3.0, 4.0))
    assert (rf.half_state, rf.half_local) == (4.0, 1.0)
