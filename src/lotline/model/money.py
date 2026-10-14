"""Real dollars (protocol §5.9): every `*_usd` amount is converted to dollars of one base year before use.

    real = nominal × index[base_year] / index[dollar_year]

`index` is a price index by year: CPI-U (`market_geo_year.cpi_u`) for prices and rents, the BLS PPI for
residential construction inputs (`ppi_resid_inputs`) for construction costs. The base year comes from
config/params/money.yaml (`real_dollar_year`). A year missing from the index gives a missing result, never a
silently undeflated number.
"""

from __future__ import annotations

import pandas as pd

from lotline.config import Parameter, load_params

NATIONAL = "national:US"


def base_year(params: dict[str, Parameter] | None = None) -> int:
    p = params or load_params("money")
    return int(p["real_dollar_year"].value)


def index_by_year(market: pd.DataFrame, column: str = "cpi_u", geo: str = NATIONAL) -> pd.Series:
    """One price-index series (year -> level) from `market_geo_year`, e.g. national CPI-U."""
    rows = market[(market["geo"] == geo) & market[column].notna()] if column in market else market.iloc[0:0]
    if rows.empty:
        raise ValueError(f"market_geo_year has no {column} for {geo}")
    return rows.set_index(rows["year"].astype(int))[column].astype(float).sort_index()


def deflate(nominal, dollar_year, index: pd.Series, to_year: int) -> pd.Series:
    """Convert nominal amounts of `dollar_year` into `to_year` dollars with a price index (year -> level).

    `nominal` and `dollar_year` are scalars or aligned Series. Raises if the index lacks `to_year`; returns a
    missing value for any row whose own year isn't in the index.
    """
    if to_year not in index.index:
        raise ValueError(f"price index has no value for the base year {to_year}")
    like = next((x for x in (nominal, dollar_year) if isinstance(x, pd.Series)), pd.Series([0]))
    amounts = nominal if isinstance(nominal, pd.Series) else pd.Series(nominal, index=like.index)
    years = dollar_year if isinstance(dollar_year, pd.Series) else pd.Series(dollar_year, index=like.index)
    level = years.astype("Int64").map(index).astype("Float64")
    return amounts.astype("Float64") * float(index[to_year]) / level
