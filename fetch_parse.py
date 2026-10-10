"""Fetch and parse JSON data from the Eve ESI API.

This module targets specific endpoints to retrieve data for the application.
"""

import httpx
from pydantic import BaseModel, TypeAdapter, ValidationError


class OrderData(BaseModel):
    """represent an order within the array that is returned from a successful https://developers.eveonline.com/api-explorer#/operations/PostUniverseIds."""

    duration: int
    is_buy_order: bool
    issued: str
    location_id: int
    min_volume: int
    order_id: int
    price: float
    range: str
    system_id: int
    type_id: int
    volume_remain: int
    volume_total: int


type RegionOrders = list[OrderData]
region_orders_adapter = TypeAdapter(RegionOrders)


def fetch_region_orders(region_id: int) -> str:
    """Fetch json string from the regional market API."""
    url = f"https://esi.evetech.net/markets/{region_id}/orders"
    request = httpx.get(url)
    return request.text


def parse_region_orders(
    region_orders: str,
) -> RegionOrders:
    """Parse json string from fetch_region_orders()."""
    result: RegionOrders = []
    try:
        result = region_orders_adapter.validate_json(region_orders)
    except ValidationError as e:
        print("Invalid data received:", e.json())
    return result
