"""HUD income limits adapter: county rows to market_geo_year; no file registered, no rows (synthetic)."""

import pandas as pd
import pytest

from lotline.adapters.national import hud_il
from lotline.io.store import DataStore
from lotline.schemas import validate


def _raw():
    return pd.DataFrame(
        {
            "fips": ["3718399999", "3706399999", "2505300160", "0100199999"],
            "State_Alpha": ["NC", "NC", "MA", "AL"],
            "median2026": ["132,300", "132300", "150000", "80000"],
            **{f"l50_{n}": [str(v) for v in (46350 + n, 52950, 75000, 28000)] for n in range(1, 9)},
        }
    )


def test_to_canonical_keeps_whole_counties_and_parses_numbers():
    out = hud_il.to_canonical(_raw())
    assert list(out["geo"]) == ["county:37183", "county:37063", "county:01001"]  # MA town row left out
    assert out.loc[0, "hud_mfi"] == 132300.0
    assert out.loc[0, "hud_l50_1"] == 46351.0
    assert (out["year"] == 2026).all()
    validate(out, "market_geo_year")


def test_excel_dropped_leading_zero_is_restored():
    raw = _raw().assign(fips=["3718399999", "3706399999", "2505300160", "100199999"])
    assert "county:01001" in set(hud_il.to_canonical(raw)["geo"])


def test_for_state_filters_by_fips_prefix():
    assert list(hud_il.for_state(hud_il.to_canonical(_raw()), "37")["geo"]) == [
        "county:37183",
        "county:37063",
    ]


def test_missing_columns_say_which():
    with pytest.raises(ValueError, match="median"):
        hud_il.to_canonical(_raw().drop(columns="median2026"))


def test_load_without_a_registered_file_returns_no_rows(tmp_path, capsys):
    df = hud_il.load("NC", DataStore(tmp_path))
    assert df.empty and "hud_mfi" in df
    assert "manifest register" in capsys.readouterr().out


def test_load_reads_the_registered_file(tmp_path):
    f = tmp_path / "Downloads" / "Section8-FY26.csv"
    f.parent.mkdir()
    _raw().to_csv(f, index=False)
    store = DataStore(tmp_path / "data")
    store.register(f, source=hud_il.SOURCE, url=hud_il.LANDING_URL, license=hud_il.LICENSE, vintage="fy2026")
    df = hud_il.load("NC", store)
    assert sorted(df["geo"]) == ["county:37063", "county:37183"]
