import pickle, get_active_items, get_all_orders, os

Jita = ['10000002','60003760'] # The Forge
Amarr = ['10000043','60008494'] # Domain
Dodixie = ['10000032','60011866'] # Sinq Liason
Rens = ['10000030','60004588'] # Heimatar
Hek = ['10000042','60005686'] # Metropolis
region_hubs = [Jita,Amarr,Dodixie,Rens,Hek]

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
    for region in regions:
        for region_hub_data in region_hubs:
            if region in region_hub_data:
                hubs = region_hub_data
                hubs.remove(region)
        all_regional_orders = orders_in_regions[region]['orders']
        for hub in hubs:
            current_price_info[hub] = {}
            active_items = orders_in_regions[region]['active_items_list']
            for item in active_items:
                positive_infinity = float('inf')
                negative_infinity = float('-inf')
                current_price_info[hub][str(item)] = {
                    'lowest_sell': positive_infinity,
                    'highest_buy': negative_infinity
                }
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
    if not os.path.isdir('./data/orders'):
        os.makedirs('./data/orders') 
        print("orders directory created")
    high_low = open('./data/orders/high_low.pkl', 'wb')
    pickle.dump(current_price_info, high_low)
    high_low.close
    return current_price_info
        



            

'''        
orders_in_regions = get_order_info(region_hubs)
#orders_in_regions = pickle.load(open("./data/orders/orders.pkl","rb"))
high_low_prices = get_high_low_prices(region_hubs, orders_in_regions)
#print(high_low_prices['60003760']['48746']) # jita Overmind Goliath
#print(high_low_prices['60003760']['34']) # jita trit
#print(high_low_prices['60003760']['20509']) # jita HG Amulet Omega
#print(high_low_prices['60008494']['48746']) # amarr Overmind Goliath
#print(high_low_prices['60008494']['34']) # amarr trit
#print(high_low_prices['60008494']['20509']) # amarr HG Amulet Omega

'''