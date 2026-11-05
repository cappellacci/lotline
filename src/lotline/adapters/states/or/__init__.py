"""State adapters for OR: parcels (RLIS), permits, zoning, fees and reforms.

The package is named `or`, like every other state (`config/states/or.yaml`, the store's `interim/or/`, the
registry's `st.name.upper()`). `or` is a Python keyword, so `from lotline.adapters.states.or import x` is a
syntax error. Two rules follow:

- Inside this package, import siblings relatively: `from . import rlis_common`, `from .rlis_common import f`.
- Outside it (tests, scripts), use `importlib.import_module("lotline.adapters.states.or.<module>")`.

`tests/states/or/test_package.py` checks both rules and that the registry tags these sources as `OR`.
"""
