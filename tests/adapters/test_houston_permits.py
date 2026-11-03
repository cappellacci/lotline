"""The Houston permit summary is summed to complete years only (synthetic rows, no download)."""

import pandas as pd

from lotline.adapters.checks import houston_permits
from lotline.registry import PROVENANCE_KEYS, provenance_modules


def test_annual_keeps_complete_years_only():
    rows = [dict(year=2024, month=m, single_family=10, multi_family=m) for m in range(1, 13)]
    rows += [dict(year=2025, month=m, single_family=5, multi_family=1) for m in range(1, 4)]
    out = houston_permits.annual(pd.DataFrame(rows))
    assert list(out.index) == [2024]
    assert out.loc[2024, "single_family"] == 120 and out.loc[2024, "multi_family"] == 78  # 1 + ... + 12


def test_documented_in_provenance():
    assert provenance_modules()["houston_permits_summary"] is houston_permits
    prov = houston_permits.PROVENANCE
    assert all(prov.get(k) for k in PROVENANCE_KEYS)
    assert isinstance(prov["cleaning"], list) and isinstance(prov["limitations"], list)
