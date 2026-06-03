from __future__ import annotations

import pytest

from hestia.infrastructure.parsers.txt import TXTParser


@pytest.fixture
def txt_file(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("Hello, world!\nSecond line.\n", encoding="utf-8")
    return f


class TestTXTParser:

    def test_loads_content(self, txt_file):
        p = TXTParser(file=str(txt_file))
        assert p.doc is not None
        assert "Hello" in p.doc

    def test_to_markdown_returns_content(self, txt_file):
        p = TXTParser(file=str(txt_file))
        md = p.to_markdown()
        assert "Hello, world!" in md

    def test_get_metadata_has_source(self, txt_file):
        p = TXTParser(file=str(txt_file))
        meta = p.get_metadata()
        assert meta["source"] == "sample"
        assert meta["source_uri"] == str(txt_file)

    def test_handles_encoding_errors_gracefully(self, tmp_path):
        f = tmp_path / "latin.txt"
        f.write_bytes(b"Caf\xe9 au lait")
        p = TXTParser(file=str(f))
        # Should not raise
        assert p.doc is not None

    def test_empty_file_loads(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        p = TXTParser(file=str(f))
        assert p.doc == ""
