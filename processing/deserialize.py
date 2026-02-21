import datetime
import gzip
import json
import os
import re
from datetime import timedelta

import api.client as cl
import api.urls as u
import config
import fetch_data as m
import processing.csv as df

region_hubs = m.region_hubs
INCLUDE_HISTORY = True


def find_last_downtime():
    now_utc = datetime.datetime.now(datetime.UTC)
    downtime_today_utc = datetime.datetime(
        now_utc.year, now_utc.month, now_utc.day, 11, 5, 0, 0, datetime.UTC
    )
    if now_utc <= downtime_today_utc:
        last_downtime = downtime_today_utc - timedelta(days=1)
    else:
        last_downtime = downtime_today_utc
    return last_downtime.timestamp()


LAST_DOWNTIME = find_last_downtime()


def deserialize_order_item_p1(region, func):
    deserialized_results = []
    # `p1_results` are the raw results of a first page of a request
    #   `redo_urls` is a list of URLs that were not able to be loaded, and require to be
    #   requesting again
    p1_result, redo_urls, error_timer = cl.futures_results(
        cl.create_futures([func(region, 1)])
    )
    cl.pause_futures(
        error_timer,
        f"Sleep p1 order fetch due to error timer being {error_timer} seconds",
    )
    while len(redo_urls) != 0:
        p1_result, redo_urls, error_timer = cl.futures_results(
            cl.create_futures(redo_urls)
        )
        cl.pause_futures(
            error_timer,
            f"Sleep p1 order fetch due to error timer being {error_timer} seconds",
        )
    p1_deserialized_result = json.loads(p1_result[0].text)
    total_pages = int(p1_result[0].headers["x-pages"])
    deserialized_results += p1_deserialized_result
    return deserialized_results, total_pages


