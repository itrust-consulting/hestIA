from __future__ import annotations

import json
import pytest

from hestia.infrastructure.parsers.json import JSONParser
from hestia.domain.exceptions import ValidationError


@pytest.fixture
def dict_file(tmp_path):
    f = tmp_path / "doc.json"
    f.write_text(json.dumps({"title": "My Doc", "author": "Alice", "body": "Content here"}))
    return f


@pytest.fixture
def list_file(tmp_path):
    f = tmp_path / "list.json"
    f.write_text(json.dumps(["item1", "item2"]))
    return f


class TestJSONParserMetadata:

    def test_extracts_title(self, dict_file):
        p = JSONParser(file=str(dict_file))
        meta = p.get_metadata()
        assert meta["title"] == "My Doc"

    def test_extracts_author(self, dict_file):
        p = JSONParser(file=str(dict_file))
        meta = p.get_metadata()
        assert meta["author"] == "Alice"

    def test_source_is_stem(self, dict_file):
        p = JSONParser(file=str(dict_file))
        meta = p.get_metadata()
        assert meta["source"] == "doc"

    def test_ignores_unknown_top_level_keys(self, dict_file):
        p = JSONParser(file=str(dict_file))
        meta = p.get_metadata()
        assert "body" not in meta

    def test_get_metadata_applies_mask(self, dict_file):
        p = JSONParser(file=str(dict_file))
        meta = p.get_metadata(mask_name="rag_default")
        assert "source" in meta

    def test_get_metadata_on_non_dict_doc_skips_meta_extraction(self, list_file):
        p = JSONParser(file=str(list_file))
        meta = p.get_metadata()
        assert "source" in meta
        assert "title" not in meta


class TestJSONParserToMarkdown:

    def test_dict_produces_sections(self, dict_file):
        p = JSONParser(file=str(dict_file))
        md = p.to_markdown()
        assert "## title" in md or "## Title" in md or "title" in md.lower()

    def test_list_produces_code_block(self, list_file):
        p = JSONParser(file=str(list_file))
        md = p.to_markdown()
        assert "```json" in md

    def test_malformed_file_raises_on_load(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{invalid json")
        with pytest.raises(Exception):
            JSONParser(file=str(f))

    def test_scalar_doc_renders_as_plain_string(self, tmp_path):
        f = tmp_path / "scalar.json"
        f.write_text(json.dumps(42))
        p = JSONParser(file=str(f))
        md = p.to_markdown()
        assert md == "42"

    def test_nested_dict_value_renders_as_code_block(self, tmp_path):
        f = tmp_path / "nested.json"
        f.write_text(json.dumps({"title": "Doc", "nested": {"a": 1}}))
        p = JSONParser(file=str(f))
        md = p.to_markdown()
        assert "## nested" in md
        assert "```json" in md


class TestJSONParserEmptyDoc:

    def test_to_markdown_raises_when_doc_is_none(self):
        p = JSONParser.__new__(JSONParser)
        p.doc = None
        with pytest.raises(ValidationError, match="Empty document"):
            p.to_markdown()
