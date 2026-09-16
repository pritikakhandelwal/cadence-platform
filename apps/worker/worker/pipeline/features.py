"""Torso-relative joint-angle features, computed from RTMPose's COCO-17
keypoints.

Roadmap Phase 3: "joint angles + bone directions (rotation-aware;
downweight noisy Z)". The angle formed by three skeletal points (e.g.
shoulder-elbow-wrist) is automatically invariant to translation,
uniform scale, and in-plane rotation -- unlike raw (x, y) coordinates,
it doesn't need an explicit Procrustes normalization step to be
comparable between two videos shot from slightly different distances
or camera angles. There is no Z here (RTMPose-m is 2D-only), so the
roadmap's "downweight noisy Z" doesn't apply to this model choice.

Spine lean is the one feature here that *isn't* rotation-invariant by
construction (it's measured against the camera's vertical, not
another body segment) -- see its docstring for how that's handled.
"""

from __future__ import annotations

import numpy as np

# COCO-17 keypoint order, as returned by rtmlib's RTMPose.
NOSE, L_EYE, R_EYE, L_EAR, R_EAR = range(5)
L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST = range(5, 11)
L_HIP, R_HIP, L_KNEE, R_KNEE, L_ANKLE, R_ANKLE = range(11, 17)

JOINT_ANGLE_TRIPLES: dict[str, tuple[int, int, int]] = {
    "left_elbow": (L_SHOULDER, L_ELBOW, L_WRIST),
    "right_elbow": (R_SHOULDER, R_ELBOW, R_WRIST),
    "left_knee": (L_HIP, L_KNEE, L_ANKLE),
    "right_knee": (R_HIP, R_KNEE, R_ANKLE),
    "left_hip": (L_SHOULDER, L_HIP, L_KNEE),
    "right_hip": (R_SHOULDER, R_HIP, R_KNEE),
    "left_shoulder": (L_HIP, L_SHOULDER, L_ELBOW),
    "right_shoulder": (R_HIP, R_SHOULDER, R_ELBOW),
}

# The 8 limb joint angles -- used by scoring.py to compute "motion energy"
# (frame-to-frame change) without spine_lean/balance_offset diluting it,
# since those two are about posture/stance, not limb movement.
LIMB_JOINT_NAMES: list[str] = list(JOINT_ANGLE_TRIPLES)

FEATURE_NAMES: list[str] = LIMB_JOINT_NAMES + ["spine_lean", "balance_offset"]


DEFAULT_MIN_CONFIDENCE = 0.3


