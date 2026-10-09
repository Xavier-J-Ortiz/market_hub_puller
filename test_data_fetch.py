"""Tests fetch_parse module."""

import httpx
import pytest
import respx

from fetch_parse import fetch_region_orders, parse_region_orders, region_orders_adapter


@pytest.fixture
def region_orders_example() -> str:
    """Return Simple example order list."""
    return """
        [
          {
            "duration": 0,
            "is_buy_order": true,
            "issued": "2019-08-24T14:15:22Z",
            "location_id": 0,
            "min_volume": 0,
            "order_id": 0,
            "price": 10.34,
            "range": "station",
            "system_id": 0,
            "type_id": 0,
            "volume_remain": 0,
            "volume_total": 0
          }
        ]
    """


@respx.mock
def test_fetch_region_order_data(region_orders_example: str):
    """Test fetch_region_orders()."""
    # system: str = "Jita"
    # system_id: int = 30000142
    # region: str = "The Forge"
    # IDs can be fetched from https://developers.eveonline.com/api-explorer#/operations/PostUniverseIds
    region_id: int = 10000002
    # Region orders can be fetched from https://developers.eveonline.com/api-explorer#/operations/PostUniverseIds
    url = f"https://esi.evetech.net/markets/{region_id}/orders"
    route = respx.get(url).mock(
        return_value=httpx.Response(
            200,
            text=region_orders_example,
        )
    )

    result = fetch_region_orders(region_id)
    assert result == region_orders_example
    assert route.called


def test_parse_region_order_data(region_orders_example: str):
    """Test parse_region_orders()."""
    result = parse_region_orders(region_orders_example)
    assert result == region_orders_adapter.validate_json(region_orders_example)
