import csv
import gzip
import os

import config
import fetch_data as m
import processing.deserialize as ds

# Both PROCESS_DATA and SAVE_PROCESSED_DATA are necessary so that future implementations
#   can utilized the processed data, and independently decide to save it as a CSV
PROCESS_DATA = True  # Does comparison calculation filters
# To save processed data, you need to to save processed data in a CSV, both PROCESS_DATA
#   and SAVE_PROCESSED_DATA need to be True
SAVE_PROCESSED_DATA = True  # Save processed data
SAVE_SOURCE_DATA = True
INCLUDE_HISTORY = ds.INCLUDE_HISTORY
LAST_DOWNTIME = ds.LAST_DOWNTIME
ARE_SAVED_MARKETS_STALE = {}
region_hubs = m.region_hubs


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
        ds.min_max_source_data(region, regional_orders, regional_min_max)
        # Uses result of `min_max_source_data` and processes it for comparison on a per
        #   item basis
        if PROCESS_DATA:
            ds.process_filtered_data(
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


def get_source_history_data(region, regional_orders, region_item_ids):
    if ARE_SAVED_MARKETS_STALE[region]:
        print(f"{region} history pulling has started")
        # Dictionary: {item_id: [{history_day_1}, {history_day_2}], ...}
        regional_orders[region]["activeOrderHistory"] = ds.deserialize_history(
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
        missing_order_histories = ds.deserialize_history(
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
