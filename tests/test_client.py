from unittest.mock import MagicMock, patch

from requests import HTTPError

from api.client import (
    FutureResults,
    UrlJsonHeader,
    create_futures,
    create_history_futures,
    create_post_futures,
    futures_results,
)


class TestCreateFutures:
    def test_create_futures_returns_list(self):
        """Verify create_futures returns a list of Future objects."""
        urls = ["http://example1.com", "http://example2.com"]

        with patch("api.client.session") as mock_session:
            mock_future = MagicMock()
            mock_session.get = MagicMock(return_value=mock_future)

            result = create_futures(urls)

            assert isinstance(result, list)
            assert len(result) == 2

    def test_create_history_futures_returns_list(self):
        """Verify create_history_futures returns list of futures."""
        urls = ["http://history1.com", "http://history2.com"]

        with patch("api.client.FuturesSession") as mock_cls:
            mock_future = MagicMock()
            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_future
            mock_cls.return_value = mock_instance

            result = create_history_futures(urls)

            assert isinstance(result, list)
            assert len(result) == 2

    def test_create_post_futures_returns_list(self):
        """Verify create_post_futures returns list of futures."""
        url_json_headers = [
            UrlJsonHeader(url="http://example.com", ids=[1, 2], header={"key": "value"})
        ]

        with patch("api.client.session") as mock_session:
            mock_future = MagicMock()
            mock_session.post = MagicMock(return_value=mock_future)

            result = create_post_futures(url_json_headers)

            assert isinstance(result, list)
            assert len(result) == 1


class TestFuturesResults:
    def test_handles_empty_list(self):
        """Verify futures_results handles empty list gracefully."""
        result = futures_results([])

        assert isinstance(result, FutureResults)
        assert result.results == []
        assert result.redo_urls == []
        assert result.error_timer == 0

    def test_extracts_successful_results(self):
        """Verify futures_results extracts successful results."""
        mock_response = MagicMock()
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()
        mock_response.url = "http://example.com"

        mock_future = MagicMock()
        mock_future.result.return_value = mock_response

        with patch("api.client.as_completed", return_value=[mock_future]):
            result = futures_results([mock_future])

        assert len(result.results) == 1
        assert result.results[0] == mock_response

    def test_extracts_error_timer(self):
        """Verify futures_results extracts error timer from headers."""
        mock_response = MagicMock()
        mock_response.headers = {
            "x-esi-error-limit-remain": "5",
            "x-esi-error-limit-reset": "30",
        }
        mock_response.raise_for_status = MagicMock(side_effect=HTTPError("HTTP Error"))
        mock_response.text = "Some error"
        mock_response.url = "http://example.com"

        mock_future = MagicMock()
        mock_future.result.return_value = mock_response

        with patch("api.client.as_completed", return_value=[mock_future]):
            result = futures_results([mock_future])

        assert result.error_timer == 30

    def test_adds_to_redo_urls_on_error(self):
        """Verify failed requests (non-type-not-found) added to redo_urls."""
        mock_response = MagicMock()
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock(side_effect=HTTPError("HTTP Error"))
        mock_response.text = "Server error"
        mock_response.url = "http://example.com"

        mock_future = MagicMock()
        mock_future.result.return_value = mock_response

        with patch("api.client.as_completed", return_value=[mock_future]):
            result = futures_results([mock_future])

        assert "http://example.com" in result.redo_urls

    def test_skips_type_not_found(self):
        """Verify 'Type not found!' errors are NOT added to redo_urls."""
        mock_response = MagicMock()
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock(side_effect=HTTPError("HTTP Error"))
        mock_response.text = "Type not found!"
        mock_response.url = "http://example.com"

        mock_future = MagicMock()
        mock_future.result.return_value = mock_response

        with patch("api.client.as_completed", return_value=[mock_future]):
            result = futures_results([mock_future])

        assert "http://example.com" not in result.redo_urls

    def test_skips_not_tradable(self):
        """Verify 'Type not tradable on market!' errors NOT added to redo_urls."""
        mock_response = MagicMock()
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock(side_effect=HTTPError("HTTP Error"))
        mock_response.text = "Type not tradable on market!"
        mock_response.url = "http://example.com"

        mock_future = MagicMock()
        mock_future.result.return_value = mock_response

        with patch("api.client.as_completed", return_value=[mock_future]):
            result = futures_results([mock_future])

        assert "http://example.com" not in result.redo_urls
