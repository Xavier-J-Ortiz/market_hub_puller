# Market Hub Puller

Effort to consume EVE Online's ESI for sorting out items.

## Requirements

Though previously, it was recommended to use `python3` and
`python3-requres-future` packages on debian and ubuntu by running:

We've moved to using pyenv in order to have a more standard development platform
, and keep experience ubiquitous for development and when using the script.

We recommend using the [Automatic Installer](https://github.com/pyenv/pyenv?tab=readme-ov-file#1-automatic-installer-recommended)
from the pyenv project.

Below is one of the recommended ways to install `pyenv`.

```bash
git clone https://github.com/pyenv/pyenv.git ~/.pyenv
```

On install, the script has recommendations on what to add to your `.bashrc`.
Please follow the suggestions shown on the output. Refer to the official
[pyenv installation section](https://github.com/pyenv/pyenv?tab=readme-ov-file#installation)
for further detail as these instructions may be out of date.

Once successfully installed run:

```bash
pyenv install

pip install -r requirements
```

The environment should be ready to use.

## How to Run

Specify what region hubs you want to do analysis on. Default has the 5 high sec npc stations, located in Jita, Amarr, Rens, and Hek. Other locations can be added, so long as the `Jita` entry is at the top of the dict, and their region ID and hub ID is specified in the `region_hubs` dictionary. Example shown below:

```python3
region_hubs = {
    "Jita": ["10000002", "60003760"],  # Do Not Delete. Must always be on top.
    "Region_Name": [RegionID, StationID],  # Sample format
    "Hek": ["10000042", "60005686"],
}
```

Running file `fetch_data.py` will retrieve data from specified market hubs, and process said data.

The output fields will be `["name", "id", f"{region}sv", f"{region}bv", "jsv", "jbv", "diff", "jsv_sell_margin", "jbv_sell_margin",]`.

## Saving Source and Processed Data

You may save the source data, as well as the processed data, by setting the `SAVE_PROCESSED_DATA` or `SAVE_SOURCE_DATA` values to `True` in the file. If saved, the data will be saved as a `csv.gz` and be placed within the `market_data` folder.

By default, `SAVE_SOURCE_DATA` is set to `False` as it takes longer than saving the processed data. `SAVE_PROCESSED_DATA` is set to True.

## Adding Additional Filters

There is a toggle that allows additional filtering for more useful data.

The toggle is `FINAL_FILTER`, and will enable the ability to use a final additional filter over the processed cut of data.

The additional filter and filter values shown below are a set as a default.

```python3

filter_values = {
    "jsv_margin": 0.17,
    "jsv_min": 70000000,
    "jbv_margin": 0.17,
    "jbv_min": 70000000,
}
final_filter = (
    jsv > filter_values["jsv_min"]
    and jsv_sell_margin > filter_values["jsv_margin"]
) or (
    jbv > filter_values["jbv_min"]
    and jbv_sell_margin > filter_values["jbv_margin"]
)
```

The value `final_filter` will be applied to all rows of the processed data.

# Disclaimer about Fetching History

History is currently being worked on. It is recommended to set `INCLUDE_HISTORY = False` at the moment, otherwise there will be errors.

History fetching may need to be changed, and it's scope may need to be re-assessed, given that fetching all active items in a market hub may take 30-40 minutes at the current rate limit. If only fetching history per-market, it will take around 8-10 minutes to fetch. Either way, it will take some time to get said market history, so will have a rethink about how to best approach this.

## Rate Limiting Will Cause Errors

There is some rate limiting going on on the EVE API, currently set at [300 requests per minute](https://forums.eveonline.com/t/esi-market-history-endpoint/387151/45#:~:text=The%20endpoint%20is%20tentatively%20limited%20to%20300%20requests%20per%20minute%20per%20IP%20address.%20The%20rate%20limit%20is%20subject%20to%20review%20at%20any%20time%2C%20and%20we%20will%20update%20according%20if%20and%20when%20a%20change%20is%20made%20such%20that%20all%20third%2Dparty%20developers%20can%20adjust%20their%20apps%20accordingly.) . This puts a damper on using `requests-futures` `FutureSession(max_worker=50)`.

Requests to the API start to work as soon as the `session.get(url)` starts, and since we're doing all of them in batch, the `response.result()` may hit the rate limit, but it's too late for us to action, as it's setup to work for a non-rate limited end point, like the market orders value.

Because of this, the error handling, specifically the `x-esi-error-limit-reset` value which would allow us to wait for the rate limit reset, doesn't work quite right.

This will need to be fixed in order to have all of this properly work.

## Time to Fetch Data

All data until now is fetched in parallel via `requests-futures`.

There are ~13000 unique active items in Jita at the moment. Each item has a history. And at 300 history requests per second, fetching all the data for all active items in Jita would take about 43 minutes and 20 seconds in the worst case scenario.

Processed items with current filters comparing Amarr to Jita, which whittles down items to dig deeper into, are around ~3000, which would take around 10 minutes.

Assuming 8 minutes for the other 3 remaining highsec markets, it would take about 34 minutes total to fetch the history of interesting items in all markets.
