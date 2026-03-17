import csv
import gzip

from processing.csv import data_to_csv_gz


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
