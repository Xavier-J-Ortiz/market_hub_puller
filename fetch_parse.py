"""Fetch and parse JSON data from the Eve ESI API.

This module targets specific endpoints to retrieve data for the application.
"""

import json

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


def fetch_region_orders(region_id: int) -> list[httpx.Response]:
    """Fetch json string from the regional market API."""
    requests: list[httpx.Response] = []
    page = 1
    url = f"https://esi.evetech.net/markets/{region_id}/orders?page={page}"
    request: httpx.Response = httpx.get(url)
    requests.append(request)
    pages = int(request.headers["x-pages"])
    for p in range(2, pages + 1):
        url = f"https://esi.evetech.net/markets/{region_id}/orders?page={p}"
        request = httpx.get(url)
        requests.append(request)
    return requests


def parse_region_orders(
    region_orders: list[httpx.Response],
) -> RegionOrders:
    """Parse json string from fetch_region_orders()."""
    answer: RegionOrders = []
    try:
        for order in region_orders:
            answer = answer + region_orders_adapter.validate_json(order.text)
    except ValidationError as e:
        print("Invalid data received:", e.json())
    return answer
