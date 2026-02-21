ID_SEGMENT_CHUNK = 1000


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


def create_item_ids(region, regional_orders):
    region_item_ids = set()
    for order in regional_orders[region]["allOrdersData"]:
        region_item_ids.add(order["type_id"])
    return list(region_item_ids)
