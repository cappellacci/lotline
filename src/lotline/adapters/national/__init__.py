"""National adapters: Census BPS, ACS, FHFA HPI, FRED, BLS PPI, Census geographies."""

from lotline.adapters.national import acs, bps, fhfa, fred

# source id -> (adapter module exposing load(state, store, ...), canonical table it builds)
SOURCES = {
    "acs": (acs, "acs_geo_year"),
    "bps": (bps, "bps_place_year"),
    "fhfa": (fhfa, "market_geo_year"),
    "fred": (fred, "market_geo_year"),
}
