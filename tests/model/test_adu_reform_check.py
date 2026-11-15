"""D-095: the reform-ratio check's pieces against hand-worked examples."""

import math

import numpy as np
import pytest

from lotline.model import adu_reform_check as rc
from lotline.model import calibrate_adu as cal

FULL, PARTIAL = 4, 2  # calibrate_adu type indices: c = 1 and m_x


def _pl(y, base, types, w=(1.0,)):
    n = len(y)
    t = np.asarray(types).reshape(len(w), n, 1)
    return cal.PlaceData(
        "MN",
        "1",
        "Testville",
        np.arange(2016, 2016 + n),
        np.asarray(y, float),
        np.asarray(base, float),
        t,
        np.ones((n, 1)),
        np.asarray(w, float),
        None,
        {},
    )


def test_share_path_hand_worked():
    pl = _pl([0, 0], [10, 10], [[FULL, PARTIAL]])
    assert rc.share_path(pl, cal._cvals(1.0, 0.4)) == pytest.approx([1.0, 0.4])
    two = _pl([0, 0], [10, 10], [[FULL, PARTIAL], [PARTIAL, PARTIAL]], w=(1.0, 3.0))
    assert rc.share_path(two, cal._cvals(1.0, 0.4)) == pytest.approx([0.25 + 0.3, 0.4])


def test_event_from_hand_worked():
    pl = _pl([1, 2, 3, 4], [10, 10, 10, 10], [[PARTIAL, PARTIAL, FULL, FULL]])
    ev = rc.event_from(pl, 2018, cal._cvals(1.0, 0.5))
    assert (ev.y_before, ev.e_before, ev.y_after, ev.e_after) == (3, 20, 7, 20)
    assert ev.ratio == pytest.approx(2.0)


def test_rate_draws_mean_and_switch_off():
    ev = rc.Event("x", 3.0, 300.0, 0.0, 100.0, 1.0)
    d = rc.rate_draws(ev, 0.0, 200_000, 1)
    assert d.mean() == pytest.approx(3.5 / 300 * 100, rel=0.01)  # Gamma(3.5, 300) mean × E_after
    dd = rc.rate_draws(ev, 0.5, 200_000, 1)
    assert np.median(dd / d) == pytest.approx(1.0, abs=0.02)  # same rate draws; the drift has median 1
    assert np.array_equal(rc.rate_draws(ev, 0.5, 10, 1), rc.rate_draws(ev, 0.5, 10, 1))


def test_log_score_hand_worked():
    assert rc.log_score(2, np.array([1.0, 1.0])) == pytest.approx(math.log(math.exp(-1) / 2))
    want = math.log(
        (math.exp(-1) + math.exp(-2) * 2) / 2
    )  # y 1: Poisson(1; 1) = e^-1, Poisson(1; 2) = 2 e^-2
    assert rc.log_score(1, np.array([1.0, 2.0])) == pytest.approx(want)


def test_b_profile_recovers_the_ratio_exponent():
    # after counts at exactly the no-effect mean × ratio: b̂ = 1; at the no-effect mean: b̂ = 0
    evs = [
        rc.Event(str(i), 0, 1, y, 1, r) for i, (y, r) in enumerate([(200.0, 2.0), (50.0, 0.5), (400.0, 4.0)])
    ]
    mus = [np.full(50, 100.0)] * 3
    b, lo, hi = rc.b_interval(rc.b_profile(evs, mus))
    assert b == pytest.approx(1.0) and lo < 1.0 < hi
    evs0 = [rc.Event(e.name, 0, 1, 100.0, 1, e.ratio) for e in evs]
    assert rc.b_interval(rc.b_profile(evs0, mus))[0] == pytest.approx(0.0)
    inf = [rc.Event("z", 0, 1, 5.0, 1, math.inf)]
    assert rc.b_profile(inf, [np.ones(3)]) == pytest.approx(np.zeros(len(rc.B_GRID)))


def test_reading_hand_worked():
    assert rc.reading(5, 1, 0.5, 1.5) == "supported"
    assert rc.reading(-3, 1, 0.0, 2.0) == "contradicted"
    assert rc.reading(1, 1, -0.5, 2.0) == "not shown either way"
    assert rc.reading(1, 1, 1.2, 2.0) == "contradicted"
