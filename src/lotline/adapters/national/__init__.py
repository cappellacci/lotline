"""National adapters: Census BPS, ACS, FHFA HPI, FRED, BLS PPI, Census geographies."""

from lotline.adapters.national import bps

# source id -> adapter module exposing load(state, store, ...) and the table it builds
SOURCES = {"bps": (bps, "bps_place_year")}
