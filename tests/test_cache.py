import csv
import gzip
from unittest.mock import MagicMock, patch

from processing.cache import find_missing_orders, load_history_cache
from processing.constants import GlobalOrders, ItemHistory, RegionOrdersData


class TestLoadHistoryCache:
    def test_loads_history_from_gzip_csv(self, tmp_path):
        """Verify load_history_cache correctly reads gzipped CSV."""
        history_file = tmp_path / "test_history.csv.gz"
        history_data = [
            {
                "type_id": 34,
                "history": (
                    '[{"average": 100.0, "date": "2025-01-01", "highest": '
                    '110.0, "lowest": 90.0, "order_count": 50, "volume": 1000}]'
                ),
            },
        ]

        with gzip.open(history_file, "wt") as f:
            writer = csv.DictWriter(f, fieldnames=["type_id", "history"])
            writer.writeheader()
            writer.writerows(history_data)

        with patch("processing.cache.ItemHistory") as mock_item:
            mock_item.side_effect = lambda type_id, history: ItemHistory(
                type_id=int(type_id), history=history
            )
            with patch("processing.cache.DataclassReader") as mock_reader:
                mock_reader.return_value = [
                    ItemHistory(type_id=34, history=[])
                ]
                result = load_history_cache("Jita", str(history_file))

        assert len(result) == 1
        assert result[0].type_id == 34


class TestFindMissingOrders:
    @patch("processing.cache.hs")
    @patch("processing.cache.df")
    @patch("processing.cache.os")
    def test_finds_and_fetches_missing_orders(
        self, mock_os, mock_df, mock_hs, tmp_path
    ):
        """Verify find_missing_orders fetches missing item IDs."""
        mock_os.path.exists.return_value = True
        mock_os.path.getsize.return_value = 100

        existing_history = ItemHistory(type_id=34, history=[])
        missing_history = ItemHistory(type_id=35, history=[])

        global_orders: GlobalOrders = {
            "Jita": RegionOrdersData(
                all_orders_data=[],
                active_order_names=[],
                all_order_history=[existing_history],
            )
        }

        mock_hs.deserialize_history.return_value = [missing_history]

        history_file = tmp_path / "jita_history.csv.gz"
        history_file.touch()

        with patch("builtins.open", MagicMock()):
            find_missing_orders(
                "Jita", global_orders, [34, 35], str(history_file)
            )

        assert len(global_orders["Jita"].all_order_history) == 2
        mock_hs.deserialize_history.assert_called_once_with(
            "10000002", [35]
        )

    @patch("processing.cache.hs")
    @patch("processing.cache.df")
    @patch("processing.cache.os")
    def test_no_missing_orders(self, mock_os, mock_df, mock_hs):
        """Verify find_missing_orders does nothing when no missing orders."""
        mock_os.path.exists.return_value = True
        mock_os.path.getsize.return_value = 100

        existing_history = ItemHistory(type_id=34, history=[])
        global_orders: GlobalOrders = {
            "Jita": RegionOrdersData(
                all_orders_data=[],
                active_order_names=[],
                all_order_history=[existing_history],
            )
        }

        history_file = "/tmp/test.csv.gz"

        find_missing_orders("Jita", global_orders, [34], history_file)

        mock_hs.deserialize_history.assert_not_called()
