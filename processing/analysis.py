import re

import fetch_data as m
import processing.csv as df
import processing.deserialize as ds
from config import region_hubs


def min_max_source_data(region, regional_orders, regional_min_max):
    regional_min_max[region] = {}
    pos_infinity = float("inf")
    neg_infinity = float("-inf")
    min_sell_order = {}
    max_buy_order = {}
    for order in regional_orders[region]["allOrdersData"]:
        type_id = order["type_id"]
        if type_id not in regional_min_max[region]:
            min_sell_order[type_id] = pos_infinity
            max_buy_order[type_id] = neg_infinity
            regional_min_max[region][type_id] = {}
            regional_min_max[region][type_id]["name"] = ds.find_name(
                type_id, regional_orders[region]["active_order_names"], region
            )["name"]
        if (
            (not order["is_buy_order"])
            & (order["location_id"] == int(region_hubs[region][1]))
            & (order["price"] <= min_sell_order[type_id])
        ):
            regional_min_max[region][type_id]["min"] = order
            min_sell_order[type_id] = order["price"]
        elif (
            (order["is_buy_order"])
            & (order["location_id"] == int(region_hubs[region][1]))
            & (order["price"] >= max_buy_order[type_id])
        ):
            regional_min_max[region][type_id]["max"] = order
            max_buy_order[type_id] = order["price"]


def process_filtered_data(region, regional_min_max, actionable_data, regional_orders):
    actionable_data[region] = {}
    for type_id in regional_min_max["Jita"]:
        if type_id in regional_min_max[region]:
            if "min" in regional_min_max[region][type_id]:
                hsv = regional_min_max[region][type_id]["min"]["price"]
            else:
                hsv = float("inf")
            if "max" in regional_min_max[region][type_id]:
                hbv = regional_min_max[region][type_id]["max"]["price"]
            else:
                hbv = float("-inf")
            if "min" in regional_min_max["Jita"][type_id]:
                jsv = regional_min_max["Jita"][type_id]["min"]["price"]
            else:
                jsv = float("nan")
            if "max" in regional_min_max["Jita"][type_id]:
                jbv = regional_min_max["Jita"][type_id]["max"]["price"]
            else:
                jbv = float("nan")
            name = regional_min_max["Jita"][type_id]["name"]
            diff = hsv - jsv
            jsv_sell_margin = 1 - (jsv / hsv)
            jbv_sell_margin = 1 - (jbv / hsv)
            filter_values = {
                "jsv_margin": 0.17,
                "jsv_min": 70000000,
                "jbv_margin": 0.17,
                "jbv_min": 70000000,
            }
            final_filter = (
                jsv > filter_values["jsv_min"]
                and jsv_sell_margin > filter_values["jsv_margin"]
            ) or (
                jbv > filter_values["jbv_min"]
                and jbv_sell_margin > filter_values["jbv_margin"]
            )
            if final_filter:
                actionable_data[region][name] = {
                    "name": name,
                    "id": type_id,
                    f"{region}sv": hsv,
                    f"{region}bv": hbv,
                    "jsv": jsv,
                    "jbv": jbv,
                    "diff": diff,
                    "jsv_sell_margin": jsv_sell_margin,
                    "jbv_sell_margin": jbv_sell_margin,
                }
                if ds.INCLUDE_HISTORY:
                    add_history_to_processed_data(
                        regional_orders, region, actionable_data, name, type_id
                    )


def add_history_to_processed_data(
    regional_orders, region, actionable_data, name, type_id
):
    if (
        df.ARE_SAVED_MARKETS_STALE[region]
        or type_id in regional_orders[region]["activeOrderHistory"]
    ):
        actionable_data[region][name]["history"] = regional_orders[region][
            "activeOrderHistory"
        ][type_id]
    else:
        actionable_data[region][name]["history"] = []


# Not strictly deserialization, but removes bad orders so that the object is usable. Data scrubbing
def remove_bad_orders_names(regional_orders, region):
    active_orders_names_cleaned = []
    for active_order_name in regional_orders[region]["active_order_names"]:
        # Data sanitizing for later processing - Remove blueprints and Expired items
        #   from active items
        is_blueprint = re.match(r".+Blueprint$", active_order_name["name"])
        is_expired = re.match(r"^Expired", active_order_name["name"])
        is_ore_processing = re.match(
            r"\w+(\s\w+)?\sProcessing$", active_order_name["name"]
        )
        if not (is_blueprint or is_expired or is_ore_processing):
            active_orders_names_cleaned.append(active_order_name)
    return active_orders_names_cleaned


# Not strictly deserialization, but removes bad orders so that the object is usable.
#   Data scrubbing.
def remove_bad_orders(regional_orders, region, region_item_ids):
    active_orders_names_cleaned = remove_bad_orders_names(regional_orders, region)
    all_orders_cleaned = []
    cleaned_active_orders_ids = [
        active_order_name_cleaned["id"]
        for active_order_name_cleaned in active_orders_names_cleaned
    ]
    removed_orders_id = list(set(region_item_ids) - set(cleaned_active_orders_ids))
    for i in range(len(regional_orders[region]["allOrdersData"])):
        if (
            regional_orders[region]["allOrdersData"][i]["type_id"]
            not in removed_orders_id
        ):
            all_orders_cleaned.append(regional_orders[region]["allOrdersData"][i])
    return all_orders_cleaned, active_orders_names_cleaned, cleaned_active_orders_ids
