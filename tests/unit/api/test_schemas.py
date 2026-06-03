from __future__ import annotations

import pytest

from hestia.api.schemas.base import Response


class TestResponseSuccess:

    def test_data_is_set(self):
        r = Response.success({"key": "value"})
        assert r.data == {"key": "value"}

    def test_error_is_none(self):
        r = Response.success("ok")
        assert r.error is None

    def test_meta_defaults_to_empty(self):
        r = Response.success("ok")
        assert r.meta == {}

    def test_meta_can_be_set(self):
        r = Response.success("ok", meta={"page": 1})
        assert r.meta["page"] == 1


class TestResponseFail:

    def test_data_is_none(self):
        r = Response.fail("ERR_001", "Something went wrong")
        assert r.data is None

    def test_error_has_code_and_message(self):
        r = Response.fail("ERR_001", "Something went wrong")
        assert r.error is not None
        assert r.error.code == "ERR_001"
        assert r.error.message == "Something went wrong"

    def test_details_default_to_empty(self):
        r = Response.fail("E", "m")
        assert r.error.details == {}

    def test_details_can_be_set(self):
        r = Response.fail("E", "m", details={"field": "name"})
        assert r.error.details["field"] == "name"

    def test_meta_defaults_to_empty(self):
        r = Response.fail("E", "m")
        assert r.meta == {}
