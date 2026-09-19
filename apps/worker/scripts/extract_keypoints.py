#!/usr/bin/env python
"""Run the real detect -> track -> lock -> pose pipeline on one video and
save the result as a *_keypoints.npz -- the same format tasks.py writes
into an analysis workspace, and what the eval scripts (eval_planted_errors.py,
eval_planted_signals.py) take as input.

    python scripts/extract_keypoints.py --video clip.mp4 --out clip_keypoints.npz

Locks the track with the most frames unless --track-id is given. Needs
ultralytics + rtmlib (apps/worker/requirements.txt). Keypoints derived
from third-party footage shouldn't be committed -- keep the output local.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from worker.pipeline.pipeline import detect_tracks, extract_locked_pose


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--track-id", type=int, default=None)
    args = parser.parse_args()

    summary, detections = detect_tracks(args.video)
    for track in summary.tracks:
        print(f"track {track.track_id}: {track.frame_count} frames, mean confidence {track.mean_confidence:.2f}")

    track_id = args.track_id
    if track_id is None:
        track_id = max(summary.tracks, key=lambda t: t.frame_count).track_id
    print(f"locking track {track_id}")

    locked = extract_locked_pose(args.video, detections, track_id, summary.fps, summary.total_frames)
    print(f"quality gate passed={locked.quality_gate.passed} reasons={locked.quality_gate.reasons}")

    np.savez(
        args.out,
        keypoints=np.array(locked.keypoints),
        scores=np.array(locked.scores),
        frame_indices=np.array(locked.frame_indices),
        fps=locked.fps,
    )
    print(f"saved {len(locked.keypoints)} frames at {locked.fps:.1f} fps to {args.out}")


if __name__ == "__main__":
    main()
