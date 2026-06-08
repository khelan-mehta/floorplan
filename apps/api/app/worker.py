"""Arq worker entrypoint for production job execution.

Run with:  arq app.worker.WorkerSettings
Runs the SAME executors as the in-process path so behaviour is identical at scale.
"""

from __future__ import annotations

from typing import Any, ClassVar

from arq.connections import RedisSettings

from .jobs import run_generate
from .settings import settings


async def generate_task(ctx: dict[str, Any], job_id: str) -> None:
    await run_generate(job_id)


class WorkerSettings:
    functions: ClassVar = [generate_task]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
