
from config import DATA_DIR, MAX_WORKERS, region_hubs, version


def test_config_loads_region_hubs():
    """Verify region_hubs loads with expected structure."""
    assert isinstance(region_hubs, dict)
    assert len(region_hubs) > 0
    assert "Jita" in region_hubs


def test_config_region_hubs_structure():
    """Verify each region has correct structure [region_id, station_id, toon_name]."""
    for _region, data in region_hubs.items():
        assert isinstance(data, list)
        assert len(data) == 3
        assert isinstance(data[0], str)  # region_id
        assert isinstance(data[1], str)  # station_id
        assert isinstance(data[2], str)  # toon_name


def test_config_has_max_workers():
    """Verify MAX_WORKERS is set."""
    assert isinstance(MAX_WORKERS, int)
    assert MAX_WORKERS > 0


def test_config_has_data_dir():
    """Verify DATA_DIR is set."""
    assert isinstance(DATA_DIR, str)
    assert len(DATA_DIR) > 0


def test_config_has_version():
    """Verify version is set."""
    assert isinstance(version, str)
    assert len(version) > 0
