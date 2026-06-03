from __future__ import annotations

import openpyxl
import pytest

from hestia.infrastructure.parsers.xlsx import XLSXParser


def _make_xlsx(tmp_path, sheet_data=None):
    if sheet_data is None:
        sheet_data = {"Sheet1": [["Name", "Age"], ["Alice", 30], ["Bob", 25]]}
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet_name, rows in sheet_data.items():
        ws = wb.create_sheet(sheet_name)
        for row in rows:
            ws.append(row)
    path = tmp_path / "test.xlsx"
    wb.save(str(path))
    return path


class TestXLSXParser:

    def test_loads_without_error(self, tmp_path):
        path = _make_xlsx(tmp_path)
        p = XLSXParser(file=str(path))
        assert p.doc is not None

    def test_loads_all_sheets(self, tmp_path):
        path = _make_xlsx(tmp_path, sheet_data={
            "Sheet1": [["A", "B"], [1, 2]],
            "Sheet2": [["X", "Y"], [3, 4]],
        })
        p = XLSXParser(file=str(path))
        assert "Sheet1" in p.doc
        assert "Sheet2" in p.doc

    def test_selected_sheets_filter(self, tmp_path):
        path = _make_xlsx(tmp_path, sheet_data={
            "Sheet1": [["A"], [1]],
            "Sheet2": [["B"], [2]],
        })
        p = XLSXParser(file=str(path), selected_sheets=["Sheet1"])
        assert "Sheet1" in p.doc
        assert "Sheet2" not in p.doc

    def test_to_markdown_contains_data(self, tmp_path):
        path = _make_xlsx(tmp_path)
        p = XLSXParser(file=str(path))
        md = p.to_markdown()
        assert "Alice" in md
        assert "Bob" in md

    def test_metadata_has_source(self, tmp_path):
        path = _make_xlsx(tmp_path)
        p = XLSXParser(file=str(path))
        meta = p.get_metadata()
        assert "source" in meta

    def test_to_markdown_sheets_returns_dict(self, tmp_path):
        path = _make_xlsx(tmp_path, sheet_data={
            "S1": [["A"], [1]],
            "S2": [["B"], [2]],
        })
        p = XLSXParser(file=str(path))
        sheets = p.to_markdown_sheets()
        assert "S1" in sheets
        assert "S2" in sheets
        assert isinstance(sheets["S1"], str)


# ---------------------------------------------------------------------------
# XLSXParser.to_csv
# ---------------------------------------------------------------------------

class TestXLSXToCSV:

    def test_to_csv_returns_csv_string(self, tmp_path):
        path = _make_xlsx(tmp_path, sheet_data={"Data": [["Col1", "Col2"], ["a", "b"]]})
        p = XLSXParser(file=str(path))
        result = p.to_csv()
        assert "Data" in result
        csv_content = result["Data"]
        assert "Col1" in csv_content or "0" in csv_content  # header row

    def test_to_csv_writes_file_when_output_path_given(self, tmp_path):
        path = _make_xlsx(tmp_path, sheet_data={"Sheet1": [["A", "B"], [1, 2]]})
        p = XLSXParser(file=str(path))
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        result = p.to_csv(output_path=str(out_dir))
        assert "Sheet1" in result
        import os
        assert os.path.exists(result["Sheet1"])


# ---------------------------------------------------------------------------
# XLSXParser.get_builtin_metadata
# ---------------------------------------------------------------------------

class TestXLSXBuiltinMetadata:

    def test_get_builtin_metadata_returns_dict(self, tmp_path):
        path = _make_xlsx(tmp_path)
        p = XLSXParser(file=str(path))
        meta = p.get_builtin_metadata()
        assert isinstance(meta, dict)


# ---------------------------------------------------------------------------
# ITRXLSXParser
# ---------------------------------------------------------------------------

def _make_itr_xlsx(tmp_path):
    """Create a minimal XLSX with the ITR 'Hist' sheet layout."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hist"
    # Row 0 (1-indexed row 1): Title
    ws.append(["My ITR Document Title"])
    # Row 1: Subject
    ws.append(["Document Subject"])
    # Row 2: blank
    ws.append([""])
    # Rows 3-8: key/value pairs (col A = key, col C = value)
    for i, (key, val) in enumerate([
        ("Reference", "ITR-001"),
        ("Version", "1.2"),
        ("Classification", "Internal"),
    ]):
        row = [""] * 3
        row[0] = key
        row[2] = val
        ws.append(row)
    path = tmp_path / "itr.xlsx"
    wb.save(str(path))
    return path


from hestia.infrastructure.parsers.xlsx import ITRXLSXParser


class TestITRXLSXParser:

    def test_loads_without_error(self, tmp_path):
        path = _make_itr_xlsx(tmp_path)
        p = ITRXLSXParser(file=str(path))
        assert p.doc is not None

    def test_get_metadata_from_cover_page_extracts_title(self, tmp_path):
        path = _make_itr_xlsx(tmp_path)
        p = ITRXLSXParser(file=str(path))
        meta = p.get_metadata_from_cover_page()
        assert meta.get("title") == "My ITR Document Title"

    def test_get_metadata_from_cover_page_extracts_subject(self, tmp_path):
        path = _make_itr_xlsx(tmp_path)
        p = ITRXLSXParser(file=str(path))
        meta = p.get_metadata_from_cover_page()
        assert meta.get("subject") == "Document Subject"

    def test_get_metadata_merges_builtin_and_cover(self, tmp_path):
        path = _make_itr_xlsx(tmp_path)
        p = ITRXLSXParser(file=str(path))
        meta = p.get_metadata(builtIn_only=False)
        assert "title" in meta
        assert "source" in meta

    def test_raises_when_no_hist_sheet(self, tmp_path):
        path = _make_xlsx(tmp_path, sheet_data={"Sheet1": [["A"], [1]]})
        p = ITRXLSXParser(file=str(path))
        from hestia.domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="Hist"):
            p.get_metadata_from_cover_page()
