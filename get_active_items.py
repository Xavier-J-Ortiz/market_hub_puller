from concurrent import futures
import json
import os
import pickle
from requests.exceptions import HTTPError, RequestException
from requests_futures.sessions import FuturesSession
from concurrent.futures import as_completed

session = FuturesSession(max_workers=200)

# High sec market hubs only, [RegionID, StationID]

Jita = ['10000002', '60003760']  # The Forge
Amarr = ['10000043', '60008494']  # Domain
Dodixie = ['10000032', '60011866']  # Sinq Liason
Rens = ['10000030', '60004588']  # Heimatar
Hek = ['10000042', '60005686']  # Metropolis

url_base = 'https://esi.evetech.net/latest/markets/'
url_end = '/types/?datasource=tranquility&page='

region_hubs = [Jita, Amarr, Dodixie, Rens, Hek]


def create_url(region_id, page, url_base, url_end):
  return url_base + region_id + url_end + page


def create_page1_urls(region_hubs, urls):
  for region in region_hubs:
    page1_url = create_url(region[0], '1', url_base, url_end)
    url = [page1_url, region[0]]
    urls.append(url)
  return urls


def create_all_active_item_urls(region_hubs, active_items):
  urls = []
  if len(active_items.keys()) == 0:
    urls = create_page1_urls(region_hubs, urls)
    return urls
  for region in region_hubs:
    pages = int(active_items[region[0]]['pages'])
    for page in range(2, pages + 1):
      url = [create_url(region[0], str(page), url_base, url_end), region[0]]
      urls.append(url)
  return urls

def create_active_item_futures(urls):
  futures = []
  for url in urls:
    region = url[1]
    future = session.get(url[0])
    future.region_id = region
    futures.append(future)
  return futures

def get_region_active_items_results(futures, active_items, redo_urls, error_write):
    for response in as_completed(futures):
        result = response.result()
        try:
            result.raise_for_status()
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
            redo_url = [result.url, response.region_id]
            redo_urls.append(redo_url)
            continue
        except RequestException as e:
            error_write.write("other error is " + e + " from " + result.url)
            continue
        items = json.loads(result.text)
        if response.region_id in active_items:
            active_items[response.region_id]['items'] += items
        else:
            total_pages = result.headers["x-pages"]
            active_items[response.region_id] = {
                'items': items,
                'pages': total_pages
            }
    return active_items, redo_urls


def get_region_active_items(urls, active_items, error_write):
  redo_urls = []
  futures = create_active_item_futures(urls)
  active_items, redo_urls = get_region_active_items_results(
      futures, active_items, redo_urls, error_write)
  if len(redo_urls) != 0:
    active_items = get_region_active_items(
        redo_urls, active_items, error_write)
  return active_items

active_items = {}
if not os.path.isdir('./errors'):
  os.makedirs('./errors') 
  print("error directory created")
error_write = open('./errors/active_items.txt','w+')
page1_urls =  create_all_active_item_urls(region_hubs, active_items)
active_items = get_region_active_items(page1_urls, active_items, error_write)

rest_of_urls = create_all_active_item_urls(region_hubs, active_items)
active_items =  get_region_active_items(rest_of_urls, active_items, error_write)

if not os.path.isdir('./data/orders'):
  os.makedirs('./data/orders') 
  print("orders directory created")
highsec_active_orders = open('./data/orders/active_orders.pkl', 'wb')
pickle.dump(active_items, highsec_active_orders)
highsec_active_orders.close

print(str(len(active_items[Jita[0]]['items'])) + ", " + str(len(active_items[Amarr[0]]['items'])) + ", " + str(len(active_items[Dodixie[0]]['items'])) + ", " + str(len(active_items[Rens[0]]['items'])) + ", " + str(len(active_items[Hek[0]]['items'])))
print(str((active_items[Jita[0]]['pages'])) + ", " + str((active_items[Amarr[0]]['pages'])) + ", " + str((active_items[Dodixie[0]]['pages'])) + ", " + str((active_items[Rens[0]]['pages'])) + ", " + str((active_items[Hek[0]]['pages'])))