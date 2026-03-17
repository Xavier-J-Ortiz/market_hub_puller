import pytest

from processing.analysis import remove_bad_orders_names
from processing.constants import GlobalOrders, NameData, RegionOrdersData


class TestRemoveBadOrders:
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
