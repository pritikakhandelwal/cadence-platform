"""Cadence background jobs.

detect_tracks_job is what apps/api's POST /analyses actually enqueues.
It writes its result straight into the shared `analyses` table
(packages/db) rather than returning it through arq's result backend --
apps/api reads the row back via GET /analyses/{id}, not via the job
result, matching the roadmap's "both API and workers talk to
PostgreSQL" architecture.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


async def echo(ctx: dict[str, Any], message: str) -> str:
    """Trivial job: prove the queue round-trips a payload."""

    return message


async def detect_tracks_job(ctx: dict[str, Any], analysis_id: str, video_path: str) -> dict[str, Any]:
    """Run detection+tracking once for an analysis's user-video upload,
    then either auto-lock a single confident track (scoring against the
    reference video and writing a final complete/rejected AnalysisResult)
    or, if multiple tracks are comparably sized (two real people, or a
    mirror reflection -- see quality.is_lock_ambiguous), mark the
    analysis needs_dancer_pick and stash the raw detections for a
    future lock endpoint to resume from without re-running YOLO.
    """

    from cadence_db import Analysis, SessionLocal
    from cadence_schema import AnalysisStatus, QualityGate, TrackingInfo

    from .pipeline.pipeline import detect_tracks, extract_locked_pose
    from .pipeline.quality import is_lock_ambiguous

    db = SessionLocal()
    try:
        analysis = db.get(Analysis, analysis_id)
        if analysis is None:
            return {"error": "analysis_not_found", "analysis_id": analysis_id}

        try:
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
                    "tracks": [
                        {
                            "track_id": t.track_id,
                            "frame_count": t.frame_count,
                            "mean_confidence": t.mean_confidence,
                            "fragments": t.fragments,
                        }
                        for t in summary.tracks
                    ],
                }
            else:
                track_id = summary.tracks[0].track_id
                locked = extract_locked_pose(video_path, detections, track_id, summary.fps, summary.total_frames)
                _finish_lock(analysis, locked, track_id)
        except Exception:
            _record_internal_failure(db, analysis, analysis_id)

        analysis.updated_at = datetime.now(timezone.utc)
        db.commit()
        return {"analysis_id": analysis_id, "status": analysis.status}
    finally:
        db.close()


def _record_internal_failure(db, analysis, analysis_id: str) -> None:
    """Called from inside an `except` block. Without this, an exception in
    the pipeline (a video ffprobe accepts but OpenCV can't decode, an ML
    error, a bad reference clip) made arq mark the job failed while the
    analysis row stayed `queued` forever -- and the UI polled it forever,
    telling the person it "usually takes under a minute".

    The row is the source of truth (see the module docstring), so the
    failure is written there -- as `rejected`, the one terminal state the
    frontend already turns into "here's why, try again" -- with a reason
    that's honest that it was our fault, not theirs. The traceback is
    logged, not swallowed. A dedicated `failed` status would be cleaner
    (see docs/decisions.md), but changes the frozen AnalysisResult contract.
    """

    from cadence_schema import AnalysisStatus, QualityGate, TrackingInfo

    logger.exception("analysis %s failed while processing", analysis_id)
    db.rollback()
    analysis.pending_lock_data = None
    _finish(
        analysis,
        AnalysisStatus.rejected,
        TrackingInfo(confidence=0, reliable_frame_pct=0, person_count=0),
        QualityGate(
            passed=False,
            reasons=["Something went wrong on our side while analyzing this video. Please try again."],
        ),
    )


def _finish(analysis, status, tracking, quality_gate, overall=None, segments=None) -> None:
    from cadence_schema import AnalysisResult

    analysis.status = status.value
    analysis.result = AnalysisResult(
        analysis_id=analysis.id,
        user_id=analysis.user_id,
        status=status,
        tracking=tracking,
        overall=overall,
        segments=segments or [],
        quality_gate=quality_gate,
    ).model_dump(mode="json")


def _finish_lock(analysis, locked, track_id: int) -> None:
    """Common tail of detect_tracks_job's auto-lock branch and
    extract_locked_pose_job: given a successfully-produced LockedPoseResult
    for the user's video, either reject (bad lock) or go on to score
    against the reference video and write the final result."""

    from cadence_schema import AnalysisStatus, QualityGate, TrackingInfo

    tracking = TrackingInfo(
        confidence=locked.quality.mean_confidence,
        reliable_frame_pct=locked.quality.reliable_frame_pct,
        person_count=locked.quality.person_count,
        lock_id=str(track_id),
    )

    if not locked.quality_gate.passed:
        _finish(
            analysis,
            AnalysisStatus.rejected,
            tracking,
            QualityGate(passed=False, reasons=locked.quality_gate.reasons),
        )
        return

    _save_keypoints(analysis.workspace_id, "user", locked)
    _score_against_reference(analysis, tracking, locked)


def _save_keypoints(workspace_id: str, role: str, locked) -> None:
    """Persists a locked pose sequence to <role>_keypoints.npz in the
    analysis's workspace. Phase 2 computed these and threw them away;
    Phase 3 needs them for alignment, hence saving them now."""

    from cadence_workspace import workspace_for

    workspace = workspace_for(workspace_id)
    path = workspace.user_keypoints if role == "user" else workspace.professional_keypoints
    np.savez(
        path,
        keypoints=np.array(locked.keypoints),
        scores=np.array(locked.scores),
        frame_indices=np.array(locked.frame_indices),
        fps=locked.fps,
    )


def _score_against_reference(analysis, user_tracking, user_locked) -> None:
    """Runs the reference (professional) video through the same
    detect+lock pipeline (assumed solo/clean -- a messy reference is a
    real, if rare, failure mode, handled below rather than assumed
    away), then scores the user's already-locked pose against it."""

    from cadence_db import Analysis  # noqa: F401  (for type clarity only)
    from cadence_schema import AnalysisStatus, Issue, OverallScore, QualityGate, Segment
    from cadence_workspace import workspace_for

    from .pipeline.pipeline import detect_tracks, extract_locked_pose
    from .pipeline.quality import is_lock_ambiguous
    from .pipeline.scoring import score_analysis

    workspace = workspace_for(analysis.workspace_id)
    reference_path = str(workspace.professional_upload)

    ref_summary, ref_detections = detect_tracks(reference_path)

    if not ref_summary.tracks or is_lock_ambiguous(ref_summary.tracks):
        _finish(
            analysis,
            AnalysisStatus.rejected,
            user_tracking,
            QualityGate(
                passed=False,
                reasons=["Reference video could not be locked onto a single clear dancer."],
            ),
        )
        return

    ref_track_id = ref_summary.tracks[0].track_id
    ref_locked = extract_locked_pose(
        reference_path, ref_detections, ref_track_id, ref_summary.fps, ref_summary.total_frames
    )
    if not ref_locked.quality_gate.passed:
        _finish(
            analysis,
            AnalysisStatus.rejected,
            user_tracking,
            QualityGate(
                passed=False,
                reasons=[f"Reference video: {reason}" for reason in ref_locked.quality_gate.reasons],
            ),
        )
        return

    _save_keypoints(analysis.workspace_id, "professional", ref_locked)

    scored = score_analysis(
        ref_locked.keypoints,
        ref_locked.frame_indices,
        ref_locked.fps,
        user_locked.keypoints,
        user_locked.frame_indices,
        user_locked.fps,
        reference_scores=ref_locked.scores,
        user_scores=user_locked.scores,
    )

    segments = [
        Segment(
            t0=s.t0,
            t1=s.t1,
            score=s.score,
            confidence=s.confidence,
            issues=[Issue(joint=i.joint, type=i.type, magnitude=i.magnitude, message=i.message) for i in s.issues],
        )
        for s in scored.segments
    ]

    _finish(
        analysis,
        AnalysisStatus.complete,
        user_tracking,
        QualityGate(passed=True, reasons=[]),
        overall=OverallScore(score=scored.overall_score, method=scored.method, version=scored.version),
        segments=segments,
    )


