# Market Hub Puller

Effort to consume EVE Online's ESI for sorting out items.
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

## Adding additional filters.
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
