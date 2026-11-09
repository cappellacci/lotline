"""scripts/dev/housing_need.py: household growth over the forecast window (D-057, D-061 open item 2).

The window follows D-061 (2027-2031 from origin 2025), so growth runs from July 1, 2026 to July 1, 2031. A
year the demographer does not publish is read on the straight line between the nearest published years.
"""

import importlib.util
from pathlib import Path

import pytest

from lotline.config import load_params

_spec = importlib.util.spec_from_file_location(
    "housing_need", Path(__file__).resolve().parents[1] / "scripts" / "dev" / "housing_need.py"
)
housing_need = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(housing_need)


def test_window_years_follow_the_forecast_window():
    # origin 2025, lead 1, horizon 5 -> window 2027-2031 -> July 2026 to July 2031
    assert housing_need.window_years() == (2026, 2031)


def test_population_between_published_years_by_hand():
    pts = {2025: 100.0, 2030: 110.0, 2035: 130.0}
    assert housing_need.population_at(pts, 2026) == pytest.approx(102.0)  # 100 + 10 × 1/5
    assert housing_need.population_at(pts, 2031) == pytest.approx(114.0)  # 110 + 20 × 1/5
    assert housing_need.population_at(pts, 2030) == 110.0  # a published year is used as is
    with pytest.raises(ValueError):
        housing_need.population_at(pts, 2036)  # never extrapolated


def test_household_growth_by_hand(monkeypatch):
    """Five-year steps 1,000,000 / 1,050,000 / 1,080,000: mid-2026 = 1,010,000, mid-2031 = 1,056,000;
    change 46,000 × 0.4 households per person = 18,400. Low and high scenarios give the range."""
    spec = {
        "source": "test",
        "url": "https://example.test",
        "vintage": "test",
        "mid": {2025: 1_000_000, 2030: 1_050_000, 2035: 1_080_000},
        "low": {2025: 1_000_000, 2030: 1_040_000, 2035: 1_060_000},
        "high": {2025: 1_000_000, 2030: 1_060_000, 2035: 1_100_000},
    }
    monkeypatch.setitem(housing_need.POPULATION, "ZZ", spec)
    out = housing_need.household_growth("ZZ", 0.4, (2026, 2031))
    assert out["value"] == 18_400
    # low: 1,008,000 -> 1,044,000 = 36,000 × 0.4; high: 1,012,000 -> 1,068,000 = 56,000 × 0.4
    assert (out["low"], out["high"]) == (14_400, 22_400)
    assert out["unit"] == "households, mid-2026 to mid-2031"
    assert "2026 interpolated 2025-2030, 2031 interpolated 2030-2035" in out["notes"]


def test_generated_config_uses_the_window():
    p = load_params("housing_need")
    for st in ("mn", "nc", "tx", "oh", "or"):
        assert p[f"household_growth_5y_{st}"].unit == "households, mid-2026 to mid-2031"
    # Minnesota and Oregon publish every year: no interpolation
    assert "2026 published, 2031 published" in p["household_growth_5y_mn"].notes
    assert "2026 published, 2031 published" in p["household_growth_5y_or"].notes
