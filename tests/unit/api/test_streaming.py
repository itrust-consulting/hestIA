from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from hestia.api.streaming import abort_on_disconnect


def _run(coro):
    return asyncio.run(coro)


async def _agen(items):
    for item in items:
        yield item


async def _collect(agen):
    return [chunk async for chunk in agen]


class TestAbortOnDisconnect:

    def test_yields_all_chunks_when_never_disconnected(self):
        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        result = _run(_collect(abort_on_disconnect(request, _agen([b"a", b"b", b"c"]))))
        assert result == [b"a", b"b", b"c"]

    def test_stops_early_once_disconnected(self):
        request = MagicMock()
        request.is_disconnected = AsyncMock(side_effect=[False, False, True])

        result = _run(_collect(abort_on_disconnect(request, _agen([b"a", b"b", b"c", b"d"]))))
        assert result == [b"a", b"b"]

    def test_closes_upstream_generator_on_disconnect(self):
        cleaned_up = False

        async def upstream():
            nonlocal cleaned_up
            try:
                yield b"a"
                yield b"b"
                yield b"c"
            finally:
                cleaned_up = True

        request = MagicMock()
        request.is_disconnected = AsyncMock(side_effect=[False, True])

        result = _run(_collect(abort_on_disconnect(request, upstream())))
        assert result == [b"a"]
        assert cleaned_up is True

    def test_closes_upstream_generator_on_normal_completion(self):
        cleaned_up = False

        async def upstream():
            nonlocal cleaned_up
            try:
                yield b"a"
            finally:
                cleaned_up = True

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        result = _run(_collect(abort_on_disconnect(request, upstream())))
        assert result == [b"a"]
        assert cleaned_up is True

    def test_cancelled_error_while_iterating_is_logged_and_reraised(self, caplog):
        # Per the module's own docstring, this -- not the is_disconnected()
        # poll above -- is the common real-world disconnect path: uvicorn
        # cancels the request task directly, which surfaces as
        # asyncio.CancelledError raised while advancing the wrapped
        # generator, rather than is_disconnected() ever returning True.
        cleaned_up = False

        async def upstream():
            nonlocal cleaned_up
            try:
                yield b"a"
                raise asyncio.CancelledError()
            finally:
                cleaned_up = True

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        async def consume():
            chunks = []
            async for chunk in abort_on_disconnect(request, upstream()):
                chunks.append(chunk)
            return chunks

        with caplog.at_level(logging.INFO, logger="hestia.system"):
            with pytest.raises(asyncio.CancelledError):
                _run(consume())

        assert cleaned_up is True
        messages = [r.getMessage() for r in caplog.records if r.name == "hestia.system"]
        assert "client_disconnected_aborting_generation" in messages

    def test_cancelled_error_still_closes_the_generator(self):
        # aclose() in the finally block must run even on the CancelledError
        # path, not just the is_disconnected()/normal-completion paths. Wraps
        # the real async generator in a thin proxy to observe the aclose()
        # call directly, since AsyncGenerator.aclose is a read-only attribute
        # and can't be monkeypatched on the instance itself.
        class _TrackingAgen:
            def __init__(self, agen):
                self._agen = agen
                self.aclose_called = False

            def __aiter__(self):
                return self

            def __anext__(self):
                return self._agen.__anext__()

            async def aclose(self):
                self.aclose_called = True
                await self._agen.aclose()

        async def upstream():
            yield b"a"
            raise asyncio.CancelledError()

        tracked = _TrackingAgen(upstream())

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        async def consume():
            chunks = []
            async for chunk in abort_on_disconnect(request, tracked):
                chunks.append(chunk)
            return chunks

        with pytest.raises(asyncio.CancelledError):
            _run(consume())

        assert tracked.aclose_called is True
