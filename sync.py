import urllib3, json
# High sec market hubs only, [RegionID, StationID]

Jita = ['10000002','60003760'] # The Forge
Amarr = ['10000043','60008494'] # Domain
Dodixie = ['10000032','60011866'] # Sinq Liason
Rens = ['10000030','60004588'] # Heimatar
Hek = ['10000042','60005686'] # Metropolis

market_region_hub = [Jita,Amarr,Dodixie,Rens,Hek]
# market_region_hub = [Rens]

http=urllib3.PoolManager()
url_base = 'https://esi.evetech.net/latest/markets/'
url_end = '/orders/?datasource=tranquility&order_type=all&page='

def market_p1_data(region_hubs):
  payload = {}
  for region in region_hubs:
    url = url_creator(region[0], '1')
    page_one = http.request('GET', url)
    region.append(page_one.headers['x-pages'])
    payload[region[0]] = json.loads(page_one.data)
  return payload

def market_data_fetch(region_hubs, raw_data):
  for region in region_hubs:
    for page in range(2, int(region[2]) + 1):
      url = url_creator(region[0], str(page))
      answer = http.request('GET', url)
      new_data = json.loads(answer.data)
      raw_data[region[0]] = raw_data[region[0]] + new_data
  return raw_data

def url_creator(region_id, page):
  return url_base + region_id + url_end + page
  
raw_data = market_p1_data(market_region_hub)
raw_data = market_data_fetch(market_region_hub, raw_data)

print(raw_data.keys())
# print(market_region_hub)
print(str(len(raw_data[Jita[0]])) + ", " + str(len(raw_data[Amarr[0]])) + ", " + str(len(raw_data[Dodixie[0]])) + ", " + str(len(raw_data[Rens[0]])) + ", " + str(len(raw_data[Hek[0]])))
print(str(len(raw_data[Rens[0]])))
