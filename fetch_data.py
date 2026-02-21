#!/usr/bin/env python3
import csv
import datetime
import gzip
import json
import os
import re
import sys
from concurrent.futures import as_completed
from datetime import timedelta
from time import sleep

from requests.exceptions import HTTPError, RequestException
from requests_futures.sessions import FuturesSession

import config

session = FuturesSession(max_workers=160)


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


region_hubs = config.region_hubs


def is_saved_market_history_data_stale():
    are_markets_stale = {}
    for region_name in region_hubs:
        file_path = (
            f"./market_data/source_data/{region_name}_activeOrderHistory_source.csv.gz"
        )
        if os.path.exists(file_path) and os.path.getctime(file_path) > LAST_DOWNTIME:
            are_markets_stale[region_name] = False
        else:
            are_markets_stale[region_name] = True
    return are_markets_stale


ERR_MIN_THRESHOLD = 10
ID_SEGMENT_CHUNK = 1000

# Both PROCESS_DATA and SAVE_PROCESSED_DATA are necessary so that future implementations
#   can utilized the processed data, and independently decide to save it as a CSV
PROCESS_DATA = True  # Does comparison calculation filters
# To save processed data, you need to to save processed data in a CSV, both PROCESS_DATA
#   and SAVE_PROCESSED_DATA need to be True
SAVE_PROCESSED_DATA = True  # Save processed data
SAVE_SOURCE_DATA = True
PRINT_INFORMATIONAL_ERR_LIMITS = (
    False  # set true to see informational error information for troubleshooting only.
)
INCLUDE_HISTORY = True
LAST_DOWNTIME = find_last_downtime()
ARE_SAVED_MARKETS_STALE = is_saved_market_history_data_stale()


def create_all_order_url(region, page_number):
    url_base = "https://esi.evetech.net/latest/markets/"
    url_end = "/orders/?datasource=tranquility&order_type=all&page="
    url = url_base + str(region) + url_end + str(page_number)
    return url


def create_active_items_url(region, page_number):
    url_base = "https://esi.evetech.net/latest/markets/"
    url_end = "/types/?datasource=tranquility&page="
    url = url_base + str(region) + url_end + str(page_number)
    return url


def create_item_history_url(region, item_id):
    url_base = "https://esi.evetech.net/latest/markets/"
    url_end = "/history/?datasource=tranquility&page=1&type_id="
    url = url_base + str(region) + url_end + str(item_id)
    return url


def create_name_urls_json_headers(ids):
    urls_json_headers = []
    url = "https://esi.evetech.net/latest/universe/names/?datasource=tranquility"
    header = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }
    if len(ids) <= ID_SEGMENT_CHUNK:
        id_segment = ids
        urls_json_headers.append([url, id_segment, header])
        return urls_json_headers
    segmented_ids = []
    for i in range(0, len(ids), 1000):
        end = 1000 + i
        segmented_ids.append(ids[i:end])
    for id_segment in segmented_ids:
        urls_json_headers.append([url, id_segment, header])
    return urls_json_headers


def create_futures(urls):
    all_futures = []
    for url in urls:
        future = session.get(url)
        all_futures.append(future)
    return all_futures


def create_history_futures(urls):
    all_futures = []
    history_session = FuturesSession(max_workers=160)
    for url in urls:
        future = history_session.get(url)
        all_futures.append(future)
    return all_futures


def create_post_futures(urls_json_headers):
    all_futures = []
    for url_json_header in urls_json_headers:
        url = url_json_header[0]
        ids = url_json_header[1]
        header = url_json_header[2]
        future = session.post(url, json=ids, headers=header)
        all_futures.append(future)
    return all_futures


# Generic function that resolves futures results with some error handling that returns
#   the raw output from the
#   requested endpoint used in other functions like deserialize_order_items,
#   deserialize_history, and deserialize_order_names
def futures_results(futures):
    results = []
    redo_urls = []
    error_timer = 0
    for response in as_completed(futures):
        result = response.result()
        try:
            result.raise_for_status()
            error_limit_remaining = result.headers["x-esi-error-limit-remain"]
            if error_limit_remaining != "100" and PRINT_INFORMATIONAL_ERR_LIMITS:
                error_limit_time_to_reset = result.headers["x-esi-error-limit-reset"]
                print(
                    f"INFORMATIONAL: Though no error, for {result.url} the Error Limit "
                    f"Remaning: {error_limit_remaining} Limit-Rest "
                    f"{error_limit_time_to_reset} \n\n"
                )
        except HTTPError:
            print(
                f"Received status code {result.status_code} from {result.url} With "
                f"headers:\n{str(result.headers)}, and result.text {result.text} of "
                f"type {type(result.text)}\n"
            )
            if "x-esi-error-limit-remain" in result.headers:
                error_limit_remaining = result.headers["x-esi-error-limit-remain"]
                error_limit_time_to_reset = result.headers["x-esi-error-limit-reset"]
                print(
                    f"Error Limit Remaining: {error_limit_remaining} Limit-Rest "
                    f"{error_limit_time_to_reset} \n"
                )
                print("\n")
                if (
                    int(error_limit_remaining) < ERR_MIN_THRESHOLD
                    and int(error_limit_time_to_reset) >= 1
                ):
                    error_timer = error_limit_time_to_reset
            if ("Type not found!" not in result.text) and (
                "Type not tradable on market!" not in result.text
            ):
                redo_url = result.url
                redo_urls.append(redo_url)
            else:
                print(f"Not added to redo_urls due to {result.text} output\n")
            continue
        except RequestException as e:
            print(f"other error is {e} from {result.url}")
            continue
        results.append(result)
    return results, redo_urls, int(error_timer)


