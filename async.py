import aiohttp
import asyncio
import json

# High sec market hubs only, [RegionID, StationID]

jita = ['10000002','60003760'] # The Forge
amarr = ['10000043','60008494'] # Domain
dodixie = ['10000032','60011866'] # Sinq Liason
rens = ['10000030','60004588'] # Heimatar
hek = ['10000042','60005686'] # Metropolis

url_base = 'https://esi.evetech.net/latest/markets/'
url_end = '/orders/?datasource=tranquility&order_type=all&page='

market_region_hub = [jita,amarr,dodixie,rens,hek]
#market_region_hub = [rens]
async def test():
  async with aiohttp.ClientSession() as session:
    async with session.get(url_creator(market_region_hub[0][0], '1')) as response:
      data = await response.text()
      pages = response.headers['x-pages']
#      print(data)
#      print(pages)
      return data, pages

async def market_p1_data(region_hubs):
  payload = {}
  async with aiohttp.ClientSession() as session:
    for region in region_hubs:
      url = url_creator(region[0], '1') 
      async with session.get(url) as response:
        page_one = response.headers['x-pages']
        region.append(page_one)
        data = await response.text()
        payload[region[0]] = json.loads(data)
  return payload

def url_creator(region_id, page):
  return url_base + region_id + url_end + page

async def market_data_fetch(region_hubs, raw_data):
  async with aiohttp.ClientSession() as session:
    for region in region_hubs:
      for page in range(2, int(region[2]) + 1):
        url = url_creator(region[0], str(page))
        async with session.get(url) as response:
          answer = await response.text()
          new_data = json.loads(answer)
          raw_data[region[0]] = raw_data[region[0]] + new_data
  return raw_data


loop = asyncio.get_event_loop()
raw_data = loop.run_until_complete(market_p1_data(market_region_hub))
raw_data = loop.run_until_complete(market_data_fetch(market_region_hub, raw_data))

print(raw_data.keys())
print(market_region_hub)
print(str(len(raw_data[jita[0]])) + ", " + str(len(raw_data[amarr[0]])) + ", " + str(len(raw_data[dodixie[0]])) + ", " + str(len(raw_data[rens[0]])) + ", " + str(len(raw_data[hek[0]])))
#print(str(len(raw_data[rens[0]])))

"""
http=urllib3.PoolManager()

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

raw_data = market_p1_data(market_region_hub)
raw_data = market_data_fetch(market_region_hub, raw_data)

print(raw_data.keys())
# print(market_region_hub)
print(str(len(raw_data[jita[0]])) + ", " + str(len(raw_data[amarr[0]])) + ", " + str(len(raw_data[dodixie[0]])) + ", " + str(len(raw_data[rens[0]])) + ", " + str(len(raw_data[hek[0]])))
print(str(len(raw_data[rens[0]])))
"""
