import json

from requests import Response

import api.client as cl
import api.urls as u
from processing.constants import All_order_history


def deserialize_history_chunk(
    history_urls: list[list[str]], histories: All_order_history
) -> tuple[All_order_history, list[str]]:
    for history_chunk in history_urls:
        fr = cl.futures_results(cl.create_history_futures(history_chunk))
        parse_history_results(fr.results, histories)
        cl.pause_futures(
            fr.error_timer,
            f"Sleep history fetch due to error timer being {fr.error_timer} seconds",
        )
        while len(fr.redo_urls) != 0:
            fr = cl.futures_results(cl.create_history_futures(fr.redo_urls))
            parse_history_results(fr.results, histories)
            cl.pause_futures(
                fr.error_timer,
                f"Sleep history fetch due to error timer being {fr.error_timer} "
                "seconds",
            )
    return histories, fr.redo_urls


# Deserializes resulting JSON specifically from history futures, used in
#  `get_source_data`
def deserialize_history(region: str, item_ids: list[int]) -> All_order_history:
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


def parse_history_results(
    results: list[Response], histories: All_order_history
) -> None:
    for result in results:
        result_item_id = int(result.url.split("=")[-1])
        item_history = json.loads(result.text)
        histories[result_item_id] = item_history
