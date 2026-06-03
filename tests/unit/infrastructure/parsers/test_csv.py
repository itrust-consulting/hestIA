from __future__ import annotations

import pytest

from hestia.infrastructure.parsers.csv import CSVParser


@pytest.fixture
def csv_file(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("Name,Age,City\nAlice,30,Paris\nBob,25,Berlin\n")
    return f


class TestCSVParser:

    def test_loads_without_error(self, csv_file):
        p = CSVParser(file=str(csv_file))
        assert p.doc is not None

    def test_row_count(self, csv_file):
        p = CSVParser(file=str(csv_file))
        meta = p.get_metadata()
        assert meta["row_count"] == 2

    def test_columns_in_metadata(self, csv_file):
        p = CSVParser(file=str(csv_file))
        meta = p.get_metadata()
        assert "Name" in meta["columns"]

    def test_source_is_stem(self, csv_file):
        p = CSVParser(file=str(csv_file))
        meta = p.get_metadata()
        assert meta["source"] == "data"

    def test_to_markdown_produces_table(self, csv_file):
        p = CSVParser(file=str(csv_file))
        md = p.to_markdown()
        assert "|" in md  # markdown table uses pipes
        assert "Alice" in md
        assert "Bob" in md

    def test_normalizes_column_names(self, tmp_path):
        f = tmp_path / "whitespace.csv"
        f.write_text("First Name , Last Name\nJohn,Doe\n")
        p = CSVParser(file=str(f))
        cols = p.doc.columns.tolist()
        assert all(col.strip() == col for col in cols)

    def test_drops_all_na_rows(self, tmp_path):
        f = tmp_path / "empties.csv"
        f.write_text("A,B\n1,2\n,\n3,4\n")
        p = CSVParser(file=str(f))
        assert len(p.doc) == 2
