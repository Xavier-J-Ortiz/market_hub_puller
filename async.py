import json, os
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

def create_page1_market_region_futures(region_hubs):
  raw_data = {}
  futures = []
  for region in region_hubs:
    url = create_url(region[0], '1')
    future =  session.get(url)
    future.region_hub = region
    futures.append(future)
  return futures

def get_page1_market_region_results(futures, redo_region_hub, error_write):
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
      redo_region_hub.append(response.region_hub)
      continue
    except RequestException as e: 
      error_write.write("other error is " + e + "\n")
      continue
    orders = json.loads(result.text)
    total_pages = result.headers["x-pages"]
    raw_data[response.region_hub[0]] = {
      'orders': orders,
      'pages': total_pages
      }
  return raw_data, redo_region_hub

def get_page1_market_region_data(region_hubs, raw_data, error_write):
  redo_region_hub = []
  futures = create_page1_market_region_futures(region_hubs)
  raw_data, redo_region_hub = get_page1_market_region_results(futures, redo_region_hub, error_write)
  if len(redo_region_hub) != 0:
    # recursion - need to think if futures need to be re-created, if futures that need to be redone can 
    # be separated... maybe can be optimized
    raw_data = get_page1_market_region_data(redo_region_hub, raw_data, error_write)
  return raw_data
    
def create_market_order_futures(region_hubs):
  futures = {}
  return futures

def get_market_order_results():
  results = 1
  return results

def get_market_orders():
  market_orders = {}
  return market_orders

def create_url(region_id, page):
  return url_base + region_id + url_end + page

def market_data_fetch(region_hubs, raw_data):
  return raw_data
 

raw_data = {}
if not os.path.isdir('./data/error'):
  os.makedirs('./data/error') 
  print("error directory created")
error_write = open('./data/error/order.txt','w+')
#raw_data, redo_region_hub = get_page1_market_region_results(futures, region_hubs, redo_region_hub, error_write)
get_page1_market_region_data(region_hubs, raw_data, error_write)
print(str(len(raw_data[Jita[0]]['orders'])) + ", " + str(len(raw_data[Amarr[0]]['orders'])) + ", " + str(len(raw_data[Dodixie[0]]['orders'])) + ", " + str(len(raw_data[Rens[0]]['orders'])) + ", " + str(len(raw_data[Hek[0]]['orders'])))
print(str((raw_data[Jita[0]]['pages'])) + ", " + str((raw_data[Amarr[0]]['pages'])) + ", " + str((raw_data[Dodixie[0]]['pages'])) + ", " + str((raw_data[Rens[0]]['pages'])) + ", " + str((raw_data[Hek[0]]['pages'])))