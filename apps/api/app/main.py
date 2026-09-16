"""Cadence API — FastAPI BFF.

Phase 1 scope: real accounts (Argon2id + lockout), validated video
uploads (magic bytes + ffprobe), UUID-isolated workspaces, and
persisted analysis rows. The auth/validation/workspace logic here is
ported from legacy/cadence-streamlit/modules rather than rewritten,
since it already matched the roadmap's intent.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from cadence_db import init_db

from .routers import analyses, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Cadence API", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(analyses.router)
