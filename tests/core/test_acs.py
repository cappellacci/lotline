import json

import httpx
import pandas as pd
import pytest

from lotline.adapters.national import acs
from lotline.io import DataStore, fetch
from lotline.schemas import assert_conforms

LABELS = {"B25077_001": "Median value (dollars)", "B25024_004": "Total:!!2"}


def _payload():
    return [
        ["B25077_001E", "B25077_001M", "B25024_004E", "B25024_004M", "state", "place"],
        ["345600", "3908", "17048", "-555555555", "27", "43000"],  # controlled MOE -> 0
        ["-666666666", "-222222222", "12", "9", "27", "00316"],  # estimate code -> missing
    ]


def test_parse_long_format_with_sentinels():
    df = acs.parse(_payload(), "place", 2023, LABELS)
    assert_conforms(df, "acs_geo_year")
    mpls = df[df.geo == "place:2743000"].set_index("variable")
    assert mpls.loc["B25077_001", "estimate"] == 345600 and mpls.loc["B25077_001", "moe"] == 3908
    assert mpls.loc["B25024_004", "moe"] == 0
    other = df[df.geo == "place:2700316"].set_index("variable")
    assert pd.isna(other.loc["B25077_001", "estimate"]) and pd.isna(other.loc["B25077_001", "moe"])
    assert set(df.table_id) == {"B25077", "B25024"} and set(df.end_year) == {2023}


def test_tract_and_cousub_geoids_concatenate_codes():
    payload = [["B25077_001E", "B25077_001M", "state", "county", "tract"], ["1", "1", "27", "053", "000100"]]
    assert acs.parse(payload, "tract", 2023, LABELS).geo.tolist() == ["tract:27053000100"]
    payload = [
        ["B25077_001E", "B25077_001M", "state", "county", "county subdivision"],
        ["1", "1", "27", "001", "02224"],
    ]
    assert acs.parse(payload, "cousub", 2023, LABELS).geo.tolist() == ["cousub:2700102224"]


def test_variables_and_labels_from_group_metadata():
    groups = {
        "B25003": {
            "variables": {
                "B25003_001E": {"label": "Estimate!!Total:"},
                "B25003_001M": {"label": "Margin"},
                "B25003_001EA": {"label": "Annotation"},
                "B25003_002E": {"label": "Estimate!!Total:!!Owner occupied"},
                "NAME": {"label": "Geographic Area Name"},
            }
        }
    }
    assert acs.variables_for(groups) == ["B25003_001", "B25003_002"]
    assert acs.labels_for(groups)["B25003_002"] == "Total:!!Owner occupied"


def test_requests_stay_under_the_variable_limit():
    parts = acs.chunks([f"B25034_{i:03d}" for i in range(1, 60)])
    assert all(2 * len(p) <= acs.MAX_VARS for p in parts) and sum(map(len, parts)) == 59


def test_api_key_never_reaches_the_manifest(tmp_path):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, content=json.dumps(_payload()).encode())

    store = DataStore(tmp_path)
    url = "https://api.census.gov/data/2023/acs/acs5?get=B25077_001E&for=place:*&in=state:27"
    fetch(
        url,
        tmp_path / "raw/x.json",
        store=store,
        source="s",
        license="PD",
        adapter="a",
        adapter_version="1",
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        secret_params={"key": "SECRET123"},
    )
    assert "key=SECRET123" in seen[0] and "for=place" in seen[0]  # sent, query preserved
    assert "SECRET123" not in store.manifest_path.read_text()


def test_html_error_page_is_not_cached(tmp_path, monkeypatch):
    monkeypatch.setattr(
        acs,
        "fetch",
        lambda url, dest, **kw: (
            dest.parent.mkdir(parents=True, exist_ok=True),
            dest.write_text("<html>Invalid Key</html>"),
            dest,
        )[2],
    )
    dest = tmp_path / "raw/x.json"
    with pytest.raises(acs.CensusKeyError):
        acs._fetch_json("https://api.census.gov/x", dest, DataStore(tmp_path), False, "K")
    assert not dest.exists()


def test_missing_key_is_a_clear_error(monkeypatch, tmp_path):
    monkeypatch.delenv("CENSUS_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)  # no .env here
    with pytest.raises(acs.CensusKeyError, match="CENSUS_API_KEY"):
        acs.api_key()
