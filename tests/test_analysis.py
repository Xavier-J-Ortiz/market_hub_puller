import math
from unittest.mock import patch

import pytest

from config import region_hubs
from processing.analysis import (
    add_history_to_processed_data,
    min_max_source_data,
    process_filtered_data,
    remove_bad_orders,
    remove_bad_orders_names,
)
from processing.constants import (
    GlobalOrders,
    ItemHistory,
    NameData,
    Regional_actionable_data,
    Regional_min_max,
    RegionOrdersData,
)


class TestRemoveBadOrdersNames:
    def test_removes_blueprints(self):
        """Verify blueprints are filtered out."""
        names = [
            NameData(category="inventory_type", id=1, name="Tritanium"),
            NameData(category="inventory_type", id=2, name="Tritanium Blueprint"),
        ]
        global_orders: GlobalOrders = {
            "Jita": RegionOrdersData(
                all_orders_data=[],
                active_order_names=names,
                all_order_history=[],
            )
        }

        result = remove_bad_orders_names(global_orders, "Jita")

        assert len(result) == 1
        assert result[0].name == "Tritanium"

    def test_removes_expired(self):
        """Verify expired items are filtered out."""
        names = [
            NameData(category="inventory_type", id=1, name="Tritanium"),
            NameData(category="inventory_type", id=2, name="Expired: Some Item"),
        ]
        global_orders: GlobalOrders = {
            "Jita": RegionOrdersData(
                all_orders_data=[],
                active_order_names=names,
                all_order_history=[],
            )
        }

        result = remove_bad_orders_names(global_orders, "Jita")

        assert len(result) == 1
        assert result[0].name == "Tritanium"

    def test_removes_ore_processing(self):
        """Verify ore processing items are filtered out."""
        names = [
            NameData(category="inventory_type", id=1, name="Tritanium"),
            NameData(category="inventory_type", id=2, name="Arkonor Processing"),
            NameData(category="inventory_type", id=3, name="Mercoxit Processing"),
            NameData(category="inventory_type", id=4, name="Crocite"),
        ]
        global_orders: GlobalOrders = {
            "Jita": RegionOrdersData(
                all_orders_data=[],
                active_order_names=names,
                all_order_history=[],
            )
        }

        result = remove_bad_orders_names(global_orders, "Jita")

        names_remaining = [n.name for n in result]
        assert "Tritanium" in names_remaining
        assert "Crocite" in names_remaining
        assert "Arkonor Processing" not in names_remaining
        assert "Mercoxit Processing" not in names_remaining

    def test_keeps_valid_items(self):
        """Verify valid items are kept."""
        names = [
            NameData(category="inventory_type", id=1, name="Tritanium"),
            NameData(category="inventory_type", id=2, name="Pyerite"),
            NameData(category="inventory_type", id=3, name="Mexallon"),
            NameData(category="inventory_type", id=4, name="Isogen"),
        ]
        global_orders: GlobalOrders = {
            "Jita": RegionOrdersData(
                all_orders_data=[],
                active_order_names=names,
                all_order_history=[],
            )
        }

        result = remove_bad_orders_names(global_orders, "Jita")

        assert len(result) == 4

    def test_raises_on_invalid_name_type(self):
        """Verify TypeError is raised when name is not a string."""
        names = [
            NameData(category="inventory_type", id=1, name=12345),  # type: ignore
        ]
        global_orders: GlobalOrders = {
            "Jita": RegionOrdersData(
                all_orders_data=[],
                active_order_names=names,
                all_order_history=[],
            )
        }

        with pytest.raises(TypeError, match="not of type `str`"):
            remove_bad_orders_names(global_orders, "Jita")


class TestRemoveBadOrders:
    def test_removes_blueprints_and_expired(self):
        """Verify remove_bad_orders removes bad orders."""
        orders = [
            {
                "type_id": 1,
                "is_buy_order": False,
                "location_id": 60003760,
                "price": 100.0,
            },
            {
                "type_id": 2,
                "is_buy_order": False,
                "location_id": 60003760,
                "price": 200.0,
            },
        ]
        names = [
            NameData(category="inventory_type", id=1, name="Tritanium"),
            NameData(category="inventory_type", id=2, name="Tritanium Blueprint"),
        ]
        global_orders: GlobalOrders = {
            "Jita": RegionOrdersData(
                all_orders_data=orders,
                active_order_names=names,
                all_order_history=[],
            )
        }

        result = remove_bad_orders(global_orders, "Jita", [1, 2])

        assert len(result[0]) == 1
        assert len(result[1]) == 1
        assert result[1][0].name == "Tritanium"


