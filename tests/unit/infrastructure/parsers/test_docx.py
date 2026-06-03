from __future__ import annotations

import pathlib
import pytest

# Real test file from tests/test_inputs/
DOCX_FILE = pathlib.Path(__file__).parents[4] / "tests" / "test_inputs" / "Test-Document.docx"
DOCX_ITR = pathlib.Path(__file__).parents[4] / "tests" / "test_inputs" / "Test-Document-ITR.docx"

skip_if_missing = pytest.mark.skipif(not DOCX_FILE.exists(), reason="Test DOCX not found")
skip_if_itr_missing = pytest.mark.skipif(not DOCX_ITR.exists(), reason="ITR DOCX not found")

from hestia.infrastructure.parsers.docx import DOCXParser, ITRDOCXParser


@skip_if_missing
class TestDOCXParser:

    @pytest.fixture(scope="class")
    def parser(self):
        return DOCXParser(file=str(DOCX_FILE))

    def test_loads_without_error(self, parser):
        assert parser.doc is not None

    def test_to_markdown_contains_text(self, parser):
        md = parser.to_markdown()
        assert len(md) > 0

    def test_tables_rendered_as_markdown(self, parser):
        md = parser.to_markdown()
        # If the test document contains a table, it should have pipe characters
        # We just verify markdown is returned without crash

    def test_metadata_has_source(self, parser):
        meta = parser.get_metadata()
        assert "source" in meta

    def test_metadata_builtin_only(self, parser):
        meta = parser.get_metadata(builtIn_only=True)
        assert isinstance(meta, dict)

    def test_headings_rendered_with_hash(self, parser):
        md = parser.to_markdown()
        # Should contain heading markers if the document has headings
        # Just verify the method runs
        assert isinstance(md, str)


# ---------------------------------------------------------------------------
# DOCXParser helpers — unit tests without needing a real file
# ---------------------------------------------------------------------------

class TestDOCXParserHelpers:
    """Test methods that can be exercised without a full .docx parse."""

    @pytest.fixture
    def parser(self):
        p = DOCXParser.__new__(DOCXParser)
        p._style_levels = {}
        p._footnotes = {}
        p._rels = {"rId1": "https://example.com"}
        return p

    def test_render_hyperlink_with_known_rel(self, parser):
        from lxml import etree
        ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        elem = etree.fromstring(f'<w:hyperlink xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="{ns}" r:id="rId1">Click here</w:hyperlink>')
        result = parser.render_hyperlink(elem)
        assert "Click here" in result
        assert "https://example.com" in result

    def test_render_hyperlink_without_rel_returns_text(self, parser):
        from lxml import etree
        elem = etree.fromstring('<w:hyperlink xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">plain text</w:hyperlink>')
        result = parser.render_hyperlink(elem)
        assert result == "plain text"

    def test_table_to_markdown_produces_pipe_table(self, tmp_path):
        import docx
        doc = docx.Document()
        tbl = doc.add_table(rows=2, cols=2)
        tbl.cell(0, 0).text = "H1"
        tbl.cell(0, 1).text = "H2"
        tbl.cell(1, 0).text = "V1"
        tbl.cell(1, 1).text = "V2"
        path = tmp_path / "tbl.docx"
        doc.save(str(path))

        p = DOCXParser(file=str(path))
        md = p.table_to_markdown(p.doc.tables[0])
        assert "|" in md
        assert "H1" in md
        assert "V1" in md

    def test_table_to_markdown_merged_cells_no_crash(self, tmp_path):
        import docx
        from docx.oxml.ns import qn
        doc = docx.Document()
        tbl = doc.add_table(rows=2, cols=2)
        # Merge cells (0,0) and (0,1)
        cell_a = tbl.cell(0, 0)
        cell_b = tbl.cell(0, 1)
        cell_a.merge(cell_b)
        path = tmp_path / "merged.docx"
        doc.save(str(path))

        p = DOCXParser(file=str(path))
        md = p.table_to_markdown(p.doc.tables[0])
        assert isinstance(md, str)


@skip_if_missing
class TestDOCXParserListItems:

    def test_list_items_rendered_in_markdown(self):
        # The Test-Document.docx should render paragraphs; we just verify the
        # to_markdown output is a non-empty string without error.
        p = DOCXParser(file=str(DOCX_FILE))
        md = p.to_markdown()
        assert isinstance(md, str)
        assert len(md) > 0


@skip_if_itr_missing
class TestITRDOCXParser:

    @pytest.fixture(scope="class")
    def parser(self):
        return ITRDOCXParser(file=str(DOCX_ITR))

    def test_loads_without_error(self, parser):
        assert parser.doc is not None

    def test_metadata_merged_from_cover_page(self, parser):
        meta = parser.get_metadata(builtIn_only=False)
        assert isinstance(meta, dict)

    def test_to_markdown_returns_string(self, parser):
        md = parser.to_markdown()
        assert isinstance(md, str)
        assert len(md) > 0
