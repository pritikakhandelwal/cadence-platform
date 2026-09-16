"""Turn a DTW warping path between two pose sequences into a score,
timestamped segments, and joint-level issues.

Roadmap Phase 3 target:

    Overall 84.2%    Tracking 93%    Reliable frames 96%

    00:12.4-00:15.1
    - Left elbow over-extended ~18deg
    - Transition 0.3s early
    - Hip rotation lagging shoulders

This module produces the "angle" and "timing" issue types from that
example. It deliberately does not produce a "path" issue (spatial
trajectory deviation) -- packages/schema's IssueType supports it, but
nothing here generates one yet; that's an honest gap, not a promise.

Scoring formula: score = 100 * exp(-mean_abs_angle_error_deg / TAU),
TAU chosen so a 20-degree average joint-angle error gives ~50%. This
replaces the "100 - similarity*2" style formula the legacy app used
(and the roadmap explicitly calls out as a fake score) -- the fix
isn't "no formula," it's a formula over a *principled feature*
(normalized joint angles, not raw pixel distance), with its constant
chosen for and documented against a specific, stated reference point
rather than picked to look right on one example.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field

import numpy as np

from .alignment import dtw_align
from .features import FEATURE_NAMES, feature_sequence

ANGLE_ISSUE_THRESHOLD_DEG = 15.0
TIMING_DRIFT_THRESHOLD_SECONDS = 0.2
DEFAULT_SEGMENT_SECONDS = 2.0
# score = 100 * exp(-mean_abs_angle_error_deg / SCORE_TAU); solved so a
# 20-degree average error gives 50%: TAU = 20 / ln(2)
SCORE_TAU_DEG = 20.0 / math.log(2)
SCORING_METHOD_VERSION = "angle-dtw-v1"


@dataclass(frozen=True)
class ScoredIssue:
    joint: str
    type: str  # "angle" | "timing"
    magnitude: float
    message: str


@dataclass(frozen=True)
class ScoredSegment:
    t0: float
    t1: float
    score: float
    confidence: float
    issues: list[ScoredIssue] = field(default_factory=list)


@dataclass(frozen=True)
class ScoringResult:
    overall_score: float
    method: str
    version: str
    segments: list[ScoredSegment]


def _segment_path_by_reference_time(
    path: list[tuple[int, int]], reference_frame_indices: list[int], fps: float, segment_seconds: float
) -> list[list[tuple[int, int]]]:
    """Groups warping-path pairs into windows of ~segment_seconds each,
    based on the reference (professional) sequence's own timeline."""

    if not path:
        return []

    window_frames = max(1, int(round(segment_seconds * fps)))
    segments: list[list[tuple[int, int]]] = []
    current: list[tuple[int, int]] = []
    window_start_frame = reference_frame_indices[path[0][0]]

    for ref_idx, other_idx in path:
        frame = reference_frame_indices[ref_idx]
        if frame - window_start_frame >= window_frames and current:
            segments.append(current)
            current = []
            window_start_frame = frame
        current.append((ref_idx, other_idx))

    if current:
        segments.append(current)
    return segments


def _angle_issues(mean_abs_diff: np.ndarray) -> list[ScoredIssue]:
    issues = []
    for name, diff in zip(FEATURE_NAMES, mean_abs_diff):
        if name == "spine_lean" or np.isnan(diff) or diff < ANGLE_ISSUE_THRESHOLD_DEG:
            continue
        label = name.replace("_", " ").title()
        issues.append(
            ScoredIssue(
                joint=name,
                type="angle",
                magnitude=round(float(diff), 1),
                message=f"{label} off by about {diff:.0f} degrees.",
            )
        )
    issues.sort(key=lambda issue: -issue.magnitude)
    return issues


