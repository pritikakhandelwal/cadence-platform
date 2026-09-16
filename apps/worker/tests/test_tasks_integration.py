"""Verifies detect_tracks_job actually writes to the shared `analyses`
table -- the thing STATUS.md previously flagged as an open, undecided
question (shared DB vs. callback). Uses a real temp SQLite file (set
via DATABASE_URL before cadence_db is ever imported in this process --
its engine is created once at import time, so this has to happen
before the `from cadence_db import ...` below, not inside a fixture)
and the same real solo dance clip the other Phase 2 integration tests
use. Skips itself cleanly if ultralytics/rtmlib/cadence_db aren't
installed or the sample clip isn't present -- see
test_pipeline_integration.py for why these aren't in CI.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

# Must happen before `pytest.importorskip("cadence_db")` / any import of
# cadence_db below: its engine is created once, from DATABASE_URL, at
# module-import time. Setting the env var after that first import (e.g.
# via a fixture) would silently do nothing -- the already-imported
# module keeps its original engine, bound to the default
# sqlite:///./cadence.db (a real bug this test file had until it was
# caught by finding a stray apps/worker/cadence.db after a run).
_tmp_db_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db_dir}/test.db"

pytest.importorskip("ultralytics")
pytest.importorskip("rtmlib")
pytest.importorskip("cadence_db")

_SAMPLE_VIDEO = Path(
    os.environ.get(
        "CADENCE_SAMPLE_VIDEO",
        r"C:\Users\khand\Downloads\CADENCE\data\professional\professional_dance.mp4",
    )
)

if not _SAMPLE_VIDEO.is_file():
    pytest.skip(f"sample video not found at {_SAMPLE_VIDEO}", allow_module_level=True)

from cadence_db import Analysis, Base, SessionLocal, User, engine  # noqa: E402

from worker.pipeline.pipeline import detect_tracks  # noqa: E402
from worker.tasks import detect_tracks_job, extract_locked_pose_job  # noqa: E402


@pytest.fixture(autouse=True)
def _tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _make_queued_analysis() -> str:
    db = SessionLocal()
    try:
        user = User(name="Ada", email="ada@example.com", password_hash="x")
        db.add(user)
        db.commit()

        analysis = Analysis(user_id=user.id, workspace_id="ws1", status="queued")
        db.add(analysis)
        db.commit()
        return analysis.id
    finally:
        db.close()


def test_detect_tracks_job_auto_locks_a_solo_clip_and_writes_a_complete_result():
    analysis_id = _make_queued_analysis()

    outcome = asyncio.run(
        detect_tracks_job({}, analysis_id=analysis_id, video_path=str(_SAMPLE_VIDEO))
    )
    assert outcome["status"] == "complete"

    db = SessionLocal()
    try:
        refreshed = db.get(Analysis, analysis_id)
        assert refreshed.status == "complete"
        assert refreshed.result is not None
        assert refreshed.result["quality_gate"]["passed"] is True
        assert refreshed.result["tracking"]["reliable_frame_pct"] > 50
        assert refreshed.result["tracking"]["lock_id"] is not None
    finally:
        db.close()


def test_detect_tracks_job_returns_gracefully_for_a_missing_analysis():
    outcome = asyncio.run(
        detect_tracks_job({}, analysis_id="does-not-exist", video_path=str(_SAMPLE_VIDEO))
    )
    assert outcome.get("error") == "analysis_not_found"


def test_extract_locked_pose_job_resumes_from_stashed_detections_and_clears_them():
    """Simulates the POST /analyses/{id}/lock path: an analysis that
    already has detections stashed (as detect_tracks_job would leave
    for a needs_dancer_pick clip) gets locked onto a track without
    re-running detection."""

    from dataclasses import asdict

    summary, detections = detect_tracks(_SAMPLE_VIDEO)
    track_id = summary.tracks[0].track_id

    analysis_id = _make_queued_analysis()
    db = SessionLocal()
    try:
        analysis = db.get(Analysis, analysis_id)
        analysis.status = "needs_dancer_pick"
        analysis.pending_lock_data = {
            "detections": [asdict(d) for d in detections],
            "fps": summary.fps,
            "total_frames": summary.total_frames,
            "tracks": [{"track_id": t.track_id, "frame_count": t.frame_count} for t in summary.tracks],
        }
        db.commit()
    finally:
        db.close()

    outcome = asyncio.run(
        extract_locked_pose_job(
            {},
            analysis_id=analysis_id,
            video_path=str(_SAMPLE_VIDEO),
            track_id=track_id,
            fps=summary.fps,
            total_frames=summary.total_frames,
            detections=[asdict(d) for d in detections],
        )
    )
    assert outcome["status"] == "complete"

    db = SessionLocal()
    try:
        refreshed = db.get(Analysis, analysis_id)
        assert refreshed.status == "complete"
        assert refreshed.result["quality_gate"]["passed"] is True
        assert refreshed.result["tracking"]["lock_id"] == str(track_id)
        assert refreshed.pending_lock_data is None
    finally:
        db.close()
