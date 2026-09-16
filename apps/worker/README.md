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
- `detect_tracks_job(analysis_id, video_path)` — what `apps/api`'s `POST /analyses` actually enqueues now. Runs detection, then either auto-locks a single confident track (locks it, saves its keypoints, scores it against the reference video -- see Phase 3 below -- and writes a final `complete`/`rejected` `AnalysisResult` straight into the shared `analyses` table, `packages/db`, both this app and `apps/api` talking to the same DB directly, no callback API between them) or, if `is_lock_ambiguous` says no track is clearly dominant, marks the row `needs_dancer_pick` and stashes the raw detections in `Analysis.pending_lock_data` for later.
- `extract_locked_pose_job(analysis_id, video_path, track_id, fps, total_frames, detections)` — resumes from stashed detections once a track is picked, without re-running YOLO. Enqueued by `apps/api`'s `POST /analyses/{id}/lock`. Shares the same lock-then-score tail as `detect_tracks_job`'s auto-lock path (`_finish_lock` in `tasks.py`), and clears `pending_lock_data` once done.

**Duo/mirror stress test** (see `STATUS.md` for the full numbers): built two synthetic clips from real footage with `ffmpeg` — two distinct real dancers side by side, and one dancer next to their own flipped reflection. The duo case tracked cleanly (2 stable tracks). The mirror case produced 4 fragmented track IDs and would have silently auto-locked onto whichever had the most frames without `is_lock_ambiguous` — with it, both cases now correctly get flagged `needs_dancer_pick` instead of a confident wrong guess. That heuristic hasn't been tuned against a real eval set (still just these two synthetic clips), so treat its threshold as a reasonable default, not a validated one.

## Scoring (Phase 3)

Once the user's video is locked, `tasks.py` also runs the reference (professional) video through the same detect+lock pipeline (assumed solo/clean; a messy reference is a real if rare failure mode, handled by rejecting with a clear reason, not assumed away) and scores the two against each other:

- `features.py` — converts RTMPose's 17 keypoints into 8 joint angles (elbow/knee/hip/shoulder, both sides) + a per-video baseline-corrected spine lean. Angles between three skeletal points are automatically invariant to translation, scale, and in-plane rotation, unlike raw (x, y) coordinates -- this is what makes them comparable between two videos shot from different distances/angles without an explicit Procrustes step. Masks a joint to NaN if any of its keypoints is below `DEFAULT_MIN_CONFIDENCE` (0.3) -- RTMPose still emits *some* coordinate for an occluded/uncertain keypoint, extrapolated from its training prior, and treating that as real signal was a real bug this file had, caught by comparing output against real footage (see below).
- `alignment.py` — classic DTW (a plain numpy DP table, no external dependency) on the two feature sequences, producing a frame-to-frame warping path. O(N\*M) time and memory -- fine for the clips tested (a few hundred frames), not verified to scale to the platform's 5-minute upload limit; a Sakoe-Chiba band is the standard fix if that turns out to matter.
- `scoring.py` — segments the warping path into ~2s windows (in the reference video's own timeline), computes per-joint mean angle error per window, turns errors over 15 degrees into `angle` issues and a growing reference/user time gap into a `timing` issue, and maps mean error to a 0-100 score via `100 * exp(-error/TAU)` (TAU chosen so a 20-degree average error gives 50%) -- a formula over a normalized, rotation-invariant feature, not the raw-pixel-distance formula the roadmap's own Section 7 calls out as a fake score. Does not produce `path`-type issues (schema supports the enum value; nothing here generates one yet).

**Verified two ways, and this one took three tries to get the eval fixture right, not just the scoring code:**

1. **Synthetic planted-error eval**, matching the roadmap's own bar ("bad must score lower AND the top issue must match the planted error >= 70% of the time"): a synthetic skeleton with a known, exact ground-truth error. Three fixture designs failed before one worked -- a single animated joint let DTW erase a constant offset by re-timing to a matching phase elsewhere in the periodic signal; three independently-animated sine waves still left enough retiming freedom for DTW to partially hide the error; linear ramps were the worst choice, since for a straight ramp a constant value-offset and a constant time-shift are mathematically interchangeable. What works: independent smoothed random walks per joint (no shift resembles a constant offset of uncorrelated noise), which correctly isolates a planted 25-degree elbow error to `left_elbow` in every synthetic test segment. See `tests/test_scoring.py`'s module docstring for the full story.
2. **Real footage**: the two real solo clips (`professional_dance.mp4`, `user_dance.mp4`) scored against each other end-to-end -- real detection, real tracking, real pose, real DTW, real score. Result: overall score ~39/100, with large (40-90 degree) hip-angle differences that persisted even after the confidence-masking fix above. Checked this against the actual video frames (not just trusted the number): at a comparable timestamp the two dancers' arm positions are visibly different, so a low score isn't obviously wrong -- but hip-angle disagreement specifically is also consistent with a known, unresolved limitation: RTMPose-m here is 2D-only, so a genuine hip-angle difference and a camera-viewpoint difference are indistinguishable to this pipeline. That's a real gap, not a bug to patch by nudging a threshold to make one example look nicer -- see `docs/decisions.md`.

## Roadmap

Phase 2 (detect->track->lock->quality-gate) and Phase 3 (align->score->segment) are both wired end-to-end now, for the auto-lock path and the `needs_dancer_pick` path alike. Still missing: any actual UI (`apps/web` calls none of this), a real eval dataset beyond two synthetic ffmpeg-composited stress clips and one real-but-unlabeled clip pair (roadmap's "film 30 clips yourself, with planted errors" hasn't happened), and the 2D-viewpoint limitation noted above. See [`../../STATUS.md`](../../STATUS.md).
