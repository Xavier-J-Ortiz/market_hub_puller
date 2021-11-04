import pickle, get_active_items, get_all_orders, os, competitive_prices

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
        for sell_region in sell_region_hubs:
            hub = sell_region[1]
            sell_hub_orders = high_low_prices[hub]
            if hub not in profit_data:
                profit_data[hub] = {}
            jbv = jita_orders[item]['highest_buy']
            jsv = jita_orders[item]['lowest_sell']

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
                'hub_sell_value': hub_sell_value
            }
    
    return profit_data
'''
orders_in_regions = competitive_prices.get_order_info(region_hubs)
#orders_in_regions = pickle.load(open("./data/orders/orders.pkl","rb"))
high_low_prices = competitive_prices.get_high_low_prices(region_hubs, orders_in_regions)
#print(high_low_prices['60003760']['48746']) # jita Overmind Goliath
#print(high_low_prices['60003760']['34']) # jita trit
#print(high_low_prices['60003760']['20509']) # jita HG Amulet Omega
#print(high_low_prices['60008494']['48746']) # amarr Overmind Goliath
#print(high_low_prices['60008494']['34']) # amarr trit
#print(high_low_prices['60008494']['20509']) # amarr HG Amulet Omega
profit_data = create_hub_data(region_hubs, high_low_prices)
print(profit_data.keys())
print(profit_data[Amarr[1]]['48746'])
print(profit_data[Dodixie[1]]['48746'])
print(profit_data[Rens[1]]['48746'])
print(profit_data[Hek[1]]['48746'])
print(profit_data[Amarr[1]]['40718'])
print(profit_data[Dodixie[1]]['40718'])
print(profit_data[Rens[1]]['40718'])
print(profit_data[Hek[1]]['40718'])
'''