from __future__ import annotations

import asyncio
from typing import Any

import httpx


_client: httpx.AsyncClient | None = None


def get_async_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        timeout = httpx.Timeout(connect=10.0, read=60.0, write=60.0, pool=10.0)
        _client = httpx.AsyncClient(timeout=timeout)
    return _client


async def close_async_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def request_with_retry(
    method: str,
    url: str,
    *,
    retries: int = 3,
    retry_statuses: set[int] | None = None,
    **kwargs: Any,
) -> httpx.Response:
    retry_statuses = retry_statuses or {429, 500, 502, 503, 504}
    client = get_async_client()

    for attempt in range(retries):
        response = await client.request(method, url, **kwargs)
        if response.status_code not in retry_statuses:
            return response

        if attempt == retries - 1:
            return response
        await asyncio.sleep(2**attempt)

    return response
