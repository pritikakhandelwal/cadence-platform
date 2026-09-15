"""Minimal per-process rate limiting for auth endpoints.

Fixed-window counter per client IP, in memory. Good enough for Phase 1
(protects against basic credential-stuffing on a single process); move
to a Redis-backed limiter in Phase 7 once there are multiple API
processes and it needs to be shared across them.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def __call__(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window_start = now - self.window_seconds

        hits = self._hits[client_ip]
        while hits and hits[0] < window_start:
            hits.pop(0)

        if len(hits) >= self.max_requests:
            raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")

        hits.append(now)


login_rate_limit = RateLimiter(max_requests=10, window_seconds=300)
register_rate_limit = RateLimiter(max_requests=5, window_seconds=3600)
