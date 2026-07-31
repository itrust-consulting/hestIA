from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

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
