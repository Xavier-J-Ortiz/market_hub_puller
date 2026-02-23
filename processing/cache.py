import csv
import gzip

import processing.csv as df
import processing.deserialize as ds
import processing.history as hs
from config import region_hubs


def get_source_history_data(region, regional_orders, region_item_ids):
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
        regional_orders[region]["activeOrderHistory"] = load_history_cache(
            region, history_file_path
        )
        find_missing_orders(region, regional_orders, region_item_ids, history_file_path)


def find_missing_orders(region, regional_orders, region_item_ids, history_file_path):
    missing_orders = list(
        set(region_item_ids) - set(regional_orders[region]["activeOrderHistory"].keys())
    )
    if len(missing_orders) != 0:
        print(f"Fetching missing orders from stale {region} cache.")
        print(missing_orders)
        missing_order_histories = hs.deserialize_history(
            region_hubs[region][0], missing_orders
        )
        regional_orders[region]["activeOrderHistory"].update(missing_order_histories)
        fields = ["type_id", "history"]
        with gzip.open(history_file_path, "at") as history_csv:
            writer = csv.DictWriter(history_csv, fieldnames=fields)
            for type_id, history in missing_order_histories.items():
                writer.writerow({"type_id": type_id, "history": history})
    print(f"{region} history fetch from file has ended")


def load_history_cache(region, history_file_path):
    print(f"{region} history fetch from file has started")
    histories = {}
    with gzip.open(history_file_path, "rt") as history_csv:
        reader = csv.DictReader(history_csv)
        for row in reader:
            histories[int(row["type_id"])] = row["history"]
    return histories
