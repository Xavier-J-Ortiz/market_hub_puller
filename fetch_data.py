#!/usr/bin/env python3
import re
import csv
import gzip
import json
import os
from concurrent.futures import as_completed

from requests.exceptions import HTTPError, RequestException
from requests_futures.sessions import FuturesSession  # type: ignore

session = FuturesSession(max_workers=50)

SAVE_PROCESSED_DATA = True
SAVE_SOURCE_DATA = True
FINAL_FILTER = True
PRINT_INFORMATIONAL_ERR_LIMITS = False  # set true to see informational error information for troubleshooting only.
INCLUDE_HISTORY = False

# TODO: Filter processed data per station, which in the market data is the `location_id`
# <region>: [<region>, <station>]
region_hubs = {
        "Jita": ["10000002", "60003760"],  # Do Not Delete. must always be on top
        "Amarr": ["10000043", "60008494"],
        "Dodixie": ["10000032", "60011866"],
        "Rens": ["10000030", "60004588"],
        "Hek": ["10000042", "60005686"],
        # "Deklein": ["10000035", "1043621617719"],  # B0RT keepstar in 3T7-M8
        # "Vale": ["10000003", "1035466617946"]  # FRT staging in 4-HWWF
        }


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
    if len(ids) <= 1000:
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


def create_post_futures(urls_json_headers):
    all_futures = []
    for url_json_header in urls_json_headers:
        url = url_json_header[0]
        ids = url_json_header[1]
        header = url_json_header[2]
        future = session.post(url, json=ids, headers=header)
        all_futures.append(future)
    return all_futures


def pull_results(futures):
    results = []
    redo_urls = []
    for response in as_completed(futures):
        result = response.result()
        try:
            result.raise_for_status()
            error_limit_remaining = result.headers["x-esi-error-limit-remain"]
            if error_limit_remaining != "100" and PRINT_INFORMATIONAL_ERR_LIMITS:
                error_limit_time_to_reset = result.headers["x-esi-error-limit-reset"]
                print(
                        f"INFORMATIONAL: Though no error, for {result.url} the Error Limit Remaning: {error_limit_remaining} Limit-Rest "
                        f"{error_limit_time_to_reset} \n\n"
                        )
        except HTTPError:
            print(
                    f"Received status code {result.status_code} from {result.url} With headers:\n{str(result.headers)}, and result.text {result.text} of type {type(result.text)}\n"
                    )
            if "x-esi-error-limit-remain" in result.headers:
                error_limit_remaining = result.headers["x-esi-error-limit-remain"]
                error_limit_time_to_reset = result.headers["x-esi-error-limit-reset"]
                print(
                        "Error Limit Remaining: {error_limit_remaining} Limit-Rest {error_limit_time_to_reset} \n"
                        )
            print("\n")
            if ("Type not found!" not in result.text) and ("Type not tradable on market!" not in result.text):
                redo_url = result.url
                redo_urls.append(redo_url)
            else:
                print(f"Not added to redo_urls due to {result.text} output\n")
            continue
        except RequestException as e:
            print("other error is " + e + " from " + result.url)
            continue
        results.append(result)
    return results, redo_urls


# Pulls all order data
# func is the url generator
def pull_all_get_data(region, redo_urls, func):
    if len(redo_urls) == 0:
        active_items = []
        p1_result, redo_urls = pull_results(create_futures([func(region, 1)]))
        # While loop does not overwrite a good page one result.
        # It either has a p1_result, or has redo_urls.
        while len(redo_urls) != 0:
            p1_result, redo_urls = pull_results(create_futures(redo_urls))
        p1_active_items = json.loads(p1_result[0].text)
        total_pages = int(p1_result[0].headers["x-pages"])
        active_items += p1_active_items

    if len(redo_urls) == 0:
        urls = []
        for page in range(2, total_pages + 1):
            url = func(region, str(page))
            urls.append(url)
        pages_futures = create_futures(urls)
        pages_results, redo_urls = pull_results(pages_futures)
        for result in pages_results:
            active_item = json.loads(result.text)
            active_items += active_item
        while len(redo_urls) != 0:
            pages_futures = create_futures(redo_urls)
            pages_results, redo_urls = pull_results(pages_futures)
            for result in pages_results:
                active_item = json.loads(result.text)
                active_items += active_item
    return active_items, redo_urls


def pull_all_item_history_data(region, item_ids):
    redo_urls = []
    history_urls = []
    answer = {}
    for item_id in item_ids:
        answer[item_id] = []
        history_url = create_item_history_url(region, item_id)
        history_urls.append(history_url)
    results, redo_urls = pull_results(create_futures(history_urls))
    while len(redo_urls) != 0:
        addtl_results, redo_urls = pull_results(redo_urls)
        results.append(addtl_results)
    for result in results:
        result_item_id = result.url.split("=")[-1]
        if result_item_id in answer:
            answer[result_item_id] = json.loads(result.text)
    return answer, redo_urls


def pull_all_post_data(ids):
    all_names = []
    item_ids = create_name_urls_json_headers(ids)
    all_futures = create_post_futures(item_ids)
    results = pull_results(all_futures)[0]
    for result in results:
        names = json.loads(result.text)
        all_names += names
    return all_names


