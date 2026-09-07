from __future__ import annotations

import pytest

from hestia.domain.exceptions import ValidationError
from hestia.infrastructure.parsers.base import BaseParser, Mask, MetadataFilter


# ---------------------------------------------------------------------------
# Mask
# ---------------------------------------------------------------------------

class TestMask:

    def test_whitelist_keeps_listed_keys(self):
        mask = Mask("m", {"a", "b"}, is_whitelist=True)
        result = mask.filter({"a": 1, "b": 2, "c": 3})
        assert set(result.keys()) == {"a", "b"}

    def test_blacklist_removes_listed_keys(self):
        mask = Mask("m", {"secret"}, is_whitelist=False)
        result = mask.filter({"secret": "x", "public": "y"})
        assert "secret" not in result
        assert "public" in result

    def test_empty_whitelist_returns_nothing(self):
        mask = Mask("m", set(), is_whitelist=True)
        result = mask.filter({"a": 1})
        assert result == {}

    def test_empty_blacklist_returns_everything(self):
        mask = Mask("m", set(), is_whitelist=False)
        result = mask.filter({"a": 1, "b": 2})
        assert result == {"a": 1, "b": 2}


# ---------------------------------------------------------------------------
# MetadataFilter
# ---------------------------------------------------------------------------

class TestMetadataFilter:

    def test_default_masks_loaded(self):
        mf = MetadataFilter()
        assert "rag_default" in mf.masks
        assert "ui_display" in mf.masks
        assert "internal_full" in mf.masks

    def test_filter_applies_whitelist_mask(self):
        mf = MetadataFilter()
        meta = {"title": "Doc", "source": "doc", "internal_key": "x"}
        result = mf.filter(meta, "rag_default")
        assert "title" in result
        assert "internal_key" not in result

    def test_filter_normalizes_keys_to_lowercase(self):
        mf = MetadataFilter()
        meta = {"TITLE": "Doc", "Source": "s"}
        result = mf.filter(meta, "rag_default")
        assert "title" in result or "source" in result

    def test_filter_returns_unchanged_when_mask_missing_non_strict(self):
        mf = MetadataFilter()
        meta = {"a": 1}
        result = mf.filter(meta, "nonexistent")
        assert result == meta

    def test_filter_raises_when_mask_missing_strict(self):
        mf = MetadataFilter()
        with pytest.raises(ValidationError, match="not found"):
            mf.filter({"a": 1}, "nonexistent", strict=True)

    def test_add_custom_mask(self):
        mf = MetadataFilter()
        mf.add_mask(Mask("custom", {"x"}, is_whitelist=True))
        result = mf.filter({"x": 1, "y": 2}, "custom")
        assert result == {"x": 1}

    def test_remove_mask(self):
        mf = MetadataFilter()
        mf.remove_mask("ui_display")
        assert "ui_display" not in mf.masks


# ---------------------------------------------------------------------------
# BaseParser helpers (via a concrete subclass)
# ---------------------------------------------------------------------------

class _ConcreteParser(BaseParser):
    def __init__(self, file=None):
        self._loader_map = {".txt": lambda f: open(f).read()}
        super().__init__(file=file)

    def get_metadata(self, builtIn_only=True, mask_name=None):
        return {}

    def to_markdown(self):
        return self.doc or ""


class TestBaseParserHelpers:

    def test_normalize_key_lowercases(self):
        p = _ConcreteParser()
        assert p.normalize_key("MyKey") == "mykey"

    def test_normalize_key_replaces_spaces(self):
        p = _ConcreteParser()
        assert p.normalize_key("my key") == "my_key"

    def test_clean_string_strips_extra_whitespace(self):
        p = _ConcreteParser()
        assert p.clean_string("  hello   world  ") == "hello world"

    def test_clean_string_handles_empty(self):
        p = _ConcreteParser()
        assert p.clean_string("") == ""

    def test_parse_raises_on_missing_file(self, tmp_path):
        p = _ConcreteParser()
        from hestia.domain.exceptions import NotFoundError
        with pytest.raises(NotFoundError):
            p.parse(str(tmp_path / "missing.txt"))

    def test_dumps_returns_frontmatter_post(self, tmp_path):
        f = tmp_path / "sample.txt"
        f.write_text("Hello world")
        p = _ConcreteParser(file=str(f))
        post = p.dumps()
        import frontmatter
        assert isinstance(post, frontmatter.Post)

    def test_parse_raises_on_unsupported_file_type(self, tmp_path):
        f = tmp_path / "sample.docx"
        f.write_text("not really a docx")
        p = _ConcreteParser()
        with pytest.raises(ValidationError, match="not supported"):
            p.parse(str(f))

    def test_close_is_a_noop(self, tmp_path):
        f = tmp_path / "sample.txt"
        f.write_text("Hello world")
        p = _ConcreteParser(file=str(f))
        assert p.close() is None

    def test_dump_writes_to_explicit_output_path(self, tmp_path):
        f = tmp_path / "sample.txt"
        f.write_text("Hello world")
        p = _ConcreteParser(file=str(f))
        out_path = tmp_path / "out.md"
        p.dump(output_path=out_path)
        assert out_path.exists()
        assert "Hello world" in out_path.read_text()

    def test_dump_writes_to_default_dump_dir_when_no_output_path(self, tmp_path):
        f = tmp_path / "sample.txt"
        f.write_text("Hello world")
        p = _ConcreteParser(file=str(f))
        dump_dir = tmp_path / "dumped"
        p.dump(dump_dir=str(dump_dir))
        expected = dump_dir / "sample.md"
        assert expected.exists()
        assert "Hello world" in expected.read_text()
