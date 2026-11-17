# ruff: noqa: E501  (hand-worked examples)
"""Component taxonomy, the group rule and polite access (LESSONS T1, D4, R1-R5)."""

from datetime import date

import pytest

from lotline.rule_agents.fees import access, classify, groups


@pytest.mark.parametrize(
    "pays_for,name,comp,flagged",
    [
        (
            "water",
            "Water impact fee, lots platted after 2023-10-01",
            "water_sewer",
            False,
        ),  # TX: water, not impact
        ("sewer", "Sewer permit fee", "water_sewer", False),  # Columbus
        ("sewer", "Metropolitan SAC charge", "water_sewer", False),
        ("parks", "Park dedication cash-in-lieu - single family", "impact", False),
        ("stormwater", "Stormwater SDC, general capacity", "impact", False),
        ("plan_review", "Building permit plan review", "permit", False),
        ("conditional_use", "Conditional use permit application", "planning", False),  # planning words win
        ("parks", "Building permit", "impact", True),
        ("something_new", "Technology fee", "other", True),
    ],
)
def test_component(pays_for, name, comp, flagged):
    got, flag = classify.check(pays_for, name)
    assert got == comp
    assert (flag is not None) == flagged


def test_area_group_median():
    # odd count: the middle row (SAWS-like elevation areas)
    assert groups.central_index([4749, 4908, 5100], "area") == 1
    # even count: median 250 is equally near 200 and 300 -> the lower one (Ben, 2026-10-30)
    assert groups.central_index([400, 300, 200, 100], "area") == 2
    assert groups.group_range([400, 300, 200, 100]) == (100, 400)


def test_plat_date_group_newest():
    starts = [date(2007, 10, 1), date(2023, 10, 1), date(2015, 1, 1)]
    assert groups.central_index([1100, 4800, 2000], "plat_date", starts) == 1
    with pytest.raises(ValueError):
        groups.central_index([1, 2], "plat_date", [None, date(2020, 1, 1)])


def test_robots():
    txt = "User-agent: *\nDisallow: /regs/\n"
    assert not access.robots_allows(txt, "https://online.example.com/regs/doc.aspx")
    assert access.robots_allows(txt, "https://online.example.com/fees.pdf")
    assert access.robots_allows(None, "https://anything.example.com/x")


def test_access_reasons():
    assert access.access_reason(403) == "http_403_waf"
    assert access.access_reason(200, "<title>Just a moment...</title>") == "http_403_waf"
    assert access.access_reason(200, "fees " * 5000 + "akamai") is None  # long real page naming a CDN
    assert access.access_reason(200, '<form><input type="password"></form>') == "login_required"
    assert access.access_reason(200, "ok", robots_ok=False) == "robots_disallow"
    assert access.access_reason(404) == "not_found"
    assert access.access_reason(200, "Water capacity fee $1,828") is None


def test_quote_found():
    text = "Zone 1:\n  Single-family   dwelling $1871.00  $1916.00 per unit\nZone 2 – other"
    assert access.quote_found("Single-family dwelling $1871.00 $1916.00 per unit", text)
    assert access.quote_found("Zone 1: ... $1916.00 per unit", text)
    assert access.quote_found("zone 2 - other", text)
    assert not access.quote_found("Single-family dwelling $1916.00", text)
    assert not access.quote_found("$1916.00 ... Zone 1:", text)  # parts out of order


def test_doc_id_and_sidecar(tmp_path):
    from lotline.io.store import DataStore, sha256_file
    from lotline.rule_agents.fees import cli

    store = DataStore(tmp_path / "data")
    page = tmp_path / "fees.html"
    page.write_text("<html><script>x()</script><p>Water&nbsp;tap fee: $1,828</p></html>")
    doc_id = cli._sidecar(store, page)
    assert doc_id == sha256_file(page)
    side = (store.root / "interim" / "docs" / f"{doc_id}.txt").read_text()
    assert access.quote_found("Water tap fee: $1,828", side) and "x()" not in side
    # a hand-saved PDF gets a doc id but no text sidecar until a PDF reader is approved
    pdf = tmp_path / "s.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    entry = store.register(
        pdf,
        source="rule-agents-fees-manual",
        url="https://x.example/s.pdf",
        license="public record",
        vintage="mn",
    )
    assert cli._sidecar(store, store.root / entry.path) == entry.sha256
    assert not (store.root / "interim" / "docs" / f"{entry.sha256}.txt").exists()
