import json
from unittest.mock import MagicMock, patch

import pytest

from processing.constants import NameData
from processing.deserialize import (
    deserialize_order_items,
    deserialize_order_items_p2_onwards,
    deserialize_order_names,
    find_name,
)


class TestFindName:
    def test_finds_name_by_id(self):
        """Verify find_name returns correct NameData for given type_id."""
        names = [
            NameData(category="inventory_type", id=1, name="Tritanium"),
            NameData(category="inventory_type", id=2, name="Pyerite"),
        ]
        result = find_name(2, names, "Jita")
        assert result.id == 2
        assert result.name == "Pyerite"

    def test_raises_when_id_not_found(self):
        """Verify find_name raises LookupError when type_id not found."""
        names = [NameData(category="inventory_type", id=1, name="Tritanium")]
        with pytest.raises(LookupError, match="Could not find the type_id: 999"):
            find_name(999, names, "Jita")


class TestDeserializeOrderItemsP2Onwards:
    def test_returns_empty_when_single_page(self):
        """Verify returns empty results when total_pages is 1."""
        result, redo_urls = deserialize_order_items_p2_onwards(
            "Jita", 1, [], lambda r, p: f"url{p}"
        )
        assert result == []
        assert redo_urls == []

    @patch("processing.deserialize.cl")
    def test_processes_multiple_pages(self, mock_cl):
        """Verify processes pages 2 onwards correctly."""
        mock_response = MagicMock()
        mock_response.text = json.dumps([{"type_id": 1, "price": 100.0}])

        mock_fr = MagicMock()
        mock_fr.results = [mock_response]
        mock_fr.redo_urls = []
        mock_fr.error_timer = 0
        mock_cl.create_futures.return_value = [MagicMock()]
        mock_cl.futures_results.return_value = mock_fr

        result, redo_urls = deserialize_order_items_p2_onwards(
            "Jita", 2, [], lambda r, p: f"url{p}"
        )
        assert len(result) == 1
        assert redo_urls == []


class TestDeserializeOrderItems:
    @patch("processing.deserialize.deserialize_order_item_p1")
    @patch("processing.deserialize.deserialize_order_items_p2_onwards")
    def test_calls_p1_and_p2(self, mock_p2, mock_p1):
        """Verify deserialize_order_items calls p1 then p2."""
        mock_p1.return_value = ([{"type_id": 1}], 2)
        mock_p2.return_value = ([{"type_id": 1}, {"type_id": 2}], [])

        result, redo_urls = deserialize_order_items(
            "Jita", [], lambda r, p: f"url{p}"
        )
        assert len(result) == 2
        mock_p1.assert_called_once()
        mock_p2.assert_called_once()


class TestDeserializeOrderNames:
    @patch("processing.deserialize.cl")
    def test_deserializes_names_from_post(self, mock_cl):
        """Verify deserialize_order_names correctly parses POST response."""
        mock_response = MagicMock()
        mock_response.text = json.dumps([
            {"category": "inventory_type", "id": 1, "name": "Tritanium"},
            {"category": "inventory_type", "id": 2, "name": "Pyerite"},
        ])

        mock_fr = MagicMock()
        mock_fr.results = [mock_response]
        mock_cl.create_post_futures.return_value = [MagicMock()]
        mock_cl.futures_results.return_value = mock_fr

        with patch(
            "processing.deserialize.u.create_name_urls_json_headers"
        ) as mock_urls:
            mock_urls.return_value = [
                MagicMock(url="url", ids=[1, 2], header={})
            ]
            result = deserialize_order_names([1, 2])

        assert len(result) == 2
        assert result[0].name == "Tritanium"
        assert result[1].name == "Pyerite"
