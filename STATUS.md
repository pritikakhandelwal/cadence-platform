# Status

Honest snapshot of where the build actually is against [`ROADMAP.md`](ROADMAP.md). Update this file at the end of every phase — it is the thing to read before assuming something is or isn't done.

_Last updated: 2026-09-15 (Phase 1 substantially done)._

## Phase 0 — Foundation — **done**

- [x] Monorepo layout (`apps/web`, `apps/api`, `apps/worker`, `packages/schema`, `legacy/`)
- [x] `.gitignore` for venvs, videos, weights, db
- [x] Root README + this status file
- [x] `AnalysisResult` frozen in Python (Pydantic) and TypeScript
- [x] CI covers lint/typecheck/pytest across all four packages + legacy
- [x] `web` hello-route builds, `api` `/health` passes, worker `echo` job passes (all verified locally; CI not yet run on GitHub Actions since first push)

## Phase 1 — Trust — **substantially done, ported into `apps/api`**

The legacy Streamlit modules were ported (not rewritten) onto FastAPI + SQLAlchemy, since they already matched the roadmap's intent:

- [x] UUID-per-analysis workspace with path-jail on delete — [`apps/api/app/workspace.py`](apps/api/app/workspace.py) (ported from legacy `modules/workspace.py`)
- [x] Argon2id password hashing with automatic upgrade from legacy SHA-256, login lockout after 5 failed attempts — [`apps/api/app/security/auth.py`](apps/api/app/security/auth.py) (ported from legacy `modules/auth.py`, sqlite3 → SQLAlchemy)
- [x] Upload validation: MP4 magic bytes, size cap (250MB), extension check — [`apps/api/app/security/video_validation.py`](apps/api/app/security/video_validation.py) (ported, adapted to FastAPI's async `UploadFile`)
- [x] `ffprobe`-based duration/codec/stream validation with explicit errors — same file
- [x] Registration/login field validation — [`apps/api/app/security/input_validation.py`](apps/api/app/security/input_validation.py) (ported near-verbatim)
- [x] Real accounts + sessions persisted in Postgres-or-SQLite via SQLAlchemy (`apps/api/app/models.py`) — `User`, `LoginSecurity`, `UserSession`, `Analysis`
- [x] Analysis rows persisted (`POST /analyses`, `GET /analyses/{id}`) — survives a refresh, not session-only
- [x] Per-IP rate limiting on `/auth/login` and `/auth/register` — [`apps/api/app/rate_limit.py`](apps/api/app/rate_limit.py) (new; legacy only rate-limited per-account, and there was no API to rate-limit before now)
- [x] FFmpeg-missing → explicit product error (`video_validation.validate_saved_video`)
- [x] Cleanup job for abandoned workspaces — [`apps/api/scripts/cleanup_workspaces.py`](apps/api/scripts/cleanup_workspaces.py) (run on a schedule; not wired into `apps/worker`, see that script's docstring for why)
- [x] 34 tests passing: ported auth/validation/workspace unit tests + new endpoint integration tests (register→login→upload→retrieve, cross-user access denied, lockout, rate limits)
- [ ] Not yet using Alembic migrations (`Base.metadata.create_all` for now — fine until the schema needs to change without dropping data)
- [ ] Not yet verified against a real running Postgres instance in this environment (no Docker available here) — the code is dialect-agnostic and should work per `DATABASE_URL`, but hasn't been run against Postgres yet, only SQLite. Verify with `docker compose up postgres` before trusting this in a real deploy.
- [ ] HTML-escaping (legacy `html_safety.py`) intentionally **not** ported — it was a Streamlit-specific `unsafe_allow_html` concern. The equivalent risk in the new stack is `apps/web` ever using `dangerouslySetInnerHTML` on user content; don't do that, and this becomes moot.

**What's left of Phase 1:** wire `apps/web` to actually call these endpoints (currently a placeholder page with no API calls), and get a real Postgres run to confirm the dialect-agnostic models actually work there, not just on SQLite.

## Phase 2 — Lock-on — **not started**

Legacy app runs MediaPipe on the full frame (`modules/pose_detector.py`, `requirements.txt` pins `mediapipe==0.10.35`). No person detection, no tracking, no multi-person handling. This is the next real technical work after Phase 0/CI is green.

## Phase 3 — Coaching intelligence — **not started (legacy score is a placeholder)**

`legacy/cadence-streamlit/modules/dtw_compare.py` currently does raw, unnormalized per-frame DTW distance averaged across frames — no Procrustes/torso normalization, no joint angles, no confidence, no segment-level feedback. This is exactly the "fake score" Section 7 of the roadmap calls out to replace.

## Phase 4 — Arena frontend — **not started**

`apps/web` is a placeholder Next.js app (hello route only). No Arena UI, no 3D skeleton, no timeline.

## Phase 5 — Learning platform (song → choreo animation) — **not started**

Scoped per [`docs/decisions.md`](docs/decisions.md): curated phrases + BPM/genre matching + 3D animation playback, not generative choreography.

## Phase 6 — Music intelligence — **not started**

## Phase 7 — Production hardening — **not started**

## Phase 8 — Research track (incl. dance-form auto-detection) — **not started, and intentionally last**

---

## Next concrete step

Start Phase 2 (lock-on): YOLO person detection → ByteTrack/BoT-SORT identity tracking → crop → RTMPose, replacing legacy's full-frame MediaPipe (`legacy/cadence-streamlit/modules/pose_detector.py`). This is the technical heart of the roadmap and the biggest single piece of remaining work before the score means anything. Wire the resulting job into `apps/worker`, writing back into the `Analysis.result` column added in Phase 1.
