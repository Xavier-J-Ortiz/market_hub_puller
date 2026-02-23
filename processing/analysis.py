import re
from typing import Any, cast

import processing.csv as df
import processing.deserialize as ds
from config import region_hubs
from processing.constants import (
    INCLUDE_HISTORY,
    Active_order_ids,
    Active_order_names,
    All_orders_data,
    Regional_actionable_data,
    Regional_min_max,
    Regional_orders,
)


def min_max_source_data(
    region: str,
    regional_orders: Regional_orders,
    regional_min_max: Regional_min_max,
) -> None:
    regional_min_max[region] = {}
    pos_infinity = float("inf")
    neg_infinity = float("-inf")
    min_sell_order = {}
    max_buy_order = {}
    orders: All_orders_data = cast(
        All_orders_data, regional_orders[region]["allOrdersData"]
    )
    for order in orders:
        if isinstance(order["type_id"], int):
            type_id = order["type_id"]
        if type_id not in regional_min_max[region]:
            min_sell_order[type_id] = pos_infinity
            max_buy_order[type_id] = neg_infinity
            regional_min_max[region][type_id] = cast(dict[str, Any], {})
            regional_min_max[region][type_id]["name"] = ds.find_name(
                type_id,
                cast(Active_order_names, regional_orders[region]["active_order_names"]),
                region,
            )["name"]
        if (
            (not order["is_buy_order"])
            & (order["location_id"] == int(region_hubs[region][1]))
            & (order["price"] <= min_sell_order[type_id])
        ):
            if not isinstance(order["price"], float):
                raise TypeError(
                    f"Variable `order['price']` for min_sell_order expected type "
                    f"float, got {type(order['price'])}"
                )
            regional_min_max[region][type_id]["min"] = order
            min_sell_order[type_id] = order["price"]
        elif (
            (order["is_buy_order"])
            and (order["location_id"] == int(region_hubs[region][1]))
            and (order["price"] >= max_buy_order[type_id])
        ):
            if not isinstance(order["price"], float):
                raise TypeError(
                    f"Variable `order['price']` for min_sell_order expected type "
                    f"float, got {type(order['price'])}"
                )
            regional_min_max[region][type_id]["max"] = order
            max_buy_order[type_id] = order["price"]


def process_filtered_data(
    region: str,
    regional_min_max: Regional_min_max,
    actionable_data: Regional_actionable_data,
    regional_orders: Regional_orders,
) -> None:
    actionable_data[region] = {}
    # For an item of potential purchase in Jita
    for type_id in regional_min_max["Jita"]:
        # If the item is in remote hub, get all price data collected.
        if type_id in regional_min_max[region]:
            if "min" in regional_min_max[region][type_id]:
                # TODO: regional_min_max (and other structures) would benefit from
                #   dataclass or typed dicts.
                hsv: float = float(regional_min_max[region][type_id]["min"]["price"])
            else:
                hsv: float = float("inf")
            if "max" in regional_min_max[region][type_id]:
                hbv: float = float(regional_min_max[region][type_id]["max"]["price"])
            else:
                hbv: float = float("-inf")
            if "min" in regional_min_max["Jita"][type_id]:
                jsv: float = float(regional_min_max["Jita"][type_id]["min"]["price"])
            else:
                jsv: float = float("nan")
            if "max" in regional_min_max["Jita"][type_id]:
                jbv: float = float(regional_min_max["Jita"][type_id]["max"]["price"])
            else:
                jbv = float("nan")
            # With price data collected, process it to useful data.
            name = cast(str, regional_min_max["Jita"][type_id]["name"])
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
                if INCLUDE_HISTORY:
                    add_history_to_processed_data(
                        regional_orders, region, actionable_data, name, type_id
                    )


def add_history_to_processed_data(
    regional_orders: Regional_orders,
    region: str,
    actionable_data: Regional_actionable_data,
    name: str,
    type_id: int,
) -> None:
    if (
        df.ARE_SAVED_MARKETS_STALE[region]
        or type_id in regional_orders[region]["activeOrderHistory"]
    ):
        actionable_data[region][name]["history"] = regional_orders[region][
            "activeOrderHistory"
        ][type_id]
    else:
        actionable_data[region][name]["history"] = []


# Not strictly deserialization, but removes bad orders so that the object is usable.
#   Data scrubbing
def remove_bad_orders_names(
    regional_orders: Regional_orders,
    region: str,
) -> Active_order_names:
    active_orders_names_cleaned = []
    active_order_names: Active_order_names = cast(
        Active_order_names, regional_orders[region]["active_order_names"]
    )
    for active_order_name in active_order_names:
        # Data sanitizing for later processing - Remove blueprints and Expired items
        #   from active items
        if not isinstance(active_order_name["name"], str):
            raise TypeError(
                f'active_order_names["name"] is not of type `str`, got '
                f"{type(active_order_name['name'])}"
            )
        order_name = active_order_name["name"]
        is_blueprint = re.match(r".+Blueprint$", order_name)
        is_expired = re.match(r"^Expired", order_name)
        is_ore_processing = re.match(r"\w+(\s\w+)?\sProcessing$", order_name)
        if not (is_blueprint or is_expired or is_ore_processing):
            active_orders_names_cleaned.append(active_order_name)
    return active_orders_names_cleaned


# Not strictly deserialization, but removes bad orders so that the object is usable.
#   Data scrubbing.
def remove_bad_orders(
    regional_orders: Regional_orders, region: str, region_item_ids: list[int]
) -> tuple[All_orders_data, Active_order_names, Active_order_ids]:
    active_orders_names_cleaned = remove_bad_orders_names(regional_orders, region)
    all_orders_cleaned: All_orders_data = []
    cleaned_active_orders_ids: Active_order_ids = [
        cast(int, active_order_name_cleaned["id"])
        for active_order_name_cleaned in active_orders_names_cleaned
    ]
    removed_orders_id = list(set(region_item_ids) - set(cleaned_active_orders_ids))
    all_orders = cast(All_orders_data, regional_orders[region]["allOrdersData"])
    for i in range(len(all_orders)):
        if all_orders[i]["type_id"] not in removed_orders_id:
            all_orders_cleaned.append(all_orders[i])
    return all_orders_cleaned, active_orders_names_cleaned, cleaned_active_orders_ids