def _angle_deg(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Angle at vertex b, in degrees, formed by points a-b-c. NaN if
    either segment is degenerate (near-zero length -- e.g. a missing
    keypoint collapsed to (0, 0))."""

    v1, v2 = a - b, c - b
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < 1e-6 or n2 < 1e-6:
        return float("nan")
    cos_angle = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_angle)))


def joint_angles(
    keypoints: np.ndarray,
    scores: np.ndarray | None = None,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> dict[str, float]:
    """keypoints: (17, 2). One angle in degrees per named joint.

    `scores` (17,), if given, are RTMPose's own per-keypoint
    confidence. A joint whose triple includes any keypoint below
    `min_confidence` returns NaN rather than a geometrically-valid but
    likely-meaningless angle -- RTMPose still emits *some* coordinate
    for an occluded or off-screen keypoint (extrapolated from its
    training prior, not observed), and a chest-up dance clip with the
    hips/knees out of frame will otherwise report large, confident-
    looking hip/knee "errors" that are actually just pose-estimation
    guesswork on body parts nobody can see. Found by comparing real
    pipeline output against the source clips: two TikTok-style videos
    framed from the chest up reported 60-80 degree hip differences
    before this existed.
    """

    result = {}
    for name, (a, b, c) in JOINT_ANGLE_TRIPLES.items():
        if scores is not None and (
            scores[a] < min_confidence or scores[b] < min_confidence or scores[c] < min_confidence
        ):
            result[name] = float("nan")
        else:
            result[name] = _angle_deg(keypoints[a], keypoints[b], keypoints[c])
    return result


def spine_lean_deg(
    keypoints: np.ndarray, scores: np.ndarray | None = None, min_confidence: float = DEFAULT_MIN_CONFIDENCE
) -> float:
    """Angle (degrees) of the hip-midpoint -> shoulder-midpoint vector
    from vertical, in [-180, 180]. Unlike the joint angles above, this
    is measured against the camera's vertical, so it also captures
    real camera tilt -- two videos shot from different angles will
    have different absolute spine_lean even for an identical pose.
    `feature_sequence` below corrects for this by subtracting each
    video's own median lean, so what's compared is *change* in lean
    over time within each video, not its absolute value.

    NaN if any of the four keypoints it depends on (both hips, both
    shoulders) is below `min_confidence` -- see joint_angles' docstring
    for why a low-confidence keypoint shouldn't be trusted just
    because it's geometrically well-defined.
    """

    if scores is not None and any(
        scores[i] < min_confidence for i in (L_HIP, R_HIP, L_SHOULDER, R_SHOULDER)
    ):
        return float("nan")

    mid_hip = (keypoints[L_HIP] + keypoints[R_HIP]) / 2
    mid_shoulder = (keypoints[L_SHOULDER] + keypoints[R_SHOULDER]) / 2
    vector = mid_shoulder - mid_hip
    # image y grows downward, so "up" is (0, -1)
    return float(np.degrees(np.arctan2(vector[0], -vector[1])))


def balance_offset(
    keypoints: np.ndarray, scores: np.ndarray | None = None, min_confidence: float = DEFAULT_MIN_CONFIDENCE
) -> float:
    """Horizontal distance from the hip midpoint to the ankle midpoint
    (the base of support), normalized by hip width so it's comparable
    across dancers/distances-from-camera. Like spine_lean, this is
    measured in the camera's frame, not intrinsic to the pose, so
    `feature_sequence` baseline-corrects it per video -- what's
    compared is *wobble away from one's own stance*, not absolute
    stance width (which varies by dancer and framing for reasons that
    have nothing to do with balance).

    NaN if any of the four keypoints it depends on (both hips, both
    ankles) is below `min_confidence`, or if the hips are degenerate
    (near-zero width, making normalization meaningless).
    """

    if scores is not None and any(
        scores[i] < min_confidence for i in (L_HIP, R_HIP, L_ANKLE, R_ANKLE)
    ):
        return float("nan")

    hip_width = np.linalg.norm(keypoints[L_HIP] - keypoints[R_HIP])
    if hip_width < 1e-6:
        return float("nan")

    mid_hip = (keypoints[L_HIP] + keypoints[R_HIP]) / 2
    mid_ankle = (keypoints[L_ANKLE] + keypoints[R_ANKLE]) / 2
    return float((mid_hip[0] - mid_ankle[0]) / hip_width)


def feature_sequence(
    keypoint_sequence: list[np.ndarray],
    score_sequence: list[np.ndarray] | None = None,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> np.ndarray:
    """Converts a sequence of (17, 2) keypoint frames into a (T, F)
    matrix of named features (FEATURE_NAMES), for DTW alignment.
    Per-video baseline-corrects spine_lean (see its docstring); NaNs
    from degenerate joint angles or low-confidence keypoints (if
    `score_sequence` is given) are left as NaN for the caller to
    handle (alignment.py imputes them)."""

    if not keypoint_sequence:
        return np.zeros((0, len(FEATURE_NAMES)))

    rows = []
    for i, kp in enumerate(keypoint_sequence):
        frame_scores = score_sequence[i] if score_sequence is not None else None
        angles = joint_angles(kp, frame_scores, min_confidence)
        lean = spine_lean_deg(kp, frame_scores, min_confidence)
        balance = balance_offset(kp, frame_scores, min_confidence)
        rows.append([angles[name] for name in LIMB_JOINT_NAMES] + [lean, balance])
    matrix = np.array(rows, dtype=float)

    # spine_lean and balance_offset are measured against the camera's
    # frame, not intrinsic to the pose -- baseline-correct both so what's
    # compared is deviation from each video's own median, not an absolute
    # value that differs for reasons unrelated to technique (camera tilt,
    # natural stance width).
    for name in ("spine_lean", "balance_offset"):
        idx = FEATURE_NAMES.index(name)
        column = matrix[:, idx]
        valid = ~np.isnan(column)
        if valid.any():
            matrix[:, idx] = column - np.nanmedian(column[valid])
    return matrix
