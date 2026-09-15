"""arq worker settings.

Run with: arq worker.settings.WorkerSettings
Requires a Redis instance at REDIS_URL (defaults to localhost:6379).
"""

from __future__ import annotations

import os

from arq.connections import RedisSettings

from .tasks import echo


class WorkerSettings:
    functions = [echo]
    redis_settings = RedisSettings.from_dsn(
        os.getenv("REDIS_URL", "redis://localhost:6379")
    )
