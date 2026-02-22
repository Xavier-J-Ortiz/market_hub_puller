import csv
import gzip
import os

import fetch_data as m
import processing.analysis as an
import processing.deserialize as ds
from config import LAST_DOWNTIME, region_hubs

# Both PROCESS_DATA and SAVE_PROCESSED_DATA are necessary so that future implementations
#   can utilized the processed data, and independently decide to save it as a CSV
PROCESS_DATA = True  # Does comparison calculation filters
# To save processed data, you need to to save processed data in a CSV, both PROCESS_DATA
#   and SAVE_PROCESSED_DATA need to be True
SAVE_PROCESSED_DATA = True  # Save processed data
SAVE_SOURCE_DATA = True
INCLUDE_HISTORY = ds.INCLUDE_HISTORY
ARE_SAVED_MARKETS_STALE = {}


def is_saved_market_history_data_stale():
    are_markets_stale = {}
    global ARE_SAVED_MARKETS_STALE
    for region_name in region_hubs:
        file_path = (
            f"./market_data/source_data/{region_name}_activeOrderHistory_source.csv.gz"
        )
        if os.path.exists(file_path) and os.path.getctime(file_path) > LAST_DOWNTIME:
            are_markets_stale[region_name] = False
        else:
            are_markets_stale[region_name] = True
    ARE_SAVED_MARKETS_STALE = are_markets_stale


is_saved_market_history_data_stale()


def data_to_csv_gz(actionable_data, fields, filename, path):
    if not os.path.exists(path):
        os.makedirs(path)
    if os.path.exists(filename):
        os.remove(filename)
    with gzip.open(f"{path}/{filename}", "wt") as g:
        writer = csv.DictWriter(g, fieldnames=fields)
        writer.writeheader()
        if isinstance(actionable_data, dict):
            if isinstance(list(actionable_data.keys())[0], int):
                for type_id, history in actionable_data:
                    writer.writerow({"type_id": type_id, "history": history})
            else:
                for item in actionable_data.values():
                    writer.writerow(item)
        elif isinstance(actionable_data, list):
            writer.writerows(actionable_data)


def create_actionable_data():
    regional_orders = {}
    regional_min_max = {}
    actionable_data = {}
    for region in region_hubs:
        # Gets all source data, mainly active orders, names, and history
        ds.get_source_data(region, regional_orders)
        # Creates a set of data that captures the min sell/max buy order of a region
        an.min_max_source_data(region, regional_orders, regional_min_max)
        # Uses result of `min_max_source_data` and processes it for comparison on a per
        #   item basis
        if PROCESS_DATA:
            an.process_filtered_data(
                region, regional_min_max, actionable_data, regional_orders
            )
    # Uncomment to see examples of actionable data:
    #
    # print(actionable_data["Jita"]["Stratios"])
    # print(actionable_data["Dodixie"]["Stratios"])
    for region in region_hubs:
        if PROCESS_DATA and SAVE_PROCESSED_DATA:
            path = "./market_data/processed_data"
            if INCLUDE_HISTORY:
                fields = [
                    "name",
                    "id",
                    f"{region}sv",
                    f"{region}bv",
                    "jsv",
                    "jbv",
                    "diff",
                    "jsv_sell_margin",
                    "jbv_sell_margin",
                    "history",
                ]
            else:
                fields = [
                    "name",
                    "id",
                    f"{region}sv",
                    f"{region}bv",
                    "jsv",
                    "jbv",
                    "diff",
                    "jsv_sell_margin",
                    "jbv_sell_margin",
                ]
            filename = f"{region}_processed.csv.gz"
            data_to_csv_gz(actionable_data[region], fields, filename, path)
        if SAVE_SOURCE_DATA:
            path = "./market_data/source_data"
            for data_type, data in regional_orders[region].items():
                filename = f"{region}_{data_type}_source.csv.gz"
                if data_type != "activeOrderHistory":
                    fields = list(data[0].keys())
                    data_to_csv_gz(data, fields, filename, path)
                elif (
                    data_type == "activeOrderHistory"
                    and ARE_SAVED_MARKETS_STALE[region]
                ):
                    fields = ["type_id", "history"]
                    formatted_data = []
                    for type_id, history in data.items():
                        item_history = {"type_id": type_id, "history": history}
                        formatted_data.append(item_history)
                    data_to_csv_gz(formatted_data, fields, filename, path)
    return actionable_data
