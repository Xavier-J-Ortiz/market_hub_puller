import pickle, get_active_items, get_all_orders, os, competitive_prices, json

from requests.sessions import session
from requests.exceptions import HTTPError, RequestException
from requests_futures.sessions import FuturesSession
from concurrent.futures import as_completed
from competitive_prices import create_names_future


Jita = ['10000002','60003760'] # The Forge
Amarr = ['10000043','60008494'] # Domain
Dodixie = ['10000032','60011866'] # Sinq Liason
Rens = ['10000030','60004588'] # Heimatar
Hek = ['10000042','60005686'] # Metropolis
region_hubs = [Jita,Amarr,Dodixie,Rens,Hek]
# Forge/Jita must be first hub in region_hubs, or we must remove from array
# and create a global variable that always assumes this is Jita.
def create_hub_data(region_hubs, high_low_prices):
    profit_data = {}
    positive_infinity = float('inf')
    negative_infinity = float('-inf')
    jita = region_hubs[0][1]
    sell_region_hubs = region_hubs
    sell_region_hubs.pop(0)
    jita_orders = high_low_prices[jita]
    for item in jita_orders:
        if item != 'name':
            jbv = jita_orders[item]['highest_buy']
            jsv = jita_orders[item]['lowest_sell']
            item_name = jita_orders[item]['name']
            for sell_region in sell_region_hubs:
                hub = sell_region[1]
                sell_hub_orders = high_low_prices[hub]
                if hub not in profit_data:
                    station_hub_name = high_low_prices[hub]['name']
                    profit_data[hub] = {'name': station_hub_name}
                if item not in sell_hub_orders:
                    hub_sell_value = positive_infinity
                else:
                    hub_sell_value = sell_hub_orders[item]['lowest_sell']
                if jsv == negative_infinity:
                    jsv = None
                    profit_from_jsv = None
                else:
                    profit_from_jsv = 1 - jsv/hub_sell_value
                if jbv == positive_infinity:
                    jbv = None
                    profit_from_jbv = None
                else:
                    profit_from_jbv = 1 - jbv/hub_sell_value
                profit_data[hub][item] = {
                    'jbv_sourced': profit_from_jbv,
                    'jsv_sourced': profit_from_jsv,
                    'jbv': jbv,
                    'jsv': jsv,
                    'hub_sell_value': hub_sell_value,
                    'name': item_name
                }
                if 'name' not in profit_data[hub]:
                    profit_data[hub]['name'] = sell_hub_orders['item_name']
    if not os.path.isdir('./data/profits'):
        os.makedirs('./data/profits') 
        print('profits directory created')
    hub_profits = open('./data/orders/profits.pkl', 'wb')
    pickle.dump(profit_data, hub_profits)
    hub_profits.close
    return profit_data


orders_in_regions = competitive_prices.get_order_info(region_hubs)
high_low_prices  = competitive_prices.get_high_low_prices(region_hubs, orders_in_regions)
profit_data = create_hub_data(region_hubs, high_low_prices)
for key in profit_data:
    print(profit_data[key]['name'])

print(profit_data['60008494']['20509'])
print(profit_data['60008494']['name'])