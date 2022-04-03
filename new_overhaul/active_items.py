from concurrent import futures
import json
from requests.exceptions import HTTPError, RequestException
from requests_futures.sessions import FuturesSession
from concurrent.futures import as_completed

session = FuturesSession(max_workers=200)

def create_active_order_url(region, page):
  url_base = 'https://esi.evetech.net/latest/markets/'
  url_end = '/types/?datasource=tranquility&page='
  url = url_base + str(region) + url_end + str(page)
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
      redo_url = [result.url, result.region_id]
      redo_urls.append(redo_url)
      continue
    except RequestException as e:
      print("other error is " + e + " from " + result.url)
      continue
    results.append(result)
  return results, redo_urls

def pull_all_active_items(region, redo_urls):
  if len(redo_urls) == 0:
    active_items=[]
    p1_url = [create_active_order_url(region, 1)]
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
      url = create_active_order_url(region, str(page))
      urls.append(url)
    pages_futures = create_futures(urls) 
    pages_results, redo_urls = pull_results(pages_futures)
    for result in pages_results:
      active_item = json.loads(result.text)
      active_items += active_item
    while len(redo_urls) != 0:
      pages_futures = redo_urls
      pages_results, redo_urls = pull_results(pages_futures)
      for result in pages_results:
        active_item = json.loads(result.text)
        active_items += active_item
  return active_items, redo_urls 

#########
#print(create_active_order_url(10000002, 1))
#
##p1_url = [create_url(10000002, 1)]
##p1_future = create_futures(p1_url)
##p1_results, redo_urls = pull_results(p1_future)
##p1_active_items = p1_results[0].text
##p1_total_pages = p1_results[0].headers['x-pages']
##print(p1_active_items, redo_urls, p1_total_pages)
#
##urls = [create_url(10000002, 1), create_url(10000002, 2), create_url(10000002, 3)]
##active_item_futures = create_futures(urls)
##results, redo_urls = pull_results(active_item_futures)
##active_items = results[0].text + results[1].text + results[2].text
##total_pages = results[0].headers['x-pages']
##print(active_items, redo_urls,total_pages)
#
##active_items, redo_urls = pull_all_active_items(10000002, [])
##print(active_items)
##print('\n')
##print(len(active_items))
##print('\n')
##print(redo_urls)