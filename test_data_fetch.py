"""Tests fetch_parse module."""

import gzip

import httpx
import pytest
import respx

from fetch_parse import fetch_region_orders, parse_region_orders, region_orders_adapter

MOCK_PAGE_LENGTH = 2
REGION_ID: int = 10000002


@pytest.fixture
def region_orders_1() -> str:
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


@pytest.fixture
def region_orders_2() -> str:
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
            "price": 10.35,
            "range": "station",
            "system_id": 1,
            "type_id": 1,
            "volume_remain": 1,
            "volume_total": 0
          }
        ]
    """


@pytest.fixture
def mock_header() -> dict[str, str]:
    """Mock Header for mock responses."""
    return {
        "date": "Sat, 10 Oct 2026 14:43:15 GMT",
        "content-type": "application/json; charset=UTF-8",
        "transfer-encoding": "chunked",
        "connection": "keep-alive",
        "access-control-allow-origin": "*",
        "access-control-expose-headers": "\
                Etag, \
                Retry-After, \
                X-Compatibility-Date, \
                X-Esi-Error-Limit-Remain, \
                X-Esi-Error-Limit-Reset, \
                X-Pages, \
                X-Ratelimit-Group, \
                X-Ratelimit-Limit, \
                X-Ratelimit-Remaining, \
                X-Ratelimit-Used\
                ",
        "cache-control": "public",
        "content-encoding": "gzip",
        "content-language": "en",
        "etag": '"3e7737d589195b9c3b34265d43ea9a345b107228cead2722fde330e1"',
        "expires": "Sat, 10 Oct 2026 14:45:36 GMT",
        "last-modified": "Sat, 10 Oct 2026 14:40:36 GMT",
        "strict-transport-security": "max-age=31536000",
        "vary": "X-Tenant, Accept-Language, X-Compatibility-Date, Accept-Encoding",
        "x-compatibility-date": "2020-01-01",
        "x-esi-cache-status": "HIT",
        "x-esi-request-id": "f3ea6f8d-169b-4841-b81b-d4b0fe83ede5",
        "x-pages": "2",
        "x-ratelimit-group": "market-order",
        "x-ratelimit-limit": "12000/15m",
        "x-ratelimit-remaining": "11995",
        "x-ratelimit-used": "2",
    }


@pytest.fixture
def region_order_routes(
    region_orders_1, region_orders_2, mock_header
) -> tuple[respx.Route, respx.Route]:
    """Return mocked routes for regional market orders."""
    url_1 = f"https://esi.evetech.net/markets/{REGION_ID}/orders?page=1"
    url_2 = f"https://esi.evetech.net/markets/{REGION_ID}/orders?page=2"

    route_1 = respx.get(url_1).mock(
        return_value=httpx.Response(
            200,
            headers=mock_header,
            content=gzip.compress(region_orders_1.encode("UTF-8")),
        )
    )
    route_2 = respx.get(url_2).mock(
        return_value=httpx.Response(
            200,
            headers=mock_header,
            content=gzip.compress(region_orders_2.encode("UTF-8")),
        )
    )
    return route_1, route_2


@respx.mock
def test_fetch_region_order_data(
    region_orders_1: str, region_orders_2: str, region_order_routes: tuple[respx.Route, respx.Route]
):
    """Test fetch_region_orders()."""
    # system: str = "Jita"
    # system_id: int = 30000142
    # region: str = "The Forge"
    # IDs can be fetched from https://developers.eveonline.com/api-explorer#/operations/PostUniverseIds
    # Region orders can be fetched from https://developers.eveonline.com/api-explorer#/operations/PostUniverseIds
    route_1, route_2 = region_order_routes

    results = fetch_region_orders(REGION_ID)
    assert len(results) == MOCK_PAGE_LENGTH

    # page 1 results
    assert results[0].text == region_orders_1
    assert results[0].headers["x-pages"] == "2"
    assert route_1.called

    # page 2 results
    assert results[1].text == region_orders_2
    assert results[1].headers["x-pages"] == "2"
    assert route_2.called


@respx.mock
def test_parse_region_order_data(
    region_orders_1: str,
    region_orders_2: str,
    region_order_routes: tuple[respx.Route, respx.Route],
):
    """Test parse_region_orders()."""
    route_1, route_2 = region_order_routes
    result = parse_region_orders(fetch_region_orders(REGION_ID))
    region_orders = region_orders_adapter.validate_json(
        region_orders_1
    ) + region_orders_adapter.validate_json(region_orders_2)
    assert route_1.called
    assert route_2.called
    assert result == region_orders
