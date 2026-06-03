from __future__ import annotations

import uuid

import pytest

from hestia.domain.auth.models import AuthResult


class TestAuthResultAck:

    def test_success_is_true(self):
        uid = uuid.uuid4()
        r = AuthResult.ack(uid)
        assert r.success is True

    def test_user_id_set(self):
        uid = uuid.uuid4()
        r = AuthResult.ack(uid)
        assert r.user_id == uid

    def test_custom_message(self):
        uid = uuid.uuid4()
        r = AuthResult.ack(uid, message="Welcome back.")
        assert r.message == "Welcome back."

    def test_default_message(self):
        uid = uuid.uuid4()
        r = AuthResult.ack(uid)
        assert "successful" in r.message.lower()


class TestAuthResultNack:

    def test_success_is_false(self):
        r = AuthResult.nack()
        assert r.success is False

    def test_user_id_is_none(self):
        r = AuthResult.nack()
        assert r.user_id is None

    def test_custom_message(self):
        r = AuthResult.nack("Account locked.")
        assert r.message == "Account locked."

    def test_default_message(self):
        r = AuthResult.nack()
        assert len(r.message) > 0
