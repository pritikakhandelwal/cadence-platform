# apps/api — Cadence BFF

FastAPI backend. Owns auth, uploads, and the `AnalysisResult` API surface.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Without a `DATABASE_URL` env var it falls back to a local SQLite file (`cadence.db`) — fine for manual testing. For something closer to production, run Postgres via the root [`docker-compose.yml`](../../docker-compose.yml) (`docker compose up postgres`) and set `DATABASE_URL` per [`.env.example`](../../.env.example).

FFmpeg (`ffprobe`) must be on `PATH` — video upload validation shells out to it.

## Endpoints (Phase 1)

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health` | — | liveness check |
| POST | `/auth/register` | — | rate-limited (5/hour/IP) |
| POST | `/auth/login` | — | Argon2id verify, 5-attempt lockout, rate-limited (10/5min/IP), sets `cadence_session` httpOnly cookie |
| POST | `/auth/logout` | cookie | |
| GET | `/auth/me` | cookie | |
| POST | `/analyses` | cookie | multipart `professional_video` + `user_video` (MP4, ≤250MB, ≤5min); validates magic bytes + `ffprobe`, creates a UUID-isolated workspace, persists a `queued` row |
| GET | `/analyses/{id}` | cookie | returns an `AnalysisResult` (packages/schema); `queued` until Phase 2/3 fill in real tracking/scoring |

## Test

```bash
pytest
```

Tests use a temp SQLite file per test (no Postgres needed) and generate a tiny real MP4 with `ffmpeg` for upload-validation fixtures — `ffmpeg`/`ffprobe` must be on `PATH` to run them.

## Cleanup job

`scripts/cleanup_workspaces.py` removes workspace directories older than `--max-age-hours` (default 24). Run it on a schedule (cron / Task Scheduler / a platform scheduled job) — it isn't wired into `apps/worker` because the worker won't necessarily share a filesystem with the API once Phase 7 moves to object storage.

```bash
python scripts/cleanup_workspaces.py --max-age-hours 24
```

## What's ported from the legacy app vs. new

Ported near-verbatim (already matched the roadmap's Phase 1 intent): `app/security/auth.py`, `app/security/input_validation.py`, `app/security/video_validation.py` (adapted from Streamlit's sync `UploadedFile` to FastAPI's async `UploadFile`), `app/workspace.py` (+ added `cleanup_abandoned_workspaces`).

New in this app: `app/db.py` / `app/models.py` (SQLAlchemy, Postgres in prod / SQLite in tests — the legacy app used raw sqlite3), the FastAPI routers, cookie-based sessions (the legacy app used Streamlit session state), and `app/rate_limit.py` (the legacy app only rate-limited login attempts per-account; this adds a basic per-IP limiter — a real one, but process-local; move to Redis-backed in Phase 7 once there are multiple API processes).

## Roadmap

Phase 1 (this app) is mostly here: isolated uploads, validated video, real accounts, persisted analysis rows. Not yet done: Postgres migrations via Alembic (currently `Base.metadata.create_all`, fine until the schema needs to change without dropping data). Phase 2 adds the actual detect→track→pose job dispatched to `apps/worker`. See [`../../STATUS.md`](../../STATUS.md).
