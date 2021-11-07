import pickle, get_active_items, get_all_orders, os, json
from requests.exceptions import HTTPError, RequestException
from requests_futures.sessions import FuturesSession
from concurrent.futures import as_completed

def get_order_info(region_hubs):
    active_items = {}
    if not os.path.isdir('./errors'):
        os.makedirs('./errors') 
        print("error directory created")
    error_write = open('./errors/active_items.txt','w+')
    page1_urls =  get_active_items.create_all_active_item_urls(region_hubs, active_items)
    active_items = get_active_items.get_region_active_items(page1_urls, active_items, error_write)

    rest_of_urls = get_active_items.create_all_active_item_urls(region_hubs, active_items)
    active_items =  get_active_items.get_region_active_items(rest_of_urls, active_items, error_write)

    orders_in_regions = {}
    if not os.path.isdir('./errors'):
        os.makedirs('./errors') 
        print("error directory created")
    error_write = open('./errors/order.txt','w+')
    page1_urls = get_all_orders.create_all_market_order_urls(region_hubs, orders_in_regions)
    orders_in_regions = get_all_orders.get_region_market_orders(page1_urls, orders_in_regions, active_items, error_write)

    rest_of_urls = get_all_orders.create_all_market_order_urls(region_hubs, orders_in_regions)
    orders_in_regions = get_all_orders.get_region_market_orders(rest_of_urls, orders_in_regions, active_items, error_write)

    if not os.path.isdir('./data/orders'):
        os.makedirs('./data/orders') 
        print("orders directory created")
    highsec_orders = open('./data/orders/orders.pkl', 'wb')
    pickle.dump(orders_in_regions, highsec_orders)
    highsec_orders.close
    return orders_in_regions

def build_current_price_info(hubs, all_hub_names, current_price_info, region, orders_in_regions, unique_order_items_names):
    for hub in hubs:
        all_hub_names[hub] = ''
        current_price_info[hub] = {}
        active_items = orders_in_regions[region]['active_items_list']
        for item in active_items:
            positive_infinity = float('inf')
            negative_infinity = float('-inf')
            current_price_info[hub][str(item)] = {
                'lowest_sell': positive_infinity,
                'highest_buy': negative_infinity
            }
            unique_order_items_names[str(item)] = ''
    all_regional_orders = orders_in_regions[region]['orders']
    return all_regional_orders, unique_order_items_names, current_price_info, all_hub_names 

def get_raw_prices(hubs, hub_ids, all_hub_names, hub_data, current_price_info, all_regional_orders):
    for i in range(0, len(hub_ids)):
        all_hub_names[hub_ids[i]] = hub_data[i]['name']
        current_price_info[hub_ids[i]]['name'] = hub_data[i]['name']
    for order in all_regional_orders:
        hub = str(order['location_id'])
        if hub in hubs:
            order_item_id = str(order['type_id'])
            order_price = order['price']
            if order['is_buy_order']:
                current_highest_buy = current_price_info[hub][order_item_id]['highest_buy'] 
                current_price_info[hub][order_item_id]['highest_buy']  = order_price if order_price > current_highest_buy else current_highest_buy
            else:
                current_lowest_sell = current_price_info[hub][order_item_id]['lowest_sell'] 
                current_price_info[hub][order_item_id]['lowest_sell']  = order_price if order_price < current_lowest_sell else current_lowest_sell
    return current_price_info

def get_high_low_prices(region_hubs, orders_in_regions):
    regions = orders_in_regions.keys()
    current_price_info = {}
    all_hub_names = {}
    unique_order_items_names = {}
    for region in regions:
        hubs = []
        for region_hub_data in region_hubs:
            if region in region_hub_data:
                hubs = region_hub_data.copy()
                hubs.remove(region)
        all_regional_orders, unique_order_items_names, current_price_info, all_hub_names =  build_current_price_info(hubs, all_hub_names, current_price_info, region, orders_in_regions, unique_order_items_names)         
        if not os.path.isdir('./errors'):
            os.makedirs('./errors') 
            print("error directory created")
        error_write = open('./errors/hub_ids.txt','w+')
        hub_ids = list(all_hub_names.keys())
        hub_data = get_hub_ids(hub_ids, all_hub_names, error_write)
        current_price_info = get_raw_prices(hubs, hub_ids, all_hub_names, hub_data, current_price_info, all_regional_orders)
    item_name_futures = create_names_future(list(unique_order_items_names.keys()))
    if not os.path.isdir('./errors'):
        os.makedirs('./errors') 
        print("error directory created")
    error_write = open('./errors/item_name.txt','w+')
    unique_order_items_names = get_item_name(item_name_futures, unique_order_items_names, error_write)
    for hub in current_price_info:
        current_hub_price_info = current_price_info[hub]
        for item in current_hub_price_info:
            if item != 'name':
                current_hub_price_info[item]['name'] = unique_order_items_names[item]
    if not os.path.isdir('./data/orders'):
        os.makedirs('./data/orders') 
        print("orders directory created")
    high_low = open('./data/orders/high_low.pkl', 'wb')
    pickle.dump(current_price_info, high_low)
    high_low.close
    return current_price_info

