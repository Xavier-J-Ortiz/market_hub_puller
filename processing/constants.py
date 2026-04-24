import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict

from config import (
    CHUNK_LENGTH,
    DATA_DIR,
    ID_SEGMENT_CHUNK,
    INCLUDE_HISTORY,
    LOWEST_MARGIN,
    MIN_VALUE_OF_ITEM_OF_INTEREST,
    PROCESS_DATA,
    SAVE_PROCESSED_DATA,
    SAVE_SOURCE_DATA,
    region_hubs,
)

CHUNK_LENGTH = CHUNK_LENGTH
ID_SEGMENT_CHUNK = ID_SEGMENT_CHUNK
INCLUDE_HISTORY = INCLUDE_HISTORY
MIN_VALUE_OF_ITEM_OF_INTEREST = MIN_VALUE_OF_ITEM_OF_INTEREST
LOWEST_MARGIN = LOWEST_MARGIN
PROCESS_DATA = PROCESS_DATA
SAVE_PROCESSED_DATA = SAVE_PROCESSED_DATA
SAVE_SOURCE_DATA = SAVE_SOURCE_DATA


def find_last_downtime() -> float:
    now_utc = datetime.now(UTC)
    downtime_today_utc = datetime(
        now_utc.year, now_utc.month, now_utc.day, 11, 5, 0, 0, UTC
    )
    if now_utc <= downtime_today_utc:
        last_downtime = downtime_today_utc - timedelta(days=1)
    else:
        last_downtime = downtime_today_utc
    return last_downtime.timestamp()


LAST_DOWNTIME = find_last_downtime()


def is_saved_market_history_data_stale() -> dict[str, bool]:
    are_markets_stale = {}
    for region_name in region_hubs:
        file_path = (
            f"{DATA_DIR}/source_data/{region_name}_all_order_history_source.csv.gz"
        )
        if os.path.exists(file_path) and os.path.getctime(file_path) > LAST_DOWNTIME:
            are_markets_stale[region_name] = False
        else:
            are_markets_stale[region_name] = True
    return are_markets_stale


ARE_SAVED_MARKETS_STALE: dict[str, bool] = is_saved_market_history_data_stale()

Actionable_data = dict[str, dict[str, Any]]
Regional_actionable_data = dict[str, Actionable_data]
Regional_min_max = dict[str, dict[int, dict[str, Any]]]


@dataclass()
class HistoryDataPoint:
    # A single history data point from a list of history data points of a given type_id
    #   fetched from https://developers.eveonline.com/api-explorer#/operations/GetMarketsRegionIdHistory
    average: float
    date: str
    highest: float
    lowest: float
    order_count: int
    volume: int


@dataclass
class ItemHistory:
    # An list of history data points from a given type_id fetched from https://developers.eveonline.com/api-explorer#/operations/GetMarketsRegionIdHistory
    type_id: int
    history: list[HistoryDataPoint]


@dataclass
class NameData:
    # One name data from the list of names fetched from https://developers.eveonline.com/api-explorer#/operations/PostUniverseNames
    category: str
    id: int
    name: str


class Order(TypedDict):
    # One order from the list of orders fetched from https://developers.eveonline.com/api-explorer#/operations/GetMarketsRegionIdOrders
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


@dataclass
class RegionOrdersData:
    # https://developers.eveonline.com/api-explorer#/operations/GetMarketsRegionIdOrders
    all_orders_data: list[Order]
    active_order_names: list[NameData]
    all_order_history: list[ItemHistory]


# GlobalOrders points to all order data relevant to a given region:str
GlobalOrders = dict[str, RegionOrdersData]
