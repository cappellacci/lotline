"""Shared undercount arithmetic (`lotline.validation.undercount`), by hand, and NC's re-export."""

import pytest

from lotline.adapters.states.nc import wake_roll_diff as wd
from lotline.validation import undercount as uc


def test_nc_module_reexports_the_same_functions():
    for name in uc.__all__:
        assert getattr(wd, name) is getattr(uc, name)


def test_k_by_hand():
    # Raleigh, duplexes removed: |P∩R| 30, |a| 2 -> k = 32/30
    k, lo, hi = uc.k_undercount(30, 2)
    assert k == pytest.approx(32 / 30)
    assert 1 < lo < k < hi


def test_chapman_by_hand():
    # (4+1)(2+1)/(1+1) - 1 = 6.5
    assert uc.chapman(4, 2, 1)[0] == pytest.approx(6.5)
