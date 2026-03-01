from api.client import UrlJsonHeader
from processing.constants import GlobalOrders, Order

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


def create_item_ids(region: str, global_orders: GlobalOrders) -> list[int]:
    region_item_ids: set[int] = set()
    orders: list[Order] = global_orders[region].all_orders_data
    for order in orders:
        if isinstance(order.type_id, int):
            region_item_ids.add(order.type_id)
        else:
            raise TypeError(
                f"`order.type_id` is expected to be `int`, but was "
                f"{type(order.type_id)}"
            )
    return list(region_item_ids)
