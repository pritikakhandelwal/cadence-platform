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

## Phase 2 — Lock-on — **core pipeline built and verified against a real video; not wired to the API yet**

`apps/worker/worker/pipeline/` (see that app's README for the module breakdown):

- [x] YOLO person detection + ByteTrack/BoT-SORT tracking (`detection.py`, via `ultralytics .track()`)
- [x] Pose-on-crop-only via RTMPose (`pose.py`, via `rtmlib`) — never runs on the full frame, so a second person or a mirror can't corrupt the signal
- [x] Short-gap (≤3 frames) linear interpolation, longer gaps left as real discontinuities (`interpolation.py`)
- [x] One-Euro jitter smoothing, per joint/axis (`smoothing.py`)
- [x] Track summaries for a future multi-person "pick your dancer" UI, and a quality gate (reliable-frame %, fragmentation, person count) that rejects a bad lock with a human reason (`quality.py`)
- [x] 20 fast unit tests (no ML deps needed) covering smoothing/interpolation/quality-gate logic in isolation — passing
- [x] 2 integration tests that run the **real** pipeline against a real solo dance clip (`professional_dance.mp4`, not committed — see `apps/worker/README.md`) — both passing: detection finds the dancer, tracking holds them through the clip, pose comes back with plausible non-zero keypoints, the quality gate passes
- [x] **Performance problem found and fixed.** First version took ~48 minutes for a few seconds of video on CPU, because `pose.py` used `rtmlib`'s `Body`, which runs its *own* internal YOLOX person detector on every cropped frame — on top of the YOLO detection already done for tracking. Fix: read `Body`'s source (`rtmlib/tools/solution/body.py`) to find which onnx checkpoint + input size it resolves for a given `mode`, then call `rtmlib.RTMPose` directly with that checkpoint and our own bbox — `RTMPose.__call__(image, bboxes=[bbox])` takes the *full* frame and does its own internal affine crop per bbox, so "pose on crop only" still holds with one model per frame instead of two. Re-measured on the same real clip (432 frames): pose estimation is now ~33ms/frame (~14s for the whole clip), and the full integration suite (detect + lock + pose) runs in **76 seconds**, down from 48 minutes — about a 38x speedup on the full suite, more on pose alone. Both integration tests still pass with correct-looking output (COCO-17 keypoints, confidence scores 0.9+ on a clean solo clip).
- [ ] No eval dataset yet (roadmap's "film 30 clips yourself" for MOTA/IDF1, reliable-frame %, false-lock-on-mirror numbers) — only spot-checked on one solo clip so far, not the 20-clip battery the roadmap asks for
- [ ] `apps/api` doesn't call any of this yet — `POST /analyses` still just creates a `queued` row (see that endpoint's comment). Wiring it in means either giving `apps/worker` its own DB access (duplicating `apps/api`'s models, or moving them to a shared package) or having the API poll/callback — not decided yet, don't guess at it, decide deliberately when picking this up
- [ ] Multi-person "pick your dancer" UI doesn't exist (no frontend calls into any of this)

**What's real here:** the pipeline actually runs, on actual footage, and produces a plausible pose sequence with a working accept/reject gate — this isn't stubbed. **What's not real yet:** it's not fast enough to ship, it's not connected to anything a user can trigger, and it hasn't been measured against more than one clip.

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

Phase 2's pipeline is now correct and fast on one clip — next is breadth, not more speed work: run it against more than this one solo clip (a duo clip, a mirror clip) before trusting the quality gate's thresholds. In parallel, decide how `apps/worker` and `apps/api` share analysis state (shared DB models vs. callback), wire `POST /analyses` to actually enqueue `detect_tracks_job`, and build the multi-person pick UI. Phase 3 (real scoring) depends on Phase 2 output being trustworthy, so don't jump ahead of this.
