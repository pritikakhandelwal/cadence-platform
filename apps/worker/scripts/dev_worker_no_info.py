"""Dev-only launcher: the real arq WorkerSettings, for use with
scripts/dev_fake_redis.py.

fakeredis's TcpFakeServer doesn't implement INFO, and arq's worker calls
INFO exactly once, for a startup log line (arq.worker.log_redis_info).
This no-ops that one function and changes nothing else. Against a real
Redis, just run `arq worker.settings.WorkerSettings` as usual.

    cd apps/worker
    REDIS_URL=redis://127.0.0.1:6379 python scripts/dev_worker_no_info.py
"""

import sys
from pathlib import Path

# scripts/ is on sys.path when run as a file, apps/worker/ (which holds the
# `worker` package) is not -- add it.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import arq.worker  # noqa: E402
from arq.worker import run_worker  # noqa: E402


async def _skip_redis_info(*args, **kwargs):
    return None


arq.worker.log_redis_info = _skip_redis_info

from worker.settings import WorkerSettings  # noqa: E402

run_worker(WorkerSettings)
