# apps/worker — Cadence background jobs

`arq` worker for anything too slow to run in-request: pose/tracking (Phase 2), alignment/scoring (Phase 3), cleanup jobs (Phase 1/7).

## Run locally

Requires Redis running locally (`redis-server`, or `docker run -p 6379:6379 redis`).

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
arq worker.settings.WorkerSettings
```

First run downloads YOLO and RTMPose weights (a few hundred MB) — needs internet once, then they're cached.

Performance: the full pipeline (detect + track + lock + pose) runs a 432-frame solo clip in ~76 seconds on CPU (~33ms/frame for pose itself). Earlier versions used `rtmlib`'s `Body`, which runs its own internal person detector per frame on top of the YOLO detection `detection.py` already does for tracking — two detectors per frame instead of one, and ~48 minutes for the same clip. `pose.py` now calls `rtmlib.RTMPose` directly with our own bbox instead. See `STATUS.md` for the full history if this regresses.

## Test

```bash
pytest                 # fast: pure-logic unit tests only (smoothing, quality, interpolation)
pytest -m integration  # slow: runs the real YOLO+ByteTrack+RTMPose pipeline against a real clip
```

The unit tests call job functions directly — no live Redis needed, and no ML deps either (they test `pipeline/smoothing.py`, `pipeline/quality.py`, `pipeline/interpolation.py` in isolation). The integration tests exercise `pipeline/detection.py` and `pipeline/pose.py` for real, but need `ultralytics` + `rtmlib` installed and a sample video (`CADENCE_SAMPLE_VIDEO` env var, defaults to a path on the original dev machine) — they skip themselves cleanly if either is missing, which is why they're excluded from the default `pytest` run (see `pytest.ini`) and from CI.

## Pipeline (Phase 2)

`worker/pipeline/`:

- `detection.py` — YOLO person detection + ByteTrack/BoT-SORT identity tracking (via `ultralytics`'s built-in `.track()`, not a hand-rolled tracker)
- `pose.py` — RTMPose via `rtmlib`, called directly with our own bbox (never the full frame, and never `rtmlib`'s own internal detector — see the performance note above)
- `interpolation.py` — fills tracking gaps ≤3 frames by linear interpolation; longer gaps are left as real discontinuities
- `smoothing.py` — One-Euro filter per joint/axis, killing jitter without lagging behind fast motion
- `quality.py` — per-track summaries (for a "pick your dancer" UI), `is_lock_ambiguous` (refuses to auto-lock when no track is clearly dominant — this is what catches the mirror/duo case, see below), and the accept/reject quality gate (reliable-frame %, fragmentation, person count)
- `pipeline.py` — orchestrates all of the above; this is what `tasks.py`'s jobs call

`tasks.py` exposes:
- `detect_tracks_job(analysis_id, video_path)` — what `apps/api`'s `POST /analyses` actually enqueues now. Runs detection, then either auto-locks a single confident track and writes a final `complete`/`rejected` `AnalysisResult` straight into the shared `analyses` table (`packages/db` — both this app and `apps/api` talk to the same DB directly, no callback API between them), or, if `is_lock_ambiguous` says no track is clearly dominant, marks the row `needs_dancer_pick` and stashes the raw detections in `Analysis.pending_lock_data` for later.
- `extract_locked_pose_job(video_path, track_id, ...)` — resumes from stashed detections once a track is picked. Not called from anywhere yet: there's no `POST /analyses/{id}/lock` endpoint for a user to actually pick a track, so `needs_dancer_pick` is a real, correctly-detected status today with no way to act on it.

**Duo/mirror stress test** (see `STATUS.md` for the full numbers): built two synthetic clips from real footage with `ffmpeg` — two distinct real dancers side by side, and one dancer next to their own flipped reflection. The duo case tracked cleanly (2 stable tracks). The mirror case produced 4 fragmented track IDs and would have silently auto-locked onto whichever had the most frames without `is_lock_ambiguous` — with it, both cases now correctly get flagged `needs_dancer_pick` instead of a confident wrong guess. That heuristic hasn't been tuned against a real eval set (still just these two synthetic clips), so treat its threshold as a reasonable default, not a validated one.

## Roadmap

Phase 2 (this pipeline) covers detect→track→lock→quality-gate, and is now wired end-to-end for the auto-lock path (upload → enqueue → detect → lock → persisted result). Still missing: the pick-UI/lock endpoint for the `needs_dancer_pick` path, and a real eval dataset (roadmap's "film 30 clips yourself" — MOTA/IDF1 numbers need that, and don't exist yet; two synthetic ffmpeg-composited clips is a spot-check, not that battery). Phase 3 (align → score → segment) is next. See [`../../STATUS.md`](../../STATUS.md).
