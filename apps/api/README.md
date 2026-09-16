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

## Endpoints

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health` | — | liveness check |
| POST | `/auth/register` | — | rate-limited (5/hour/IP) |
| POST | `/auth/login` | — | Argon2id verify, 5-attempt lockout, rate-limited (10/5min/IP), sets `cadence_session` httpOnly cookie |
| POST | `/auth/logout` | cookie | |
| GET | `/auth/me` | cookie | |
| POST | `/analyses` | cookie | multipart `user_video` (required) + exactly one of `professional_video` (file) or `professional_video_url` (a YouTube link — see below); validates magic bytes + `ffprobe`, creates a UUID-isolated workspace, persists a `queued` row, enqueues `apps/worker`'s `detect_tracks_job` |
| GET | `/analyses/{id}` | cookie | returns an `AnalysisResult` (packages/schema) built from the row; if `needs_dancer_pick`, points at the two endpoints below |
| GET | `/analyses/{id}/candidate-tracks` | cookie | only valid while `status == needs_dancer_pick`; lists the tracks a "pick your dancer" UI would show (track_id, frame_count, mean_confidence, fragments) |
| POST | `/analyses/{id}/lock` | cookie | body `{"track_id": int}`; only valid while `needs_dancer_pick`; enqueues `extract_locked_pose_job` to resume from the stashed detections (no re-running YOLO), marks the row `running` |

`needs_dancer_pick` happens when `apps/worker`'s `is_lock_ambiguous` can't confidently pick a single dominant track (two real people, or a mirror reflection producing a spurious second track — see `apps/worker/README.md`). There's no frontend calling any of this yet; these three endpoints together are the whole multi-person flow so far.

### `professional_video_url` (YouTube reference)

`app/security/youtube.py` downloads it with `yt-dlp`, restricted to `youtube.com`/`youtu.be` hosts over `http`/`https` only — never an arbitrary URL (that would be a server-side-request-forgery vector). The downloaded file goes through the same `ffprobe` validation an uploaded file does. This sits in a real copyright/ToS gray area (downloading YouTube content server-side) — see [`../../docs/decisions.md`](../../docs/decisions.md) for why it was built anyway and scoped this narrow.

Tests never make a real network call: `tests/conftest.py` has an autouse fixture that makes the real `download_youtube_video` raise if any test reaches it unmocked, added after exactly that happened once during development (a test-logic bug, not an endpoint bug, let a request through that downloaded a real 229MB video mid-test-run). Tests that want the download path mock it explicitly via `monkeypatch.setattr(analyses_module, "download_youtube_video", ...)`.

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

Ported near-verbatim (already matched the roadmap's Phase 1 intent): `app/security/auth.py`, `app/security/input_validation.py`, `app/security/video_validation.py` (adapted from Streamlit's sync `UploadedFile` to FastAPI's async `UploadFile`).

New in this app: cookie-based sessions (the legacy app used Streamlit session state), `app/rate_limit.py` (the legacy app only rate-limited login attempts per-account; this adds a basic per-IP limiter — a real one, but process-local; move to Redis-backed in Phase 7 once there are multiple API processes), and `app/queue.py` (enqueues jobs onto `apps/worker` via arq, Phase 2).

The DB models (`User`, `LoginSecurity`, `UserSession`, `Analysis`) and the per-analysis file workspace live in [`packages/db`](../../packages/db) and [`packages/workspace`](../../packages/workspace) respectively, not in this app — they moved out in Phase 2 once `apps/worker` needed to read/write the same rows and files. See [`../../docs/decisions.md`](../../docs/decisions.md).

## Roadmap

Phase 1 (isolated uploads, validated video, real accounts, persisted rows) and Phase 2's API surface (enqueue detection, multi-person pick flow) are both here. Not yet done: Postgres migrations via Alembic (currently `Base.metadata.create_all`, fine until the schema needs to change without dropping data), and nothing in `apps/web` calls any of this yet. See [`../../STATUS.md`](../../STATUS.md).
