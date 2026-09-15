"""Cadence background jobs.

Phase 0 scope: one echo job proving the worker process, arq wiring, and
CI all agree. Phase 2/3 add the real jobs: detect+track+pose, then
alignment+scoring, each returning an AnalysisResult.
"""

from __future__ import annotations

from typing import Any


async def echo(ctx: dict[str, Any], message: str) -> str:
    """Trivial job: prove the queue round-trips a payload."""

    return message
