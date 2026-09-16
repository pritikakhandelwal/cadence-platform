"""Runs scripts/eval_planted_errors.py's methodology as a real,
re-runnable regression test -- extracts real keypoints fresh from the
real solo clip (same pattern as the other integration tests: skips
cleanly if ultralytics/rtmlib aren't installed or the clip isn't
present) rather than relying on a committed fixture. The extracted
keypoints are real motion capture, not committed to the repo (derived
from third-party footage; kept local-only the same way the source
clips themselves are) -- see apps/worker/README.md's Phase 3 section
and scripts/eval_planted_errors.py's module docstring for why this
exists alongside the fully-synthetic eval in test_scoring.py.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

pytest.importorskip("ultralytics")
pytest.importorskip("rtmlib")

_SAMPLE_VIDEO = Path(
    os.environ.get(
        "CADENCE_SAMPLE_VIDEO",
        r"C:\Users\khand\Downloads\CADENCE\data\professional\professional_dance.mp4",
    )
)
if not _SAMPLE_VIDEO.is_file():
    pytest.skip(f"sample video not found at {_SAMPLE_VIDEO}", allow_module_level=True)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from eval_planted_errors import ISSUE_THRESHOLD_DEG, TARGET_HIT_RATE, apply_joint_offset, corrupt_sequence  # noqa: E402


@pytest.fixture(scope="module")
def real_pose_sequence():
    from worker.pipeline.pipeline import detect_tracks, extract_locked_pose

    summary, detections = detect_tracks(_SAMPLE_VIDEO)
    track_id = summary.tracks[0].track_id
    locked = extract_locked_pose(_SAMPLE_VIDEO, detections, track_id, summary.fps, summary.total_frames)
    assert locked.quality_gate.passed
    return locked


def test_planted_error_attribution_meets_roadmap_bar_on_real_motion(real_pose_sequence):
    """The regression-test version of scripts/eval_planted_errors.py:
    fewer variants (elbow, knee -- the joints least entangled with a
    neighboring triple, see the script's module docstring on why hip/
    shoulder corruptions partially leak into knee/elbow), but the same
    real motion and the same >=70% bar."""

    from worker.pipeline.scoring import score_analysis

    keypoints = real_pose_sequence.keypoints
    scores = real_pose_sequence.scores
    frame_indices = real_pose_sequence.frame_indices
    fps = real_pose_sequence.fps

    variants = [
        ("left_elbow", 20.0),
        ("left_elbow", 35.0),
        ("right_elbow", -20.0),
        ("left_knee", 25.0),
        ("right_knee", -25.0),
    ]

    hits = 0
    total = 0
    for joint, offset in variants:
        bad_keypoints = corrupt_sequence(keypoints, {joint: offset})
        result = score_analysis(
            keypoints, frame_indices, fps, bad_keypoints, frame_indices, fps,
            reference_scores=scores, user_scores=scores,
        )
        assert result.segments, f"expected at least one segment for {joint}"
        for segment in result.segments:
            total += 1
            if segment.issues and segment.issues[0].joint == joint:
                hits += 1

    hit_rate = hits / total
    assert hit_rate >= TARGET_HIT_RATE, f"only {hit_rate:.0%} ({hits}/{total}) met the roadmap's 70% bar"


def test_a_below_threshold_offset_does_not_produce_a_spurious_issue(real_pose_sequence):
    keypoints = real_pose_sequence.keypoints
    scores = real_pose_sequence.scores
    frame_indices = real_pose_sequence.frame_indices
    fps = real_pose_sequence.fps

    small_offset = ISSUE_THRESHOLD_DEG - 5.0
    bad_keypoints = corrupt_sequence(keypoints, {"left_elbow": small_offset})

    from worker.pipeline.scoring import score_analysis

    result = score_analysis(
        keypoints, frame_indices, fps, bad_keypoints, frame_indices, fps,
        reference_scores=scores, user_scores=scores,
    )
    flagged = {issue.joint for segment in result.segments for issue in segment.issues}
    assert "left_elbow" not in flagged


def test_self_comparison_of_real_motion_scores_near_100(real_pose_sequence):
    from worker.pipeline.scoring import score_analysis

    keypoints = real_pose_sequence.keypoints
    scores = real_pose_sequence.scores
    frame_indices = real_pose_sequence.frame_indices
    fps = real_pose_sequence.fps

    result = score_analysis(
        keypoints, frame_indices, fps, keypoints, frame_indices, fps,
        reference_scores=scores, user_scores=scores,
    )
    assert result.overall_score > 99.0
