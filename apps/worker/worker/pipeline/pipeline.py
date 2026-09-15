"""End-to-end Phase 2 orchestration: detect+track a video, expose track
summaries for a multi-person "pick your dancer" UI, then (once locked)
extract a smoothed, quality-scored pose sequence for one track.

This is the module Phase 3 (coaching intelligence) and apps/api's
analyses endpoints will actually call.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .detection import detect_and_track
from .interpolation import interpolate_short_gaps, split_into_contiguous_segments
from .pose import PoseEstimator
from .quality import (
    Detection,
    LockQuality,
    QualityGateResult,
    TrackSummary,
    compute_lock_quality,
    evaluate_quality_gate,
    summarize_tracks,
)
from .smoothing import smooth_keypoint_sequence


@dataclass
class DetectionSummary:
    tracks: list[TrackSummary]
    fps: float
    total_frames: int


def detect_tracks(video_path: str | Path) -> tuple[DetectionSummary, list[Detection]]:
    """Run detection+tracking once. Returns the summary for a pick-UI
    plus the raw detections, which the caller should hold onto (e.g.
    persist to the analysis workspace) so locking a track doesn't
    require re-running YOLO."""

    detections, fps, total_frames = detect_and_track(video_path)
    summary = DetectionSummary(
        tracks=summarize_tracks(detections, fps), fps=fps, total_frames=total_frames
    )
    return summary, detections


@dataclass
class LockedPoseResult:
    track_id: int
    fps: float
    frame_indices: list[int]
    keypoints: list[np.ndarray]  # smoothed, one (num_joints, 2) array per frame_indices entry
    scores: list[np.ndarray]
    quality: LockQuality
    quality_gate: QualityGateResult


def extract_locked_pose(
    video_path: str | Path,
    detections: list[Detection],
    track_id: int,
    fps: float,
    total_frames: int,
    pose_estimator: PoseEstimator | None = None,
    bbox_margin: float = 0.15,
    max_interpolation_gap: int = 3,
) -> LockedPoseResult:
    """Crop to the locked track's bbox each frame it appears in, run
    pose on the crop only (never the full frame -- that's how a second
    person in frame stops corrupting the signal), interpolate short
    gaps, then smooth."""

    import cv2

    quality = compute_lock_quality(detections, track_id, total_frames, fps)
    gate = evaluate_quality_gate(quality)

    locked_by_frame = {d.frame_idx: d for d in detections if d.track_id == track_id}

    if not gate.passed or not locked_by_frame:
        return LockedPoseResult(
            track_id=track_id, fps=fps, frame_indices=[], keypoints=[], scores=[],
            quality=quality, quality_gate=gate,
        )

    estimator = pose_estimator or PoseEstimator()

    raw_keypoints: dict[int, np.ndarray] = {}
    raw_scores: dict[int, np.ndarray] = {}

    cap = cv2.VideoCapture(str(video_path))
    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        detection = locked_by_frame.get(frame_idx)
        if detection is not None:
            bbox = _expand_bbox(detection.bbox, frame.shape, margin=bbox_margin)
            keypoints, scores = estimator.estimate(frame, bbox)
            raw_keypoints[frame_idx] = keypoints
            raw_scores[frame_idx] = scores
        frame_idx += 1
    cap.release()

    filled_keypoints = interpolate_short_gaps(raw_keypoints, max_gap=max_interpolation_gap)
    segments = split_into_contiguous_segments(filled_keypoints)

    all_frame_indices: list[int] = []
    all_smoothed: list[np.ndarray] = []
    for segment in segments:
        segment_frames = [filled_keypoints[i] for i in segment]
        smoothed = smooth_keypoint_sequence(segment_frames, fps=fps)
        all_frame_indices.extend(segment)
        all_smoothed.extend(smoothed)

    all_scores = [raw_scores.get(i, raw_scores.get(_nearest(raw_scores, i))) for i in all_frame_indices]

    return LockedPoseResult(
        track_id=track_id,
        fps=fps,
        frame_indices=all_frame_indices,
        keypoints=all_smoothed,
        scores=all_scores,
        quality=quality,
        quality_gate=gate,
    )


def _expand_bbox(
    bbox: tuple[float, float, float, float], frame_shape: tuple[int, ...], margin: float
) -> tuple[float, float, float, float]:
    """Grow a tight person bbox by `margin` (fraction of box size) so
    limbs at the edge of the detector's box aren't clipped before pose
    estimation runs on the crop, then clamp to the frame."""

    x1, y1, x2, y2 = bbox
    height, width = frame_shape[0], frame_shape[1]
    box_w, box_h = x2 - x1, y2 - y1
    x1 -= box_w * margin
    x2 += box_w * margin
    y1 -= box_h * margin
    y2 += box_h * margin
    return (max(0, x1), max(0, y1), min(width, x2), min(height, y2))


def _nearest(mapping: dict[int, np.ndarray], frame_idx: int) -> int:
    if not mapping:
        return frame_idx
    return min(mapping, key=lambda k: abs(k - frame_idx))
