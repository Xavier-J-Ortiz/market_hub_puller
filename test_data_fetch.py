import datetime
import json

import httpx
import pytest
import respx


@respx.mock
def test_fetch_region_order_data():
    system: str = "Jita"
    # IDs can be fetched from https://developers.eveonline.com/api-explorer#/operations/PostUniverseIds
    system_id: int = 30000142
    region: str = "The Forge"
    region_id: int = 10000002
    # Region orders can be fetched from https://developers.eveonline.com/api-explorer#/operations/PostUniverseIds
    url = "https://esi.evetech.net/markets/{region_id}/orders"
    region_orders_example: str = """
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

    result = fetch_region_orders(region_id)
    assert result == region_orders_example


def test_parse_region_order_data():
    region_orders_example: str = """
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
    result = parse_region_orders(region_orders_example)
    assert result == json.loads(region_orders_example)