def _timing_issue(
    pairs: list[tuple[int, int]],
    baseline_offset_seconds: float,
    ref_frame_indices: list[int],
    other_frame_indices: list[int],
    ref_fps: float,
    other_fps: float,
) -> ScoredIssue | None:
    offsets = [
        other_frame_indices[o] / other_fps - ref_frame_indices[r] / ref_fps for r, o in pairs
    ]
    drift = float(np.mean(offsets)) - baseline_offset_seconds
    if abs(drift) < TIMING_DRIFT_THRESHOLD_SECONDS:
        return None
    direction = "behind" if drift > 0 else "ahead of"
    return ScoredIssue(
        joint="overall",
        type="timing",
        magnitude=round(abs(drift), 2),
        message=f"Running {abs(drift):.1f}s {direction} the reference by this point.",
    )


def score_analysis(
    reference_keypoints: list[np.ndarray],
    reference_frame_indices: list[int],
    reference_fps: float,
    user_keypoints: list[np.ndarray],
    user_frame_indices: list[int],
    user_fps: float,
    reference_scores: list[np.ndarray] | None = None,
    user_scores: list[np.ndarray] | None = None,
    segment_seconds: float = DEFAULT_SEGMENT_SECONDS,
) -> ScoringResult:
    """Aligns a user's pose sequence to a reference's, and scores it.

    "reference" is the professional video's timeline -- segment
    timestamps are reported in the reference's time, matching the
    roadmap's target output.

    `reference_scores`/`user_scores` (RTMPose's per-keypoint
    confidence, same shape as the keypoints lists), if given, mask out
    low-confidence joints before computing angles -- see
    features.joint_angles for why. Optional and defaults to no
    masking, mainly so tests that only care about geometry don't have
    to fabricate confidence arrays.
    """

    reference_features = feature_sequence(reference_keypoints, reference_scores)
    user_features = feature_sequence(user_keypoints, user_scores)

    if len(reference_features) == 0 or len(user_features) == 0:
        return ScoringResult(overall_score=0.0, method=SCORING_METHOD_VERSION, version="1", segments=[])

    path = dtw_align(reference_features, user_features)
    windows = _segment_path_by_reference_time(
        path, reference_frame_indices, reference_fps, segment_seconds
    )

    baseline_offset = float(
        np.mean(
            [
                user_frame_indices[o] / user_fps - reference_frame_indices[r] / reference_fps
                for r, o in windows[0]
            ]
        )
    ) if windows else 0.0

    segments: list[ScoredSegment] = []
    for window in windows:
        ref_indices = [r for r, _ in window]
        other_indices = [o for _, o in window]

        diffs = np.abs(reference_features[ref_indices] - user_features[other_indices])
        with warnings.catch_warnings():
            # a feature that's low-confidence (masked to NaN) for every
            # frame in this window is expected, not an error -- numpy's
            # "Mean of empty slice" RuntimeWarning here is just noise.
            warnings.simplefilter("ignore", category=RuntimeWarning)
            mean_abs_diff = np.nanmean(diffs, axis=0)
            overall_diff = float(np.nanmean(mean_abs_diff))
        score = 100.0 * math.exp(-overall_diff / SCORE_TAU_DEG)

        issues = _angle_issues(mean_abs_diff)
        timing_issue = _timing_issue(
            window, baseline_offset, reference_frame_indices, user_frame_indices, reference_fps, user_fps
        )
        if timing_issue:
            issues.append(timing_issue)

        finite_columns = np.sum(~np.isnan(mean_abs_diff))
        confidence = float(finite_columns / len(FEATURE_NAMES))

        t0 = reference_frame_indices[ref_indices[0]] / reference_fps
        t1 = reference_frame_indices[ref_indices[-1]] / reference_fps
        segments.append(ScoredSegment(t0=t0, t1=t1, score=score, confidence=confidence, issues=issues))

    overall_score = (
        float(np.mean([segment.score for segment in segments])) if segments else 0.0
    )

    return ScoringResult(
        overall_score=overall_score, method=SCORING_METHOD_VERSION, version="1", segments=segments
    )
