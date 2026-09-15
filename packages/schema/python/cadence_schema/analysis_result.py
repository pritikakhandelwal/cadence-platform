"""The canonical AnalysisResult contract.

Frontend, API, worker, and Figma all speak this shape. If a field is not
here, it does not exist in the product — no page may invent its own metric
(e.g. `pose_accuracy = similarity + 3`).

Mirrors packages/schema/typescript/src/analysisResult.ts field-for-field.
Keep the two in sync by hand until a codegen step replaces this note.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class AnalysisStatus(str, Enum):
    queued = "queued"
    running = "running"
    needs_dancer_pick = "needs_dancer_pick"
    complete = "complete"
    rejected = "rejected"


class IssueType(str, Enum):
    angle = "angle"
    timing = "timing"
    path = "path"


class TrackingInfo(BaseModel):
    confidence: float = Field(ge=0, le=1)
    reliable_frame_pct: float = Field(ge=0, le=100)
    person_count: int = Field(ge=0)
    lock_id: str | None = None


class OverallScore(BaseModel):
    score: float = Field(ge=0, le=100)
    method: str
    version: str


class Issue(BaseModel):
    joint: str
    type: IssueType
    magnitude: float
    message: str


class Segment(BaseModel):
    t0: float
    t1: float
    score: float = Field(ge=0, le=100)
    issues: list[Issue] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class Artifacts(BaseModel):
    overlay_url: str | None = None
    skeleton_3d_url: str | None = None
    thumbs: list[str] = Field(default_factory=list)


class QualityGate(BaseModel):
    passed: bool
    reasons: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    analysis_id: str
    user_id: str
    status: AnalysisStatus
    tracking: TrackingInfo
    overall: OverallScore | None = None
    segments: list[Segment] = Field(default_factory=list)
    artifacts: Artifacts = Field(default_factory=Artifacts)
    quality_gate: QualityGate
