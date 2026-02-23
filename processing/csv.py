import csv
import gzip
import os

import processing.analysis as an
import processing.deserialize as ds
from config import region_hubs
from processing.constants import (
    ARE_SAVED_MARKETS_STALE,
    INCLUDE_HISTORY,
    PROCESS_DATA,
    SAVE_PROCESSED_DATA,
    SAVE_SOURCE_DATA,
    Regional_actionable_data,
    Regional_min_max,
    Regional_orders,
)


def data_to_csv_gz(
    actionable_data: dict | list,
    fields: list[str],
    filename: str,
    path: str,
) -> None:
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


def create_actionable_data() -> Regional_actionable_data:
    regional_orders: Regional_orders = {}
    regional_min_max: Regional_min_max = {}
    actionable_data: Regional_actionable_data = {}
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
    #
    # TODO: Provide an example of expanded actionable_data[region][item_name]
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
                if data_type != "activeOrderHistory" and isinstance(data, list):
                    fields = list(data[0].keys())
                    data_to_csv_gz(data, fields, filename, path)
                elif (
                    data_type == "activeOrderHistory"
                    and ARE_SAVED_MARKETS_STALE[region]
                    and isinstance(data, dict)
                ):
                    fields = ["type_id", "history"]
                    formatted_data = []
                    for type_id, history in data.items():
                        item_history = {"type_id": type_id, "history": history}
                        formatted_data.append(item_history)
                    data_to_csv_gz(formatted_data, fields, filename, path)
    return actionable_data
