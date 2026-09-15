# Status

Honest snapshot of where the build actually is against [`ROADMAP.md`](ROADMAP.md). Update this file at the end of every phase — it is the thing to read before assuming something is or isn't done.

_Last updated: 2026-09-15 (Phase 0 kickoff)._

## Phase 0 — Foundation — **in progress**

- [x] Monorepo layout (`apps/web`, `apps/api`, `apps/worker`, `packages/schema`, `legacy/`)
- [x] `.gitignore` for venvs, videos, weights, db
- [x] Root README + this status file
- [x] `AnalysisResult` frozen in Python (Pydantic) and TypeScript
- [ ] CI green (lint, typecheck, pytest across all four packages)
- [ ] `web` hello-route + `api` health + one worker echo job, all passing CI

## Phase 1 — Trust — **partially done, inside the legacy Streamlit app**

The existing `legacy/cadence-streamlit` code already implements a meaningful chunk of Phase 1, ahead of schedule:

- [x] UUID-per-analysis workspace with path-jail on delete — [`modules/workspace.py`](legacy/cadence-streamlit/modules/workspace.py)
- [x] Argon2id password hashing with automatic upgrade from legacy SHA-256, login lockout after 5 failed attempts — [`modules/auth.py`](legacy/cadence-streamlit/modules/auth.py)
- [x] Upload validation: MP4 magic bytes, size cap (250MB), extension check — [`modules/video_validation.py`](legacy/cadence-streamlit/modules/video_validation.py)
- [x] `ffprobe`-based duration/codec/stream validation with explicit errors — same file
- [x] HTML-escaping helper for user strings — [`modules/html_safety.py`](legacy/cadence-streamlit/modules/html_safety.py)
- [x] Registration/login field validation — [`modules/input_validation.py`](legacy/cadence-streamlit/modules/input_validation.py)
- [x] A real `tests/` suite covering auth, database, html_safety, input_validation, session_security, video_processing, video_validation, workspace
- [ ] Still on SQLite, not Postgres (fine for now, migrate in Phase 7)
- [ ] Rate limiting is login-only; no general API rate limit yet (there is no API yet)
- [ ] Cleanup job for abandoned workspaces not yet automated

**Action:** carry this logic (and its tests) forward into `apps/api`/`packages/schema` rather than rewriting it — it already matches the roadmap's intent.

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

Finish Phase 0: get CI green across `apps/web`, `apps/api`, `apps/worker`, `packages/schema`, then start Phase 1 by porting the legacy `auth`/`validation`/`workspace` modules (already solid) onto the FastAPI + Postgres stack instead of rewriting them from scratch.
