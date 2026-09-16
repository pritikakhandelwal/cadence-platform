from __future__ import annotations

import numpy as np

from worker.pipeline.features import (
    FEATURE_NAMES,
    L_ANKLE,
    L_ELBOW,
    L_HIP,
    L_KNEE,
    L_SHOULDER,
    L_WRIST,
    joint_angles,
    spine_lean_deg,
    feature_sequence,
)


def _straight_leg_pose() -> np.ndarray:
    kp = np.zeros((17, 2))
    kp[L_HIP] = (0, 0)
    kp[L_KNEE] = (0, 40)
    kp[L_ANKLE] = (0, 80)
    kp[L_SHOULDER] = (0, -50)
    kp[L_ELBOW] = (0, -20)
    kp[L_WRIST] = (0, 10)
    return kp


def test_straight_limbs_measure_180_degrees():
    kp = _straight_leg_pose()
    angles = joint_angles(kp)
    assert angles["left_knee"] == 180.0
    assert angles["left_elbow"] == 180.0


def test_right_angle_elbow_measures_90_degrees():
    kp = _straight_leg_pose()
    # bend the forearm to point straight out sideways from the elbow
    kp[L_WRIST] = kp[L_ELBOW] + np.array([30.0, 0.0])
    angles = joint_angles(kp)
    assert abs(angles["left_elbow"] - 90.0) < 1e-6


def test_degenerate_zero_length_segment_gives_nan():
    kp = _straight_leg_pose()
    kp[L_WRIST] = kp[L_ELBOW]  # zero-length forearm
    angles = joint_angles(kp)
    assert np.isnan(angles["left_elbow"])


def test_joint_angle_is_translation_invariant():
    kp = _straight_leg_pose()
    shifted = kp + np.array([500.0, -300.0])
    original, moved = joint_angles(kp), joint_angles(shifted)
    for name in original:
        # np.nan != np.nan, so a straight `==` comparison would fail on
        # the fixture's degenerate right-side joints even though both
        # sides genuinely agree (both NaN) -- compare NaN-aware instead.
        if np.isnan(original[name]):
            assert np.isnan(moved[name])
        else:
            assert original[name] == moved[name]


def test_joint_angle_is_scale_invariant():
    kp = _straight_leg_pose()
    kp[L_WRIST] = kp[L_ELBOW] + np.array([30.0, 0.0])
    scaled = kp * 3.0
    a = joint_angles(kp)["left_elbow"]
    b = joint_angles(scaled)["left_elbow"]
    assert abs(a - b) < 1e-9


def test_spine_lean_zero_when_upright():
    kp = _straight_leg_pose()
    kp[11] = (0, 0)  # L_HIP
    kp[12] = (20, 0)  # R_HIP
    kp[5] = (0, -50)  # L_SHOULDER
    kp[6] = (20, -50)  # R_SHOULDER
    assert abs(spine_lean_deg(kp)) < 1e-9


def test_spine_lean_nonzero_when_leaning():
    kp = _straight_leg_pose()
    kp[11] = (0, 0)
    kp[12] = (20, 0)
    kp[5] = (30, -50)  # shoulders shifted sideways relative to hips
    kp[6] = (50, -50)
    assert abs(spine_lean_deg(kp)) > 10.0


def test_feature_sequence_shape_matches_feature_names():
    frames = [_straight_leg_pose() for _ in range(5)]
    matrix = feature_sequence(frames)
    assert matrix.shape == (5, len(FEATURE_NAMES))


def test_feature_sequence_empty_input():
    matrix = feature_sequence([])
    assert matrix.shape == (0, len(FEATURE_NAMES))


def test_low_confidence_keypoint_masks_its_joint_angle_to_nan():
    kp = _straight_leg_pose()
    assert joint_angles(kp)["left_knee"] == 180.0  # no scores given: trusted as-is

    scores = np.ones(17)
    scores[L_KNEE] = 0.1  # e.g. an off-screen/occluded knee RTMPose still guessed a position for
    angles = joint_angles(kp, scores=scores)
    assert np.isnan(angles["left_knee"])
    # an unrelated joint whose keypoints are all high-confidence should be unaffected
    assert angles["left_elbow"] == 180.0


def test_confidence_at_exactly_the_threshold_is_not_masked():
    kp = _straight_leg_pose()
    scores = np.ones(17)
    scores[L_KNEE] = 0.3  # == DEFAULT_MIN_CONFIDENCE
    angles = joint_angles(kp, scores=scores, min_confidence=0.3)
    assert angles["left_knee"] == 180.0


def test_spine_lean_masked_when_a_hip_or_shoulder_is_low_confidence():
    kp = _straight_leg_pose()
    kp[11], kp[12] = (0, 0), (20, 0)
    kp[5], kp[6] = (30, -50), (50, -50)
    scores = np.ones(17)
    scores[11] = 0.0  # L_HIP
    assert np.isnan(spine_lean_deg(kp, scores=scores))


def test_feature_sequence_masks_low_confidence_frames():
    frames = [_straight_leg_pose() for _ in range(3)]
    scores = [np.ones(17), np.ones(17), np.ones(17)]
    scores[1][L_KNEE] = 0.0  # only the middle frame's knee is untrustworthy

    matrix = feature_sequence(frames, score_sequence=scores)
    knee_idx = FEATURE_NAMES.index("left_knee")
    assert matrix[0, knee_idx] == 180.0
    assert np.isnan(matrix[1, knee_idx])
    assert matrix[2, knee_idx] == 180.0


def test_feature_sequence_baseline_corrects_spine_lean():
    # every frame has the exact same constant lean -- after baseline
    # correction (subtract the sequence's own median), it should
    # become ~0, since there's no *change* in lean to report
    frames = []
    for _ in range(5):
        kp = _straight_leg_pose()
        kp[11] = (0, 0)
        kp[12] = (20, 0)
        kp[5] = (30, -50)
        kp[6] = (50, -50)
        frames.append(kp)
    matrix = feature_sequence(frames)
    spine_idx = FEATURE_NAMES.index("spine_lean")
    assert np.allclose(matrix[:, spine_idx], 0.0)
