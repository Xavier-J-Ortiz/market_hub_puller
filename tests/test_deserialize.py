import json
from unittest.mock import MagicMock, patch

import pytest

from processing.constants import NameData, VolumetricData
from processing.deserialize import (
    deserialize_order_items,
    deserialize_order_items_p2_onwards,
    deserialize_order_names,
    deserialize_volumetric_data,
    find_name,
    update_names_with_volumetric_data,
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


class TestDeserializeVolumetricData:
    def test_returns_empty_dict_for_empty_ids(self):
        """Verify returns empty dict when ids list is empty."""
        result = deserialize_volumetric_data([])
        assert result == {}

    @patch("processing.deserialize.cl")
    def test_parses_esi_response_correctly(self, mock_cl):
        """Verify correctly parses ESI type info response."""
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "type_id": 34,
            "volume": 0.01,
            "packaged_volume": 0.01,
        })

        mock_fr = MagicMock()
        mock_fr.results = [mock_response]
        mock_fr.redo_urls = []
        mock_fr.error_timer = 0
        mock_cl.create_futures.return_value = [MagicMock()]
        mock_cl.futures_results.return_value = mock_fr

        result = deserialize_volumetric_data([34])

        assert 34 in result
        assert result[34].type_id == 34
        assert result[34].volume == 0.01
        assert result[34].packaged_volume == 0.01

    @patch("processing.deserialize.cl")
    def test_handles_json_decode_error(self, mock_cl):
        """Verify gracefully handles invalid JSON response."""
        mock_response = MagicMock()
        mock_response.text = "not valid json"

        mock_fr = MagicMock()
        mock_fr.results = [mock_response]
        mock_fr.redo_urls = []
        mock_fr.error_timer = 0
        mock_cl.create_futures.return_value = [MagicMock()]
        mock_cl.futures_results.return_value = mock_fr

        result = deserialize_volumetric_data([34])

        assert result == {}

    @patch("processing.deserialize.cl")
    def test_handles_redo_urls(self, mock_cl):
        """Verify correctly handles retry requests for failed URLs."""
        mock_response1 = MagicMock()
        mock_response1.text = json.dumps({
            "type_id": 34,
            "volume": 0.01,
            "packaged_volume": 0.01,
        })
        mock_response2 = MagicMock()
        mock_response2.text = json.dumps({
            "type_id": 35,
            "volume": 0.02,
            "packaged_volume": 0.02,
        })

        mock_fr = MagicMock()
        mock_fr.results = [mock_response1]
        mock_fr.redo_urls = ["http://retry-url"]
        mock_fr.error_timer = 0
        mock_cl.create_futures.return_value = [MagicMock()]
        mock_cl.futures_results.side_effect = [
            mock_fr,
            MagicMock(results=[mock_response2], redo_urls=[], error_timer=0),
        ]

        result = deserialize_volumetric_data([34, 35])

        assert 34 in result
        assert 35 in result
        assert result[35].volume == 0.02


class TestUpdateNamesWithVolumetricData:
    def test_updates_names_with_volume_data(self):
        """Verify names are updated with volumetric data when type_id matches."""
        names = [
            NameData(category="inventory_type", id=34, name="Tritanium"),
            NameData(category="inventory_type", id=35, name="Pyerite"),
        ]
        volumetric_data = {
            34: VolumetricData(type_id=34, volume=0.01, packaged_volume=0.01),
        }

        result = update_names_with_volumetric_data(names, volumetric_data)

        assert result[0].volume == 0.01
        assert result[0].packaged_volume == 0.01
        assert result[1].volume is None
        assert result[1].packaged_volume is None

    def test_returns_original_names_when_no_volumetric_data(self):
        """Verify returns original names when no volumetric data provided."""
        names = [
            NameData(category="inventory_type", id=34, name="Tritanium"),
        ]
        volumetric_data: dict[int, VolumetricData] = {}

        result = update_names_with_volumetric_data(names, volumetric_data)

        assert len(result) == 1
        assert result[0].name == "Tritanium"
        assert result[0].volume is None
        assert result[0].packaged_volume is None

    def test_handles_mixed_case(self):
        """Verify handles mixed case where some items have volume data."""
        names = [
            NameData(category="inventory_type", id=34, name="Tritanium"),
            NameData(category="inventory_type", id=35, name="Pyerite"),
            NameData(category="inventory_type", id=36, name="Mexallon"),
        ]
        volumetric_data = {
            34: VolumetricData(type_id=34, volume=0.01, packaged_volume=0.01),
            36: VolumetricData(type_id=36, volume=0.5, packaged_volume=0.5),
        }

        result = update_names_with_volumetric_data(names, volumetric_data)

        assert result[0].volume == 0.01
        assert result[1].volume is None
        assert result[2].volume == 0.5
