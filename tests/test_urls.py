from api.client import UrlJsonHeader
from api.urls import (
    create_active_items_url,
    create_all_order_url,
    create_item_history_url,
    create_name_urls_json_headers,
)
from processing.constants import ID_SEGMENT_CHUNK


def test_create_all_order_url_format():
    """Verify all order URL is correctly formatted."""
    url = create_all_order_url("10000002", 1)
    assert "esi.evetech.net" in url
    assert "10000002" in url
    assert "orders" in url
    assert "order_type=all" in url
    assert "page=1" in url


def test_create_active_items_url_format():
    """Verify active items URL is correctly formatted."""
    url = create_active_items_url("10000002", 1)
    assert "esi.evetech.net" in url
    assert "10000002" in url
    assert "types" in url
    assert "page=1" in url


def test_create_item_history_url_format():
    """Verify item history URL is correctly formatted."""
    url = create_item_history_url("10000002", 34)
    assert "esi.evetech.net" in url
    assert "10000002" in url
    assert "history" in url
    assert "type_id=34" in url


def test_create_name_urls_json_headers_single_chunk():
    """Verify single chunk when ids <= ID_SEGMENT_CHUNK."""
    ids = [1, 2, 3]
    result = create_name_urls_json_headers(ids)

    assert len(result) == 1
    assert isinstance(result[0], UrlJsonHeader)
    assert result[0].ids == ids
    assert "esi.evetech.net" in result[0].url


def test_create_name_urls_json_headers_multiple_chunks():
    """Verify multiple chunks when ids > ID_SEGMENT_CHUNK."""
    ids = list(range(1, ID_SEGMENT_CHUNK + 500))
    result = create_name_urls_json_headers(ids)

    assert len(result) > 1
    first_chunk_size = len(result[0].ids)
    assert first_chunk_size == ID_SEGMENT_CHUNK


def test_create_name_urls_json_headers_header():
    """Verify header is correctly set."""
    ids = [1, 2]
    result = create_name_urls_json_headers(ids)

    header = result[0].header
    assert "accept" in header
    assert "Content-Type" in header
    assert header["Content-Type"] == "application/json"
