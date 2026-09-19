"""Turn a DTW warping path between two pose sequences into a score,
timestamped segments, and joint-level issues.

Roadmap Phase 3 target:

    Overall 84.2%    Tracking 93%    Reliable frames 96%

    00:12.4-00:15.1
    - Left elbow over-extended ~18deg
    - Transition 0.3s early
    - Hip rotation lagging shoulders

This module produces five issue types: `angle` (elbow/knee/hip/shoulder
+ torso lean -- the `joint` field says which), `timing` (growing
reference/user lag), `occlusion` (a joint was too low-confidence to
trust for part of a window), `tempo` (the DTW path stretched or
compressed here far more than elsewhere -- a move likely
skipped/rushed or added/repeated), and `balance` (hip position
wandering from the base of support more than the reference). It
deliberately does not produce a `path` issue (spatial trajectory
deviation) -- packages/schema's IssueType supports it, but nothing
here generates one yet; that's an honest gap, not a promise.

None of `occlusion`/`tempo`/`energy`/`balance` have been checked
against real footage the way `angle`/`timing` have (see
apps/worker/README.md and STATUS.md for what *has* been verified on
real clips and real motion). Their thresholds are reasonable-looking
defaults, not tuned against any eval set -- treat them accordingly
until they've been run against more than synthetic ground truth.

Scoring formula: score = 100 * exp(-mean_abs_angle_error_deg / TAU),
TAU chosen so a 20-degree average joint-angle error gives ~50%. Only
the degrees-based features (limb angles + torso lean) feed the score;
balance_offset is a dimensionless ratio, not degrees, so mixing it into
the same mean would be unit-inconsistent -- it only ever produces its
own `balance` issue, never moves the score. This replaces the
"100 - similarity*2" style formula the legacy app used (and the
roadmap explicitly calls out as a fake score) -- the fix isn't "no
formula," it's a formula over a *principled feature* (normalized joint
angles, not raw pixel distance), with its constant chosen for and
documented against a specific, stated reference point rather than
picked to look right on one example. See docs/decisions.md.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field

import numpy as np

from .alignment import dtw_align
from .features import FEATURE_NAMES, LIMB_JOINT_NAMES, feature_sequence

ANGLE_ISSUE_THRESHOLD_DEG = 15.0
TIMING_DRIFT_THRESHOLD_SECONDS = 0.2
OCCLUSION_FRACTION_THRESHOLD = 0.3
TEMPO_LOW_RATIO = 0.6
TEMPO_HIGH_RATIO = 1.6
ENERGY_RATIO_THRESHOLD = 0.5
# Energy is measured as mean joint-angle change over a fixed real-time
# lag, not per frame: the reference and user clips are usually different
# frame rates (60 vs 30 fps on the first real clip pair), and a per-frame
# difference changes with fps -- and simply scaling by fps doesn't fix it
# either, since jitter and rough motion don't scale linearly with frame
# spacing. Comparing displacement over the same physical interval does.
# The threshold (2.5 deg over 0.1s, ~25 deg/s) only marks "the reference
# is nearly still here"; it's a first-pass default, not tuned -- and not
# a mechanical conversion of the old per-frame 1.5, since rough motion
# doesn't scale linearly with the lag.
ENERGY_LAG_SECONDS = 0.1
MIN_REFERENCE_ENERGY_DEG = 2.5
BALANCE_ISSUE_THRESHOLD = 0.15
DEFAULT_SEGMENT_SECONDS = 2.0
# score = 100 * exp(-mean_abs_angle_error_deg / SCORE_TAU); solved so a
# 20-degree average error gives 50%: TAU = 20 / ln(2)
SCORE_TAU_DEG = 20.0 / math.log(2)
SCORING_METHOD_VERSION = "angle-dtw-v2"

# Features that feed the score (degrees-based). balance_offset is
# excluded -- see module docstring.
_SCORE_FEATURE_NAMES = LIMB_JOINT_NAMES + ["spine_lean"]
_SCORE_FEATURE_INDICES = [FEATURE_NAMES.index(n) for n in _SCORE_FEATURE_NAMES]
_LIMB_FEATURE_INDICES = [FEATURE_NAMES.index(n) for n in LIMB_JOINT_NAMES]
_BALANCE_INDEX = FEATURE_NAMES.index("balance_offset")

_JOINT_LABELS = {"spine_lean": "torso lean"}


def _label(name: str) -> str:
    return _JOINT_LABELS.get(name, name.replace("_", " ")).title()


@dataclass(frozen=True)
class ScoredIssue:
    joint: str
    type: str  # "angle" | "timing" | "occlusion" | "tempo" | "energy" | "balance"
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


def _angle_issues(mean_abs_diff: np.ndarray, excluded: set[str]) -> list[ScoredIssue]:
    """One issue per degrees-based feature (limb joints + torso lean)
    whose mean error exceeds the threshold. `excluded` names (e.g. a
    joint already flagged `occlusion` this window) are skipped -- an
    angle computed from mostly-missing data isn't trustworthy enough
    to also report as a technique error."""

    issues = []
    for name, diff in zip(_SCORE_FEATURE_NAMES, mean_abs_diff[_SCORE_FEATURE_INDICES]):
        if name in excluded or np.isnan(diff) or diff < ANGLE_ISSUE_THRESHOLD_DEG:
            continue
        issues.append(
            ScoredIssue(
                joint=name,
                type="angle",
                magnitude=round(float(diff), 1),
                message=f"{_label(name)} off by about {diff:.0f} degrees.",
            )
        )
    issues.sort(key=lambda issue: -issue.magnitude)
    return issues


def _balance_issue(
    mean_abs_diff: np.ndarray,
    reference_nan_mask: np.ndarray,
    ref_indices: list[int],
    user_nan_mask: np.ndarray,
    other_indices: list[int],
) -> ScoredIssue | None:
    # Same trust rule as `occlusion`: balance_offset depends on both
    # ankles, and on real clips framed above the feet they clear the
    # confidence bar in only ~30-60% of frames (mean confidence right at
    # the 0.3 threshold). A "wobble" computed from a few marginal ankle
    # estimates is noise, so say nothing rather than report it -- on the
    # first real clip pair this gate is what removed two large
    # (0.6-0.7 hip-width) balance flags built on such ankles.
    missing = max(
        float(np.mean(reference_nan_mask[ref_indices, _BALANCE_INDEX])),
        float(np.mean(user_nan_mask[other_indices, _BALANCE_INDEX])),
    )
    if missing >= OCCLUSION_FRACTION_THRESHOLD:
        return None

    diff = mean_abs_diff[_BALANCE_INDEX]
    if np.isnan(diff) or diff < BALANCE_ISSUE_THRESHOLD:
        return None
    return ScoredIssue(
        joint="balance_offset",
        type="balance",
        magnitude=round(float(diff), 2),
        message="Noticeable balance wobble relative to the reference in this window.",
    )


def _occlusion_issues(user_nan_mask: np.ndarray, other_indices: list[int]) -> tuple[list[ScoredIssue], set[str]]:
    """For each limb joint, the fraction of this window's user frames
    where that joint was too low-confidence to trust (masked to NaN
    before DTW's imputation -- see score_analysis). Returns the issues
    plus the set of joint names to exclude from _angle_issues this
    window."""

    issues: list[ScoredIssue] = []
    excluded: set[str] = set()
    for name, col in zip(LIMB_JOINT_NAMES, _LIMB_FEATURE_INDICES):
        fraction = float(np.mean(user_nan_mask[other_indices, col]))
        if fraction < OCCLUSION_FRACTION_THRESHOLD:
            continue
        excluded.add(name)
        issues.append(
            ScoredIssue(
                joint=name,
                type="occlusion",
                magnitude=round(fraction, 2),
                message=f"{_label(name)} wasn't visible enough to score for about {fraction:.0%} of this window.",
            )
        )
    issues.sort(key=lambda issue: -issue.magnitude)
    return issues, excluded


def _tempo_issue(
    ref_frames: list[int], ref_fps: float, other_frames: list[int], other_fps: float
) -> ScoredIssue | None:
    """Roadmap-adjacent, not validated against real footage (see
    module docstring): a proxy for "a move was skipped/rushed" or
    "added/repeated", from how much the DTW path locally stretches or
    compresses. A window where the user's matched frame-span is much
    smaller than the reference's suggests the aligner had few user
    frames to explain a chunk of reference motion (a skipped or rushed
    move); much larger suggests extra frames with no reference
    counterpart (an added or repeated move)."""

    # Compare durations in seconds, not frame counts: comparing raw
    # frame spans made a 60 fps reference vs. a 30 fps user clip read as
    # "half the frames" in every window (a false tempo issue everywhere,
    # found the first time this ran on real footage).
    ref_seconds = (max(ref_frames) - min(ref_frames) + 1) / ref_fps
    user_seconds = (max(other_frames) - min(other_frames) + 1) / other_fps
    if ref_seconds <= 0:
        return None
    ratio = user_seconds / ref_seconds

    if TEMPO_LOW_RATIO <= ratio <= TEMPO_HIGH_RATIO:
        return None

    if ratio < TEMPO_LOW_RATIO:
        message = "Far fewer matching frames here than expected -- a move may have been skipped or rushed."
    else:
        message = "Far more matching frames here than expected -- a move may have been added or repeated."
    return ScoredIssue(joint="overall", type="tempo", magnitude=round(abs(ratio - 1), 2), message=message)


def _segment_energy(features: np.ndarray, indices: list[int], fps: float) -> float:
    """Mean change in the limb joint angles over ENERGY_LAG_SECONDS,
    within these (sequence-position) indices -- higher means more
    motion. The lag is converted to frames per clip, so clips recorded at
    different frame rates are compared over the same real-time interval."""

    # `indices` come straight off the DTW warping path, where a frame is
    # repeated whenever the other clip has more frames in the same span
    # (e.g. every 30 fps user frame appears ~twice against a 60 fps
    # reference). Measuring a "lag" across repeats spans about half the
    # real time -- so only real, distinct frames count. (Found by
    # checking a per-window "user has ~0.4x the energy" flag against
    # whole-clip motion, which was identical between the two clips.)
    indices = list(dict.fromkeys(indices))
    sub = features[indices][:, _LIMB_FEATURE_INDICES]
    lag = max(1, round(fps * ENERGY_LAG_SECONDS))
    if len(sub) <= lag:
        return 0.0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return float(np.nanmean(np.abs(sub[lag:] - sub[:-lag])))


def _energy_issue(
    reference_features: np.ndarray,
    ref_indices: list[int],
    reference_fps: float,
    user_features: np.ndarray,
    other_indices: list[int],
    user_fps: float,
) -> ScoredIssue | None:
    ref_energy = _segment_energy(reference_features, ref_indices, reference_fps)
    if ref_energy < MIN_REFERENCE_ENERGY_DEG:
        return None  # the reference itself is nearly still here; a ratio would just be noise

    user_energy = _segment_energy(user_features, other_indices, user_fps)
    ratio = user_energy / ref_energy
    if ratio >= ENERGY_RATIO_THRESHOLD:
        return None

    return ScoredIssue(
        joint="overall",
        type="energy",
        magnitude=round(ratio, 2),
        message="Movement energy is noticeably lower than the reference in this window.",
    )


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
        return ScoringResult(overall_score=0.0, method=SCORING_METHOD_VERSION, version="2", segments=[])

    # Captured *before* dtw_align's internal NaN imputation, which would
    # otherwise erase which user frames were actually low-confidence.
    user_nan_mask = np.isnan(user_features)
    reference_nan_mask = np.isnan(reference_features)

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
            overall_diff = float(np.nanmean(mean_abs_diff[_SCORE_FEATURE_INDICES]))
        score = 100.0 * math.exp(-overall_diff / SCORE_TAU_DEG)

        # Angle issues lead the list: they name a specific joint and a
        # specific error, which is the actual technique feedback. The
        # others are secondary context (a data-quality caveat, or a
        # window-level observation with no single joint to blame) and
        # come after, so a low-confidence *unrelated* joint elsewhere in
        # the window can't bury the real finding as "the top issue" --
        # this ordering used to be occlusion-first, which is what made a
        # real-motion regression test's attribution accuracy collapse
        # from 82% to 20% (occlusion is common on real footage even when
        # it's irrelevant to the joint that's actually wrong).
        occlusion_issues, excluded_joints = _occlusion_issues(user_nan_mask, other_indices)
        issues = _angle_issues(mean_abs_diff, excluded_joints) + occlusion_issues

        balance_issue = _balance_issue(
            mean_abs_diff, reference_nan_mask, ref_indices, user_nan_mask, other_indices
        )
        if balance_issue:
            issues.append(balance_issue)

        tempo_issue = _tempo_issue(
            [reference_frame_indices[i] for i in ref_indices],
            reference_fps,
            [user_frame_indices[i] for i in other_indices],
            user_fps,
        )
        if tempo_issue:
            issues.append(tempo_issue)

        energy_issue = _energy_issue(
            reference_features, ref_indices, reference_fps, user_features, other_indices, user_fps
        )
        if energy_issue:
            issues.append(energy_issue)

        timing_issue = _timing_issue(
            window, baseline_offset, reference_frame_indices, user_frame_indices, reference_fps, user_fps
        )
        if timing_issue:
            issues.append(timing_issue)

        finite_columns = np.sum(~np.isnan(mean_abs_diff[_SCORE_FEATURE_INDICES]))
        confidence = float(finite_columns / len(_SCORE_FEATURE_INDICES))

        t0 = reference_frame_indices[ref_indices[0]] / reference_fps
        t1 = reference_frame_indices[ref_indices[-1]] / reference_fps
        segments.append(ScoredSegment(t0=t0, t1=t1, score=score, confidence=confidence, issues=issues))

    overall_score = (
        float(np.mean([segment.score for segment in segments])) if segments else 0.0
    )

    return ScoringResult(
        overall_score=overall_score, method=SCORING_METHOD_VERSION, version="2", segments=segments
    )