def pause_futures(error_timer, message):
    if error_timer != 0:
        print(message)
        sleep(error_timer + 1)


def deserialize_order_item_p1(region, func):
    deserialized_results = []
    # `p1_results` are the raw results of a first page of a request
    #   `redo_urls` is a list of URLs that were not able to be loaded, and require to be
    #   requesting again
    p1_result, redo_urls, error_timer = futures_results(
        create_futures([func(region, 1)])
    )
    pause_futures(
        error_timer,
        f"Sleep p1 order fetch due to error timer being {error_timer} seconds",
    )
    while len(redo_urls) != 0:
        p1_result, redo_urls, error_timer = futures_results(create_futures(redo_urls))
        pause_futures(
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
        pages_futures = create_futures(chunk_urls)
        pages_results, redo_urls, error_timer = futures_results(pages_futures)
        for result in pages_results:
            deserialized_result = json.loads(result.text)
            deserialized_results += deserialized_result
        pause_futures(
            error_timer,
            f"Sleep order fetch due to error timer being {error_timer} seconds",
        )
        while len(redo_urls) != 0:
            pages_futures = create_futures(redo_urls)
            pages_results, redo_urls, error_timer = futures_results(pages_futures)
            for result in pages_results:
                deserialized_result = json.loads(result.text)
                deserialized_results += deserialized_result
            pause_futures(
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


def parse_history_results(results, histories):
    for result in results:
        result_item_id = int(result.url.split("=")[-1])
        item_history = json.loads(result.text)
        histories[result_item_id] = item_history


def deserialize_history_chunk(history_urls, histories):
    for history_chunk in history_urls:
        results, redo_urls, error_timer = futures_results(
            create_history_futures(history_chunk)
        )
        parse_history_results(results, histories)
        pause_futures(
            error_timer,
            f"Sleep history fetch due to error timer being {error_timer} seconds",
        )
        while len(redo_urls) != 0:
            addtl_results, redo_urls, error_timer = futures_results(
                create_history_futures(redo_urls)
            )
            parse_history_results(addtl_results, histories)
            pause_futures(
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
        history_url = create_item_history_url(region, item_id)
        if idx % chunk_length == 0:
            history_urls.append([])
        history_urls[idx // chunk_length].append(history_url)
        histories[item_id] = []
    # Only need histories data at this point, so only what's in index zero
    histories = deserialize_history_chunk(history_urls, histories)[0]
    return histories


def deserialize_order_names(ids):
    all_names = []
    item_ids = create_name_urls_json_headers(ids)
    all_futures = create_post_futures(item_ids)
    results = futures_results(all_futures)[0]
    for result in results:
        names = json.loads(result.text)
        all_names += names
    return all_names


def find_missing_orders(region, regional_orders, region_item_ids, history_file_path):
    missing_orders = list(
        set(region_item_ids) - set(regional_orders[region]["activeOrderHistory"].keys())
    )
    if len(missing_orders) != 0:
        print(f"Fetching missing orders from stale {region} cache.")
        print(missing_orders)
        missing_order_histories = deserialize_history(
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


def get_source_history_data(region, regional_orders, region_item_ids):
    if ARE_SAVED_MARKETS_STALE[region]:
        print(f"{region} history pulling has started")
        # Dictionary: {item_id: [{history_day_1}, {history_day_2}], ...}
        regional_orders[region]["activeOrderHistory"] = deserialize_history(
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


def create_item_ids(region, regional_orders):
    region_item_ids = set()
    for order in regional_orders[region]["allOrdersData"]:
        region_item_ids.add(order["type_id"])
    return list(region_item_ids)


# Gets source data _per region_, removes any items that might cause issues, aggregates
#   them to `regional_orders`
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
        region_name, [], create_all_order_url
    )[0]
    # Fetches all Active order item IDs in a region, region_item_ids looks like:
    #
    # [31316, 31318, 27065, 31320, 31322, ...]
    region_item_ids = create_item_ids(region, regional_orders)

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
        get_source_history_data(region, regional_orders, region_item_ids)


def find_name(type_id, active_order_names, region):
    for active_order_name in active_order_names:
        if active_order_name["id"] == type_id:
            return active_order_name
    raise LookupError(f"Could not find the type_id: {type_id} in region: {region}")


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


def add_history_to_processed_data(
    regional_orders, region, actionable_data, name, type_id
):
    if (
        ARE_SAVED_MARKETS_STALE[region]
        or type_id in regional_orders[region]["activeOrderHistory"]
    ):
        actionable_data[region][name]["history"] = regional_orders[region][
            "activeOrderHistory"
        ][type_id]
    else:
        actionable_data[region][name]["history"] = []


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
        get_source_data(region, regional_orders)
        # Creates a set of data that captures the min sell/max buy order of a region
        min_max_source_data(region, regional_orders, regional_min_max)
        # Uses result of `min_max_source_data` and processes it for comparison on a per
        #   item basis
        if PROCESS_DATA:
            process_filtered_data(
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


def main():
    try:
        create_actionable_data()
        print("Actionable Data Created Successfully")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
