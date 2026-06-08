"""Typed-ish HTTP clients for calling internal services (generator/validator/geometry/export/codes).

Phase 03 provides the resilient call wrapper (timeouts + bounded retries). Individual service calls
are wired in the phases that need them (08/09/11/15).
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=5.0)


async def call_service(
    base_url: str,
    method: str,
    path: str,
    *,
    json: Any = None,
    retries: int = 2,
    timeout: httpx.Timeout = DEFAULT_TIMEOUT,  # noqa: ASYNC109 - httpx client timeout, not a deadline
) -> Any:
    """Call an internal service with bounded retries on transport/5xx errors."""
    last_exc: Exception | None = None
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        for attempt in range(retries + 1):
            try:
                resp = await client.request(method, path, json=json)
                if resp.status_code >= 500:
                    raise httpx.HTTPStatusError("server error", request=resp.request, response=resp)
                resp.raise_for_status()
                return resp.json()
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_exc = exc
                if attempt < retries:
                    await asyncio.sleep(0.2 * (2**attempt))
    raise RuntimeError(f"service call failed: {method} {base_url}{path}: {last_exc}")
