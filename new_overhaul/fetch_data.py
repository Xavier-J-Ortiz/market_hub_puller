#!/usr/bin/env python3
import json
from concurrent import futures
from concurrent.futures import as_completed

from requests.exceptions import HTTPError, RequestException
from requests_futures.sessions import FuturesSession

session = FuturesSession(max_workers=200)

# region_hubs is focused currently on high sec hubs. Each entry points to a
# list comprised of it's region, and it's main market hub in the region in that
# order. In the future, may put in some thought into renaming the dictionary
# key, since we may want to point to multiple different market hubs, within a
# given region.
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
        segmented_ids.append(ids[i : 1000 + i])
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
                    "INFORMATIONAL: Though no error, for {} the Error Limit Remaning: {} Limit-Rest {} \n\n".format(
                        result.url, error_limit_remaining, error_limit_time_to_reset
                    )
                )
        except HTTPError:
            print(
                "Received status code {} from {} With headers:\n{}\n".format(
                    result.status_code, result.url, str(result.headers)
                )
            )
            if "x-esi-error-limit-remain" in result.headers:
                error_limit_remaining = result.headers["x-esi-error-limit-remain"]
                error_limit_time_to_reset = result.headers["x-esi-error-limit-reset"]
                print(
                    "Error Limit Remaing: {} Limit-Rest {} \n".format(
                        error_limit_remaining, error_limit_time_to_reset
                    )
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
        p1_url = [func(region, 1)]
        p1_future = create_futures(p1_url)
        p1_result, redo_urls = pull_results(p1_future)
        while len(redo_urls) != 0:
            p1_future = create_futures(redo_urls)
            p1_result, redo_urls = pull_results(p1_future)
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


def main():
    regional_orders = {}
    for region in region_hubs:
        regional_orders[region] = {}
        regional_orders[region]["allOrdersData"] = pull_all_get_data(
            region_hubs[region][0], [], create_all_order_url
        )[0]
        regional_orders[region]["activeOrderNames"] = pull_all_post_data(
            pull_all_get_data(region_hubs[region][0], [], create_active_items_url)[0]
        )

    # Below would show the output of `regional_orders` for all order data of a
    # region and the names of all active orders. Basically a check, but
    # unactionable.
    for region in regional_orders:
        print(f"{region}: {len(regional_orders[region]['allOrdersData'])}")
        print(f"{region}: {len(regional_orders[region]['activeOrderNames'])}")


if __name__ == "__main__":
    main()
