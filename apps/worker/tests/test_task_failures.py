"""What happens to an analysis when the pipeline blows up.

Before this was handled, an exception inside detect_tracks_job /
extract_locked_pose_job made arq mark the *job* failed while the *analysis
row* stayed `queued` forever -- the UI polled it indefinitely. These tests
fake the pipeline module (so no ML dependencies are needed, and they run in
CI's lightweight worker job) and use an in-memory database, so they check
the one thing that matters: the row always ends in a state the frontend
knows how to show.
"""

import asyncio
import sys
import types

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("cadence_db")

import cadence_db  # noqa: E402
from cadence_db import Analysis, Base, User  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from worker.pipeline.quality import TrackSummary  # noqa: E402
from worker.tasks import detect_tracks_job, extract_locked_pose_job  # noqa: E402


@pytest.fixture
def Session(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(cadence_db, "SessionLocal", factory)
    return factory


def _make_analysis(Session, status="queued", pending_lock_data=None) -> str:
    db = Session()
    try:
        user = User(name="Ada", email="ada@example.com", password_hash="x")
        db.add(user)
        db.commit()
        analysis = Analysis(
            user_id=user.id, workspace_id="w", status=status, pending_lock_data=pending_lock_data
        )
        db.add(analysis)
        db.commit()
        return analysis.id
    finally:
        db.close()


def _reload(Session, analysis_id: str) -> Analysis:
    db = Session()
    try:
        analysis = db.get(Analysis, analysis_id)
        db.expunge(analysis)
        return analysis
    finally:
        db.close()


def _fake_pipeline(monkeypatch, **functions):
    module = types.ModuleType("worker.pipeline.pipeline")
    for name, fn in functions.items():
        setattr(module, name, fn)
    monkeypatch.setitem(sys.modules, "worker.pipeline.pipeline", module)


def _one_track_summary():
    track = TrackSummary(track_id=1, frame_count=100, first_frame=0, last_frame=99, mean_confidence=0.9, fragments=1)
    return types.SimpleNamespace(tracks=[track], fps=30.0, total_frames=100)


def _boom(*args, **kwargs):
    raise RuntimeError("boom")


def _assert_rejected_as_our_fault(analysis: Analysis):
    assert analysis.status == "rejected"
    assert analysis.result["status"] == "rejected"
    assert analysis.result["quality_gate"]["passed"] is False
    assert "our side" in analysis.result["quality_gate"]["reasons"][0]


def test_detection_crash_is_recorded_not_left_queued_forever(Session, monkeypatch):
    analysis_id = _make_analysis(Session)
    _fake_pipeline(monkeypatch, detect_tracks=_boom, extract_locked_pose=_boom)

    outcome = asyncio.run(detect_tracks_job({}, analysis_id=analysis_id, video_path="x.mp4"))

    assert outcome["status"] == "rejected"
    _assert_rejected_as_our_fault(_reload(Session, analysis_id))


def test_pose_extraction_crash_after_a_good_detection_is_recorded(Session, monkeypatch):
    analysis_id = _make_analysis(Session)
    _fake_pipeline(monkeypatch, detect_tracks=lambda path: (_one_track_summary(), []), extract_locked_pose=_boom)

    asyncio.run(detect_tracks_job({}, analysis_id=analysis_id, video_path="x.mp4"))

    _assert_rejected_as_our_fault(_reload(Session, analysis_id))


def test_a_crash_while_scoring_against_the_reference_is_recorded(Session, monkeypatch):
    import worker.tasks as tasks

    analysis_id = _make_analysis(Session)
    _fake_pipeline(
        monkeypatch,
        detect_tracks=lambda path: (_one_track_summary(), []),
        extract_locked_pose=lambda *a, **k: types.SimpleNamespace(),
    )
    monkeypatch.setattr(tasks, "_finish_lock", _boom)

    asyncio.run(detect_tracks_job({}, analysis_id=analysis_id, video_path="x.mp4"))

    _assert_rejected_as_our_fault(_reload(Session, analysis_id))


def test_a_legitimate_rejection_keeps_its_own_reason(Session, monkeypatch):
    # "no person detected" is the user's video, not our bug -- the safety net
    # must not overwrite it with the generic internal-error message.
    analysis_id = _make_analysis(Session)
    empty = types.SimpleNamespace(tracks=[], fps=30.0, total_frames=100)
    _fake_pipeline(monkeypatch, detect_tracks=lambda path: (empty, []), extract_locked_pose=_boom)

    asyncio.run(detect_tracks_job({}, analysis_id=analysis_id, video_path="x.mp4"))

    analysis = _reload(Session, analysis_id)
    assert analysis.status == "rejected"
    assert analysis.result["quality_gate"]["reasons"] == ["No person detected in this clip."]


def test_a_crash_after_picking_a_dancer_is_recorded_and_clears_the_stashed_detections(Session, monkeypatch):
    analysis_id = _make_analysis(
        Session, status="needs_dancer_pick", pending_lock_data={"tracks": [{"track_id": 1}], "detections": []}
    )
    _fake_pipeline(monkeypatch, detect_tracks=_boom, extract_locked_pose=_boom)

    outcome = asyncio.run(
        extract_locked_pose_job(
            {}, analysis_id=analysis_id, video_path="x.mp4", track_id=1, fps=30.0, total_frames=100, detections=[]
        )
    )

    assert outcome["status"] == "rejected"
    analysis = _reload(Session, analysis_id)
    _assert_rejected_as_our_fault(analysis)
    assert analysis.pending_lock_data is None