# Uses functions to build source data.
# This is where all source data should be created
def get_source_data(region, regional_orders):
    regional_orders[region] = {}
    regional_orders[region]["allOrdersData"] = pull_all_get_data(region_hubs[region][0], [], create_all_order_url)[0]
    # Active order item IDs
    region_item_ids = pull_all_get_data(region_hubs[region][0], [], create_active_items_url)[0]
    # List of dictionaries containing category, id, and name data
    regional_orders[region]["activeOrderNames"] = pull_all_post_data(region_item_ids)
    cleaned_active_orders = []
    cleaned_all_orders = []
    relevant_active_orders_ids = []
    for i in range(len(regional_orders[region]["activeOrderNames"])):
        # Remove blueprints and Expired items from active items
        if not (re.match(r".+Blueprint$", regional_orders[region]["activeOrderNames"][i]["name"]) or re.match(r"^Expired", regional_orders[region]["activeOrderNames"][i]["name"])):
            cleaned_active_orders.append(regional_orders[region]["activeOrderNames"][i])
            relevant_active_orders_ids.append(regional_orders[region]["activeOrderNames"][i]["id"])
    regional_orders[region]["activeOrderNames"] = cleaned_active_orders
    removed_orders_id = list(set(region_item_ids)-set(relevant_active_orders_ids))
    region_item_ids = relevant_active_orders_ids
    for i in range(len(regional_orders[region]["allOrdersData"])):
        if regional_orders[region]["allOrdersData"][i]["type_id"] not in removed_orders_id:
            cleaned_all_orders.append(regional_orders[region]["allOrdersData"][i])
    regional_orders[region]["allOrdersData"] = cleaned_all_orders
    # Dictionary: {item_id: [{history_day_a}, {historyi_day_b}], ...}
    # TODO Seems like there are too many requests. seeing `{"error":"Undefined 429 response. Original message: Too
    # many requests."}` To solve, try something suggested here to space out requests and avoid too many:
    # https://github.com/esi/esi-issues/issues/1227#issuecomment-687437225
    if INCLUDE_HISTORY:
        regional_orders[region]["activeOrderHistory"] = pull_all_item_history_data(region_hubs[region][0], region_item_ids)


def filter_source_data(region, regional_orders, regional_min_max):
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
            # Getting stopiteration errors in Next sometimes, don't understand why.
            # Might need to do this differently
            regional_min_max[region][type_id]["name"] = next(
                    name
                    for name in regional_orders[region]["activeOrderNames"]
                    if name["id"] == type_id
                    )
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


def process_filtered_data(region, regional_min_max, actionable_data, do_final_filter):
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
            # Why nested name? Might be worth fixing.
            # TODO evaluate if this could be flattened
            name = regional_min_max["Jita"][type_id]["name"]["name"]
            diff = hsv - jsv
            jsv_sell_margin = 1 - (jsv / hsv)
            jbv_sell_margin = 1 - (jbv / hsv)
            if do_final_filter:
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
                    # history = pull_all_item_history_data(region_hubs[region][0], [str(type_id)])[0][str(type_id)]
                    # print(f"TAKE A LOOK AT {region} HISTORY of {name}")
                    # print(history)
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


def data_to_csv_gz(actionable_data, fields, filename, path):
    if not os.path.exists(path):
        os.makedirs(path)
    if os.path.exists(filename):
        os.remove(filename)
    with gzip.open(f"{path}/{filename}", "tw") as g:
        writer = csv.DictWriter(g, fieldnames=fields)
        writer.writeheader()
        if isinstance(actionable_data, dict):
            for item in actionable_data.values():
                writer.writerow(item)
        elif isinstance(actionable_data, list):
            writer.writerows(actionable_data)


def create_actionable_data():
    regional_orders = {}
    regional_min_max = {}
    actionable_data = {}
    for region in region_hubs:
        # Gets all orders and their names
        get_source_data(region, regional_orders)
        # Creates a set of data that captures the min sell/max buy order of a region
        filter_source_data(region, regional_orders, regional_min_max)
        # Calls relevant price data for an item, and processes it for comparison
        process_filtered_data(region, regional_min_max, actionable_data, FINAL_FILTER)
    # print(actionable_data["Jita"]["Stratios"])
    # print(actionable_data["Amarr"]["Stratios"])
    # print(actionable_data["Dodixie"]["Stratios"])
    # print(actionable_data["Rens"]["Stratios"])
    # print(actionable_data["Hek"]["Stratios"])
    for region in region_hubs:
        if SAVE_PROCESSED_DATA:
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
                        "history"
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
                        "jbv_sell_margin"
                        ]
            filename = f"{region}_processed.csv.gz"
            data_to_csv_gz(actionable_data[region], fields, filename, path)
        if SAVE_SOURCE_DATA:
            path = "./market_data/source_data"
            for data_type, data in regional_orders[region].items():
                filename = f"{region}_{data_type}_source.csv.gz"
                fields = list(data[0].keys())
                data_to_csv_gz(data, fields, filename, path)

    return actionable_data


def main():
    actionable_data = create_actionable_data()
    return actionable_data


if __name__ == "__main__":
    main()
