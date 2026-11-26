"""The app tests run the page's JavaScript under node and skip when it is missing on a laptop.

On CI (`CI` set, as GitHub Actions does) a missing node is an error instead, so the JavaScript/Python parity
tests can't silently disappear from a green run (nightly review, 2026-11-25)."""

import os
import shutil

import pytest


def pytest_collection_modifyitems(config, items):
    if os.environ.get("CI") and shutil.which("node") is None:
        raise pytest.UsageError("node is required on CI for tests/app (actions/setup-node in the workflow)")
