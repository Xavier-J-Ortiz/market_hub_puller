import csv
import gzip
from typing import Any, cast

import processing.csv as df
import processing.history as hs
from config import region_hubs
from processing.constants import Regional_orders


def get_source_history_data(
    region: str, regional_orders: Regional_orders, region_item_ids: list[int]
) -> None:
    if df.ARE_SAVED_MARKETS_STALE[region]:
        print(f"{region} history pulling has started")
        # Dictionary: {item_id: [{history_day_1}, {history_day_2}], ...}
        regional_orders[region]["activeOrderHistory"] = hs.deserialize_history(
            region_hubs[region][0], region_item_ids
        )
        print(f"{region} history pulling has ended")
    else:
        history_file_path = (
            f"./market_data/source_data/{region}_activeOrderHistory_source.csv.gz"
        )
        regional_orders[region]["activeOrderHistory"]: dict[int, str] = (
            load_history_cache(region, history_file_path)
        )
        find_missing_orders(region, regional_orders, region_item_ids, history_file_path)


def find_missing_orders(
    region: str,
    regional_orders: Regional_orders,
    region_item_ids: list[int],
    history_file_path: str,
) -> None:
    active_history = cast(dict[int, Any], regional_orders[region]["activeOrderHistory"])
    known_region_item_ids: list[int] = list(active_history.keys())
    missing_orders = list(set(region_item_ids) - set(known_region_item_ids))
    if len(missing_orders) != 0:
        print(f"Fetching missing orders from stale {region} cache.")
        print(missing_orders)
        missing_order_histories = hs.deserialize_history(
            region_hubs[region][0], missing_orders
        )
        active_history.update(missing_order_histories)
        fields = ["type_id", "history"]
        with gzip.open(history_file_path, "at") as history_csv:
            writer = csv.DictWriter(history_csv, fieldnames=fields)
            for type_id, history in missing_order_histories.items():
                writer.writerow({"type_id": type_id, "history": history})
    print(f"{region} history fetch from file has ended")


# Historical Market Statistics: https://developers.eveonline.com/api-explorer#/operations/GetMarketsRegionIdHistory
#   Move this to location where the history array is loaded with json.loads and turned
#   into a python object.
item_history = list[dict[int, int | str | None]]


def load_history_cache(region: str, history_file_path: str) -> dict[int, str]:
    print(f"{region} history fetch from file has started")
    histories: dict[int, str] = {}
    with gzip.open(history_file_path, "rt") as history_csv:
        reader = csv.DictReader(history_csv)
        for row in reader:
            if type(row["history"]) is not str:
                raise TypeError(
                    f"Expected loaded CSV row to be of `str`, Got: "
                    f"{type(row['history'])}"
                )
            histories[int(row["type_id"])] = row["history"]
    return histories
