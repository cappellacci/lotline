"""National adapters: Census BPS, ACS, FHFA HPI, FRED, BLS PPI, Census geographies."""

from lotline.adapters.national import bps, fhfa

# source id -> (adapter module exposing load(state, store, ...), canonical table it builds)
SOURCES = {"bps": (bps, "bps_place_year"), "fhfa": (fhfa, "market_geo_year")}
