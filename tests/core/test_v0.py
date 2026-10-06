import pandas as pd

from lotline.validation import v0


def _places(rows):
    df = pd.DataFrame(rows, columns=["year", "geoid", "units_1", "units_5p"])
    df["units_2"] = df["units_3_4"] = 0
    for c in v0.UNITS:
        df[c + "_rep"] = df[c]
    df["imputed"] = False
    return df


def _census(rows):
    df = pd.DataFrame(rows, columns=["year", "units_1", "units_5p"])
    df["units_2"] = df["units_3_4"] = 0
    return df


def test_reconcile_statuses_and_diffs():
    places = _places([[2020, "a", 100, 50], [2020, "b", 0, 0], [2021, "a", 101, 0], [2022, "a", 120, 0]])
    census = _census([[2020, 100, 50], [2021, 100, 0], [2022, 100, 0]])
    rec = v0.reconcile(places, census, blocked=set()).set_index("year")
    assert rec.loc[2020, "status"] == "match" and rec.loc[2020, "diff"] == 0
    assert rec.loc[2021, "status"] == "within 1%" and rec.loc[2021, "diff_1"] == 1
    assert rec.loc[2022, "status"] == "gap" and rec.loc[2022, "diff_pct"] == "+20.00%"


def test_held_out_years_reveal_nothing():
    # state total minus our (filtered) sum would equal the held-out place: no numbers may appear
    places = _places([[2024, "a", 10, 0]])
    census = _census([[2024, 25, 0]])
    row = v0.reconcile(places, census, blocked={2024}).iloc[0]
    assert row["status"] == "held out (not compared)"
    assert set(row.dropna().index) == {"year", "status"}


def test_attribution_shares():
    places = _places([[2010, "a", 90, 0], [2010, None, 10, 0], [2000, "a", 50, 0]])
    att = v0.attribution(places).set_index("period")
    assert att.loc["2009 on", "unattributed"] == "10.00%"
    assert att.loc["1992–2008", "unattributed"] == "0.00%"


def test_held_out_years_from_config():
    assert {2024, 2025, 2026} <= v0.held_out_years("MN")
    assert 2023 in v0.held_out_years("NC") and v0.held_out_years("OH") == set()