class TestMinMaxSourceData:
    def test_finds_min_sell_and_max_buy(self):
        """Verify min_max_source_data captures correct orders."""
        jita_location = int(region_hubs["Jita"][1])
        orders = [
            {
                "type_id": 1,
                "is_buy_order": False,
                "location_id": jita_location,
                "price": 100.0,
            },
            {
                "type_id": 1,
                "is_buy_order": False,
                "location_id": jita_location,
                "price": 90.0,
            },
            {
                "type_id": 1,
                "is_buy_order": True,
                "location_id": jita_location,
                "price": 80.0,
            },
            {
                "type_id": 1,
                "is_buy_order": True,
                "location_id": jita_location,
                "price": 85.0,
            },
        ]
        names = [NameData(category="inventory_type", id=1, name="Tritanium")]
        global_orders: GlobalOrders = {
            "Jita": RegionOrdersData(
                all_orders_data=orders,
                active_order_names=names,
                all_order_history=[],
            )
        }
        regional_min_max: Regional_min_max = {}

        min_max_source_data("Jita", global_orders, regional_min_max)

        assert "Jita" in regional_min_max
        assert 1 in regional_min_max["Jita"]
        min_data = regional_min_max["Jita"][1]
        assert min_data["min"]["price"] == 90.0
        assert min_data["max"]["price"] == 85.0
        assert min_data["name"] == "Tritanium"


class TestProcessFilteredData:
    def test_filters_and_processes_data(self):
        """Verify process_filtered_data filters and processes."""
        jita_location = int(region_hubs["Jita"][1])
        amarr_location = int(region_hubs["Amarr"][1])
        jita_orders = [
            {
                "type_id": 1,
                "is_buy_order": False,
                "location_id": jita_location,
                "price": 80000000.0,
            },
        ]
        amarr_orders = [
            {
                "type_id": 1,
                "is_buy_order": False,
                "location_id": amarr_location,
                "price": 120000000.0,
            },
        ]
        names = [NameData(category="inventory_type", id=1, name="Tritanium")]
        global_orders: GlobalOrders = {
            "Jita": RegionOrdersData(
                all_orders_data=jita_orders,
                active_order_names=names,
                all_order_history=[],
            ),
            "Amarr": RegionOrdersData(
                all_orders_data=amarr_orders,
                active_order_names=names,
                all_order_history=[],
            ),
        }
        regional_min_max: Regional_min_max = {
            "Jita": {1: {"min": jita_orders[0], "name": "Tritanium"}},
            "Amarr": {1: {"min": amarr_orders[0], "name": "Tritanium"}},
        }
        actionable_data: Regional_actionable_data = {}

        process_filtered_data("Amarr", regional_min_max, actionable_data, global_orders)

        assert "Amarr" in actionable_data
        assert "Tritanium" in actionable_data["Amarr"]
        data = actionable_data["Amarr"]["Tritanium"]
        assert data["diff"] == 40000000.0
        assert not math.isnan(data["jsv_sell_margin"])


class TestAddHistoryToProcessedData:
    def test_adds_history_when_stale(self):
        """Verify add_history_to_processed_data adds history."""
        history = ItemHistory(type_id=1, history=[])
        global_orders: GlobalOrders = {
            "Jita": RegionOrdersData(
                all_orders_data=[],
                active_order_names=[],
                all_order_history=[history],
            )
        }
        actionable_data: Regional_actionable_data = {
            "Jita": {"Tritanium": {"name": "Tritanium", "id": 1}}
        }

        with patch("processing.analysis.df") as mock_df:
            mock_df.ARE_SAVED_MARKETS_STALE = {"Jita": True}
            add_history_to_processed_data(
                global_orders, "Jita", actionable_data, "Tritanium", 1
            )

        assert "history" in actionable_data["Jita"]["Tritanium"]
        assert actionable_data["Jita"]["Tritanium"]["history"] == []

    def test_sets_none_when_not_stale_and_no_history(self):
        """Verify history is None when not stale and no history."""
        global_orders: GlobalOrders = {
            "Jita": RegionOrdersData(
                all_orders_data=[],
                active_order_names=[],
                all_order_history=[],
            )
        }
        actionable_data: Regional_actionable_data = {
            "Jita": {"Tritanium": {"name": "Tritanium", "id": 999}}
        }

        with patch("processing.analysis.df") as mock_df:
            mock_df.ARE_SAVED_MARKETS_STALE = {"Jita": False}
            add_history_to_processed_data(
                global_orders, "Jita", actionable_data, "Tritanium", 999
            )

        assert actionable_data["Jita"]["Tritanium"]["history"] is None
