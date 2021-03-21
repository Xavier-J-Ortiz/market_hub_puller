import urllib3, json
# High sec market hubs only, [RegionID, StationID]

Jita = ['10000002','60003760'] # The Forge
Amarr = ['10000043','60008494'] # Domain
Dodixie = ['10000032','60011866'] # Sinq Liason
Rens = ['10000030','60004588'] # Heimatar
Hek = ['10000042','60005686'] # Metropolis

market_region_hub = [Jita,Amarr,Dodixie,Rens,Hek]

http=urllib3.PoolManager()
url_base = 'https://esi.evetech.net/latest/markets/'
url_end = '/orders/?datasource=tranquility&order_type=all&page='

def market_p1_data(region_hubs):
  pages = []
  payload = []
  for region in region_hubs:
    url = url_base + region[0] + url_end + '1'
    page_one = http.request('GET', url)
    pages.append(page_one.headers['x-pages'])
    payload.append(json.loads(page_one.data))
  return pages, payload

max_pages, raw_data = market_p1_data(market_region_hub)
print(raw_data)
print(max_pages)

