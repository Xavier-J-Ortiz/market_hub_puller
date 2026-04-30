import json
from unittest.mock import MagicMock, patch

from processing.constants import HistoryDataPoint, ItemHistory
from processing.history import (
    deserialize_history,
    deserialize_history_chunk,
    parse_history_results,
)


class TestParseHistoryResults:
    def test_parses_valid_history(self):
        """Verify parse_history_results correctly parses history data."""
        histories = [ItemHistory(type_id=34, history=[])]

        mock_response = MagicMock()
        mock_response.url = (
            "https://esi.evetech.net/v3/markets/10000002/history/?type_id=34"
        )
        mock_response.text = json.dumps([
            {
                "average": 100.5,
                "date": "2025-01-01",
                "highest": 110.0,
                "lowest": 90.0,
                "order_count": 50,
                "volume": 1000,
            },
            {
                "average": 101.0,
                "date": "2025-01-02",
                "highest": 111.0,
                "lowest": 91.0,
                "order_count": 55,
                "volume": 1100,
            },
        ])

        parse_history_results([mock_response], histories)

        assert len(histories[0].history) == 2
        assert histories[0].history[0].average == 100.5
        assert histories[0].history[1].date == "2025-01-02"

    def test_skips_empty_text(self):
        """Verify parse_history_results skips responses with empty text."""
        histories = [ItemHistory(type_id=34, history=[])]

        mock_response = MagicMock()
        mock_response.url = (
            "https://esi.evetech.net/v3/markets/10000002/history/?type_id=34"
        )
        mock_response.text = ""

        parse_history_results([mock_response], histories)

        assert len(histories[0].history) == 0

    def test_skips_invalid_json(self):
        """Verify parse_history_results skips invalid JSON."""
        histories = [ItemHistory(type_id=34, history=[])]

        mock_response = MagicMock()
        mock_response.url = (
            "https://esi.evetech.net/v3/markets/10000002/history/?type_id=34"
        )
        mock_response.text = "invalid json"

        parse_history_results([mock_response], histories)

        assert len(histories[0].history) == 0

    def test_handles_non_list_response(self):
        """Verify parse_history_results handles non-list JSON response."""
        histories = [ItemHistory(type_id=34, history=[])]

        mock_response = MagicMock()
        mock_response.url = (
            "https://esi.evetech.net/v3/markets/10000002/history/?type_id=34"
        )
        mock_response.text = json.dumps({"error": "not a list"})

        parse_history_results([mock_response], histories)

        assert len(histories[0].history) == 0

    def test_skips_response_without_url(self):
        """Verify parse_history_results skips responses without URL."""
        histories = [ItemHistory(type_id=34, history=[])]

        mock_response = MagicMock()
        mock_response.url = None

        parse_history_results([mock_response], histories)

        assert len(histories[0].history) == 0


class TestDeserializeHistoryChunk:
    @patch("processing.history.cl")
    def test_deserializes_chunk(self, mock_cl):
        """Verify deserialize_history_chunk processes history URLs."""
        histories = [ItemHistory(type_id=34, history=[])]

        mock_response = MagicMock()
        mock_response.url = (
            "https://esi.evetech.net/v3/markets/10000002/history/?type_id=34"
        )
        mock_response.text = json.dumps([
            {
                "average": 100.0,
                "date": "2025-01-01",
                "highest": 110.0,
                "lowest": 90.0,
                "order_count": 50,
                "volume": 1000,
            },
        ])

        mock_fr = MagicMock()
        mock_fr.results = [mock_response]
        mock_fr.redo_urls = []
        mock_fr.error_timer = 0
        mock_cl.create_history_futures.return_value = [MagicMock()]
        mock_cl.futures_results.return_value = mock_fr

        result, redo_urls = deserialize_history_chunk(
            [["url1"]], histories
        )

        assert len(result[0].history) == 1
        assert redo_urls == []


class TestDeserializeHistory:
    @patch("processing.history.deserialize_history_chunk")
    def test_creates_history_entries(self, mock_chunk):
        """Verify deserialize_history creates ItemHistory for each item."""
        mock_chunk.return_value = (
            [
                ItemHistory(
                    type_id=34,
                    history=[
                        HistoryDataPoint(
                            average=100.0,
                            date="2025-01-01",
                            highest=110.0,
                            lowest=90.0,
                            order_count=50,
                            volume=1000,
                        )
                    ],
                )
            ],
            [],
        )

        with patch("processing.history.u.create_item_history_url") as mock_url:
            mock_url.return_value = "url"
            result = deserialize_history("Jita", [34])

        assert len(result) == 1
        assert result[0].type_id == 34
