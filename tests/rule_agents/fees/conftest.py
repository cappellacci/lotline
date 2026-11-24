"""Synthetic fixtures for the fees rule agent helpers (no downloaded data)."""

from datetime import date

import pytest

from lotline.rule_agents.fees.prototype import prototypes
from lotline.rule_agents.fees.records import FeeItem

# proforma.yaml central values written out, so the hand-worked numbers below don't move if the config does
PARAMS = {"single_family_sqft": 2150, "plex_unit_sqft": 1000, "adu_sqft": 800, "hard_cost_per_sqft_usd": 165}


@pytest.fixture
def protos():
    return prototypes(PARAMS)


def item(**kw) -> FeeItem:
    base = dict(
        item_id="x1",
        state="MN",
        place_geoid="2799999",
        place_name="Testville",
        levying_body="City of Testville",
        body_kind="city",
        fee_type="Building permit",
        pays_for="building_permit",
        building_type="SFD",
        basis_kind="per_unit",
        amount=100.0,
        effective_date=date(2026, 1, 1),
        url="https://example.org/fees.pdf",
        retrieved_at=date(2026, 11, 17),
        page_or_section="p. 3",
        quote="Building permit $100.00",
        quote_status="verbatim",
        coder="test",
    )
    base.update(kw)
    return FeeItem(**base)


@pytest.fixture
def make_item():
    return item
