from concurrent.futures import as_completed
from time import sleep

from requests import HTTPError, RequestException
from requests_futures.sessions import FuturesSession

session = FuturesSession(max_workers=160)

# set true to see informational error information for troubleshooting only.
PRINT_INFORMATIONAL_ERR_LIMITS = False
ERR_MIN_THRESHOLD = 10


def create_futures(urls):
    all_futures = []
    for url in urls:
        future = session.get(url)
        all_futures.append(future)
    return all_futures


def create_history_futures(urls):
    all_futures = []
    history_session = FuturesSession(max_workers=160)
    for url in urls:
        future = history_session.get(url)
        all_futures.append(future)
    return all_futures


def create_post_futures(urls_json_headers):
    all_futures = []
    for url_json_header in urls_json_headers:
        url = url_json_header[0]
        ids = url_json_header[1]
        header = url_json_header[2]
        future = session.post(url, json=ids, headers=header)
        all_futures.append(future)
    return all_futures


def pause_futures(error_timer, message):
    if error_timer != 0:
        print(message)
        sleep(error_timer + 1)


# Generic function that resolves futures results with some error handling that returns
#   the raw output from the
#   requested endpoint used in other functions like deserialize_order_items,
#   deserialize_history, and deserialize_order_names
def futures_results(futures):
    results = []
    redo_urls = []
    error_timer = 0
    for response in as_completed(futures):
        result = response.result()
        try:
            result.raise_for_status()
            error_limit_remaining = result.headers["x-esi-error-limit-remain"]
            if error_limit_remaining != "100" and PRINT_INFORMATIONAL_ERR_LIMITS:
                error_limit_time_to_reset = result.headers["x-esi-error-limit-reset"]
                print(
                    f"INFORMATIONAL: Though no error, for {result.url} the Error Limit "
                    f"Remaning: {error_limit_remaining} Limit-Rest "
                    f"{error_limit_time_to_reset} \n\n"
                )
        except HTTPError:
            print(
                f"Received status code {result.status_code} from {result.url} With "
                f"headers:\n{str(result.headers)}, and result.text {result.text} of "
                f"type {type(result.text)}\n"
            )
            if "x-esi-error-limit-remain" in result.headers:
                error_limit_remaining = result.headers["x-esi-error-limit-remain"]
                error_limit_time_to_reset = result.headers["x-esi-error-limit-reset"]
                print(
                    f"Error Limit Remaining: {error_limit_remaining} Limit-Rest "
                    f"{error_limit_time_to_reset} \n"
                )
                print("\n")
                if (
                    int(error_limit_remaining) < ERR_MIN_THRESHOLD
                    and int(error_limit_time_to_reset) >= 1
                ):
                    error_timer = error_limit_time_to_reset
            if ("Type not found!" not in result.text) and (
                "Type not tradable on market!" not in result.text
            ):
                redo_url = result.url
                redo_urls.append(redo_url)
            else:
                print(f"Not added to redo_urls due to {result.text} output\n")
            continue
        except RequestException as e:
            print(f"other error is {e} from {result.url}")
            continue
        results.append(result)
    return results, redo_urls, int(error_timer)