def deserialize_order_items_p2_onwards(region, total_pages, deserialized_results, func):
    urls = []
    chunk_length = 30000
    for page in range(2, total_pages + 1):
        url = func(region, str(page))
        if (page - 2) % chunk_length == 0:
            urls.append([])
        # urls is a list of (at most 100 url) lists.
        urls[(page - 2) // chunk_length].append(url)
    for chunk_urls in urls:
        pages_futures = cl.create_futures(chunk_urls)
        pages_results, redo_urls, error_timer = cl.futures_results(pages_futures)
        for result in pages_results:
            deserialized_result = json.loads(result.text)
            deserialized_results += deserialized_result
        cl.pause_futures(
            error_timer,
            f"Sleep order fetch due to error timer being {error_timer} seconds",
        )
        while len(redo_urls) != 0:
            pages_futures = cl.create_futures(redo_urls)
            pages_results, redo_urls, error_timer = cl.futures_results(pages_futures)
            for result in pages_results:
                deserialized_result = json.loads(result.text)
                deserialized_results += deserialized_result
            cl.pause_futures(
                error_timer,
                f"Sleep redo order fetch due to error timer being {error_timer} \
                        seconds",
            )
    return deserialized_results, redo_urls


# Deserializes resulting JSON from futures, used in `get_source_data`
def deserialize_order_items(region, redo_urls, func):
    if len(redo_urls) == 0:
        deserialized_results, total_pages = deserialize_order_item_p1(region, func)
    if len(redo_urls) == 0:
        deserialized_results, redo_urls = deserialize_order_items_p2_onwards(
            region, total_pages, deserialized_results, func
        )
    return deserialized_results, redo_urls


def deserialize_history_chunk(history_urls, histories):
    for history_chunk in history_urls:
        results, redo_urls, error_timer = cl.futures_results(
            cl.create_history_futures(history_chunk)
        )
        parse_history_results(results, histories)
        cl.pause_futures(
            error_timer,
            f"Sleep history fetch due to error timer being {error_timer} seconds",
        )
        while len(redo_urls) != 0:
            addtl_results, redo_urls, error_timer = cl.futures_results(
                cl.create_history_futures(redo_urls)
            )
            parse_history_results(addtl_results, histories)
            cl.pause_futures(
                error_timer,
                f"Sleep history fetch due to error timer being {error_timer} seconds",
            )
    return histories, redo_urls


# Deserializes resulting JSON specifically from history futures, used in
#  `get_source_data`
def deserialize_history(region, item_ids):
    history_urls = []
    histories = {}
    chunk_length = 30000
    for idx, item_id in enumerate(item_ids):
        history_url = u.create_item_history_url(region, item_id)
        if idx % chunk_length == 0:
            history_urls.append([])
        history_urls[idx // chunk_length].append(history_url)
        histories[item_id] = []
    # Only need histories data at this point, so only what's in index zero
    histories = deserialize_history_chunk(history_urls, histories)[0]
    return histories


def deserialize_order_names(ids):
    all_names = []
    item_ids = u.create_name_urls_json_headers(ids)
    all_futures = cl.create_post_futures(item_ids)
    results = cl.futures_results(all_futures)[0]
    for result in results:
        names = json.loads(result.text)
        all_names += names
    return all_names


def parse_history_results(results, histories):
    for result in results:
        result_item_id = int(result.url.split("=")[-1])
        item_history = json.loads(result.text)
        histories[result_item_id] = item_history


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


# Gets source data _per region_, removes any items that might cause issues, aggregates
#   them to `regional_orders` within the main object.
def get_source_data(region, regional_orders):
    regional_orders[region] = {}
    # Fetches all orders in a region. regional_orders[region]["allOrdersData"] looks
    #  like:
    #
    # [{'duration': 90, 'is_buy_order': False, 'issued': '2025-01-28T20:37:14Z',
    #   'location_id': 60003760, 'min_volume': 1, 'order_id': 6974687044,
    #   'price': 420500000.0, 'range': 'region', 'system_id': 30000142,
    #   'type_id': 35705, 'volume_remain': 1, 'volume_total': 1}, ... ]
    region_name = region_hubs[region][0]
    regional_orders[region]["allOrdersData"] = deserialize_order_items(
        region_name, [], u.create_all_order_url
    )[0]
    # Fetches all Active order item IDs in a region, region_item_ids looks like:
    #
    # [31316, 31318, 27065, 31320, 31322, ...]
    region_item_ids = u.create_item_ids(region, regional_orders)

    # List of dictionaries containing category, id, and name data, used to extract name
    #   data for later processing
    #   regional_orders[region]["active_order_names"] looks like:
    #
    # [{'category': 'inventory_type', 'id': 54360,
    #   'name': "Women's Azure Abundance Jacket"}, {'category': 'inventory_type',
    #   'id': 21593, 'name': 'Mechanic Parts'}, ...]
    regional_orders[region]["active_order_names"] = deserialize_order_names(
        region_item_ids
    )
    # clean_regional_order_data_and_names is the same structure as
    #   regional_orders[region]["active_order_names"],
    # except it doesn't have items that will cause issues with history.
    clean_regional_order_data_and_names = remove_bad_orders(
        regional_orders, region, region_item_ids
    )
    regional_orders[region]["allOrdersData"] = clean_regional_order_data_and_names[0]
    regional_orders[region]["active_order_names"] = clean_regional_order_data_and_names[
        1
    ]
    region_item_ids = clean_regional_order_data_and_names[2]
    if INCLUDE_HISTORY:
        df.get_source_history_data(region, regional_orders, region_item_ids)


# some functions here have gz, csv, and other stuff. Adding here because it seems that
#   they support the deserialization to a certain degree. However, this may not be the
#   case as they might be better served living in `csv.py`.


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
                if INCLUDE_HISTORY:
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
            regional_min_max[region][type_id]["name"] = find_name(
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


def find_name(type_id, active_order_names, region):
    for active_order_name in active_order_names:
        if active_order_name["id"] == type_id:
            return active_order_name
    raise LookupError(f"Could not find the type_id: {type_id} in region: {region}")
