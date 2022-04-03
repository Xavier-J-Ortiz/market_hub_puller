from concurrent import futures
import json
from requests.exceptions import HTTPError, RequestException
from requests_futures.sessions import FuturesSession
from concurrent.futures import as_completed

session = FuturesSession(max_workers=200)

def create_all_order_url(region, page_number):
  url_base = 'https://esi.evetech.net/latest/markets/'
  url_end = '/orders/?datasource=tranquility&order_type=all&page='
  url = url_base + str(region) + url_end + str(page_number)
  return url

def create_active_items_url(region, page_number):
  url_base = 'https://esi.evetech.net/latest/markets/'
  url_end = '/types/?datasource=tranquility&page='
  url = url_base + str(region) + url_end + str(page_number)
  return url

def create_futures(urls):
  all_futures = []
  for url in urls:
    future = session.get(url)
    all_futures.append(future)
  return all_futures

def pull_results(futures):
  results = []
  redo_urls = []
  for response in as_completed(futures):
    result = response.result() 
    try:
      result.raise_for_status()
      error_limit_remaining = result.headers['x-esi-error-limit-remain']
      if error_limit_remaining != "100":
          error_limit_time_to_reset = result.headers['x-esi-error-limit-reset']
          print('INFORMATIONAL: Though no error, for {} the Error Limit Remaning: {} Limit-Rest {} \n\n'.format(
              result.url, error_limit_remaining, error_limit_time_to_reset))
    except HTTPError:
      print('Received status code {} from {} With headers:\n{}\n'.format(
          result.status_code, result.url, str(result.headers)))
      if 'x-esi-error-limit-remain' in result.headers:
          error_limit_remaining = result.headers['x-esi-error-limit-remain']
          error_limit_time_to_reset = result.headers['x-esi-error-limit-reset']
          print('Error Limit Remaing: {} Limit-Rest {} \n'.format(
              error_limit_remaining, error_limit_time_to_reset))
      print("\n")
      redo_url = result.url
      redo_urls.append(redo_url)
      continue
    except RequestException as e:
      print("other error is " + e + " from " + result.url)
      continue
    results.append(result)
  return results, redo_urls

def pull_all_data(region, redo_urls, func):
  if len(redo_urls) == 0:
    active_items=[]
    p1_url = [func(region, 1)]
    p1_future = create_futures(p1_url)
    p1_result, redo_urls = pull_results(p1_future)
    while len(redo_urls) != 0:
      p1_future = create_futures(redo_urls)
      p1_result, redo_urls = pull_results(p1_future)
    p1_active_items = json.loads(p1_result[0].text)
    total_pages = int(p1_result[0].headers['x-pages'])
    active_items += p1_active_items

  if len(redo_urls) == 0:
    urls = []
    for page in range (2, total_pages + 1):
      url = func(region, str(page))
      urls.append(url)
    pages_futures = create_futures(urls) 
    pages_results, redo_urls = pull_results(pages_futures)
    for result in pages_results:
      active_item = json.loads(result.text)
      active_items += active_item
    while len(redo_urls) != 0:
      pages_futures = create_futures(redo_urls)
      pages_results, redo_urls = pull_results(pages_futures)
      for result in pages_results:
        active_item = json.loads(result.text)
        active_items += active_item
  return active_items, redo_urls 
'''
print(create_active_items_url(10000002, 1))
#
p1_url = [create_active_items_url(10000002, 1)]
p1_future = create_futures(p1_url)
p1_results, redo_urls = pull_results(p1_future)
p1_active_items = json.loads(p1_results[0].text)
p1_total_pages = p1_results[0].headers['x-pages']
print(len(p1_active_items), redo_urls, p1_total_pages)
#
urls = [create_active_items_url(10000002, 1), create_active_items_url(10000002, 2), create_active_items_url(10000002, 3)]
active_item_futures = create_futures(urls)
results, redo_urls = pull_results(active_item_futures)
active_items = results[0].text + results[1].text + results[2].text
total_pages = results[0].headers['x-pages']
print(len(active_items), redo_urls,total_pages)
#
active_items, redo_urls = pull_all_data(10000002, [], create_active_items_url)
print(len(active_items) == len(active_items))
print('\n')
print(len(active_items))
print('\n')
print(redo_urls)

#########
print(create_all_order_url(10000002, 1))
#
p1_url = [create_all_order_url(10000002, 1)]
p1_future = create_futures(p1_url)
p1_results, redo_urls = pull_results(p1_future)
p1_orders = p1_results[0].text
p1_total_pages = p1_results[0].headers['x-pages']
print(len(p1_orders), redo_urls, p1_total_pages)
#
urls = [create_all_order_url(10000002, 1), create_all_order_url(10000002, 2), create_all_order_url(10000002, 3)]
active_item_futures = create_futures(urls)
results, redo_urls = pull_results(active_item_futures)
active_items = json.loads(results[0].text) + json.loads(results[1].text) + json.loads(results[2].text)
total_pages = results[0].headers['x-pages']
print(len(active_items), redo_urls,total_pages)
#
for i in range(1, 2):
    orders_forge, redo_urls_forge = pull_all_data(10000002, [], create_all_order_url)
    order_ids = []
    for order in orders_forge:
      order_ids.append(order['order_id'])
    print(len(orders_forge) == len(set(order_ids)))
    print('\n')
    print(len(orders_forge))
    print('\n')
    print(redo_urls_forge)

    orders_domain, redo_urls_domain = pull_all_data(10000043, [], create_all_order_url)
    order_ids = []
    for order in orders_domain:
      order_ids.append(order['order_id'])
    print(len(orders_domain) == len(set(order_ids)))
    print('\n')
    print(len(orders_domain))
    print('\n')
    print(redo_urls_domain)


    orders_sinq, redo_urls_sinq = pull_all_data(10000032, [], create_all_order_url)
    order_ids = []
    for order in orders_sinq:
      order_ids.append(order['order_id'])
    print(len(orders_sinq) == len(set(order_ids)))
    print('\n')
    print(len(orders_sinq))
    print('\n')
    print(redo_urls_sinq)


    orders_heimatar, redo_urls_heimatar = pull_all_data(10000030, [], create_all_order_url)
    order_ids = []
    for order in orders_heimatar:
      order_ids.append(order['order_id'])
    print(len(orders_heimatar) == len(set(order_ids)))
    print('\n')
    print(len(orders_heimatar))
    print('\n')
    print(redo_urls_heimatar)

    orders_Metropolis, redo_urls_Metropolis = pull_all_data(10000042, [], create_all_order_url)
    order_ids = []
    for order in orders_Metropolis:
      order_ids.append(order['order_id'])
    print(len(orders_Metropolis) == len(set(order_ids)))
    print('\n')
    print(len(orders_Metropolis))
    print('\n')
    print(redo_urls_Metropolis)
'''