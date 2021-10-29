import urllib3, json
# High sec market hubs only, [RegionID, StationID]

Jita = ['10000002','60003760'] # The Forge
Amarr = ['10000043','60008494'] # Domain
Dodixie = ['10000032','60011866'] # Sinq Liason
Rens = ['10000030','60004588'] # Heimatar
Hek = ['10000042','60005686'] # Metropolis

region_hub = [Jita,Amarr,Dodixie,Rens,Hek]

http=urllib3.PoolManager()
url_base = 'https://esi.evetech.net/latest/markets/'
url_end = '/orders/?datasource=tranquility&order_type=all&page='

def market_page1_data(region_hubs):
  raw_data = {}
  for region in region_hubs:
    url = url_creator(region[0], '1')

    page_one = http.request('GET', url)
    total_pages = page_one.headers['x-pages']

    orders = json.loads(page_one.data)

    raw_data[region[0]] = {
      'orders': orders,
      'pages': total_pages
      }
  return raw_data

def market_data_fetch(region_hubs, raw_data):
  for region in region_hubs:
    for page in range(2, int(raw_data[region[0]]['pages']) + 1):
      url = url_creator(region[0], str(page))
      answer = http.request('GET', url)
      orders = json.loads(answer.data)
      raw_data[region[0]]['orders'] = raw_data[region[0]]['orders'] + (orders)
  return raw_data

def url_creator(region_id, page):
  return url_base + region_id + url_end + page
'''  
page1_raw_data = market_page1_data(region_hub)
raw_data = market_data_fetch(region_hub, page1_raw_data)
print(str(len(raw_data[Jita[0]]['orders'])) + ", " + str(len(raw_data[Amarr[0]]['orders'])) + ", " + str(len(raw_data[Dodixie[0]]['orders'])) + ", " + str(len(raw_data[Rens[0]]['orders'])) + ", " + str(len(raw_data[Hek[0]]['orders'])))
print(str((raw_data[Jita[0]]['pages'])) + ", " + str((raw_data[Amarr[0]]['pages'])) + ", " + str((raw_data[Dodixie[0]]['pages'])) + ", " + str((raw_data[Rens[0]]['pages'])) + ", " + str((raw_data[Hek[0]]['pages'])))
'''