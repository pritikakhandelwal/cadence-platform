from __future__ import annotations

from cadence_db import Analysis, User, get_db
from cadence_schema import AnalysisResult, AnalysisStatus, QualityGate, TrackingInfo
from cadence_workspace import create_analysis_workspace, remove_analysis_workspace
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..deps import get_current_user
from ..queue import JobQueue, get_queue
from ..security.video_validation import (
    VideoValidationError,
    validate_saved_video,
    validate_uploaded_video,
)

router = APIRouter(prefix="/analyses", tags=["analyses"])


async def _save_upload(upload: UploadFile, destination) -> None:
    with open(destination, "wb") as out_file:
        while chunk := await upload.read(1024 * 1024):
            out_file.write(chunk)


@router.post("", status_code=201)
async def create_analysis(
    professional_video: UploadFile,
    user_video: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    queue: JobQueue = Depends(get_queue),
) -> dict[str, str]:
    for upload in (professional_video, user_video):
        try:
            await validate_uploaded_video(upload)
        except VideoValidationError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    workspace = create_analysis_workspace()
    try:
        await _save_upload(professional_video, workspace.professional_upload)
        await _save_upload(user_video, workspace.user_upload)

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
    analysis = db.get(Analysis, analysis_id)
    if not analysis or analysis.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    if analysis.result:
        return AnalysisResult.model_validate(analysis.result)

    reason = (
        "Multiple people were detected and picking one isn't supported by this API yet."
        if analysis.status == AnalysisStatus.needs_dancer_pick.value
        else "Analysis has not been processed yet."
    )
    return AnalysisResult(
        analysis_id=analysis.id,
        user_id=analysis.user_id,
        status=AnalysisStatus(analysis.status),
        tracking=TrackingInfo(confidence=0, reliable_frame_pct=0, person_count=0),
        quality_gate=QualityGate(passed=False, reasons=[reason]),
    )
