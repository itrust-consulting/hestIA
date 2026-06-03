from __future__ import annotations

import pytest

from hestia.domain.rag.classification import Classification


class TestClassificationFromLabel:

    def test_exact_label_public(self):
        assert Classification.from_label("public") == Classification.PUBLIC

    def test_exact_label_secret(self):
        assert Classification.from_label("secret") == Classification.SECRET

    def test_alias_pu(self):
        assert Classification.from_label("pu") == Classification.PUBLIC

    def test_alias_with_parentheses(self):
        assert Classification.from_label("public (pu)") == Classification.PUBLIC

    def test_alias_internal_in(self):
        assert Classification.from_label("internal (in)") == Classification.INTERNAL

    def test_case_insensitive(self):
        assert Classification.from_label("PUBLIC") == Classification.PUBLIC
        assert Classification.from_label("Secret") == Classification.SECRET

    def test_strips_whitespace(self):
        assert Classification.from_label("  public  ") == Classification.PUBLIC

    def test_unknown_label_returns_none(self):
        assert Classification.from_label("topsecret") is None

    def test_empty_string_returns_none(self):
        assert Classification.from_label("") is None

    def test_levels_ordered(self):
        assert Classification.PUBLIC.level < Classification.INTERNAL.level
        assert Classification.INTERNAL.level < Classification.RESTRICTED.level
        assert Classification.RESTRICTED.level < Classification.CONFIDENTIAL.level
        assert Classification.CONFIDENTIAL.level < Classification.SECRET.level
