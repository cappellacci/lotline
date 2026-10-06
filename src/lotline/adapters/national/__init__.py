"""National adapters: Census BPS, ACS, FHFA HPI, FRED, BLS PPI, Census geographies."""

from lotline.adapters.national import acs, bps, fhfa, fred

# source id -> (adapter module exposing load(state, store, ...), canonical table it builds)
SOURCES = {
    "acs": (acs, "acs_geo_year"),
    "bps": (bps, "bps_place_year"),
    "fhfa": (fhfa, "market_geo_year"),
    "fred": (fred, "market_geo_year"),
}


def _register_builds() -> None:
    # build steps that combine national sources; imported late to avoid a cycle
    from lotline.build import jurisdictions

    SOURCES["jurisdictions"] = (jurisdictions, "jurisdictions")


_register_builds()
