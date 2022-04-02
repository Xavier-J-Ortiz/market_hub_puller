from concurrent import futures
import json
from requests.exceptions import HTTPError, RequestException
from requests_futures.sessions import FuturesSession
from concurrent.futures import as_completed

session = FuturesSession(max_workers=200)

def create_url(region, page):
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
  for response in as_completed(futures):
    result = response.result() 
    redo_urls = []
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

#########
##print(create_url(10000002, 1))
#
##p1_url = create_url(10000002, 1)
##p1_future = create_future(p1_url)
##p1_response = p1_future.result()
##p1_active_items = p1_response.text
##print(p1_active_items)
#
#p1_url = [create_url(10000002, 1)]
#p1_future = create_futures(p1_url)
#p1_results, redo_urls = pull_results(p1_future)
#p1_active_items = p1_results[0].text
#p1_total_pages = p1_results[0].headers['x-pages']
#print(p1_active_items, redo_urls, p1_total_pages)
#
##urls = [create_url(10000002, 1), create_url(10000002, 2), create_url(10000002, 3)]
##active_item_futures = create_futures(urls)
##results, redo_urls = pull_results(active_item_futures)
##active_items = results[0].text + results[1].text + results[2].text
##total_pages = results[0].headers['x-pages']
##print(active_items, redo_urls,total_pages)