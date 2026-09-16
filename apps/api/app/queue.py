"""arq job queue access for apps/api.

A FastAPI dependency (like get_db) rather than a bare module-level
pool, so tests can override it with a fake that just records what was
enqueued -- the same pattern already used for the DB session. This
repo has no live Redis to test against (no Docker in this dev
environment); see STATUS.md. The real pool is exercised only when the
API actually runs against a real Redis instance.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Protocol


class JobQueue(Protocol):
    async def enqueue_job(self, function: str, *args, **kwargs) -> object | None: ...


async def get_queue() -> AsyncIterator[JobQueue]:
    from arq import create_pool
    from arq.connections import RedisSettings

    pool = await create_pool(RedisSettings.from_dsn(os.getenv("REDIS_URL", "redis://localhost:6379")))
    try:
        yield pool
    finally:
        await pool.close()
