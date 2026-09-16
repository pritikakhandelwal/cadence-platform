#!/usr/bin/env python
"""Planted-error eval, using a REAL extracted pose sequence as the base.

Roadmap eval methodology (Phase 2/3): "10 phrase pairs (good vs
known-bad). Bad must score lower AND the top issue must match the
planted error >= 70% of the time." No real filmed good/bad pairs
exist yet -- that needs new footage this project doesn't have. The
existing unit-test eval (apps/worker/tests/test_scoring.py) proves the
*logic* against a fully synthetic skeleton, which has exact ground
truth but none of the joint-to-joint correlation real human motion
has. This script closes that gap: it corrupts a REAL extracted pose
sequence with a KNOWN, controlled offset on one joint at a time --
real motion complexity, exact ground truth.

Usage:
    python scripts/eval_planted_errors.py --keypoints <npz path>

The npz must have `keypoints` (T, 17, 2), `scores` (T, 17),
`frame_indices` (T,), `fps` (scalar) -- the same shape
tasks.py._save_keypoints writes. Get one by running the real pipeline
once (see apps/worker/README.md's Phase 2 integration tests for how)
and pointing this script at the resulting *_keypoints.npz, or at
professional_keypoints.npz / user_keypoints.npz in any analysis
workspace under runtime/analyses/<id>/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from worker.pipeline.features import JOINT_ANGLE_TRIPLES
from worker.pipeline.scoring import score_analysis

# (joint_name, offset_degrees) -- the planted error for each variant.
# None offset = the clean, unmodified copy (sanity check: should score
# ~100 with no issues).
VARIANTS: list[tuple[str, str | None, float]] = [
    ("clean", None, 0.0),
    ("left_elbow_small", "left_elbow", 8.0),  # below the 15-degree issue threshold on purpose
    ("left_elbow_medium", "left_elbow", 20.0),
    ("left_elbow_large", "left_elbow", 35.0),
    ("right_elbow_medium", "right_elbow", -20.0),
    ("left_knee_medium", "left_knee", 25.0),
    ("right_knee_medium", "right_knee", -25.0),
    ("left_hip_medium", "left_hip", 22.0),
    ("right_shoulder_medium", "right_shoulder", 20.0),
    ("combined_elbow_and_knee", None, 0.0),  # handled specially below
]

# roadmap's own bar
TARGET_HIT_RATE = 0.70
# below this, a planted error shouldn't reliably show up as an issue --
# excluded from the hit-rate calculation, not counted as a miss
ISSUE_THRESHOLD_DEG = 15.0


def apply_joint_offset(keypoints: np.ndarray, joint_name: str, offset_deg: float) -> np.ndarray:
    """Returns a copy of `keypoints` (17, 2) with `joint_name`'s angle
    rotated by offset_deg, preserving the distal segment's length.
    Uses the same JOINT_ANGLE_TRIPLES production code uses, so
    'left_elbow' etc. mean the same thing everywhere."""

    _, b_idx, c_idx = JOINT_ANGLE_TRIPLES[joint_name]
    kp = keypoints.copy()
    b, c = kp[b_idx], kp[c_idx]
    theta = np.radians(offset_deg)
    rotation = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    kp[c_idx] = b + rotation @ (c - b)
    return kp


def corrupt_sequence(
    keypoints: list[np.ndarray], joint_offsets: dict[str, float]
) -> list[np.ndarray]:
    corrupted = []
    for kp in keypoints:
        frame = kp
        for joint_name, offset_deg in joint_offsets.items():
            frame = apply_joint_offset(frame, joint_name, offset_deg)
        corrupted.append(frame)
    return corrupted


def run_eval(npz_path: Path) -> None:
    data = np.load(npz_path)
    keypoints = list(data["keypoints"])
    scores = list(data["scores"])
    frame_indices = list(data["frame_indices"])
    fps = float(data["fps"])

    print(f"Loaded {len(keypoints)} real frames from {npz_path.name} (fps={fps:.1f})\n")

    clean_result = score_analysis(
        keypoints, frame_indices, fps, keypoints, frame_indices, fps,
        reference_scores=scores, user_scores=scores,
    )
    print(f"{'variant':<28} {'score':>7}  {'top issue per segment'}")
    print("-" * 90)
    print(f"{'clean (self-comparison)':<28} {clean_result.overall_score:>6.1f}  (expect ~100, no issues)")

    hits = 0
    total = 0
    for name, joint, offset in VARIANTS[1:-1]:  # skip "clean" (done above) and "combined" (done below)
        bad_keypoints = corrupt_sequence(keypoints, {joint: offset})
        result = score_analysis(
            keypoints, frame_indices, fps, bad_keypoints, frame_indices, fps,
            reference_scores=scores, user_scores=scores,
        )
        top_issues = [seg.issues[0].joint if seg.issues else "-" for seg in result.segments]
        matches = sum(1 for j in top_issues if j == joint)

        expect_issue = abs(offset) >= ISSUE_THRESHOLD_DEG
        if expect_issue:
            total += len(top_issues)
            hits += matches

        print(
            f"{name:<28} {result.overall_score:>6.1f}  planted={joint}({offset:+.0f}) "
            f"top_issues={top_issues} matches={matches}/{len(top_issues)}"
        )

    combined_keypoints = corrupt_sequence(keypoints, {"left_elbow": 25.0, "right_knee": 25.0})
    combined_result = score_analysis(
        keypoints, frame_indices, fps, combined_keypoints, frame_indices, fps,
        reference_scores=scores, user_scores=scores,
    )
    top2_issues = [
        {issue.joint for issue in seg.issues[:2]} if seg.issues else set()
        for seg in combined_result.segments
    ]
    both_found = sum(1 for s in top2_issues if {"left_elbow", "right_knee"} <= s)
    print(
        f"{'combined_elbow_and_knee':<28} {combined_result.overall_score:>6.1f}  "
        f"planted=left_elbow(+25)+right_knee(+25) both_in_top2={both_found}/{len(top2_issues)}"
    )

    hit_rate = hits / total if total else 0.0
    print(f"\nSingle-joint planted-error attribution hit rate: {hit_rate:.0%} "
          f"({hits}/{total} segments) -- roadmap target: >= {TARGET_HIT_RATE:.0%}")
    print("PASS" if hit_rate >= TARGET_HIT_RATE else "FAIL")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keypoints", type=Path, required=True, help="Path to a *_keypoints.npz file")
    args = parser.parse_args()
    run_eval(args.keypoints)
