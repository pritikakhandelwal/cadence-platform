"""Cadence API — FastAPI BFF.

Phase 0 scope: a health endpoint CI can check, nothing more. Auth,
uploads, and analysis endpoints land in Phase 1/2 by porting the logic
already proven in legacy/cadence-streamlit/modules (auth, validation,
workspace) onto this app instead of rewriting it from scratch.
"""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="Cadence API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
