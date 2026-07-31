import asyncio
import logging
from typing import AsyncIterator

from fastapi import Request

_log = logging.getLogger("hestia.system")


async def abort_on_disconnect(request: Request, agen: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
    """Stop consuming `agen` the moment the client disconnects, instead of
    letting the provider keep generating server-side. Closing the generator
    propagates GeneratorExit down through the LLM provider chain, closing
    the httpx connection to vLLM -- which vLLM's own engine treats as an
    abort signal and stops generating (vllm-project/vllm#7071).

    In practice, disconnects are almost always caught by uvicorn cancelling
    this request's task directly (surfacing here as CancelledError) rather
    than by the is_disconnected() poll below ever returning True -- both
    paths are logged so the abort is always visible in system.log."""
    try:
        async for chunk in agen:
            if await request.is_disconnected():
                _log.info("client_disconnected_aborting_generation")
                break
            yield chunk
    except asyncio.CancelledError:
        _log.info("client_disconnected_aborting_generation")
        raise
    finally:
        await agen.aclose()
