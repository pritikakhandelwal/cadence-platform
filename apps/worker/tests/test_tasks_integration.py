"""Verifies detect_tracks_job / extract_locked_pose_job actually write
to the shared `analyses` table -- the thing STATUS.md previously
flagged as an open, undecided question (shared DB vs. callback). Uses
a real temp SQLite file and a real temp runtime dir (both set via env
vars before cadence_db / cadence_workspace are ever imported in this
process -- cadence_db's engine in particular is created once, at
module-import time, so this has to happen before the imports below,
not inside a fixture) and the two real solo dance clips already on
this machine. Skips itself cleanly if ultralytics/rtmlib/cadence_db
aren't installed or the sample clips aren't present -- see
test_pipeline_integration.py for why these aren't in CI.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

# Must happen before `pytest.importorskip("cadence_db")` / any import of
# cadence_db or cadence_workspace below: cadence_db's engine is created
# once, from DATABASE_URL, at module-import time. Setting the env var
# after that first import (e.g. via a fixture) would silently do
# nothing -- the already-imported module keeps its original engine,
# bound to the default sqlite:///./cadence.db (a real bug this test
# file had until it was caught by finding a stray
# apps/worker/cadence.db after a run). cadence_workspace reads its env
# var lazily so this isn't strictly required for it, but setting both
# up front keeps the pattern consistent and keeps test runs out of the
# repo's real runtime/ directory.
_tmp_db_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db_dir}/test.db"
os.environ["CADENCE_RUNTIME_DIR"] = tempfile.mkdtemp()

pytest.importorskip("ultralytics")
pytest.importorskip("rtmlib")
pytest.importorskip("cadence_db")

_PROFESSIONAL_VIDEO = Path(
    os.environ.get(
        "CADENCE_SAMPLE_VIDEO",
        r"C:\Users\khand\Downloads\CADENCE\data\professional\professional_dance.mp4",
    )
)
_USER_VIDEO = Path(
    os.environ.get(
        "CADENCE_SAMPLE_USER_VIDEO",
        r"C:\Users\khand\Downloads\CADENCE\data\user\user_dance.mp4",
    )
)

if not _PROFESSIONAL_VIDEO.is_file() or not _USER_VIDEO.is_file():
    pytest.skip(
        f"sample videos not found ({_PROFESSIONAL_VIDEO}, {_USER_VIDEO})", allow_module_level=True
    )

from cadence_db import Analysis, Base, SessionLocal, User, engine  # noqa: E402
from cadence_workspace import create_analysis_workspace  # noqa: E402

from worker.pipeline.pipeline import detect_tracks  # noqa: E402
from worker.tasks import detect_tracks_job, extract_locked_pose_job  # noqa: E402


@pytest.fixture(autouse=True)
def _tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _make_queued_analysis(reference_video: Path = _PROFESSIONAL_VIDEO) -> tuple[str, str]:
    """Creates a real workspace (so _score_against_reference has an
    actual professional_upload.mp4 to find) and a queued Analysis row
    pointing at it. Returns (analysis_id, workspace_root)."""

    workspace = create_analysis_workspace()
    shutil.copyfile(reference_video, workspace.professional_upload)

    db = SessionLocal()
    try:
        user = User(name="Ada", email="ada@example.com", password_hash="x")
        db.add(user)
        db.commit()

        analysis = Analysis(user_id=user.id, workspace_id=workspace.run_id, status="queued")
        db.add(analysis)
        db.commit()
        return analysis.id, str(workspace.root)
    finally:
        db.close()


def test_detect_tracks_job_auto_locks_a_solo_clip_and_writes_a_complete_result():
    analysis_id, _ = _make_queued_analysis()

    outcome = asyncio.run(
        detect_tracks_job({}, analysis_id=analysis_id, video_path=str(_PROFESSIONAL_VIDEO))
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
        detect_tracks_job({}, analysis_id="does-not-exist", video_path=str(_PROFESSIONAL_VIDEO))
    )
    assert outcome.get("error") == "analysis_not_found"


def test_extract_locked_pose_job_resumes_from_stashed_detections_and_clears_them():
    """Simulates the POST /analyses/{id}/lock path: an analysis that
    already has detections stashed (as detect_tracks_job would leave
    for a needs_dancer_pick clip) gets locked onto a track without
    re-running detection."""

    from dataclasses import asdict

    summary, detections = detect_tracks(_PROFESSIONAL_VIDEO)
    track_id = summary.tracks[0].track_id

    analysis_id, _ = _make_queued_analysis()
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
            video_path=str(_PROFESSIONAL_VIDEO),
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


def test_full_pipeline_scores_a_real_user_clip_against_a_real_reference_clip():
    """The actual Phase 3 end-to-end path: two different real people
    (professional_dance.mp4 vs user_dance.mp4), scored against each
    other for real. There's no ground-truth "correct" score for these
    two unrelated clips, so this can't assert a specific number -- it
    asserts the structure is real and sane (0-100 score, ordered
    timestamped segments, keypoints actually persisted to disk), which
    is what's actually knowable without hand-labeled data."""

    analysis_id, workspace_root = _make_queued_analysis(reference_video=_PROFESSIONAL_VIDEO)

    outcome = asyncio.run(
        detect_tracks_job({}, analysis_id=analysis_id, video_path=str(_USER_VIDEO))
    )
    assert outcome["status"] == "complete", outcome

    db = SessionLocal()
    try:
        refreshed = db.get(Analysis, analysis_id)
        result = refreshed.result
        assert result["status"] == "complete"

        assert result["overall"] is not None
        assert 0.0 <= result["overall"]["score"] <= 100.0
        assert result["overall"]["method"]
        assert result["overall"]["version"]

        assert len(result["segments"]) > 0
        for prev, curr in zip(result["segments"], result["segments"][1:]):
            assert curr["t0"] >= prev["t0"]
        for segment in result["segments"]:
            assert 0.0 <= segment["score"] <= 100.0
            assert segment["t1"] >= segment["t0"]
            for issue in segment["issues"]:
                assert issue["type"] in ("angle", "timing", "path")
                assert issue["message"]
    finally:
        db.close()

    professional_npz = Path(workspace_root) / "professional_keypoints.npz"
    user_npz = Path(workspace_root) / "user_keypoints.npz"
    assert professional_npz.is_file(), "reference keypoints should have been persisted"
    assert user_npz.is_file(), "user keypoints should have been persisted"
