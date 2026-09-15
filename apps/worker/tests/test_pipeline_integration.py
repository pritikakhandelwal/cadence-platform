"""End-to-end verification against a real dance video with a real
person in it -- something the pure-logic unit tests can't prove.

Skipped automatically wherever the sample video isn't present (any
machine but the one this was developed on) or the ML deps aren't
installed (kept out of the default CI job below because a first-time
model download plus CPU inference is slow; this is meant to be run
locally, e.g. `pytest -m integration`).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_SAMPLE_VIDEO = Path(
    os.environ.get(
        "CADENCE_SAMPLE_VIDEO",
        r"C:\Users\khand\Downloads\CADENCE\data\professional\professional_dance.mp4",
    )
)

pytest.importorskip("ultralytics")
pytest.importorskip("rtmlib")

if not _SAMPLE_VIDEO.is_file():
    pytest.skip(f"sample video not found at {_SAMPLE_VIDEO}", allow_module_level=True)


def test_detect_tracks_finds_at_least_one_person():
    from worker.pipeline.pipeline import detect_tracks

    summary, detections = detect_tracks(_SAMPLE_VIDEO)

    assert summary.total_frames > 0
    assert summary.fps > 0
    assert len(summary.tracks) >= 1
    assert len(detections) > 0
    # a solo reference clip should have a clearly dominant track
    assert summary.tracks[0].frame_count / summary.total_frames > 0.5


def test_extract_locked_pose_produces_plausible_keypoints():
    from worker.pipeline.pipeline import detect_tracks, extract_locked_pose

    summary, detections = detect_tracks(_SAMPLE_VIDEO)
    primary_track = summary.tracks[0].track_id

    result = extract_locked_pose(
        _SAMPLE_VIDEO, detections, primary_track, summary.fps, summary.total_frames
    )

    assert result.quality_gate.passed, result.quality_gate.reasons
    assert len(result.keypoints) > 0
    assert result.quality.reliable_frame_pct > 50

    first_pose = result.keypoints[0]
    assert first_pose.shape[1] == 2
    # keypoints should land inside the frame, not at the origin or NaN
    assert not (first_pose == 0).all()
