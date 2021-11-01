import json, os, pickle
from requests.exceptions import HTTPError, RequestException
from requests_futures.sessions import FuturesSession
from concurrent.futures import as_completed

session = FuturesSession(max_workers=200)

# High sec market hubs only, [RegionID, StationID]

Jita = ['10000002','60003760'] # The Forge
Amarr = ['10000043','60008494'] # Domain
Dodixie = ['10000032','60011866'] # Sinq Liason
Rens = ['10000030','60004588'] # Heimatar
Hek = ['10000042','60005686'] # Metropolis

url_base = 'https://esi.evetech.net/latest/markets/'
url_end = '/orders/?datasource=tranquility&order_type=all&page='

region_hubs = [Jita,Amarr,Dodixie,Rens,Hek]

def create_url(region_id, page):
  return url_base + region_id + url_end + page

def create_page1_urls(region_hubs, urls):
  for region in region_hubs:
    page1_url = create_url(region[0], '1')
    url = [page1_url, region[0]]
    urls.append(url)
  return urls

def create_all_market_order_urls(region_hubs, orders_in_regions):
  urls = []
  if len(orders_in_regions.keys()) == 0:
    urls = create_page1_urls(region_hubs, urls)
    return urls
  for region in region_hubs:
    pages = int(orders_in_regions[region[0]]['pages'])
    for page in range(2, pages + 1):
      url = [create_url(region[0], str(page)), region[0]]
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
      error_limit_remaining = result.headers['x-esi-error-limit-remain']
      if error_limit_remaining != "100":
          error_limit_time_to_reset = result.headers['x-esi-error-limit-reset']
          error_write.write('INFORMATIONAL: Though no error, for {} the Error Limit Remaning: {} Limit-Rest {} \n\n'.format(result.url, error_limit_remaining, error_limit_time_to_reset))
    except HTTPError:
      error_write.write('Received status code {} from {} With headers:\n{}\n'.format(result.status_code, result.url, str(result.headers)))
      if 'x-esi-error-limit-remain' in result.headers:
        error_limit_remaining = result.headers['x-esi-error-limit-remain']
        error_limit_time_to_reset = result.headers['x-esi-error-limit-reset']
        error_write.write('Error Limit Remaing: {} Limit-Rest {} \n'.format(error_limit_remaining, error_limit_time_to_reset))
      error_write.write("\n")
      redo_url = [result.url, response.region_id]
      redo_urls.append(redo_url)
      continue
    except RequestException as e: 
      error_write.write("other error is " + e + " from " + result.url)
      continue
    orders = json.loads(result.text)
    if response.region_id in orders_in_regions:
      orders_in_regions[response.region_id]['orders'] += orders
    else:
      total_pages = result.headers["x-pages"]
      orders_in_regions[response.region_id] = {
        'orders': orders,
        'pages': total_pages,
        'active_items_list': []
        }
  return orders_in_regions, redo_urls

def get_region_market_orders(urls, orders_in_regions, error_write):
  redo_urls = []
  futures = create_market_order_futures(urls)
  orders_in_regions, redo_urls = get_regions_markets_results(futures, orders_in_regions, redo_urls, error_write)
  if len(redo_urls) != 0:
    orders_in_regions = get_region_market_orders(redo_urls, orders_in_regions, error_write)
  return orders_in_regions


orders_in_regions = {}
if not os.path.isdir('./errors'):
  os.makedirs('./errors') 
  print("error directory created")
error_write = open('./errors/order.txt','w+')
page1_urls = create_all_market_order_urls(region_hubs, orders_in_regions)
orders_in_regions = get_region_market_orders(page1_urls, orders_in_regions, error_write)

rest_of_urls = create_all_market_order_urls(region_hubs, orders_in_regions)
orders_in_regions = get_region_market_orders(rest_of_urls, orders_in_regions, error_write)

if not os.path.isdir('./data/orders'):
  os.makedirs('./data/orders') 
  print("orders directory created")
highsec_orders = open('./data/orders/orders.pkl', 'wb')
pickle.dump(orders_in_regions, highsec_orders)
highsec_orders.close

print(str(len(orders_in_regions[Jita[0]]['orders'])) + ", " + str(len(orders_in_regions[Amarr[0]]['orders'])) + ", " + str(len(orders_in_regions[Dodixie[0]]['orders'])) + ", " + str(len(orders_in_regions[Rens[0]]['orders'])) + ", " + str(len(orders_in_regions[Hek[0]]['orders'])))
print(str((orders_in_regions[Jita[0]]['pages'])) + ", " + str((orders_in_regions[Amarr[0]]['pages'])) + ", " + str((orders_in_regions[Dodixie[0]]['pages'])) + ", " + str((orders_in_regions[Rens[0]]['pages'])) + ", " + str((orders_in_regions[Hek[0]]['pages'])))