import csv
import gzip
import os
from dataclasses import fields as dataclass_fields
from dataclasses import is_dataclass
from types import MappingProxyType

import processing.analysis as an
import processing.deserialize as ds
from config import region_hubs
from processing.constants import (
    ARE_SAVED_MARKETS_STALE,
    INCLUDE_HISTORY,
    PROCESS_DATA,
    SAVE_PROCESSED_DATA,
    SAVE_SOURCE_DATA,
    GlobalOrders,
    ItemHistory,
    NameData,
    Regional_actionable_data,
    Regional_min_max,
)


def _to_dict(obj):
    if isinstance(obj, MappingProxyType):
        return dict(obj)
    elif hasattr(obj, "__dataclass_fields__"):
        return {f: _to_dict(getattr(obj, f)) for f in obj.__dataclass_fields__}
    elif hasattr(obj, "__dict__"):
        return {
            k: _to_dict(v) for k, v in obj.__dict__.items() if not k.startswith("_")
        }
    elif isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return type(obj)(_to_dict(i) for i in obj)
    return obj


def data_to_csv_gz(
    actionable_data: list,
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
                    writer.writerow(_to_dict(item))
        elif isinstance(actionable_data, list):
            if actionable_data and is_dataclass(actionable_data[0]):
                actionable_data = [_to_dict(item) for item in actionable_data]
            writer.writerows(actionable_data)


def create_actionable_data() -> Regional_actionable_data:
    global_orders: GlobalOrders = {}
    regional_min_max: Regional_min_max = {}
    actionable_data: Regional_actionable_data = {}
    for region in region_hubs:
        # Gets all source data, mainly active orders, names, and history
        ds.get_source_data(region, global_orders)
        # Creates a set of data that captures the min sell/max buy order of a region
        an.min_max_source_data(region, global_orders, regional_min_max)
        # Uses result of `min_max_source_data` and processes it for comparison on a per
        #   item basis
        if PROCESS_DATA:
            an.process_filtered_data(
                region, regional_min_max, actionable_data, global_orders
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
            filename = f"{region}_all_orders_data_source.csv.gz"
            data = global_orders[region].all_orders_data
            fields = list(data[0].keys())
            # fields = [f.name for f in dataclass_fields(Order)]
            data_to_csv_gz(data, fields, filename, path)

            filename = f"{region}_active_order_names_source.csv.gz"
            data = global_orders[region].active_order_names
            fields = [f.name for f in dataclass_fields(NameData)]
            data_to_csv_gz(data, fields, filename, path)

            if (
                ARE_SAVED_MARKETS_STALE[region]
                and global_orders[region].all_order_history
            ):
                filename = f"{region}_all_order_history_source.csv.gz"
                data = global_orders[region].all_order_history
                fields = [f.name for f in dataclass_fields(ItemHistory)]
                data_to_csv_gz(data, fields, filename, path)
    return actionable_data
