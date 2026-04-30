import csv
import gzip
from dataclasses import dataclass

from processing.csv import _to_dict, data_to_csv_gz


def test_data_to_csv_gz_creates_file(tmp_path):
    test_data = [{"name": "item1", "id": 12345}]
    fields = ["name", "id"]

    data_to_csv_gz(test_data, fields, "test.csv.gz", str(tmp_path))

    assert (tmp_path / "test.csv.gz").exists()


def test_data_to_csv_gz_writes_correct_content(tmp_path):
    """Test that the gzipped CSV contains correct headers and data."""
    test_data = [{"name": "item1", "id": 12345}, {"name": "item2", "id": 67890}]
    fields = ["name", "id"]

    data_to_csv_gz(test_data, fields, "test.csv.gz", str(tmp_path))

    with gzip.open(tmp_path / "test.csv.gz", "rt") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert rows[0]["name"] == "item1"
    assert rows[0]["id"] == "12345"
    assert rows[1]["name"] == "item2"


def test_data_to_csv_gz_handles_empty_list(tmp_path):
    """Test that empty list doesn't raise errors."""
    test_data: list[dict[str, object]] = []
    fields = ["name", "id"]

    data_to_csv_gz(test_data, fields, "test.csv.gz", str(tmp_path))

    assert (tmp_path / "test.csv.gz").exists()


def test_data_to_csv_gz_handles_dict_input(tmp_path):
    """Test that dict input (regional data) is handled correctly."""
    test_data = {
        "item1": {"name": "Tritanium", "price": 5.50},
        "item2": {"name": "Pyerite", "price": 2.30},
    }
    fields = ["name", "price"]

    data_to_csv_gz(test_data, fields, "test.csv.gz", str(tmp_path))

    with gzip.open(tmp_path / "test.csv.gz", "rt") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 2
    assert rows[0]["name"] == "Tritanium"


def test_to_dict_handles_dict():
    """Verify _to_dict handles dictionary input."""
    result = _to_dict({"key": "value"})
    assert result == {"key": "value"}


def test_to_dict_handles_dataclass():
    """Verify _to_dict converts dataclass to dict."""
    @dataclass
    class TestData:
        name: str
        id: int

    data = TestData(name="Tritanium", id=34)
    result = _to_dict(data)

    assert result == {"name": "Tritanium", "id": 34}


def test_to_dict_handles_nested_structure():
    """Verify _to_dict handles nested dataclasses."""
    @dataclass
    class Inner:
        value: int

    @dataclass
    class Outer:
        name: str
        inner: Inner

    data = Outer(name="Test", inner=Inner(value=42))
    result = _to_dict(data)

    assert result == {"name": "Test", "inner": {"value": 42}}
