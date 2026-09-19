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

**No Docker?** `scripts/dev_fake_redis.py` + `scripts/dev_worker_no_info.py` run the real worker against a pure-Python fake Redis (`pip install "fakeredis>=2.26"`; see each file's docstring). Set the same `DATABASE_URL` (an absolute SQLite path -- the default is relative to the working directory, so the API and worker would otherwise each write their own file) and `REDIS_URL=redis://127.0.0.1:6379` for both the API and the worker. This is how the API -> queue -> worker -> DB -> UI path was first verified end to end. Dev convenience only: in-memory, one process, not a substitute for testing against real Redis.

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

**If the pipeline throws**, both jobs record it on the analysis row as `rejected` ("something went wrong on our side") and log the traceback, rather than leaving the row `queued` forever with the UI polling it -- see `docs/decisions.md` for why it reuses `rejected`. A worker that's killed mid-job never gets to record anything; that row still stays `queued`.

`tasks.py` exposes:
- `detect_tracks_job(analysis_id, video_path)` — what `apps/api`'s `POST /analyses` actually enqueues now. Runs detection, then either auto-locks a single confident track (locks it, saves its keypoints, scores it against the reference video -- see Phase 3 below -- and writes a final `complete`/`rejected` `AnalysisResult` straight into the shared `analyses` table, `packages/db`, both this app and `apps/api` talking to the same DB directly, no callback API between them) or, if `is_lock_ambiguous` says no track is clearly dominant, marks the row `needs_dancer_pick` and stashes the raw detections in `Analysis.pending_lock_data` for later.
- `extract_locked_pose_job(analysis_id, video_path, track_id, fps, total_frames, detections)` — resumes from stashed detections once a track is picked, without re-running YOLO. Enqueued by `apps/api`'s `POST /analyses/{id}/lock`. Shares the same lock-then-score tail as `detect_tracks_job`'s auto-lock path (`_finish_lock` in `tasks.py`), and clears `pending_lock_data` once done.

**Duo/mirror stress test** (see `STATUS.md` for the full numbers): built two synthetic clips from real footage with `ffmpeg` — two distinct real dancers side by side, and one dancer next to their own flipped reflection. The duo case tracked cleanly (2 stable tracks). The mirror case produced 4 fragmented track IDs and would have silently auto-locked onto whichever had the most frames without `is_lock_ambiguous` — with it, both cases now correctly get flagged `needs_dancer_pick` instead of a confident wrong guess. That heuristic hasn't been tuned against a real eval set (still just these two synthetic clips), so treat its threshold as a reasonable default, not a validated one.

## Scoring (Phase 3)

Once the user's video is locked, `tasks.py` also runs the reference (professional) video through the same detect+lock pipeline (assumed solo/clean; a messy reference is a real if rare failure mode, handled by rejecting with a clear reason, not assumed away) and scores the two against each other:

- `features.py` — converts RTMPose's 17 keypoints into 8 joint angles (elbow/knee/hip/shoulder, both sides) + two camera-frame measures that are per-video baseline-corrected (median-subtracted) so what's compared is *change over time*, not an absolute value that differs for reasons unrelated to technique: spine lean (torso tilt) and `balance_offset` (hip midpoint's horizontal distance from the ankle midpoint -- the base of support, normalized by hip width). Angles between three skeletal points are automatically invariant to translation, scale, and in-plane rotation, unlike raw (x, y) coordinates -- this is what makes them comparable between two videos shot from different distances/angles without an explicit Procrustes step. Masks a joint to NaN if any of its keypoints is below `DEFAULT_MIN_CONFIDENCE` (0.3) -- RTMPose still emits *some* coordinate for an occluded/uncertain keypoint, extrapolated from its training prior, and treating that as real signal was a real bug this file had, caught by comparing output against real footage (see below).
- `alignment.py` — classic DTW (a plain numpy DP table, no external dependency) on the two feature sequences, producing a frame-to-frame warping path. O(N\*M) time and memory -- fine for the clips tested (a few hundred frames), not verified to scale to the platform's 5-minute upload limit; a Sakoe-Chiba band is the standard fix if that turns out to matter.
- `scoring.py` — segments the warping path into ~2s windows (in the reference video's own timeline) and produces up to six issue types per window:
  - `angle` — a limb joint or torso lean off by more than 15 degrees. `joint` names the specific one (e.g. `left_elbow`); there's no separate arm-vs-leg type, since the joint name already says which.
  - `timing` — a growing reference/user time gap. Independent of the score.
  - `occlusion` — a joint was too low-confidence to trust for >=30% of this window. Suppresses that joint's `angle` issue in the same window (an angle from mostly-missing data isn't a technique finding).
  - `tempo` — the user's matched span in this window lasts much longer or shorter (in *seconds*, not frames -- see the real-footage note below) than the reference's, a proxy for a move likely skipped/rushed or added/repeated.
  - `energy` — limb movement over a fixed 0.1 s lag in this window is under half the reference's (only checked when the reference itself has enough motion to compare against).
  - `balance` — hip position wanders from the ankle-to-ankle base of support more than the reference's own baseline. Suppressed when the ankles were too low-confidence to trust for >=30% of the window on either clip (same rule as `occlusion`).
  - `path` (schema reserves this for spatial trajectory deviation) is still not generated.

  Score itself only ever comes from the degrees-based features (limb angles + spine lean) via `100 * exp(-error/TAU)` (TAU chosen so a 20-degree average error gives 50%) -- a formula over a normalized, rotation-invariant feature, not the raw-pixel-distance formula the roadmap's own Section 7 calls out as a fake score. `balance_offset` is a dimensionless ratio, not degrees, so it never feeds the score -- it only ever produces its own `balance` issue.

  **`occlusion`/`tempo`/`energy`/`balance` are new and unvalidated against real footage** -- unlike `angle`/`timing`, which have both a real-motion planted-error eval (below) and a real-clip run behind them, these four have only been checked against synthetic ground truth so far (see `tests/test_scoring.py`). Their thresholds (30% for occlusion, 0.6-1.6x span ratio for tempo, 50% energy ratio, 0.15 for balance) are reasonable-looking defaults, not tuned against anything -- treat them as a first pass, not a validated bar, until they've run against more than one clip.

  **First real-footage run of these four types found three real bugs, none visible in any synthetic test** (run through the actual API -> queue -> worker -> DB path on the two real clips; ~60 fps reference vs. ~30 fps user):
  1. `tempo` fired in all 4 windows at ~0.5 -- it compared raw frame counts, so any frame-rate difference between the clips read as "half the frames." Fixed by comparing durations in seconds. (Every synthetic test used matching 30/30 fps, which is why none could catch it.)
  2. Fixing that exposed `energy` firing in 3 windows at 0.39-0.47. First attempt (scale per-frame change by fps) was wrong: rough motion and pose jitter don't scale linearly with frame spacing, and it failed a frame-rate-swap test. Now measured as mean change over a fixed 0.1 s real-time lag. That still fired, until an independent check -- whole-clip motion computed straight from the saved keypoints, which came out *identical* for both dancers (16.85 vs. 16.96 deg at the same lag) -- showed the flags weren't real: `energy` was reading DTW-*path* indices, where each 30 fps user frame repeats ~2x against a 60 fps reference, so a "3-frame lag" spanned half the real time. Fixed by deduping the indices.
  3. `balance` fired twice at 0.62-0.70 hip-widths (enormous), but on these clips the ankles clear the 0.3 confidence bar in only 32-62% of frames (mean confidence ~0.3, right at the threshold) -- the framing cuts off the legs -- so it was measuring guesses. Now gated on ankle visibility, mirroring `occlusion`.

  After all three fixes the real pair produces `angle` (17), `occlusion` (9), `timing` (2) and none of `tempo`/`energy`/`balance`; overall score unchanged (38.65, matching the earlier real-clip number). **What this does and doesn't show:** the three types stopped false-firing on one real pair, with a regression test per fix (`test_same_motion_at_different_frame_rates_*`, `test_balance_issue_is_suppressed_*`). It does *not* show they fire correctly on real errors -- true-positive evidence for these types is still only synthetic, and the thresholds are still untuned defaults.

  **True-positive evidence on real motion** (`scripts/eval_planted_signals.py`, fast regression subset in `tests/test_scoring_real_motion_eval.py`): plants one known change into a REAL extracted sequence -- both clips used as bases, each run with the user side at the same fps *and* at half fps -- and checks the right issue appears in the right windows:
  - **`tempo`: 30/36 = 83%** on skipped/repeated chunks the design should be able to catch, **0/32 false-positive windows**, and 0/24 flagged among edits below the design's own floor. Misses are all 1.2 s skips; they likely straddle a 2 s window boundary (the check needs ~0.8 s of missing time inside one window, so sensitivity depends on where the edit falls -- inferred from the pattern, not separately proven).
  - **`energy`: 10/10**, 0/64 false-positive windows. It only flags a real reduction to under half the reference's angle-space energy -- damping keypoint motion by 0.15 (energy ratio 0.20-0.34) is flagged in every window; 0.25-0.4 sits on the boundary; 0.7 is correctly silent.
  - **`occlusion`: 4/4**, 0 false positives (a masked wrist is reported as `occlusion` on `right_elbow` in every window fully inside the masked span).
  - Unedited copies at both frame-rate configs raise no `tempo`/`energy`/`balance`.

  **The first run of this eval reported `energy` 4/8 and `occlusion` 2/4 (FAIL), and both were errors in the eval, not the detector** -- corrected once, kept here so the numbers above aren't mistaken for a run that passed first time. (1) It assumed shrinking keypoint motion by 0.4 shrinks joint-angle energy by 0.4; measured, it gives 0.57-0.67 -- above the 0.5 threshold, so `energy` correctly stayed silent. Cases are now labelled by the ratio they actually produce. (2) On the user clip the occlusion mask left zero windows fully inside it, so "0/0" was no evidence either way; the mask now covers whole windows. The detector code and its thresholds were not touched between the two runs.

  **What this still doesn't show:** the "user" here is the reference with one edit -- an easier setting than two independently performed takes (no genuine dancer-to-dancer variation), though the pose noise, jitter and low-confidence keypoints are real. And **`balance` has no true-positive evidence at all**: it needs the ankles visible, and on the available clips they clear the confidence bar in only ~30-60% of frames, so the new visibility gate correctly suppresses it. That needs a full-body clip.

  **A real regression, caught by re-running the real-motion eval below, not just the new unit tests.** Adding `occlusion` first broke the *existing* `angle`/`timing` attribution accuracy: the first version put occlusion issues ahead of angle issues in each window's issue list (`issues = occlusion_issues + angle_issues`), so on real footage -- where some joint dips below the confidence threshold for part of a window fairly often, unrelated to whatever's actually wrong -- the "top issue" for a window was frequently an irrelevant occlusion notice instead of the real angle error. The real-motion planted-error regression test (below) caught this immediately: hit rate collapsed from the previously-measured 82% to 20%. All 59 synthetic unit tests still passed throughout, because none of their fixtures happen to trigger occlusion on an unrelated joint in the same window as a planted error -- a real example of why this project keeps a real-footage eval and doesn't treat synthetic-test-green as sufficient. Fixed by reordering: angle issues (they name a specific joint and a specific error -- the actual technique feedback) now lead the list, with occlusion/balance/tempo/energy/timing as secondary context after. Re-ran: 80% (16/20), back above the 70% bar.

**Verified two ways, and this one took three tries to get the eval fixture right, not just the scoring code:**

1. **Synthetic planted-error eval**, matching the roadmap's own bar ("bad must score lower AND the top issue must match the planted error >= 70% of the time"): a synthetic skeleton with a known, exact ground-truth error. Three fixture designs failed before one worked -- a single animated joint let DTW erase a constant offset by re-timing to a matching phase elsewhere in the periodic signal; three independently-animated sine waves still left enough retiming freedom for DTW to partially hide the error; linear ramps were the worst choice, since for a straight ramp a constant value-offset and a constant time-shift are mathematically interchangeable. What works: independent smoothed random walks per joint (no shift resembles a constant offset of uncorrelated noise), which correctly isolates a planted 25-degree elbow error to `left_elbow` in every synthetic test segment. See `tests/test_scoring.py`'s module docstring for the full story.
2. **Real footage, self-comparison**: the two real solo clips (`professional_dance.mp4`, `user_dance.mp4`) scored against each other end-to-end -- real detection, real tracking, real pose, real DTW, real score. Result: overall score ~39/100, with large (40-90 degree) hip-angle differences that persisted even after the confidence-masking fix above. Checked this against the actual video frames (not just trusted the number): at a comparable timestamp the two dancers' arm positions are visibly different, so a low score isn't obviously wrong -- but hip-angle disagreement specifically is also consistent with a known, unresolved limitation: RTMPose-m here is 2D-only, so a genuine hip-angle difference and a camera-viewpoint difference are indistinguishable to this pipeline. That's a real gap, not a bug to patch by nudging a threshold to make one example look nicer -- see `docs/decisions.md`.
3. **Real motion, planted errors** (`scripts/eval_planted_errors.py`, regression-tested in `tests/test_scoring_real_motion_eval.py`): there's only one real clip pair on this dev machine and no real labeled good/bad pairs (that needs new footage), so this corrupts a REAL extracted pose sequence -- not a synthetic skeleton -- with a KNOWN, controlled offset on one joint at a time. Real motion's joint-to-joint correlation makes this harder to game than the fully-synthetic eval above, and it surfaced something the synthetic one couldn't: **82% single-joint attribution hit rate** on real motion (above the 70% target), but hip/shoulder corruptions partially "leak" into the adjacent knee/elbow reading (2/4 instead of 4/4) -- because the corruption technique rotates a joint's *distal* keypoint, and for hip/shoulder that keypoint is also the *vertex* of the next joint down the chain, so moving it genuinely changes that neighbor's angle too. Not a scoring bug; a limitation of this corruption method for adjacent-joint pairs specifically. Run it yourself against any `*_keypoints.npz` with `python scripts/eval_planted_errors.py --keypoints <path>`.

## Roadmap

Phase 2 (detect->track->lock->quality-gate) and Phase 3 (align->score->segment) are both wired end-to-end now, for the auto-lock path and the `needs_dancer_pick` path alike. Still missing: any actual UI (`apps/web` calls none of this), *filmed* good/known-bad phrase pairs (roadmap's "film 30 clips yourself, with planted errors" -- what exists is a real-motion proxy for that, corrupted from one real clip, not independently filmed pairs), and the 2D-viewpoint limitation noted above. See [`../../STATUS.md`](../../STATUS.md).
