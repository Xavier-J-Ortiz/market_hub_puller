import json
from dataclasses import field

from requests import Response

import api.client as cl
import api.urls as u
from processing.constants import ItemHistory


def deserialize_history_chunk(
    history_urls: list[list[str]], histories: list[ItemHistory]
) -> tuple[list[ItemHistory], list[str]]:
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
def deserialize_history(region: str, item_ids: list[int]) -> list[ItemHistory]:
    history_urls = []
    # old {1234: <list of history data points>}
    # histories = {}
    histories: list[ItemHistory] = []
    chunk_length = 30000
    for idx, item_id in enumerate(item_ids):
        history_url = u.create_item_history_url(region, item_id)
        if idx % chunk_length == 0:
            history_urls.append([])
        history_urls[idx // chunk_length].append(history_url)
        histories.append(
            ItemHistory(type_id=item_id, history=field(default_factory=list))
        )
    # Only need histories data at this point, so only what's in index zero
    histories: list[ItemHistory] = deserialize_history_chunk(history_urls, histories)[0]
    return histories


def parse_history_results(
    results: list[Response], histories: list[ItemHistory]
) -> None:
    for result in results:
        result_item_id = int(result.url.split("=")[-1])
        item_history = json.loads(result.text)
        # TODO: Investigate if there is a better way to do this
        for ih in histories:
            if ih.type_id == result_item_id:
                ih.history = item_history
