"""Cadence background jobs.

Phase 2 adds the real detect->track->pose jobs. `echo` stays as the
Phase 0 wiring proof.
"""

from __future__ import annotations

from typing import Any


async def echo(ctx: dict[str, Any], message: str) -> str:
    """Trivial job: prove the queue round-trips a payload."""

    return message


async def detect_tracks_job(ctx: dict[str, Any], video_path: str) -> dict[str, Any]:
    """Run person detection + tracking once for a video. Returns a
    JSON-serializable summary for a multi-person "pick your dancer" UI,
    plus the raw detections (so a later lock job doesn't re-run YOLO).
    """

    from .pipeline.pipeline import detect_tracks

    summary, detections = detect_tracks(video_path)

    return {
        "fps": summary.fps,
        "total_frames": summary.total_frames,
        "tracks": [
            {
                "track_id": t.track_id,
                "frame_count": t.frame_count,
                "first_frame": t.first_frame,
                "last_frame": t.last_frame,
                "mean_confidence": t.mean_confidence,
                "fragments": t.fragments,
            }
            for t in summary.tracks
        ],
        "detections": [
            {
                "frame_idx": d.frame_idx,
                "track_id": d.track_id,
                "bbox": list(d.bbox),
                "confidence": d.confidence,
            }
            for d in detections
        ],
    }


async def extract_locked_pose_job(
    ctx: dict[str, Any],
    video_path: str,
    track_id: int,
    fps: float,
    total_frames: int,
    detections: list[dict[str, Any]],
) -> dict[str, Any]:
    """Lock onto one track from a prior detect_tracks_job call and
    extract its smoothed, quality-scored pose sequence."""

    from .pipeline.pipeline import extract_locked_pose
    from .pipeline.quality import Detection

    detection_objs = [
        Detection(
            frame_idx=d["frame_idx"], track_id=d["track_id"], bbox=tuple(d["bbox"]), confidence=d["confidence"]
        )
        for d in detections
    ]

    result = extract_locked_pose(video_path, detection_objs, track_id, fps, total_frames)

    return {
        "track_id": result.track_id,
        "fps": result.fps,
        "frame_indices": result.frame_indices,
        "keypoints": [k.tolist() for k in result.keypoints],
        "tracking": {
            "confidence": result.quality.mean_confidence,
            "reliable_frame_pct": result.quality.reliable_frame_pct,
            "person_count": result.quality.person_count,
            "lock_id": str(result.track_id),
        },
        "quality_gate": {
            "passed": result.quality_gate.passed,
            "reasons": result.quality_gate.reasons,
        },
    }
