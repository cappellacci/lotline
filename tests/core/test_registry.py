"""Source registry: state sources are discovered, checked against the contract, and documented."""

import sys
import textwrap

import pandas as pd
import pytest

from lotline import registry
from lotline.validation import holdout

GOOD = """
SOURCE = "{sid}"
TABLE = "permits"
PROVENANCE = {{
    "title": "Test permits", "landing_url": "https://example.org", "table": "permits",
    "cleaning": ["none"], "limitations": ["synthetic"],
}}

def load(state, store, *, refresh=False):
    return None
"""


@pytest.fixture
def fake_states(tmp_path, monkeypatch):
    """A throwaway `fakestates` package: fakestates/mn/<modules>."""
    root = tmp_path / "fakestates"
    (root / "mn").mkdir(parents=True)
    (root / "__init__.py").write_text("")
    (root / "mn" / "__init__.py").write_text("")
    monkeypatch.syspath_prepend(str(tmp_path))
    yield root
    for name in [m for m in sys.modules if m.startswith("fakestates")]:
        del sys.modules[name]


def _module(root, name, body):
    (root / "mn" / f"{name}.py").write_text(textwrap.dedent(body))


def test_state_source_is_discovered_for_its_state_only(fake_states):
    _module(fake_states, "metc_permits", GOOD.format(sid="metc_permits"))
    _module(fake_states, "_pins", "def normalize(pin): return pin\n")  # helper: skipped
    mn = registry.sources_for("MN", package="fakestates")
    assert (
        "metc_permits" in mn
        and mn["metc_permits"].states == ("MN",)
        and mn["metc_permits"].table == "permits"
    )
    assert {"bps", "acs", "fhfa", "fred", "jurisdictions"} <= set(mn)  # national sources everywhere
    assert "metc_permits" not in registry.sources_for("NC", package="fakestates")
    assert "_pins" not in mn


def test_state_sources_are_documented_automatically(fake_states):
    _module(fake_states, "metc_permits", GOOD.format(sid="metc_permits"))
    assert "metc_permits" in registry.provenance_modules(package="fakestates")


@pytest.mark.parametrize(
    ("body", "error"),
    [
        ('SOURCE = "x"\nTABLE = "permits"\n', "missing PROVENANCE, load"),
        (GOOD.format(sid="x").replace('TABLE = "permits"', 'TABLE = "permitz"'), "not a canonical table"),
        (GOOD.format(sid="x").replace('"limitations": ["synthetic"],', ""), "PROVENANCE lacks limitations"),
    ],
)
def test_half_defined_sources_are_errors(fake_states, body, error):
    _module(fake_states, "broken", body)
    with pytest.raises(registry.RegistryError, match=error):
        registry.sources_for("MN", package="fakestates")


def test_duplicate_manifest_ids_are_rejected(fake_states):
    _module(fake_states, "a_permits", GOOD.format(sid="same_id"))
    _module(fake_states, "b_permits", GOOD.format(sid="same_id"))
    with pytest.raises(registry.RegistryError, match="duplicate manifest SOURCE ids"):
        registry.all_sources(package="fakestates")


def test_names_cannot_shadow_national_sources(fake_states):
    _module(fake_states, "bps", GOOD.format(sid="mn_bps"))
    with pytest.raises(registry.RegistryError, match="duplicate source names"):
        registry.all_sources(package="fakestates")


def test_real_registry_is_consistent():
    sources = registry.all_sources()
    assert {s.name for s in sources} >= {"acs", "bps", "fhfa", "fred", "jurisdictions"}
    for module in registry.provenance_modules().values():
        assert all(module.PROVENANCE.get(k) for k in registry.PROVENANCE_KEYS)


def test_central_guard_catches_an_adapter_that_forgot_the_holdout_filter():
    permits = pd.DataFrame(
        {
            "jurisdiction_geoid": ["2758000", "2743000"],  # St. Paul 2025 must never reach the output
            "issue_date": pd.to_datetime(["2025-03-01", "2025-03-01"]),
            "issue_year": [2025, 2025],
        }
    )
    with pytest.raises(holdout.HoldoutLeak, match="1 held-out rows"):
        holdout.assert_no_leak(permits, "permits", "MN")
    holdout.assert_no_leak(permits.iloc[[1]], "permits", "MN")  # filtered output passes
    holdout.assert_no_leak(permits, "market_geo_year", "MN")  # not an outcome table: not checked
