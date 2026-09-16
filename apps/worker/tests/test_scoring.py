"""Tests worker/pipeline/scoring.py, including a synthetic version of
the roadmap's own eval methodology (Phase 3 section): "Bad must score
lower AND the top issue must match the planted error." There's no
real 10-phrase-pair eval set (that needs actual filmed clips per the
roadmap), but the *logic* that would grade one -- does a planted
elbow error get caught and correctly attributed -- can be verified
against a synthetic skeleton with a known, exact ground truth, which
real footage can never give you (you don't actually know the "true"
joint angle in a real video).

Fixture design note, through two failed attempts before this one:

1. First version animated *one* joint (a sine wave) and planted a
   constant offset on it. DTW erased the offset by re-timing to
   whatever other frame in the periodic wave happened to have a
   matching value -- with one varying feature, a constant amplitude
   offset and a phase shift are indistinguishable.
2. Second version animated *three* joints with different sine
   frequencies, thinking that would over-determine the alignment.
   Still failed: within a short clip, DTW could still find a
   partial shift that reduced total cost by spreading a bit of
   mismatch across all three, instead of showing the true error
   cleanly on the planted joint.
3. Third attempt used linear ramps instead of sine waves, on the
   theory that a monotonic signal can't alias. This is actually the
   *worst* choice: for a linear ramp, a constant value-offset and a
   constant time-shift are mathematically interchangeable (shifting
   a ramp by k frames changes its value by slope*k) -- so DTW could
   trade the planted amplitude error for an equivalent time-shift
   almost for free.

What actually works: independent smoothed random walks (cumulative
sum of Gaussian steps) per joint, seeded for reproducibility. Being
uncorrelated frame-to-frame, no shift of a random walk resembles a
constant offset of it, so DTW has no incentive to move off the true
(near-)diagonal, and a planted offset on one joint shows up as a
genuine, isolated value difference. Real dance has this property for
free -- many joints moving in complex, non-redundant patterns; a
synthetic sine or ramp does not, and using one would have silently
overstated how well this actually works.
"""

from __future__ import annotations

import numpy as np

from worker.pipeline.features import (
    L_ANKLE,
    L_ELBOW,
    L_HIP,
    L_KNEE,
    L_SHOULDER,
    L_WRIST,
    R_ANKLE,
    R_ELBOW,
    R_HIP,
    R_KNEE,
    R_SHOULDER,
    R_WRIST,
)
from worker.pipeline.scoring import score_analysis


def _base_pose() -> np.ndarray:
    kp = np.zeros((17, 2))
    kp[L_SHOULDER], kp[R_SHOULDER] = (0.0, -50.0), (20.0, -50.0)
    kp[L_ELBOW], kp[R_ELBOW] = (0.0, -20.0), (20.0, -20.0)
    kp[L_WRIST], kp[R_WRIST] = (0.0, 10.0), (20.0, 10.0)
    kp[L_HIP], kp[R_HIP] = (0.0, 0.0), (20.0, 0.0)
    kp[L_KNEE], kp[R_KNEE] = (0.0, 40.0), (20.0, 40.0)
    kp[L_ANKLE], kp[R_ANKLE] = (0.0, 80.0), (20.0, 80.0)
    return kp


def _set_angle(kp: np.ndarray, a_idx: int, b_idx: int, c_idx: int, angle_deg: float) -> None:
    """Repositions keypoint c_idx (in place) so the angle at b_idx
    between a_idx and c_idx measures exactly angle_deg, preserving the
    original b-c segment length."""

    a, b, c = kp[a_idx], kp[b_idx], kp[c_idx]
    length_bc = float(np.linalg.norm(c - b))
    unit_ba = (a - b) / np.linalg.norm(a - b)
    theta = np.radians(angle_deg)
    rotation = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    kp[c_idx] = b + (rotation @ unit_ba) * length_bc


