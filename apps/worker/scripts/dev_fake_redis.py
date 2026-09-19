"""Dev-only stand-in for Redis, for machines without Docker.

    pip install "fakeredis>=2.26"
    python scripts/dev_fake_redis.py

Listens on 127.0.0.1:6379. Point apps/api and apps/worker at it with
REDIS_URL=redis://127.0.0.1:6379 -- use 127.0.0.1, not "localhost": on
Windows "localhost" tries IPv6 first and the connection times out.

Not a production queue (in-memory, single process, loses everything on
exit) and it doesn't implement INFO -- which is why the worker has to be
started with scripts/dev_worker_no_info.py instead of plain `arq`.
"""

from fakeredis import TcpFakeServer

server = TcpFakeServer(("127.0.0.1", 6379), server_type="redis")
print("fake redis listening on 127.0.0.1:6379", flush=True)
server.serve_forever()
