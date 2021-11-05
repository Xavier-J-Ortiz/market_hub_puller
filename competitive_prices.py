import pickle, get_active_items, get_all_orders, os, json
from requests_futures.sessions import FuturesSession
from concurrent.futures import as_completed

Jita = ['10000002','60003760'] # The Forge
Amarr = ['10000043','60008494'] # Domain
Dodixie = ['10000032','60011866'] # Sinq Liason
Rens = ['10000030','60004588'] # Heimatar
Hek = ['10000042','60005686'] # Metropolis
region_hubs = [Jita,Amarr,Dodixie,Rens,Hek]

session = FuturesSession(max_workers=200)

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
                #print(hubs)
        all_regional_orders = orders_in_regions[region]['orders']
        #print(hubs)
        for hub in hubs:
            #print(hub)
            #print(hubs)
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
                #if hub == "60003760":
                #    unique_order_items_names[str(item)] = ''
                unique_order_items_names[str(item)] = ''
            #print(f"Hub {hub}, hub_current_price length {len(current_price_info[hub])}")
        hub_ids = list(all_hub_names.keys())
        all_hub_names_future = create_names_future(hub_ids)
        response = all_hub_names_future.result()
        hub_data = json.loads(response.text)
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
    #print(len(unique_order_items_names))
    #print(type(list(unique_order_items_names.keys())[0]))
    item_name_futures = create_names_future(list(unique_order_items_names.keys()))
    #print(len(item_name_futures))

    for item_name_future in as_completed(item_name_futures):
        response = item_name_future.result()
        item_data = json.loads(response.text)
        for item_entry in item_data:
            #print(len(item_entry))
            #print(item_entry)
            #print(item_entry['name'])
            unique_order_items_names[str(item_entry['id'])] = item_entry['name']
    
    #print(len(unique_order_items_names))
    #print(type(list(unique_order_items_names.keys())[-1]))
    for hub in current_price_info:
        #print(hub)
        current_hub_price_info = current_price_info[hub]
        for item in current_hub_price_info:
            #if item != 'name' and (item in current_hub_price_info):
            if item != 'name':
                #print(item)
                #print(type(item))
                #print(unique_order_items_names[item]) # the offender
                #print(current_hub_price_info[item])
                current_hub_price_info[item]['name'] = unique_order_items_names[item]

    if not os.path.isdir('./data/orders'):
        os.makedirs('./data/orders') 
        print("orders directory created")
    high_low = open('./data/orders/high_low.pkl', 'wb')
    pickle.dump(current_price_info, high_low)
    high_low.close



    return current_price_info, unique_order_items_names

def create_names_future(ids):
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
