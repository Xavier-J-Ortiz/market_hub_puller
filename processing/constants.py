import os
from datetime import UTC, datetime, timedelta
from typing import Any

from requests import Response

from config import region_hubs

INCLUDE_HISTORY = True


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
            f"./market_data/source_data/{region_name}_activeOrderHistory_source.csv.gz"
        )
        if os.path.exists(file_path) and os.path.getctime(file_path) > LAST_DOWNTIME:
            are_markets_stale[region_name] = False
        else:
            are_markets_stale[region_name] = True
    return are_markets_stale


ARE_SAVED_MARKETS_STALE: dict[str, bool] = is_saved_market_history_data_stale()
# Both PROCESS_DATA and SAVE_PROCESSED_DATA are necessary so that future implementations
#   can utilized the processed data, and independently decide to save it as a CSV
PROCESS_DATA = True  # Does comparison calculation filters
# To save processed data, you need to to save processed data in a CSV, both PROCESS_DATA
#   and SAVE_PROCESSED_DATA need to be True
SAVE_PROCESSED_DATA = True  # Save processed data
SAVE_SOURCE_DATA = True

# TODO: All these types below are globbed together. In next pass, maybe useful to start
#   to Dataclass it up.
Actionable_data = dict[str, dict[str, Any]]
Regional_actionable_data = dict[str, Actionable_data]
Active_order_ids = list[int]
Order_name = dict[str, str | int]
Active_order_names = list[Order_name]
Order_data = dict[str, int | bool | str | float]
All_orders_data = list[Order_data]
Futures_results = tuple[list[Response], list[str], int]
All_order_history = dict[int, str | float | int]
Regional_orders = dict[
    str, dict[str, All_orders_data | Active_order_names | All_order_history]
]
Regional_min_max = dict[str, dict[int, dict[str, Any]]]