def get_item_name(item_name_futures, unique_order_items_names, error_write):
    redo_item_name = []
    for item_name_future in as_completed(item_name_futures):
        result = item_name_future.result()
        try:
            error_limit_remaining = result.headers['x-esi-error-limit-remain']
            if error_limit_remaining != "100":
                error_limit_time_to_reset = result.headers['x-esi-error-limit-reset']
                error_write.write('INFORMATIONAL: Though no error, for {} the Error Limit Remaning: {} Limit-Rest {} \n\n'.format(
                    result.url, error_limit_remaining, error_limit_time_to_reset))
        except HTTPError:
            error_write.write('Received status code {} from {} With headers:\n{}\n'.format(
                result.status_code, result.url, str(result.headers)))
            if 'x-esi-error-limit-remain' in result.headers:
                error_limit_remaining = result.headers['x-esi-error-limit-remain']
                error_limit_time_to_reset = result.headers['x-esi-error-limit-reset']
                error_write.write('Error Limit Remaing: {} Limit-Rest {} \n'.format(
                    error_limit_remaining, error_limit_time_to_reset))
            error_write.write("\n")
            redo_item_name.append(item_name_future)
        except RequestException as e:
            error_write.write("other error is " + e + " from " + result.url)
        item_data = json.loads(result.text)
        for item_entry in item_data:
            unique_order_items_names[str(item_entry['id'])] = item_entry['name']
        if len(redo_item_name) != 0:
            get_item_name(redo_item_name, unique_order_items_names,error_write)
    return unique_order_items_names

def create_names_future(ids):
    session = FuturesSession(max_workers=200)
    if len(ids) <= 1000:
        url = 'https://esi.evetech.net/latest/universe/names/?datasource=tranquility'
        header = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache'
            }
        future = session.post(url, json=ids, headers=header)
        return future
    answer = []
    for i in range(0, len(ids), 1000):
        answer.append(ids[i: 1000+i])
    futures = []
    for id_segment in answer:
        url = 'https://esi.evetech.net/latest/universe/names/?datasource=tranquility'
        header = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache'
            }
        futures.append(session.post(url, json=id_segment, headers=header))
    return futures

def get_hub_ids(hub_ids, all_hub_names, error_write):
    all_hub_names_future = create_names_future(hub_ids)
    result = all_hub_names_future.result()
    try:
        error_limit_remaining = result.headers['x-esi-error-limit-remain']
        if error_limit_remaining != "100":
            error_limit_time_to_reset = result.headers['x-esi-error-limit-reset']
            error_write.write('INFORMATIONAL: Though no error, for {} the Error Limit Remaning: {} Limit-Rest {} \n\n'.format(
                result.url, error_limit_remaining, error_limit_time_to_reset))
    except HTTPError:
        error_write.write('Received status code {} from {} With headers:\n{}\n'.format(
            result.status_code, result.url, str(result.headers)))
        if 'x-esi-error-limit-remain' in result.headers:
            error_limit_remaining = result.headers['x-esi-error-limit-remain']
            error_limit_time_to_reset = result.headers['x-esi-error-limit-reset']
            error_write.write('Error Limit Remaing: {} Limit-Rest {} \n'.format(
                error_limit_remaining, error_limit_time_to_reset))
        error_write.write("\n")
        get_hub_ids(all_hub_names, error_write)
    except RequestException as e:
        error_write.write("other error is " + e + " from " + result.url)
    hub_data = json.loads(result.text)
    return hub_data 