def _smoothed_random_walk(num_frames: int, scale: float, offset: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return offset + np.cumsum(rng.normal(scale=scale, size=num_frames))


def _animated_sequence(num_frames: int, left_elbow_offset: float = 0.0) -> list[np.ndarray]:
    elbow_signal = _smoothed_random_walk(num_frames, scale=8.0, offset=135.0, seed=1)
    knee_signal = _smoothed_random_walk(num_frames, scale=6.0, offset=150.0, seed=2)
    hip_signal = _smoothed_random_walk(num_frames, scale=5.0, offset=130.0, seed=3)

    frames = []
    for t in range(num_frames):
        kp = _base_pose()
        _set_angle(kp, L_SHOULDER, L_ELBOW, L_WRIST, elbow_signal[t] + left_elbow_offset)
        _set_angle(kp, R_HIP, R_KNEE, R_ANKLE, knee_signal[t])
        _set_angle(kp, L_SHOULDER, L_HIP, L_KNEE, hip_signal[t])
        frames.append(kp)
    return frames


def test_identical_sequences_score_near_100():
    frames = _animated_sequence(40)
    frame_indices = list(range(40))

    result = score_analysis(frames, frame_indices, 30.0, frames, frame_indices, 30.0)

    assert result.overall_score > 99.0
    for segment in result.segments:
        assert segment.issues == []


def test_planted_elbow_error_is_caught_and_correctly_attributed():
    reference = _animated_sequence(40)
    frame_indices = list(range(40))

    planted_error_deg = 25.0
    bad_user = _animated_sequence(40, left_elbow_offset=planted_error_deg)

    good_result = score_analysis(reference, frame_indices, 30.0, reference, frame_indices, 30.0)
    bad_result = score_analysis(reference, frame_indices, 30.0, bad_user, frame_indices, 30.0)

    # 1. bad must score lower
    assert bad_result.overall_score < good_result.overall_score

    # 2. the top issue in every segment must correctly name the planted joint
    assert len(bad_result.segments) > 0
    hits = 0
    for segment in bad_result.segments:
        assert segment.issues, "expected the planted error to surface as an issue"
        top_issue = segment.issues[0]
        if top_issue.joint == "left_elbow":
            hits += 1
    hit_rate = hits / len(bad_result.segments)
    # roadmap's own bar: >= 70% planted-error attribution accuracy
    assert hit_rate >= 0.70, f"only {hit_rate:.0%} of segments correctly attributed the planted error"


def test_planted_error_magnitude_is_recovered_approximately():
    reference = _animated_sequence(40)
    frame_indices = list(range(40))
    planted_error_deg = 25.0
    bad_user = _animated_sequence(40, left_elbow_offset=planted_error_deg)

    result = score_analysis(reference, frame_indices, 30.0, bad_user, frame_indices, 30.0)

    magnitudes = [
        issue.magnitude
        for segment in result.segments
        for issue in segment.issues
        if issue.joint == "left_elbow"
    ]
    assert magnitudes, "expected at least one left_elbow issue"
    assert abs(np.mean(magnitudes) - planted_error_deg) < 3.0


def test_unrelated_joints_are_not_flagged_by_an_elbow_only_error():
    reference = _animated_sequence(40)
    frame_indices = list(range(40))
    bad_user = _animated_sequence(40, left_elbow_offset=25.0)

    result = score_analysis(reference, frame_indices, 30.0, bad_user, frame_indices, 30.0)

    flagged_joints = {issue.joint for segment in result.segments for issue in segment.issues}
    assert "left_knee" not in flagged_joints
    assert "right_elbow" not in flagged_joints
    assert "right_knee" not in flagged_joints
    assert "left_hip" not in flagged_joints


def test_segments_are_ordered_and_cover_the_reference_timeline():
    frames = _animated_sequence(90)  # 3s at 30fps
    frame_indices = list(range(90))

    result = score_analysis(frames, frame_indices, 30.0, frames, frame_indices, 30.0, segment_seconds=1.0)

    assert len(result.segments) >= 2
    for prev, curr in zip(result.segments, result.segments[1:]):
        assert curr.t0 >= prev.t0
    assert result.segments[0].t0 == 0.0


def test_timing_drift_is_detected_when_user_runs_late():
    # 150 identical frames, but "user" is claimed to be recorded at a
    # slower fps than the reference -- so per-frame the values match
    # exactly (DTW aligns on the diagonal, unambiguously optimal since
    # cost is truly zero there), but the *wall-clock* gap between
    # reference-time and user-time grows across the clip. Needs
    # multiple 2s segments (hence 150 frames, not 40) so the drift in
    # a later segment has an earlier segment's baseline to be measured
    # against.
    frames = _animated_sequence(150)
    reference_indices = list(range(150))
    user_indices = list(range(150))

    result = score_analysis(frames, reference_indices, 30.0, frames, user_indices, 20.0)

    timing_issues = [
        issue for segment in result.segments for issue in segment.issues if issue.type == "timing"
    ]
    assert timing_issues, "expected the growing lag from the fps mismatch to be flagged as a timing issue"
    # the drift is monotonically growing, so it should show up as
    # "behind", not "ahead of"
    assert all("behind" in issue.message for issue in timing_issues)


def test_empty_reference_returns_zero_score_without_crashing():
    result = score_analysis([], [], 30.0, [np.zeros((17, 2))], [0], 30.0)
    assert result.overall_score == 0.0
    assert result.segments == []


def test_low_confidence_joint_does_not_produce_a_spurious_issue():
    """Found by comparing real pipeline output against real footage:
    two chest-up-framed clips reported huge hip/knee "errors" that
    were actually just RTMPose guessing at off-screen joints, not real
    technique differences. This is the regression test for the fix
    (features.joint_angles' confidence masking) -- a joint that's
    consistently low-confidence in the user clip shouldn't surface an
    issue even if its raw geometric angle differs a lot from the
    reference."""

    num_frames = 40
    reference = _animated_sequence(num_frames)
    # planted knee error, but the knee is (realistically) low-confidence
    # throughout -- e.g. out of frame
    bad_user = _animated_sequence(num_frames, left_elbow_offset=0.0)
    for kp in bad_user:
        _set_angle(kp, R_HIP, R_KNEE, R_ANKLE, 40.0)  # wildly different from reference's knee

    frame_indices = list(range(num_frames))
    low_confidence_knee = np.ones(17)
    low_confidence_knee[R_KNEE] = 0.05
    user_scores = [low_confidence_knee.copy() for _ in range(num_frames)]
    reference_scores = [np.ones(17) for _ in range(num_frames)]

    result = score_analysis(
        reference,
        frame_indices,
        30.0,
        bad_user,
        frame_indices,
        30.0,
        reference_scores=reference_scores,
        user_scores=user_scores,
    )

    flagged_joints = {issue.joint for segment in result.segments for issue in segment.issues}
    assert "right_knee" not in flagged_joints
