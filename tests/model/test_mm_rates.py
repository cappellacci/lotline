"""The missing-middle engine's rule dose and price-to-cost (model/mm_rates.py): hand-worked examples."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lotline.config import CONFIG_DIR
from lotline.model import mm_rates as mm
from lotline.model import proforma

COLUMNS = list(pd.read_csv(CONFIG_DIR / "reforms" / "mn.csv", nrows=0).columns)


def reforms(*rows: dict) -> pd.DataFrame:
    """Coded reforms with the real CSV columns (blank where a row doesn't say) and parsed dates."""
    df = pd.DataFrame([{c: r.get(c, np.nan) for c in COLUMNS} for r in rows], columns=COLUMNS)
    for col in ("announced_date", "adoption_date", "effective_date", "end_date"):
        df[col] = pd.to_datetime(df[col])
    df["jurisdiction_geoid"] = df["jurisdiction_geoid"].astype(str)
    return df


def mm_row(geoid, effective, rid=None, **kw) -> dict:
    return {
        "reform_id": rid or f"MN-{geoid}-missing_middle-{effective[:4]}",
        "state": "MN",
        "jurisdiction_geoid": geoid,
        "theme": "missing_middle",
        "status": "in_force",
        "effective_date": effective,
        **kw,
    }


def test_units_grade_by_hand():
    assert [mm.units_grade(c) for c in (1, 2, 3, 4, 8)] == pytest.approx([0, 1 / 3, 2 / 3, 1, 1])
    assert np.isnan(mm.units_grade(np.nan))


def test_blank_shares_by_hand():
    r = reforms(
        mm_row("1", "2020-01-01", by_right="True", unit_cap=3),
        mm_row("2", "2020-01-01", by_right="True", unit_cap=2),
        mm_row("3", "2020-01-01"),
        mm_row("4", "2020-01-01", by_right="False", unit_cap=8),
    )
    p_br, grade = mm.blank_shares(r)
    assert p_br == pytest.approx(2 / 3)
    assert grade == pytest.approx((2 / 3 + 1 / 3 + 1) / 3)


def test_rule_dose_by_hand():
    d, br = mm.rule_dose({"unit_cap": 3, "by_right": np.nan}, 0.5, (0.8, 0.5), 1 / 3)
    assert d == pytest.approx(2 / 3 * (0.8 + 0.2 / 3) * 0.5)
    assert br == pytest.approx(0.8)
    # by permit only: a third of the by-right dose; a blank cap takes the coded mean grade
    assert mm.rule_dose({"unit_cap": 4, "by_right": "False"}, 1.0, (0.8, 0.5), 1 / 3) == pytest.approx(
        (1 / 3, 0)
    )
    assert mm.rule_dose({"unit_cap": np.nan, "by_right": "True"}, 1.0, (0.8, 0.5), 1 / 3)[0] == pytest.approx(
        0.5
    )
    # a rule capped under 2 units is not missing middle
    assert mm.rule_dose({"unit_cap": 1, "by_right": "True"}, 1.0, (0.8, 0.5), 1 / 3) == (0.0, 0.0)


def test_plex_price_to_cost_by_hand():
    p = proforma.central_params()
    sqft = 2 * p["plex_unit_sqft"]
    hard = p["hard_cost_per_sqft_usd"] * sqft  # duplexes stay under the residential code
    soft = p["soft_cost_share"] * hard
    financing = (
        p["construction_loan_rate"] * p["construction_years_irc"] * p["average_draw_share"] * (hard + soft)
    )
    rent = 1500.0
    value = (
        12 * rent * 2 * (1 - p["rental_vacancy_rate"]) * (1 - p["operating_expense_share"]) / p["cap_rate"]
    )
    assert float(mm.plex_price_to_cost(rent)) == pytest.approx(value / (hard + soft + financing))
    assert float(mm.plex_price_to_cost(2 * rent)) == pytest.approx(2 * float(mm.plex_price_to_cost(rent)))
    assert float(mm.plex_price_to_cost(rent, cost_index=1.2)) < float(mm.plex_price_to_cost(rent))
