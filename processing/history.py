import json

import api.client as cl
import api.urls as u


def deserialize_history_chunk(history_urls, histories):
    for history_chunk in history_urls:
        results, redo_urls, error_timer = cl.futures_results(
            cl.create_history_futures(history_chunk)
        )
        parse_history_results(results, histories)
        cl.pause_futures(
            error_timer,
            f"Sleep history fetch due to error timer being {error_timer} seconds",
        )
        while len(redo_urls) != 0:
            addtl_results, redo_urls, error_timer = cl.futures_results(
                cl.create_history_futures(redo_urls)
            )
            parse_history_results(addtl_results, histories)
            cl.pause_futures(
                error_timer,
                f"Sleep history fetch due to error timer being {error_timer} seconds",
            )
    return histories, redo_urls


# Deserializes resulting JSON specifically from history futures, used in
#  `get_source_data`
def deserialize_history(region, item_ids):
    history_urls = []
    histories = {}
    chunk_length = 30000
    for idx, item_id in enumerate(item_ids):
        history_url = u.create_item_history_url(region, item_id)
        if idx % chunk_length == 0:
            history_urls.append([])
        history_urls[idx // chunk_length].append(history_url)
        histories[item_id] = []
    # Only need histories data at this point, so only what's in index zero
    histories = deserialize_history_chunk(history_urls, histories)[0]
    return histories


def parse_history_results(results, histories):
    for result in results:
        result_item_id = int(result.url.split("=")[-1])
        item_history = json.loads(result.text)
        histories[result_item_id] = item_history