async def extract_locked_pose_job(
    ctx: dict[str, Any],
    analysis_id: str,
    video_path: str,
    track_id: int,
    fps: float,
    total_frames: int,
    detections: list[dict[str, Any]],
) -> dict[str, Any]:
    """Resume a needs_dancer_pick analysis once a user has picked a
    track_id, using the detections detect_tracks_job stashed in
    Analysis.pending_lock_data so this doesn't have to re-run YOLO.
    Enqueued by POST /analyses/{id}/lock. Shares _finish_lock with
    detect_tracks_job's auto-lock branch, so both paths score against
    the reference video the same way.
    """

    from cadence_db import Analysis, SessionLocal

    from .pipeline.pipeline import extract_locked_pose
    from .pipeline.quality import Detection

    db = SessionLocal()
    try:
        analysis = db.get(Analysis, analysis_id)
        if analysis is None:
            return {"error": "analysis_not_found", "analysis_id": analysis_id}

        detection_objs = [
            Detection(
                frame_idx=d["frame_idx"], track_id=d["track_id"], bbox=tuple(d["bbox"]), confidence=d["confidence"]
            )
            for d in detections
        ]

        try:
            locked = extract_locked_pose(video_path, detection_objs, track_id, fps, total_frames)
            _finish_lock(analysis, locked, track_id)
        except Exception:
            _record_internal_failure(db, analysis, analysis_id)

        analysis.pending_lock_data = None
        analysis.updated_at = datetime.now(timezone.utc)
        db.commit()
        return {"analysis_id": analysis_id, "status": analysis.status}
    finally:
        db.close()
