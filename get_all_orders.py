import json
import os
import pickle
from concurrent.futures import as_completed

from requests.exceptions import HTTPError, RequestException
from requests_futures.sessions import FuturesSession

session = FuturesSession(max_workers=200)


def create_url(region_id, page, url_base, url_end):
    return url_base + region_id + url_end + page


def create_page1_urls(region_hubs, urls):
    url_base = "https://esi.evetech.net/latest/markets/"
    url_end = "/orders/?datasource=tranquility&order_type=all&page="
    for region in region_hubs:
        page1_url = create_url(region[0], "1", url_base, url_end)
        url = [page1_url, region[0]]
        urls.append(url)
    return urls


def create_all_market_order_urls(region_hubs, orders_in_regions):
    url_base = "https://esi.evetech.net/latest/markets/"
    url_end = "/orders/?datasource=tranquility&order_type=all&page="
    urls = []
    if len(orders_in_regions.keys()) == 0:
        urls = create_page1_urls(region_hubs, urls)
        return urls
    for region in region_hubs:
        pages = int(orders_in_regions[region[0]]["pages"])
        for page in range(2, pages + 1):
            url = [create_url(region[0], str(page), url_base, url_end), region[0]]
            urls.append(url)
    return urls


def create_market_order_futures(urls):
    futures = []
    for url in urls:
        region = url[1]
        future = session.get(url[0])
        future.region_id = region
        futures.append(future)
    return futures


def get_regions_markets_results(futures, orders_in_regions, redo_urls, error_write):
    for response in as_completed(futures):
        result = response.result()
        try:
            result.raise_for_status()
            error_limit_remaining = result.headers["x-esi-error-limit-remain"]
            if error_limit_remaining != "100":
                error_limit_time_to_reset = result.headers["x-esi-error-limit-reset"]
                error_write.write(
                    "INFORMATIONAL: Though no error, for {} the Error Limit Remaning: {} Limit-Rest {} \n\n".format(
                        result.url, error_limit_remaining, error_limit_time_to_reset
                    )
                )
        except HTTPError:
            error_write.write(
                "Received status code {} from {} With headers:\n{}\n".format(
                    result.status_code, result.url, str(result.headers)
                )
            )
            if "x-esi-error-limit-remain" in result.headers:
                error_limit_remaining = result.headers["x-esi-error-limit-remain"]
                error_limit_time_to_reset = result.headers["x-esi-error-limit-reset"]
                error_write.write(
                    "Error Limit Remaing: {} Limit-Rest {} \n".format(
                        error_limit_remaining, error_limit_time_to_reset
                    )
                )
            error_write.write("\n")
            redo_url = [result.url, response.region_id]
            redo_urls.append(redo_url)
            continue
        except RequestException as e:
            error_write.write("other error is " + e + " from " + result.url)
            continue
        orders = json.loads(result.text)
        if response.region_id in orders_in_regions:
            orders_in_regions[response.region_id]["orders"] += orders
        else:
            total_pages = result.headers["x-pages"]
            orders_in_regions[response.region_id] = {
                "orders": orders,
                "pages": total_pages,
                "active_items_list": [],
            }
    return orders_in_regions, redo_urls


def get_region_market_orders(urls, orders_in_regions, active_items, error_write):
    redo_urls = []
    futures = create_market_order_futures(urls)
    orders_in_regions, redo_urls = get_regions_markets_results(
        futures, orders_in_regions, redo_urls, error_write
    )
    if len(redo_urls) != 0:
        orders_in_regions = get_region_market_orders(
            redo_urls, orders_in_regions, active_items, error_write
        )
    orders_in_regions = add_active_items(orders_in_regions, active_items)
    return orders_in_regions


def add_active_items(orders_in_regions, active_items):
    regions = orders_in_regions.keys()
    for region in regions:
        orders_in_regions[region]["active_items_list"] += active_items[region]["items"]
    return orders_in_regions
