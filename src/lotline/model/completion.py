"""Completion factors: the share of permitted housing units that are eventually completed (protocol §5.10).

Measured as a long-run ratio from Census New Residential Construction (via FRED): units completed in years
start+lag .. end+lag divided by units permitted in years start .. end. Over a long window, units still under
construction at either end roughly cancel, so the ratio is the share of permitted units that get built.
The lag is the typical permit-to-completion time (about 1 year for single-family, 2 for apartments).

Caveats, stated wherever these factors are shown:
- Census completions include units in areas that don't issue permits (2-5% of starts), so the single-family
  ratio can exceed 1; the true rate for permitted single-family units is just under 1.
- Permits often classify townhouse rows as 2-4 or 5+ units while completions count each townhouse as
  single-family attached, which pulls the 2+ ratio down: it is a lower bound for multifamily.
"""

from __future__ import annotations

import pandas as pd


def annual_totals(monthly: pd.Series) -> pd.Series:
    """Calendar-year sums of a monthly, not seasonally adjusted series (index: dates), complete years only."""
    values = pd.to_numeric(monthly, errors="coerce")
    years = pd.DatetimeIndex(monthly.index).year
    grouped = values.groupby(years)
    return grouped.sum().where(grouped.count() == 12).dropna().rename_axis("year")


def completion_ratio(completions: pd.Series, permits: pd.Series, start: int, end: int, lag: int) -> float:
    """Units completed in [start+lag, end+lag] per unit permitted in [start, end] (annual series by year)."""
    need_p, need_c = range(start, end + 1), range(start + lag, end + lag + 1)
    missing = [y for y in need_p if y not in permits.index] + [
        y for y in need_c if y not in completions.index
    ]
    if missing:
        raise ValueError(f"missing years: {sorted(set(missing))}")
    return float(completions.loc[list(need_c)].sum() / permits.loc[list(need_p)].sum())
