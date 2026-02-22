import datetime
import json
from datetime import timedelta

import api.client as cl
import api.urls as u
import fetch_data as m
import processing.analysis as an
import processing.cache as c
import processing.csv as df
from config import INCLUDE_HISTORY, region_hubs


def find_name(type_id, active_order_names, region):
    for active_order_name in active_order_names:
        if active_order_name["id"] == type_id:
            return active_order_name
    raise LookupError(f"Could not find the type_id: {type_id} in region: {region}")


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
    clean_regional_order_data_and_names = an.remove_bad_orders(
        regional_orders, region, region_item_ids
    )
    regional_orders[region]["allOrdersData"] = clean_regional_order_data_and_names[0]
    regional_orders[region]["active_order_names"] = clean_regional_order_data_and_names[
        1
    ]
    region_item_ids = clean_regional_order_data_and_names[2]
    if INCLUDE_HISTORY:
        c.get_source_history_data(region, regional_orders, region_item_ids)


# some functions here have gz, csv, and other stuff. Adding here because it seems that
#   they support the deserialization to a certain degree. However, this may not be the
#   case as they might be better served living in `csv.py`.
