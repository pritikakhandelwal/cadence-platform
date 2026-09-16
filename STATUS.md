# Status

Honest snapshot of where the build actually is against [`ROADMAP.md`](ROADMAP.md). Update this file at the end of every phase — it is the thing to read before assuming something is or isn't done.

_Last updated: 2026-09-16 (Phase 2 wired end-to-end for the auto-lock path)._

## Phase 0 — Foundation — **done**

- [x] Monorepo layout (`apps/web`, `apps/api`, `apps/worker`, `packages/schema`, `legacy/`)
- [x] `.gitignore` for venvs, videos, weights, db
- [x] Root README + this status file
- [x] `AnalysisResult` frozen in Python (Pydantic) and TypeScript
- [x] CI covers lint/typecheck/pytest across all four packages + legacy
- [x] `web` hello-route builds, `api` `/health` passes, worker `echo` job passes (all verified locally; CI not yet run on GitHub Actions since first push)

## Phase 1 — Trust — **substantially done, ported into `apps/api`**

The legacy Streamlit modules were ported (not rewritten) onto FastAPI + SQLAlchemy, since they already matched the roadmap's intent:

- [x] UUID-per-analysis workspace with path-jail on delete — [`packages/workspace`](packages/workspace) (ported from legacy `modules/workspace.py`; moved out of `apps/api` in Phase 2 once `apps/worker` needed to read the same files — see `docs/decisions.md`)
- [x] Argon2id password hashing with automatic upgrade from legacy SHA-256, login lockout after 5 failed attempts — [`apps/api/app/security/auth.py`](apps/api/app/security/auth.py) (ported from legacy `modules/auth.py`, sqlite3 → SQLAlchemy)
- [x] Upload validation: MP4 magic bytes, size cap (250MB), extension check — [`apps/api/app/security/video_validation.py`](apps/api/app/security/video_validation.py) (ported, adapted to FastAPI's async `UploadFile`)
- [x] `ffprobe`-based duration/codec/stream validation with explicit errors — same file
- [x] Registration/login field validation — [`apps/api/app/security/input_validation.py`](apps/api/app/security/input_validation.py) (ported near-verbatim)
- [x] Real accounts + sessions persisted in Postgres-or-SQLite via SQLAlchemy — [`packages/db`](packages/db) (moved out of `apps/api` in Phase 2 for the same reason as workspace, above) — `User`, `LoginSecurity`, `UserSession`, `Analysis`
- [x] Analysis rows persisted (`POST /analyses`, `GET /analyses/{id}`) — survives a refresh, not session-only
- [x] Per-IP rate limiting on `/auth/login` and `/auth/register` — [`apps/api/app/rate_limit.py`](apps/api/app/rate_limit.py) (new; legacy only rate-limited per-account, and there was no API to rate-limit before now)
- [x] FFmpeg-missing → explicit product error (`video_validation.validate_saved_video`)
- [x] Cleanup job for abandoned workspaces — [`apps/api/scripts/cleanup_workspaces.py`](apps/api/scripts/cleanup_workspaces.py) (run on a schedule; not wired into `apps/worker`, see that script's docstring for why)
- [x] 31 tests passing: ported auth/validation unit tests + endpoint integration tests (register→login→upload→retrieve, cross-user access denied, lockout, rate limits, job-enqueue) — workspace's own tests moved with it to `packages/workspace`
- [ ] Not yet using Alembic migrations (`Base.metadata.create_all` for now — fine until the schema needs to change without dropping data)
- [ ] Not yet verified against a real running Postgres instance in this environment (no Docker available here) — the code is dialect-agnostic and should work per `DATABASE_URL`, but hasn't been run against Postgres yet, only SQLite. Verify with `docker compose up postgres` before trusting this in a real deploy.
- [ ] HTML-escaping (legacy `html_safety.py`) intentionally **not** ported — it was a Streamlit-specific `unsafe_allow_html` concern. The equivalent risk in the new stack is `apps/web` ever using `dangerouslySetInnerHTML` on user content; don't do that, and this becomes moot.

**What's left of Phase 1:** wire `apps/web` to actually call these endpoints (currently a placeholder page with no API calls), and get a real Postgres run to confirm the dialect-agnostic models actually work there, not just on SQLite.

## Phase 2 — Lock-on — **built, fast, and wired end-to-end for the auto-lock path**

`apps/worker/worker/pipeline/` (see that app's README for the module breakdown):

- [x] YOLO person detection + ByteTrack/BoT-SORT tracking (`detection.py`, via `ultralytics .track()`)
- [x] Pose-on-crop-only via RTMPose (`pose.py`, via `rtmlib`) — never runs on the full frame, so a second person or a mirror can't corrupt the signal
- [x] Short-gap (≤3 frames) linear interpolation, longer gaps left as real discontinuities (`interpolation.py`)
- [x] One-Euro jitter smoothing, per joint/axis (`smoothing.py`)
- [x] Track summaries for a future multi-person "pick your dancer" UI, and a quality gate (reliable-frame %, fragmentation, person count) that rejects a bad lock with a human reason (`quality.py`)
- [x] 20 fast unit tests (no ML deps needed) covering smoothing/interpolation/quality-gate logic in isolation — passing
- [x] 2 integration tests that run the **real** pipeline against a real solo dance clip (`professional_dance.mp4`, not committed — see `apps/worker/README.md`) — both passing: detection finds the dancer, tracking holds them through the clip, pose comes back with plausible non-zero keypoints, the quality gate passes
- [x] **Performance problem found and fixed.** First version took ~48 minutes for a few seconds of video on CPU, because `pose.py` used `rtmlib`'s `Body`, which runs its *own* internal YOLOX person detector on every cropped frame — on top of the YOLO detection already done for tracking. Fix: read `Body`'s source (`rtmlib/tools/solution/body.py`) to find which onnx checkpoint + input size it resolves for a given `mode`, then call `rtmlib.RTMPose` directly with that checkpoint and our own bbox — `RTMPose.__call__(image, bboxes=[bbox])` takes the *full* frame and does its own internal affine crop per bbox, so "pose on crop only" still holds with one model per frame instead of two. Re-measured on the same real clip (432 frames): pose estimation is now ~33ms/frame (~14s for the whole clip), and the full integration suite (detect + lock + pose) runs in **76 seconds**, down from 48 minutes — about a 38x speedup on the full suite, more on pose alone. Both integration tests still pass with correct-looking output (COCO-17 keypoints, confidence scores 0.9+ on a clean solo clip).
- [ ] No eval dataset yet (roadmap's "film 30 clips yourself" for MOTA/IDF1, reliable-frame %, false-lock-on-mirror numbers) — this is still nowhere near that. Two synthetic clips were spot-checked (built with `ffmpeg` from the same real solo footage, not real duo/mirror recordings) with real, mixed results:
  - **Duo (two different real dancers, side by side):** handled correctly. 2 distinct tracks, each 100% frame coverage, 1 fragment, no ID confusion. Locking onto either one gives a clean quality-gate pass, and `person_count=2` correctly reflects the other dancer without penalizing the locked track's own reliability.
  - **Mirror (one dancer + their own horizontally-flipped reflection, side by side):** exposed a real gap, not a pass. YOLO+ByteTrack produced **4** track IDs for what's really one dancer + one reflection — heavy fragmentation on two of them (4 and 2 fragments), one spurious track at 2% frame coverage and 0.33 confidence. The quality gate still *passed* the top track (94% reliable, only 2 fragments) because our current thresholds are conservative enough to tolerate this — but nothing in the pipeline actually recognizes "this looks like a mirror," it just silently picked whichever track had the most frames. That is exactly the roadmap's "false lock on mirror" risk (target: 0), and this spot-check does not clear that bar. Not fixing this yet — a real fix (e.g. detecting near-mirrored bbox trajectories, or geometric symmetry checks) needs more than one synthetic clip to validate against; recorded here as a known, real limitation rather than papered over.
- [x] **`apps/api` now actually enqueues this.** Decided the open "shared DB vs. callback" question from the previous entry: `apps/worker` and `apps/api` both talk to the same Postgres/SQLite directly via a new shared [`packages/db`](packages/db) package (matches the roadmap's own architecture diagram, where both connect to PostgreSQL). `POST /analyses` enqueues `detect_tracks_job(analysis_id, video_path)` via a real arq pool (`apps/api/app/queue.py`, overridable in tests — no live Redis exists in this dev environment to test against for real, same caveat as Postgres above). The job runs detection, then either auto-locks a single confident track and writes a final `complete`/`rejected` `AnalysisResult` into the same row `GET /analyses/{id}` reads, or (see next bullet) marks it `needs_dancer_pick`.
- [x] **New: `is_lock_ambiguous` heuristic** (`worker/pipeline/quality.py`) refuses to auto-lock when no track is clearly dominant, instead of always grabbing whichever track has the most frames. Directly motivated by the mirror stress-test finding below — with this wired into `detect_tracks_job`, both the duo clip and the mirror clip now correctly come back `needs_dancer_pick` instead of the mirror case silently completing on a guess. Only validated against these same two synthetic clips, not a real eval set — treat the 0.5 dominance-ratio threshold as a reasonable default, not a tuned one.
- [x] Verified for real: a new integration test (`test_tasks_integration.py`) creates a real `Analysis` row, calls `detect_tracks_job` against the real solo clip, and confirms the row ends up `complete` with a valid `AnalysisResult` and `reliable_frame_pct > 50` — not just that the pipeline functions return sensible values in isolation, but that the actual job-writes-to-DB path works. (Caught and fixed a real bug while building this: the test's `DATABASE_URL` override was applied *after* `cadence_db` had already been imported via `pytest.importorskip`, so it silently wrote to a stray `apps/worker/cadence.db` instead of the intended temp file. Reordered so the env var is set before any import of `cadence_db`; re-ran to confirm no stray file appears anymore.)
- [ ] Multi-person "pick your dancer" UI/endpoint doesn't exist. `needs_dancer_pick` is now a correctly-detected status (see above) with nowhere for a user to act on it — `Analysis.pending_lock_data` stores what a future `POST /analyses/{id}/lock` endpoint would need (the raw detections, so it wouldn't have to re-run YOLO), but that endpoint isn't built.
- [ ] `apps/web` still doesn't call any of this — a user cannot actually trigger any of Phase 2 yet, only `apps/api`'s own tests can.

**What's real here:** the pipeline runs on actual footage, fast, with a working accept/reject gate that's been stress-tested against a real (if narrow) adversarial case, and `apps/api` genuinely enqueues it and reads its result back from the same database. **What's not real yet:** nobody outside a test can trigger it (no frontend, no pick-UI), it's only been measured against one solo clip plus two synthetic stress clips, and the live Redis/Postgres path has never actually run in this environment (only SQLite + a directly-invoked job function).

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

Two reasonable directions, not both at once:
1. **Breadth on Phase 2's eval**, not more plumbing: real footage (not synthetic ffmpeg composites) with an actual second person, an actual mirror, and actual occlusion, to see whether `is_lock_ambiguous`'s 0.5 threshold and the quality gate's other defaults hold up or need tuning.
2. **The `needs_dancer_pick` pick-UI/lock endpoint**, so a multi-person upload has somewhere to go instead of dead-ending. `Analysis.pending_lock_data` and `extract_locked_pose_job` already exist for this; what's missing is the `POST /analyses/{id}/lock` endpoint and any frontend to call it.

Either way, Phase 3 (real scoring) depends on Phase 2's output being trustworthy across more than one clip, so don't jump ahead of both of these to get there.
