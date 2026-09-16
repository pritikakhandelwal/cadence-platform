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
- `pose.py` — RTMPose via `rtmlib`, run on a numpy-cropped bbox only, never the full frame
- `interpolation.py` — fills tracking gaps ≤3 frames by linear interpolation; longer gaps are left as real discontinuities
- `smoothing.py` — One-Euro filter per joint/axis, killing jitter without lagging behind fast motion
- `quality.py` — per-track summaries (for a "pick your dancer" UI) and the accept/reject quality gate (reliable-frame %, fragmentation, person count)
- `pipeline.py` — orchestrates all of the above; this is what `tasks.py`'s `detect_tracks_job` / `extract_locked_pose_job` call

`tasks.py` exposes two real jobs on top of this: `detect_tracks_job(video_path)` (run once per upload) and `extract_locked_pose_job(video_path, track_id, ...)` (run once the user — or, for a solo clip, an automatic single-track lock — has picked who to score).

## Roadmap

Phase 2 (this pipeline) covers detect→track→lock→quality-gate. Not yet wired: `apps/api` doesn't enqueue these jobs yet (see `apps/api`'s `POST /analyses` comment), and there's no eval dataset yet (roadmap's "film 30 clips yourself" — MOTA/IDF1 numbers need that, and don't exist yet). Phase 3 (align → score → segment) is next. See [`../../STATUS.md`](../../STATUS.md).
