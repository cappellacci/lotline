"""Missing-middle rule dose and price-to-cost: the engine's share of D-024's panel code (modularity step 2).

`scenarios/mm.py` runs these on every forecast. They lived in `estimate_mm`, which moved to
`lotline.calibrate.mm` with the rest of the fitting code; it imports them from here, so the fit and the
forecast read a rule the same way.

- `units_grade`, `blank_shares`, `rule_dose`: dose = units grade × approval grade × coverage (D-024, D-022).
- `plex_price_to_cost`: a rental duplex's value over its cost from the pro forma.
- `_mm_coverage`: D-021's coverage measure for each coded missing-middle rule.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd


def units_grade(cap) -> float:
    """Grade of the units a rule allows on a single-family lot: 2 -> 1/3, 3 -> 2/3, 4 or more -> 1, under 2
    -> 0 (equal steps up to a fourplex). NaN if the cap is blank. The Handbook allows up to 6 homes, but the
    grade stops at 4 on purpose: the outcome counts BPS's 2-unit and 3-4 unit buildings only, so a 5th or 6th
    home lands in a class it doesn't count (model_and_assumptions.md, "What missing middle counts")."""
    c = pd.to_numeric(cap, errors="coerce")
    if pd.isna(c):
        return np.nan
    return float(np.clip((min(float(c), 4.0) - 1.0) / 3.0, 0.0, 1.0)) if c >= 2 else 0.0


def blank_shares(reforms: pd.DataFrame) -> tuple[float, float]:
    """(P(by right), expected units grade) for blank fields of a coded missing-middle row (D-022): the share
    of coded `by_right` values that are True, and the mean units grade of coded caps, over the coded
    missing-middle rows of every state (0.5 and 1/3 if none is coded). By hand: by_right True, True, blank,
    False and caps 3, 2, blank, 8 -> (2/3, (2/3 + 1/3 + 1) / 3 = 2/3)."""
    mm = reforms[reforms["theme"] == "missing_middle"]
    br = mm["by_right"].dropna().astype(str).str.lower()
    p_br = float((br == "true").mean()) if len(br) else 0.5
    grades = [units_grade(c) for c in mm["unit_cap"]]
    grades = [g for g in grades if not np.isnan(g)]
    return p_br, (float(np.mean(grades)) if grades else 1 / 3)


def rule_dose(row: Mapping, coverage: float, blanks: tuple[float, float], permit_grade: float):
    """(dose, P(by right)) of one coded missing-middle rule.

    dose = units grade × (P(by right) + (1 − P(by right)) × permit grade) × coverage. A blank `by_right` or
    `unit_cap` takes its coded share (`blank_shares`). A rule capped under 2 units is not missing middle: (0,
    0). By hand: cap 3 (2/3), by right blank with share 0.8, permit grade 1/3, coverage 0.5:
    2/3 × (0.8 + 0.2/3) × 0.5 = 0.2889; P(by right) = 0.8.
    """
    p_br_blank, grade_blank = blanks
    g = units_grade(row.get("unit_cap"))
    if g == 0.0:
        return 0.0, 0.0
    g = grade_blank if np.isnan(g) else g
    br = row.get("by_right")
    if br is None or pd.isna(br):
        p_br = p_br_blank
    else:
        p_br = 1.0 if str(br).lower() == "true" else 0.0
    return float(g * (p_br + (1 - p_br) * permit_grade) * coverage), float(p_br)


def plex_price_to_cost(monthly_rent, params: Mapping[str, float] | None = None, cost_index: float = 1.0):
    """Rental duplex value over its cost from the pro forma, for a place's median gross rent per unit (2025
    dollars): value = 12 × rent × units × (1 − vacancy) × (1 − operating costs) / cap rate; cost = hard + soft
    + interest while building, fees and profit left out. `cost_index` scales the hard cost per sq ft to a
    year's real construction cost (`hazard.cost_index_by_year`). Enters D-024 as a z-score, so any constant
    factor (a new unit's rent premium over the median, the prototype's size) cancels."""
    from lotline.model import proforma

    p = proforma.central_params() if params is None else dict(params)
    if cost_index != 1.0:
        p = dict(p, hard_cost_per_sqft_usd=p["hard_cost_per_sqft_usd"] * cost_index)
    one_dollar = proforma.Market(sale_price_per_sqft=0.0, monthly_rent_per_sqft=1.0 / p["plex_unit_sqft"])
    pf = proforma.pro_forma("duplex", "rental", one_dollar, 0.0, p)
    return np.asarray(monthly_rent, dtype=float) * pf.value / (pf.hard_cost + pf.soft_cost + pf.financing)


def _mm_coverage(state: str, store, mm_rows: pd.DataFrame, params: Mapping[str, float]) -> dict[str, float]:
    """Coverage of each coded missing-middle rule: the D-021 measure (`adu.rule_coverage`) on the place's
    single-family parcels, reused as is (its judgment shares are D-021's)."""
    from lotline.model.scenarios import adu

    needs = mm_rows["coverage_zones"].notna() | (pd.to_numeric(mm_rows["min_lot_sqft"], errors="coerce") > 0)
    parcels = adu._sf_parcels(state, store) if needs.any() else None
    out = {}
    for r in mm_rows.to_dict("records"):
        mine = (
            parcels[parcels["jurisdiction_geoid"] == r["jurisdiction_geoid"]] if parcels is not None else None
        )
        out[r["reform_id"]] = adu.rule_coverage(r, mine, params)[0]
    return out
