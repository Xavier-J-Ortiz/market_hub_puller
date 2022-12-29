#!/usr/bin/env python3
import json
from concurrent.futures import as_completed

from requests.exceptions import HTTPError, RequestException
from requests_futures.sessions import FuturesSession  # type: ignore

session = FuturesSession(max_workers=200)

region_hubs = {
    "Jita": ["10000002", "60003760"],
    "Amarr": ["10000043", "60008494"],
    "Dodixie": ["10000032", "60011866"],
    "Rens": ["10000030", "60004588"],
    "Hek": ["10000042", "60005686"],
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
            if error_limit_remaining != "100":
                error_limit_time_to_reset = result.headers["x-esi-error-limit-reset"]
                print(
                    f"INFORMATIONAL: Though no error, for {result.url} the Error Limit Remaning: {error_limit_remaining} Limit-Rest "
                    f"{error_limit_time_to_reset} \n\n"
                )
        except HTTPError:
            print(
                f"Received status code {result.status_code} from {result.url} With headers:\n{str(result.headers)}\n"
            )
            if "x-esi-error-limit-remain" in result.headers:
                error_limit_remaining = result.headers["x-esi-error-limit-remain"]
                error_limit_time_to_reset = result.headers["x-esi-error-limit-reset"]
                print(
                    "Error Limit Remaing: {error_limit_remaining} Limit-Rest {error_limit_time_to_reset} \n"
                )
            print("\n")
            redo_url = result.url
            redo_urls.append(redo_url)
            continue
        except RequestException as e:
            print("other error is " + e + " from " + result.url)
            continue
        results.append(result)
    return results, redo_urls


def pull_all_get_data(region, redo_urls, func):
    if len(redo_urls) == 0:
        active_items = []
        p1_result, redo_urls = pull_results(create_futures([func(region, 1)]))
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


def pull_all_post_data(ids):
    all_names = []
    item_ids = create_name_urls_json_headers(ids)
    all_futures = create_post_futures(item_ids)
    results = pull_results(all_futures)[0]
    for result in results:
        names = json.loads(result.text)
        all_names += names
    return all_names


def get_source_data(region, regional_orders):
    regional_orders[region] = {}
    regional_orders[region]["allOrdersData"] = pull_all_get_data(
        region_hubs[region][0], [], create_all_order_url
    )[0]
    regional_orders[region]["activeOrderNames"] = pull_all_post_data(
        pull_all_get_data(region_hubs[region][0], [], create_active_items_url)[0]
    )


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


def process_filtered_data(region, regional_min_max, actionable_data):
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

            name = regional_min_max["Jita"][type_id]["name"]["name"]
            # print(name)
            diff = hsv - jsv
            jsv_sell_margin = 1 - (jsv / hsv)
            jbv_sell_margin = 1 - (jbv / hsv)
            jsv_buy_margin = 1 - (jsv / hbv)
            jbv_buy_margin = 1 - (jbv / hbv)
            actionable_data[region][name] = {
                "name": name,
                "id": type_id,
                f"{region}sv": hsv,
                "jsv": jsv,
                "jbv": jbv,
                "diff": diff,
                "jsv_sell_margin": jsv_sell_margin,
                "jbv_sell_margin": jbv_sell_margin,
                "jsv_buy_margin": jsv_buy_margin,
                "jbv_buy_margin": jbv_buy_margin,
            }


def create_actionable_data():
    regional_orders = {}
    regional_min_max = {}
    actionable_data = {}
    for region in region_hubs:
        get_source_data(region, regional_orders)
        filter_source_data(region, regional_orders, regional_min_max)
        process_filtered_data(region, regional_min_max, actionable_data)
    # print(actionable_data["Jita"]["Stratios"])
    # print(actionable_data["Amarr"]["Stratios"])
    # print(actionable_data["Dodixie"]["Stratios"])
    # print(actionable_data["Rens"]["Stratios"])
    # print(actionable_data["Hek"]["Stratios"])

    return actionable_data


def main():
    actionable_data = create_actionable_data()
    return actionable_data


if __name__ == "__main__":
    main()
