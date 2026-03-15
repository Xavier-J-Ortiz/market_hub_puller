import csv
import gzip
from dataclasses import asdict, fields

from dataclass_csv import DataclassReader

import processing.csv as df
import processing.history as hs
from config import region_hubs
from processing.constants import GlobalOrders, ItemHistory


def get_source_history_data(
    region: str, global_orders: GlobalOrders, region_item_ids: list[int]
) -> None:
    if df.ARE_SAVED_MARKETS_STALE[region]:
        print(f"{region} history pulling has started")
        # Dictionary: {item_id: [{history_day_1}, {history_day_2}], ...}
        global_orders[region].all_order_history = hs.deserialize_history(
            region_hubs[region][0], region_item_ids
        )
        print(f"{region} history pulling has ended")
    else:
        history_file_path = (
            f"./market_data/source_data/{region}_all_order_history_source.csv.gz"
        )
        global_orders[region].all_order_history: list[ItemHistory] = load_history_cache(
            region, history_file_path
        )
        find_missing_orders(region, global_orders, region_item_ids, history_file_path)


def find_missing_orders(
    region: str,
    global_orders: GlobalOrders,
    region_item_ids: list[int],
    history_file_path: str,
) -> None:
    active_history: list[ItemHistory] = global_orders[region].all_order_history
    known_region_item_ids: list[int] = [ih.type_id for ih in active_history]

    missing_orders = list(set(region_item_ids) - set(known_region_item_ids))
    if len(missing_orders) != 0:
        print(f"Fetching missing orders from stale {region} cache.\n{missing_orders}")
        missing_order_histories: list[ItemHistory] = hs.deserialize_history(
            region_hubs[region][0],
            missing_orders,
        )
        active_history.extend(missing_order_histories)
        # fields = ["type_id", "history"]
        fieldnames = [field.name for field in fields(ItemHistory)]
        with gzip.open(history_file_path, "at") as history_csv:
            writer = csv.DictWriter(history_csv, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows([asdict(order) for order in missing_order_histories])
    print(f"{region} history fetch from file has ended")


# Historical Market Statistics: https://developers.eveonline.com/api-explorer#/operations/GetMarketsRegionIdHistory
item_history = list[dict[int, int | str | None]]


def load_history_cache(region: str, history_file_path: str) -> list[ItemHistory]:
    print(f"{region} history fetch from file has started")
    rih: list[ItemHistory] = []
    with gzip.open(history_file_path, "rt") as history_csv:
        rih += list(DataclassReader(history_csv, ItemHistory))
    return rih
