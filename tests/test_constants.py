import time
from unittest.mock import patch

from processing.constants import (
    find_last_downtime,
    is_saved_market_history_data_stale,
)


class TestFindLastDowntime:
    def test_returns_timestamp(self):
        """Verify find_last_downtime returns a valid timestamp."""
        result = find_last_downtime()
        assert isinstance(result, float)
        assert result > 0


class TestIsSavedMarketHistoryDataStale:
    @patch("processing.constants.os.path.exists")
    @patch("processing.constants.os.path.getctime")
    def test_returns_true_when_file_not_exists(self, mock_getctime, mock_exists):
        """Verify returns True when file doesn't exist."""
        mock_exists.return_value = False

        result = is_saved_market_history_data_stale()

        assert all(val is True for val in result.values())

    @patch("processing.constants.os.path.exists")
    @patch("processing.constants.os.path.getctime")
    def test_returns_true_when_file_stale(self, mock_getctime, mock_exists):
        """Verify returns True when file is older than last downtime."""
        mock_exists.return_value = True
        mock_getctime.return_value = time.time() - 86400

        with patch("processing.constants.LAST_DOWNTIME", time.time()):
            result = is_saved_market_history_data_stale()

        assert all(val is True for val in result.values())

    @patch("processing.constants.os.path.exists")
    @patch("processing.constants.os.path.getctime")
    def test_returns_false_when_file_fresh(self, mock_getctime, mock_exists):
        """Verify returns False when file is newer than last downtime."""
        mock_exists.return_value = True
        mock_getctime.return_value = time.time()

        with patch("processing.constants.LAST_DOWNTIME", time.time() - 86400):
            result = is_saved_market_history_data_stale()

        assert all(val is False for val in result.values())
