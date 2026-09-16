"""Cadence background jobs.

detect_tracks_job is what apps/api's POST /analyses actually enqueues.
It writes its result straight into the shared `analyses` table
(packages/db) rather than returning it through arq's result backend --
apps/api reads the row back via GET /analyses/{id}, not via the job
result, matching the roadmap's "both API and workers talk to
PostgreSQL" architecture.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any


async def echo(ctx: dict[str, Any], message: str) -> str:
    """Trivial job: prove the queue round-trips a payload."""

    return message


async def detect_tracks_job(ctx: dict[str, Any], analysis_id: str, video_path: str) -> dict[str, Any]:
    """Run detection+tracking once for an analysis's user-video upload,
    then either auto-lock a single confident track (writing a final
    complete/rejected AnalysisResult) or, if multiple tracks are
    comparably sized (two real people, or a mirror reflection -- see
    quality.is_lock_ambiguous), mark the analysis needs_dancer_pick and
    stash the raw detections for a future lock endpoint to resume from
    without re-running YOLO.
    """

    from cadence_db import Analysis, SessionLocal
    from cadence_schema import AnalysisResult, AnalysisStatus, QualityGate, TrackingInfo

    from .pipeline.pipeline import detect_tracks, extract_locked_pose
    from .pipeline.quality import is_lock_ambiguous

    db = SessionLocal()
    try:
        analysis = db.get(Analysis, analysis_id)
        if analysis is None:
            return {"error": "analysis_not_found", "analysis_id": analysis_id}

        summary, detections = detect_tracks(video_path)

        if not summary.tracks:
            _finish(
                analysis,
                AnalysisStatus.rejected,
                TrackingInfo(confidence=0, reliable_frame_pct=0, person_count=0),
                QualityGate(passed=False, reasons=["No person detected in this clip."]),
            )
        elif is_lock_ambiguous(summary.tracks):
            analysis.status = AnalysisStatus.needs_dancer_pick.value
            analysis.pending_lock_data = {
                "detections": [asdict(d) for d in detections],
                "fps": summary.fps,
                "total_frames": summary.total_frames,
            }
        else:
            track_id = summary.tracks[0].track_id
            locked = extract_locked_pose(video_path, detections, track_id, summary.fps, summary.total_frames)
            status = AnalysisStatus.complete if locked.quality_gate.passed else AnalysisStatus.rejected
            _finish(
                analysis,
                status,
                TrackingInfo(
                    confidence=locked.quality.mean_confidence,
                    reliable_frame_pct=locked.quality.reliable_frame_pct,
                    person_count=locked.quality.person_count,
                    lock_id=str(track_id),
                ),
                QualityGate(passed=locked.quality_gate.passed, reasons=locked.quality_gate.reasons),
            )

        analysis.updated_at = datetime.now(timezone.utc)
        db.commit()
        return {"analysis_id": analysis_id, "status": analysis.status}
    finally:
        db.close()


def _finish(analysis, status, tracking, quality_gate) -> None:
    from cadence_schema import AnalysisResult

    analysis.status = status.value
    analysis.result = AnalysisResult(
        analysis_id=analysis.id,
        user_id=analysis.user_id,
        status=status,
        tracking=tracking,
        quality_gate=quality_gate,
    ).model_dump(mode="json")


async def extract_locked_pose_job(
    ctx: dict[str, Any],
    video_path: str,
    track_id: int,
    fps: float,
    total_frames: int,
    detections: list[dict[str, Any]],
) -> dict[str, Any]:
    """Lock onto one track from a prior detect_tracks_job call (its
    Analysis.pending_lock_data) and extract its smoothed, quality-
    scored pose sequence. Not yet called from anywhere -- this is what
    a future POST /analyses/{id}/lock endpoint would enqueue once a
    user has picked a track_id from a needs_dancer_pick analysis; that
    endpoint doesn't exist yet. Kept separate from detect_tracks_job's
    own auto-lock path so both can call the same underlying pipeline
    function without duplicating it.
    """

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
