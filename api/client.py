from concurrent.futures import Future, as_completed
from dataclasses import dataclass
from time import sleep

from requests import HTTPError, RequestException, Response
from requests_futures.sessions import FuturesSession

from config import user_agent

session = FuturesSession(max_workers=160)
session.headers.update(user_agent)

# set true to see informational error information for troubleshooting only.
PRINT_INFORMATIONAL_ERR_LIMITS = False
ERR_MIN_THRESHOLD = 10


@dataclass
class FutureResults:
    results: list[Response]
    redo_urls: list[str]
    error_timer: int


@dataclass
class UrlJsonHeader:
    url: str
    ids: list[int]
    header: dict[str, str]


def create_futures(urls: list[str]) -> list[Future]:
    all_futures: list[Future] = []
    for url in urls:
        future: Future = session.get(url)
        all_futures.append(future)
    return all_futures


def create_history_futures(urls: list[str]) -> list[Future]:
    # Gets future of https://developers.eveonline.com/api-explorer#/operations/GetMarketsRegionIdHistory
    all_futures: list[Future] = []
    history_session = FuturesSession(max_workers=160)
    history_session.headers.update(user_agent)
    for url in urls:
        future: Future = history_session.get(url)
        all_futures.append(future)
    return all_futures


def create_post_futures(urls_json_headers: list[UrlJsonHeader]) -> list[Future]:
    all_futures: list[Future] = []
    for url_json_header in urls_json_headers:
        url: str = url_json_header.url
        # TODO: `header` can probably be de-duplicated. If we know we are create post
        #   futures, we don't need to add the headers to every URL. Needs to be changed
        #   in `create_name_urls_json_headers` in `api.urls`
        ids: list[int] = url_json_header.ids
        header: dict[str, str] = url_json_header.header
        future: Future = session.post(url, json=ids, headers=header)
        all_futures.append(future)
    return all_futures


def pause_futures(error_timer: int, message: str) -> None:
    if error_timer != 0:
        print(message)
        sleep(error_timer + 1)


# Generic function that resolves futures results with some error handling that returns
#   the raw output from the
#   requested endpoint used in other functions like deserialize_order_items,
#   deserialize_history, and deserialize_order_names
def futures_results(futures: list[Future]) -> FutureResults:
    fr = FutureResults(
        results=[],
        redo_urls=[],
        error_timer=0,
    )
    for response in as_completed(futures):
        result: Response = response.result()
        try:
            result.raise_for_status()
            if "x-esi-error-limit-remain" in result.headers:
                error_limit_remaining: str = result.headers["x-esi-error-limit-remain"]
                if error_limit_remaining != "100" and PRINT_INFORMATIONAL_ERR_LIMITS:
                    error_limit_time_to_reset: str = result.headers[
                        "x-esi-error-limit-reset"
                    ]
                    print(
                        f"INFORMATIONAL: Though no error, for {result.url} "
                        f"the Error Limit Remaining: {error_limit_remaining} "
                        f"Limit-Rest {error_limit_time_to_reset} \n\n"
                    )
        except HTTPError:
            print(
                f"Received status code {result.status_code} from {result.url} With "
                f"headers:\n{str(result.headers)}, and result.text {result.text} of "
                f"type {type(result.text)}\n"
            )
            if "x-esi-error-limit-remain" in result.headers:
                error_limit_remaining: str = result.headers["x-esi-error-limit-remain"]
                error_limit_time_to_reset: str = result.headers[
                    "x-esi-error-limit-reset"
                ]
                print(
                    f"Error Limit Remaining: {error_limit_remaining} Limit-Rest "
                    f"{error_limit_time_to_reset} \n"
                )
                print("\n")
                if (
                    int(error_limit_remaining) < ERR_MIN_THRESHOLD
                    and int(error_limit_time_to_reset) >= 1
                ):
                    fr.error_timer = int(error_limit_time_to_reset)
            if ("Type not found!" not in result.text) and (
                "Type not tradable on market!" not in result.text
            ):
                redo_url: str = result.url
                fr.redo_urls.append(redo_url)
            else:
                print(f"Not added to redo_urls due to {result.text} output\n")
            continue
        except RequestException as e:
            print(f"other error is {e} from {result.url}")
            continue
        fr.results.append(result)
    return fr
