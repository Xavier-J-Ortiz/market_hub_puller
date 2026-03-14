import json
from collections.abc import Callable

import api.client as cl
import api.urls as u
import processing.analysis as an
import processing.cache as c
from config import region_hubs
from processing.constants import (
    INCLUDE_HISTORY,
    GlobalOrders,
    NameData,
    Order,
    RegionOrdersData,
)


def find_name(
    type_id: int, active_order_names: list[NameData], region: str
) -> NameData:
    for name_data in active_order_names:
        if name_data.id == type_id:
            return name_data
    raise LookupError(f"Could not find the type_id: {type_id} in region: {region}")


def deserialize_order_item_p1(
    region: str, func: Callable[[str, int], str]
) -> tuple[list[Order], int]:
    deserialized_results = []
    # `p1_results` are the raw results of a first page of a request
    #   `redo_urls` is a list of URLs that were not able to be loaded, and require to be
    #   requesting again
    fr = cl.futures_results(cl.create_futures([func(region, 1)]))
    cl.pause_futures(
        fr.error_timer,
        f"Sleep p1 order fetch due to error timer being {fr.error_timer} seconds",
    )
    while len(fr.redo_urls) != 0:
        fr = cl.futures_results(cl.create_futures(fr.redo_urls))
        cl.pause_futures(
            fr.error_timer,
            f"Sleep p1 order fetch due to error timer being {fr.error_timer} seconds",
        )
    p1_deserialized_result: Order = json.loads(fr.results[0].text)
    total_pages = int(fr.results[0].headers["x-pages"])
    deserialized_results += p1_deserialized_result
    # print(deserialized_results)
    return deserialized_results, total_pages


def deserialize_order_items_p2_onwards(
    region: str,
    total_pages: int,
    deserialized_results: list[Order],
    func: Callable[[str, int], str],
) -> tuple[list[Order], list[str]]:
    urls = []
    chunk_length = 30000
    for page in range(2, total_pages + 1):
        url = func(region, page)
        if (page - 2) % chunk_length == 0:
            urls.append([])
        # urls is a list of (at most 100 url) lists.
        urls[(page - 2) // chunk_length].append(url)
    for chunk_urls in urls:
        pages_futures = cl.create_futures(chunk_urls)
        fr = cl.futures_results(pages_futures)
        for result in fr.results:
            deserialized_result = json.loads(result.text)
            deserialized_results += deserialized_result
        cl.pause_futures(
            fr.error_timer,
            f"Sleep order fetch due to error timer being {fr.error_timer} seconds",
        )
        while len(fr.redo_urls) != 0:
            pages_futures = cl.create_futures(fr.redo_urls)
            fr = cl.futures_results(pages_futures)
            for result in fr.results:
                deserialized_result = json.loads(result.text)
                deserialized_results += deserialized_result
            cl.pause_futures(
                fr.error_timer,
                f"Sleep redo order fetch due to error timer being {fr.error_timer} \
                        seconds",
            )
    return deserialized_results, fr.redo_urls


# Deserializes resulting JSON from futures, used in `get_source_data`
def deserialize_order_items(
    region: str,
    redo_urls: list[str],
    func: Callable[[str, int], str],
) -> tuple[list[Order], list[str]]:
    if len(redo_urls) == 0:
        deserialized_results, total_pages = deserialize_order_item_p1(region, func)
    if len(redo_urls) == 0:
        deserialized_results, redo_urls = deserialize_order_items_p2_onwards(
            region, total_pages, deserialized_results, func
        )
    return deserialized_results, redo_urls


def deserialize_order_names(ids: list[int]) -> list[NameData]:
    all_names = []
    item_ids = u.create_name_urls_json_headers(ids)
    all_futures = cl.create_post_futures(item_ids)
    # https://developers.eveonline.com/api-explorer#/operations/PostUniverseNames
    results = cl.futures_results(all_futures).results
    for result in results:
        names = json.loads(result.text)
        for name in names:
            new_name = NameData(
                category=name["category"],
                id=name["id"],
                name=name["name"],
            )
            all_names.append(new_name)
    return all_names


# Gets source data _per region_, removes any items that might cause issues, aggregates
#   them to `regional_orders` within the main object.
def get_source_data(region: str, global_orders: GlobalOrders) -> None:
    global_orders[region] = RegionOrdersData(
        all_orders_data=[],
        active_order_names=[],
        all_order_history=[],
    )
    # Fetches all orders in a region. regional_orders[region]["allOrdersData"] looks
    #  like:
    #
    # [{'duration': 90, 'is_buy_order': False, 'issued': '2025-01-28T20:37:14Z',
    #   'location_id': 60003760, 'min_volume': 1, 'order_id': 6974687044,
    #   'price': 420500000.0, 'range': 'region', 'system_id': 30000142,
    #   'type_id': 35705, 'volume_remain': 1, 'volume_total': 1}, ... ]
    #
    #   https://developers.eveonline.com/api-explorer#/operations/GetMarketsRegionIdOrders
    region_name = region_hubs[region][0]
    global_orders[region].all_orders_data = deserialize_order_items(
        region_name, [], u.create_all_order_url
    )[0]
    # Fetches all Active order item IDs in a region extracted from
    #   regional_orders[region]["allOrdersData"] fetched from line above,
    #   region_item_ids looks like:
    #
    #   [31316, 31318, 27065, 31320, 31322, ...]
    region_item_ids: list[int] = u.create_item_ids(region, global_orders)

    # List of dictionaries containing category, id, and name data, used to extract name
    #   data for later processing
    #   regional_orders[region]["active_order_names"] looks like:
    #
    # [{'category': 'inventory_type', 'id': 54360,
    #   'name': "Women's Azure Abundance Jacket"}, {'category': 'inventory_type',
    #   'id': 21593, 'name': 'Mechanic Parts'}, ...]
    global_orders[region].active_order_names = deserialize_order_names(region_item_ids)
    clean_regional_order_data_and_names = an.remove_bad_orders(
        global_orders, region, region_item_ids
    )
    # regional_orders[region]["allOrdersData"] = clean_regional_order_data_and_names[0]
    global_orders[region].all_orders_data = clean_regional_order_data_and_names[0]
    # regional_orders[region]["active_order_names"]
    #   = clean_regional_order_data_and_names[1]
    global_orders[region].active_order_names = clean_regional_order_data_and_names[1]
    region_item_ids = clean_regional_order_data_and_names[2]
    if INCLUDE_HISTORY:
        c.get_source_history_data(region, global_orders, region_item_ids)


# some functions here have gz, csv, and other stuff. Adding here because it seems that
#   they support the deserialization to a certain degree. However, this may not be the
#   case as they might be better served living in `csv.py`.
