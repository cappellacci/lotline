"""Small synthetic codings for the ADU rule-agent tests (made-up place 'Testville', GEOID 3799999)."""

from __future__ import annotations

import datetime as dt

from lotline.rule_agents.adu.coding import DateEvidence, Era, Evidence, FieldValue, PlaceCoding

DAY = dt.date(2026, 11, 17)
CODE = "https://example.gov/code/sec-5-3"
ORD = "https://example.gov/ordinances/2020-12.pdf"
MIRROR = "https://www.zoneomics.com/code/testville"


def ev(quote: str, url: str = CODE, kind: str = "official_code", section: str | None = "5.3") -> Evidence:
    return Evidence(url=url, retrieved=DAY, quote=quote, section=section, kind=kind)


def fv(value, quote="ADU text", kind="official_code", confidence="high", url=CODE) -> FieldValue:
    return FieldValue(value=value, evidence=[ev(quote, url, kind)], confidence=confidence)


def date(d: str, type_: str = "effective", precision: str = "day", url: str = ORD) -> DateEvidence:
    return DateEvidence(
        date=dt.date.fromisoformat(d),
        type=type_,
        precision=precision,
        evidence=[ev(f"effective {d}", url, "ordinance")],
    )


def none_era() -> Era:
    return Era(
        era_id="none",
        component="ADUs not listed as a permitted or conditional use in single-family districts",
        dates=[date("2012-03-01", "codified", url=CODE)],
        fields={"adus_per_lot": fv(0, "Permitted uses in R-1: single-family dwelling.")},
    )


def era_2020(sqft=800, detached=True) -> Era:
    return Era(
        era_id="2020",
        component="Ord. 2020-12: ADUs allowed by right in all single-family districts",
        dates=[date("2020-07-07", "adopted"), date("2020-07-22", "effective")],
        fields={
            "adus_per_lot": fv(1, "One accessory dwelling unit is permitted per lot."),
            "by_right": fv(True, "ADUs are a permitted use subject to Sec. 5.3."),
            "owner_occ": fv(False, "Owner occupancy is not required."),
            "adu_detached_allowed": fv(detached, "An ADU may be attached or detached."),
            "adu_max_sqft": fv(sqft, f"An ADU shall not exceed {sqft} square feet."),
            "parking_min_per_unit": fv(0, "No additional parking is required for an ADU."),
            "parking": fv("No additional parking required", "No additional parking is required for an ADU."),
            "coverage": fv("All single-family districts", "Permitted in R-1, R-2 and R-3."),
        },
    )


def coding(coder="claude-rules-adu-coder", eras=None, **kw) -> PlaceCoding:
    return PlaceCoding(
        state="NC",
        geoid="3799999",
        name="Testville",
        coder=coder,
        coded_at=DAY,
        outcome="coded",
        eras=[none_era(), era_2020()] if eras is None else eras,
        **kw,
    )
