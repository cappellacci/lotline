"""D-078: the ADU flag undercount table by source (`config/params/adu.yaml` `adu_flag_undercount`).

Synthetic table and permits only. The hand-worked example (all numbers below are worked by hand):

- Field rows A 1.10 (90%: 1.05-1.20) and B 1.05 (1.02-1.08); field row C has no k and takes the prior.
  Prior centre = exp((ln 1.10 + ln 1.05) / 2) = sqrt(1.155) = 1.07471; range 1.0 (the prior's low) to 1.20
  (the larger measured field high, A's).
- Parser rows P 1.25 (90%: 1.10-1.50) and Q 1.50 (95%: 1.20-2.00); parser row G has no hand check (k = 1).
- Floor row M (Met Council style) and no-k row COL (Columbus style): k = 1.
- Source S is a parser up to 2021 (1.60, 1.40-1.80) and a prior field row from 2022.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
import yaml

from lotline.config import UndercountTable, load_params, load_undercount
from lotline.model import undercount as uc
from lotline.model.scenarios import adu

Z90 = 1.6448536269514722
Z95 = 1.959963984540054

TABLE = {
    "table": True,
    "unit": "ratio",
    "source": "synthetic, D-078",
    "prior": {"low": 1.0, "interval": 0.9, "source": "D-078 §1"},
    "rows": [
        {
            "source": "A",
            "place": "a",
            "kind": "field",
            "value": 1.10,
            "low": 1.05,
            "high": 1.20,
            "interval": 0.9,
            "report": "r",
        },
        {
            "source": "B",
            "place": "b",
            "kind": "field",
            "value": 1.05,
            "low": 1.02,
            "high": 1.08,
            "interval": 0.9,
            "report": "r",
        },
        {"source": "C", "place": "c", "kind": "field", "prior": True, "report": "r"},
        {
            "source": "P",
            "place": "p",
            "kind": "parser",
            "value": 1.25,
            "low": 1.10,
            "high": 1.50,
            "interval": 0.9,
            "report": "r",
        },
        {
            "source": "Q",
            "place": "q",
            "kind": "parser",
            "value": 1.50,
            "low": 1.20,
            "high": 2.00,
            "interval": 0.95,
            "report": "r",
        },
        {"source": "G", "place": "g", "kind": "parser", "report": "r"},
        {"source": "M", "place": "m", "kind": "floor", "report": "r"},
        {"source": "COL", "place": "col", "kind": "none", "report": "r"},
        {
            "source": "S",
            "place": "s",
            "kind": "parser",
            "last_year": 2021,
            "value": 1.60,
            "low": 1.40,
            "high": 1.80,
            "interval": 0.9,
            "low_recall": True,
            "report": "r",
        },
        {"source": "S", "place": "s", "kind": "field", "first_year": 2022, "prior": True, "report": "r"},
    ],
}
IDX = {"A": 0, "B": 1, "C": 2, "P": 3, "Q": 4, "G": 5, "M": 6, "COL": 7, "S_old": 8, "S_new": 9}


def _table(**changes) -> UndercountTable:
    return UndercountTable.model_validate(TABLE | changes)


def _rows():
    return uc.resolve(_table())


# ---- the prior (D-078 §1) ------------------------------------------------------------------------------


def test_prior_centre_and_range_by_hand():
    centre, low, high, interval = uc.prior(_table())
    assert centre == pytest.approx(math.sqrt(1.10 * 1.05))  # 1.07471
    assert centre == pytest.approx(1.07471, abs=1e-5)
    assert (low, high, interval) == (1.0, 1.20, 0.9)


def test_prior_row_puts_its_range_at_the_90_percent_quantiles():
    c = _rows()[IDX["C"]]
    assert c.from_prior and c.kind == "field"
    assert c.quantile(0.0) == pytest.approx(1.07471, abs=1e-5)
    assert c.quantile(-Z90) == pytest.approx(1.0)
    assert c.quantile(Z90) == pytest.approx(1.20)


def test_prior_ignores_parser_rows_and_moves_with_a_new_field_row():
    rows = TABLE["rows"] + [
        {
            "source": "D",
            "place": "d",
            "kind": "field",
            "value": 1.30,
            "low": 1.25,
            "high": 1.40,
            "interval": 0.9,
            "report": "r",
        }
    ]
    centre, _, high, _ = uc.prior(_table(rows=rows))
    assert centre == pytest.approx((1.10 * 1.05 * 1.30) ** (1 / 3))  # P, Q and S (parsers) stay out
    assert high == 1.40


def test_measured_row_quantiles_by_hand():
    a, q = _rows()[IDX["A"]], _rows()[IDX["Q"]]
    assert a.quantile(0.0) == pytest.approx(1.10)
    assert a.quantile(-Z90) == pytest.approx(1.05)
    assert a.quantile(Z90) == pytest.approx(1.20)
    # halfway up in log terms: 1.10 * sqrt(1.20 / 1.10)
    assert a.quantile(Z90 / 2) == pytest.approx(1.10 * math.sqrt(1.20 / 1.10))
    assert q.quantile(-Z95) == pytest.approx(1.20)  # a 95% row uses 1.96
    assert q.quantile(Z95) == pytest.approx(2.00)


# ---- draws: shared for field flags, independent per parser (D-078 §5) -----------------------------------


def _z(row, k):
    """Back out the standard-normal score of a draw (split lognormal)."""
    zq = Z90 if row.interval == 0.9 else Z95
    lo, hi = math.log(row.value / row.low) / zq, math.log(row.high / row.value) / zq
    x = np.log(k / row.value)
    return np.where(x < 0, x / lo, x / hi)


def test_field_rows_share_one_draw_and_parsers_draw_their_own():
    rows = _rows()
    k = uc.draw_matrix(rows, 4000, np.random.default_rng(1))
    za, zb, zc = (_z(rows[IDX[s]], k[:, IDX[s]]) for s in ("A", "B", "C"))
    zs_new = _z(rows[IDX["S_new"]], k[:, IDX["S_new"]])
    np.testing.assert_allclose(za, zb)  # the same percentile in every draw
    np.testing.assert_allclose(za, zc)
    np.testing.assert_allclose(za, zs_new)
    zp, zq = _z(rows[IDX["P"]], k[:, IDX["P"]]), _z(rows[IDX["Q"]], k[:, IDX["Q"]])
    zs_old = _z(rows[IDX["S_old"]], k[:, IDX["S_old"]])
    for x, y in ((zp, zq), (zp, za), (zq, za), (zs_old, zp), (zs_old, za)):
        assert abs(np.corrcoef(x, y)[0, 1]) < 0.06
    assert np.median(k[:, IDX["P"]]) == pytest.approx(1.25, abs=0.01)
    assert np.mean(k[:, IDX["A"]] <= 1.20) == pytest.approx(0.95, abs=0.015)


def test_draws_are_reproducible_from_their_seed():
    a = uc.draws(10, 7, _table())
    b = uc.draws(10, 7, _table())
    assert [f.get("P", 2020) for f in a] == [f.get("P", 2020) for f in b]


# ---- floor, no-k and pending rows --------------------------------------------------------------------


def test_floor_none_and_pending_rows_are_one_in_every_draw():
    rows = _rows()
    k = uc.draw_matrix(rows, 500, np.random.default_rng(2))
    for s in ("M", "COL", "G"):
        assert (k[:, IDX[s]] == 1.0).all()
    assert rows[IDX["M"]].floor and not rows[IDX["COL"]].floor
    central = uc.central(_table())
    assert central.get("COL", 2020) == 1.0  # Columbus: no k (D-078 §4)
    assert central.get("M", 2020) == 1.0
    assert central.get("not_in_table", 2020) == 1.0


def test_year_split_row():
    central = uc.central(_table())
    assert central.get("S", 2021) == pytest.approx(1.60)
    assert central.get("S", 2022) == pytest.approx(1.07471, abs=1e-5)


@pytest.mark.parametrize(
    "bad",
    [
        {
            "source": "X",
            "place": "x",
            "kind": "floor",
            "value": 1.1,
            "low": 1.0,
            "high": 1.2,
            "interval": 0.9,
            "report": "r",
        },  # a floor row has k = 1
        {
            "source": "X",
            "place": "x",
            "kind": "none",
            "value": 1.1,
            "low": 1.0,
            "high": 1.2,
            "interval": 0.9,
            "report": "r",
        },  # Columbus has no k
        {"source": "X", "place": "x", "kind": "parser", "prior": True, "report": "r"},  # prior is for fields
        {"source": "X", "place": "x", "kind": "field", "report": "r"},  # a field row needs k or the prior
        {
            "source": "X",
            "place": "x",
            "kind": "parser",
            "value": 0.9,
            "low": 0.8,
            "high": 1.0,
            "interval": 0.9,
            "report": "r",
        },  # k < 1
        {"source": "A", "place": "a", "kind": "parser", "report": "r"},  # A already has a row for every year
    ],
)
def test_table_rejects_bad_rows(bad):
    with pytest.raises(ValueError):
        _table(rows=TABLE["rows"] + [bad])


# ---- k scales counted ADU permits only -----------------------------------------------------------------


def _permits(rows):
    """rows: (geoid, source, year, n ADU permits, n houses)."""
    out = []
    for g, s, y, n_adu, n_sfd in rows:
        out += [
            {
                "jurisdiction_geoid": g,
                "source": s,
                "issue_year": y,
                "building_type_std": "ADU",
                "adu_type": None,
            }
        ] * n_adu
        out += [
            {
                "jurisdiction_geoid": g,
                "source": s,
                "issue_year": y,
                "building_type_std": "SFD",
                "adu_type": None,
            }
        ] * n_sfd
    return pd.DataFrame(out)


def test_counts_scale_by_source_before_the_larger_is_kept():
    # place X: field source A 10 ADUs (x 1.10 = 11.0) and floor source M 10.5 can't happen, so M 10 -> A kept
    # place Y: parser P 4 (x 1.25 = 5.0) and floor M 6 (x 1) -> M kept at 6
    # place Z: Columbus-style COL 3 -> 3 (no k)
    p = _permits(
        [
            ("X", "A", 2020, 10, 5),
            ("X", "M", 2020, 10, 0),
            ("Y", "P", 2020, 4, 2),
            ("Y", "M", 2020, 6, 0),
            ("Z", "COL", 2020, 3, 1),
        ]
    )
    raw = adu.observed_adu_counts(p, 2020, 2020).set_index("geoid")["adu_permits"]
    assert raw.to_dict() == {"X": 10, "Y": 6, "Z": 3}
    out = adu.observed_adu_counts(p, 2020, 2020, uc.central(_table())).set_index("geoid")
    assert out.loc["X", "adu_permits"] == pytest.approx(11.0)
    assert (out.loc["X", "source"], out.loc["X", "counted"], out.loc["X", "k_row"]) == ("A", 10, IDX["A"])
    assert (out.loc["Y", "adu_permits"], out.loc["Y", "source"]) == (6.0, "M")
    assert out.loc["Z", "adu_permits"] == 3.0


def test_observed_floor_draws_scale_counts_not_eligible_lots():
    # place 0: 1,000 lots; 2.0 ADUs a year from A and 1.0 from a k = 1 source -> rate_d = (2 kA_d + 1) / 1000
    # place 1: no observed floor -> NaN in every draw
    table = _table()
    places = pd.DataFrame(
        {
            "eligible_parcels": [1000.0, 500.0],
            "observed_rate": [(2 * 1.10 + 1) / 1000, np.nan],
            "observed_adu_by_k_row": [{IDX["A"]: 2.0, -1: 1.0}, np.nan],
        }
    )
    got = adu.observed_rate_draws(places, 200, 5, table)
    k = uc.draw_matrix(uc.resolve(table), 200, np.random.default_rng(5))
    np.testing.assert_allclose(got[:, 0], (2 * k[:, IDX["A"]] + 1) / 1000)
    assert np.isnan(got[:, 1]).all()
    assert adu.observed_rate_draws(places.drop(columns="observed_adu_by_k_row"), 5, 5, table) is None


def test_terms_by_row_add_up_to_the_observed_floor():
    # origin 2025, 4 years; place X: 2022-23 from A (raw 2, 2), 2024-25 from a k = 1 source (raw 1, 3)
    counts = pd.DataFrame(
        {
            "geoid": ["X"] * 4,
            "year": [2022, 2023, 2024, 2025],
            "adu_permits": [2.2, 2.2, 1.0, 3.0],
            "counted": [2, 2, 1, 3],
            "k_row": [IDX["A"], IDX["A"], -1, -1],
        }
    )
    terms = adu.observed_terms_by_k_row(counts, 2025, 4, {})
    assert terms == {"X": {IDX["A"]: 1.0, -1: 1.0}}
    floor = adu.observed_per_year(counts, 2025, 4, {})
    assert floor["X"] == pytest.approx(1.0 * 1.10 + 1.0)  # 8.4 / 4 = 2.1


# ---- the real table -----------------------------------------------------------------------------------


def test_real_table_matches_d078():
    t = load_undercount()
    rows = {(r.source, r.first_year, r.last_year): r for r in t.rows}
    assert (
        rows[("raleigh_permits", None, None)].value,
        rows[("raleigh_permits", None, None)].low,
        rows[("raleigh_permits", None, None)].high,
    ) == (1.07, 1.02, 1.21)
    assert rows[("austin_permits", None, None)].value == 1.13
    assert rows[("portland_permits", None, None)].value == 1.06
    assert rows[("mpls_ccs_permits", None, None)].kind == "parser"
    assert rows[("durham_permits", None, None)].prior
    assert rows[("metc_residential_permits", None, None)].floor
    assert rows[("columbus_permits", None, None)].kind == "none"
    centre, low, high, _ = uc.prior(t)
    assert centre == pytest.approx(math.exp((math.log(1.07) + math.log(1.13) + math.log(1.06)) / 3))
    assert centre == pytest.approx(1.0862, abs=1e-4)
    assert (low, high) == (1.0, 1.21)
    for r in t.rows:
        assert r.report.strip() and r.place.strip()
    assert "adu_flag_undercount" not in load_params("adu")  # a table, not a single parameter


def test_real_table_reaches_every_permit_source_that_flags_adus(tmp_path):
    """Every permit adapter whose module talks about ADUs has a row, so no source is silently k = 1."""
    import pathlib
    import re

    root = pathlib.Path(adu.__file__).resolve().parents[2] / "adapters" / "states"
    sources = set()
    for f in root.glob("*/*.py"):
        text = f.read_text()
        m = re.search(r'^SOURCE = "([a-z_]+)"', text, re.M)
        if m and "parcels" not in m.group(1) and re.search(r"\bADU", text) and "building_type_std" in text:
            sources.add(m.group(1))
    in_table = {r.source for r in load_undercount().rows}
    no_adu_flag = {"stpaul_permits"}  # no ADU flag at all (its adapter says so)
    assert sources - in_table - no_adu_flag == set()


def test_yaml_table_round_trips(tmp_path):
    (tmp_path / "params").mkdir()
    (tmp_path / "params" / "adu.yaml").write_text(yaml.safe_dump({"adu_flag_undercount": TABLE}))
    assert load_undercount(tmp_path) == _table()
    assert load_params("adu", tmp_path) == {}
