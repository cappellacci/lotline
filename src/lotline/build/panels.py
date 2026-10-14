"""Jurisdiction × year panel: permits (numerator) beside eligible parcels (denominator), plus market data.

Protocol §5.1 and BUILD_PLAN §5.2: the outcome is net new units per 1,000 eligible parcels, but numerator and
denominator are **stored separately, always**. This panel never holds a rate; the model forms one when it
needs it, so a denominator change never silently rewrites history.

Key: `(state, geoid, year)`, one row per permit-issuing jurisdiction and year in `bps_place_year`.

- **Numerator** (`bps_place_year`): units by size class, total (`units_*`, incl. Census imputation) and
  reported only (`units_*_rep`). A jurisdiction BPS files under several IDs in one year (a place in two
  counties, an Ohio "County Part" plus its unincorporated area) is summed; `n_bps_rows` says how many rows,
  `imputed` is True if any was imputed. BPS rows with no GEOID can't be matched and are left out.
- **Denominator** (`eligible_parcels`): one `theme` and one `rule_version`, chosen explicitly, with its
  `denominator_source`, `denominator_quality` and `data_tier`. Unincorporated-county rows use the county
  GEOID on both sides. Years with no denominator stay missing, never 0.
- **Market** (`market_geo_year`): national `cpi_u`, `mortgage_rate`, `ppi_resid_inputs` (`national:US`);
  FHFA `hpi`/`hpi_base2000` from the first level in `hpi_levels` that has a value (`hpi_geo` records which).
"""

from __future__ import annotations

import pandas as pd

from lotline.io import DataStore
from lotline.validation import holdout

KEY = ["state", "geoid", "year"]
SIZE_CLASSES = ["1", "2", "3_4", "5p"]
UNITS = [f"units_{s}" for s in SIZE_CLASSES] + [f"units_{s}_rep" for s in SIZE_CLASSES]
NATIONAL_COLS = ["cpi_u", "mortgage_rate", "ppi_resid_inputs"]
HPI_COLS = ["hpi", "hpi_base2000"]
DENOMINATOR_COLS = ["eligible_parcels", "denominator_source", "denominator_quality", "data_tier"]


def numerator(bps: pd.DataFrame) -> pd.DataFrame:
    """BPS units by size class per jurisdiction and year (rows sharing a GEOID summed)."""
    b = bps[bps["geoid"].notna()]
    agg = {c: "sum" for c in UNITS}
    agg |= {"county_geoid": "first", "imputed": "any", "months_reported": "min", "bps_id": "count"}
    out = b.sort_values("bps_id").groupby(KEY, as_index=False).agg(agg)
    return out.rename(columns={"bps_id": "n_bps_rows", "months_reported": "months_reported_min"})


def denominator(eligible: pd.DataFrame, theme: str, rule_version: str) -> pd.DataFrame:
    """Eligible parcels for one theme and rule version, keyed like the panel."""
    e = eligible[(eligible["theme"] == theme) & (eligible["rule_version"] == rule_version)]
    if e.empty:
        found = sorted(set(zip(eligible["theme"], eligible["rule_version"], strict=True)))
        raise ValueError(
            f"no eligible_parcels for theme={theme!r}, rule_version={rule_version!r}; have {found}"
        )
    return e.rename(columns={"jurisdiction_geoid": "geoid"})[KEY + DENOMINATOR_COLS]


def _hpi(panel: pd.DataFrame, market: pd.DataFrame, levels: tuple[str, ...]) -> pd.DataFrame:
    out = pd.DataFrame(index=panel.index, columns=[*HPI_COLS, "hpi_geo"], dtype=object)
    if "hpi" not in market:
        return out
    cols = [c for c in HPI_COLS if c in market]
    m = market.dropna(subset=["hpi"]).set_index(["geo", "year"])[cols]
    for level in levels:
        code = {"county": panel["county_geoid"], "state": panel["geoid"].str[:2]}[level]
        geo = level + ":" + code
        found = m.reindex(pd.MultiIndex.from_arrays([geo, panel["year"]])).set_index(panel.index)
        fill = out["hpi"].isna() & found["hpi"].notna()
        out.loc[fill, cols] = found.loc[fill, cols]
        out.loc[fill, "hpi_geo"] = geo[fill]
    return out


def build(
    bps: pd.DataFrame,
    eligible: pd.DataFrame,
    market: pd.DataFrame,
    *,
    theme: str,
    rule_version: str,
    hpi_levels: tuple[str, ...] = ("county",),
) -> pd.DataFrame:
    """The panel: one row per (state, geoid, year) in BPS, numerator and denominator in their own columns."""
    unknown = set(hpi_levels) - {"county", "state"}
    if unknown:
        raise ValueError(f"unsupported hpi_levels {sorted(unknown)}; use 'county' and/or 'state'")
    panel = numerator(bps).merge(denominator(eligible, theme, rule_version), on=KEY, how="left")
    panel["theme"], panel["rule_version"] = theme, rule_version

    national = market[market["geo"] == "national:US"].set_index("year")
    for col in NATIONAL_COLS:
        values = national[col] if col in national else pd.Series(dtype=float)
        panel[col] = panel["year"].map(values).astype("Float64")
    hpi = _hpi(panel, market, hpi_levels)
    for col in HPI_COLS:
        panel[col] = pd.to_numeric(hpi[col]).astype("Float64")
    panel["hpi_geo"] = hpi["hpi_geo"].astype("string")
    return panel.sort_values(KEY, ignore_index=True)


def read_market(store: DataStore, state: str) -> pd.DataFrame:
    """`market_geo_year` from all of its source files (FHFA, FRED, ...), one row per (geo, year).

    Read file by file: pandas reading the folder whole takes the first file's columns and silently drops the
    rest (e.g. FRED's `cpi_u`). Where two sources share a (geo, year), each column keeps its non-null value.
    """
    files = sorted(store.processed(state, "market_geo_year").glob("*.parquet"))
    frames = [pd.read_parquet(f) for f in files]
    if not frames:
        raise FileNotFoundError(f"no market_geo_year files for {state}")
    return pd.concat(frames, ignore_index=True).groupby(["geo", "year"], as_index=False).first()


def load(state: str, store: DataStore, *, theme: str, rule_version: str, **kwargs) -> pd.DataFrame:
    """Build the panel from a state's processed tables. Outcomes come only from the holdout-filtered files,
    and the filter is re-checked here: a held-out row stops the build (validation plan §2)."""
    bps = pd.read_parquet(store.processed(state, "bps_place_year"))
    holdout.assert_no_leak(bps, "bps_place_year", state)
    eligible = pd.read_parquet(store.processed(state, "eligible_parcels"))
    market = read_market(store, state)
    return build(bps, eligible, market, theme=theme, rule_version=rule_version, **kwargs)
