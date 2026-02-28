from dataclasses import dataclass
from typing import TypedDict, cast

from api.client import UrlJsonHeader
from processing.constants import All_orders_data, Regional_orders

ID_SEGMENT_CHUNK: int = 1000


def create_all_order_url(region: str, page_number: int) -> str:
    url_base = "https://esi.evetech.net/latest/markets/"
    url_end = "/orders/?datasource=tranquility&order_type=all&page="
    url = url_base + str(region) + url_end + str(page_number)
    return url


def create_active_items_url(region: str, page_number: int) -> str:
    url_base = "https://esi.evetech.net/latest/markets/"
    url_end = "/types/?datasource=tranquility&page="
    url = url_base + str(region) + url_end + str(page_number)
    return url


def create_item_history_url(region: str, item_id: int) -> str:
    url_base = "https://esi.evetech.net/latest/markets/"
    url_end = "/history/?datasource=tranquility&page=1&type_id="
    url = url_base + str(region) + url_end + str(item_id)
    return url


def create_name_urls_json_headers(ids: list[int]) -> list[UrlJsonHeader]:
    ujhs: list[UrlJsonHeader] = []
    url: str = "https://esi.evetech.net/latest/universe/names/?datasource=tranquility"
    # TODO: `header` can probably be de-duplicated. If we know we are create post
    #   futures, we don't need to add the headers to every URL. Changes need to be made
    #   in `api.client.py` as well.
    header: dict[str, str] = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }
    if len(ids) <= ID_SEGMENT_CHUNK:
        id_segment: list[int] = ids
        ujhs.append(UrlJsonHeader(url=url, ids=id_segment, header=header))
        return ujhs
    segmented_ids: list[list[int]] = []
    for i in range(0, len(ids), ID_SEGMENT_CHUNK):
        end: int = ID_SEGMENT_CHUNK + i
        segmented_ids.append(ids[i:end])
    for id_segment in segmented_ids:
        ujhs.append(UrlJsonHeader(url=url, ids=id_segment, header=header))

    return ujhs


class GlobalOrders(TypedDict):
    region: str
    regionalOrders: list[Order]


@dataclass
class Order:
    duration: int
    is_buy_order: bool
    issued: str
    location_id: int
    min_volume: int
    order_id: int
    price: float
    range: str
    system_id: int
    type_id: int
    volume_remain: int
    volume_total: int


def create_item_ids(region: str, regional_orders: Regional_orders) -> list[int]:
    region_item_ids: set[int] = set()
    orders: All_orders_data = cast(
        All_orders_data, regional_orders[region]["allOrdersData"]
    )
    for order in orders:
        if isinstance(order["type_id"], int):
            region_item_ids.add(order["type_id"])
        else:
            raise TypeError(
                f"`type_id` is expected to be `int`, but was {type(order['type_id'])}"
            )
    return list(region_item_ids)
