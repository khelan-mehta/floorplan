"""Job-progress pub/sub.

Phase 03 ships an in-process broker (single API process: dev, tests, the e2e flow). Cross-process
fan-out via Redis pub/sub (so WebSocket progress reaches the right client across pods) is a Phase-18
scaling follow-up — the publish/subscribe interface here is what that swap will implement.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any


class ProgressBroker:
    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)

    async def publish(self, job_id: str, event: dict[str, Any]) -> None:
        for queue in list(self._subs.get(job_id, set())):
            queue.put_nowait(event)

    def subscribe(self, job_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subs[job_id].add(queue)
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._subs[job_id].discard(queue)
        if not self._subs[job_id]:
            self._subs.pop(job_id, None)


broker = ProgressBroker()
