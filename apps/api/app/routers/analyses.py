from __future__ import annotations

from cadence_schema import AnalysisResult, AnalysisStatus, QualityGate, TrackingInfo
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Analysis, User
from ..security.video_validation import (
    VideoValidationError,
    validate_saved_video,
    validate_uploaded_video,
)
from ..workspace import create_analysis_workspace, remove_analysis_workspace

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

    # Phase 2/3 enqueue the real detect->track->pose->align job here
    # (apps/worker) and fill in `analysis.result`. For now the row
    # existing and being retrievable is the Phase 1 contract.

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

    return AnalysisResult(
        analysis_id=analysis.id,
        user_id=analysis.user_id,
        status=AnalysisStatus(analysis.status),
        tracking=TrackingInfo(confidence=0, reliable_frame_pct=0, person_count=0),
        quality_gate=QualityGate(passed=False, reasons=["Analysis has not been processed yet."]),
    )
