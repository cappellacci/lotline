"""The Oregon adapter package is named `or` (a Python keyword) and still works end to end.

See `src/lotline/adapters/states/or/__init__.py` for the two import rules this file checks.
"""

import importlib
import sys
import textwrap

import pytest

from lotline import registry

SOURCE_BODY = """
from . import _helper
from ._helper import tag

SOURCE = "or_test_permits"
TABLE = "permits"
PROVENANCE = {
    "title": "Test permits", "landing_url": "https://example.org", "table": "permits",
    "cleaning": ["none"], "limitations": ["synthetic"],
}

def load(state, store, *, refresh=False):
    return tag(_helper.NAME)
"""


@pytest.fixture
def fake_states(tmp_path, monkeypatch):
    """A throwaway `fakestates_or` package with an `or` state holding one source and one helper."""
    root = tmp_path / "fakestates_or"
    (root / "or").mkdir(parents=True)
    (root / "__init__.py").write_text("")
    (root / "or" / "__init__.py").write_text("")
    (root / "or" / "_helper.py").write_text('NAME = "or"\n\ndef tag(x):\n    return f"tagged-{x}"\n')
    (root / "or" / "test_permits.py").write_text(textwrap.dedent(SOURCE_BODY))
    monkeypatch.syspath_prepend(str(tmp_path))
    yield root
    for name in [m for m in sys.modules if m.startswith("fakestates_or")]:
        del sys.modules[name]


def test_absolute_from_import_is_a_syntax_error():
    with pytest.raises(SyntaxError):
        compile("from lotline.adapters.states.or import x", "<test>", "exec")


def test_real_package_imports_with_importlib():
    pkg = importlib.import_module("lotline.adapters.states.or")
    assert pkg.__name__ == "lotline.adapters.states.or"


def test_registry_tags_an_or_package_as_state_OR(fake_states):
    found = registry.sources_for("OR", package="fakestates_or")
    assert "test_permits" in found
    assert found["test_permits"].states == ("OR",)
    assert "_helper" not in found  # helper module, skipped
    assert "test_permits" not in registry.sources_for("MN", package="fakestates_or")


def test_relative_sibling_imports_work_inside_the_package(fake_states):
    module = importlib.import_module("fakestates_or.or.test_permits")
    assert module.load("OR", None) == "tagged-or"


def test_real_registry_still_loads_with_the_or_package():
    registry.all_sources()  # discovers lotline.adapters.states.or without error
