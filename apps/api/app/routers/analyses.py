from __future__ import annotations

from cadence_db import Analysis, User, get_db
from cadence_schema import AnalysisResult, AnalysisStatus, QualityGate, TrackingInfo
from cadence_workspace import create_analysis_workspace, remove_analysis_workspace, workspace_for
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps import get_current_user
from ..queue import JobQueue, get_queue
from ..security.video_validation import (
    VideoValidationError,
    validate_saved_video,
    validate_uploaded_video,
)
from ..security.youtube import YouTubeDownloadError, download_youtube_video

router = APIRouter(prefix="/analyses", tags=["analyses"])


async def _save_upload(upload: UploadFile, destination) -> None:
    with open(destination, "wb") as out_file:
        while chunk := await upload.read(1024 * 1024):
            out_file.write(chunk)


def _get_owned_analysis(db: Session, analysis_id: str, user: User) -> Analysis:
    analysis = db.get(Analysis, analysis_id)
    if not analysis or analysis.user_id != user.id:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return analysis


def _has_file(upload: UploadFile | None) -> bool:
    return upload is not None and bool(upload.filename)


@router.post("", status_code=201)
async def create_analysis(
    user_video: UploadFile,
    professional_video: UploadFile | None = File(None),
    professional_video_url: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    queue: JobQueue = Depends(get_queue),
) -> dict[str, str]:
    has_file = _has_file(professional_video)
    has_url = bool(professional_video_url and professional_video_url.strip())
    if has_file == has_url:  # both provided, or neither
        raise HTTPException(
            status_code=400,
            detail=(
                "Provide exactly one of professional_video (a file) or "
                "professional_video_url (a YouTube link)."
            ),
        )

    try:
        await validate_uploaded_video(user_video)
        if has_file:
            await validate_uploaded_video(professional_video)
    except VideoValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    workspace = create_analysis_workspace()
    try:
        await _save_upload(user_video, workspace.user_upload)

        if has_file:
            await _save_upload(professional_video, workspace.professional_upload)
        else:
            # No upload-stream magic-byte check here (there's no upload
            # stream) -- yt-dlp only ever fetches real YouTube content
            # in the format we ask for, and validate_saved_video below
            # (ffprobe) is what actually confirms it's a short, decodable
            # video, same as the upload path.
            try:
                download_youtube_video(professional_video_url, workspace.professional_upload)
            except YouTubeDownloadError as error:
                raise HTTPException(status_code=400, detail=str(error)) from error

        for path in (workspace.professional_upload, workspace.user_upload):
            try:
                validate_saved_video(path)
            except VideoValidationError as error:
                raise HTTPException(status_code=400, detail=str(error)) from error
    except HTTPException:
        remove_analysis_workspace(workspace)
        raise

    analysis = Analysis(user_id=current_user.id, workspace_id=workspace.run_id, status="queued")
    db.add(analysis)
    db.commit()

    # Phase 2 lock-on runs on the user's own video, not the professional
    # reference -- the reference is assumed pre-vetted/clean; the user's
    # upload is the messy one that can have a second person, a mirror,
    # etc. Phase 3 (alignment/scoring) is what will need pose for the
    # reference video too, via a simpler path since it doesn't need
    # multi-person lock-on. See docs/decisions.md.
    await queue.enqueue_job(
        "detect_tracks_job", analysis_id=analysis.id, video_path=str(workspace.user_upload)
    )

    return {"analysis_id": analysis.id, "status": analysis.status}


@router.get("/{analysis_id}")
def get_analysis(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisResult:
    analysis = _get_owned_analysis(db, analysis_id, current_user)

    if analysis.result:
        return AnalysisResult.model_validate(analysis.result)

    if analysis.status == AnalysisStatus.needs_dancer_pick.value:
        person_count = len((analysis.pending_lock_data or {}).get("tracks", []))
        reason = (
            f"{person_count} people were detected. "
            f"GET /analyses/{analysis_id}/candidate-tracks to see them, "
            f"then POST /analyses/{analysis_id}/lock with a track_id."
        )
    else:
        person_count = 0
        reason = "Analysis has not been processed yet."

    return AnalysisResult(
        analysis_id=analysis.id,
        user_id=analysis.user_id,
        status=AnalysisStatus(analysis.status),
        tracking=TrackingInfo(confidence=0, reliable_frame_pct=0, person_count=person_count),
        quality_gate=QualityGate(passed=False, reasons=[reason]),
    )


@router.get("/{analysis_id}/candidate-tracks")
def get_candidate_tracks(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """The tracks a needs_dancer_pick analysis is choosing between --
    what a "pick your dancer" UI would list. Track summaries only
    (track_id, frame_count, mean_confidence, fragments); the raw
    per-frame detections stay server-side in pending_lock_data."""

    analysis = _get_owned_analysis(db, analysis_id, current_user)

    if analysis.status != AnalysisStatus.needs_dancer_pick.value or not analysis.pending_lock_data:
        raise HTTPException(
            status_code=400, detail="This analysis isn't waiting for a dancer pick."
        )

    return analysis.pending_lock_data.get("tracks", [])


class LockRequest(BaseModel):
    track_id: int


@router.post("/{analysis_id}/lock", status_code=202)
async def lock_analysis(
    analysis_id: str,
    body: LockRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    queue: JobQueue = Depends(get_queue),
) -> dict[str, str]:
    """Resume a needs_dancer_pick analysis by picking one of the tracks
    from GET /analyses/{id}/candidate-tracks. Enqueues
    extract_locked_pose_job with the detections detect_tracks_job
    already stashed, so this doesn't re-run YOLO."""

    analysis = _get_owned_analysis(db, analysis_id, current_user)

    if analysis.status != AnalysisStatus.needs_dancer_pick.value or not analysis.pending_lock_data:
        raise HTTPException(
            status_code=400, detail="This analysis isn't waiting for a dancer pick."
        )

    pending = analysis.pending_lock_data
    valid_track_ids = {t["track_id"] for t in pending.get("tracks", [])}
    if body.track_id not in valid_track_ids:
        raise HTTPException(status_code=400, detail="Unknown track_id for this analysis.")

    analysis.status = AnalysisStatus.running.value
    db.commit()

    video_path = str(workspace_for(analysis.workspace_id).user_upload)
    await queue.enqueue_job(
        "extract_locked_pose_job",
        analysis_id=analysis.id,
        video_path=video_path,
        track_id=body.track_id,
        fps=pending["fps"],
        total_frames=pending["total_frames"],
        detections=pending["detections"],
    )

    return {"analysis_id": analysis.id, "status": analysis.status}
