from __future__ import annotations

from worker.pipeline.quality import (
    Detection,
    compute_lock_quality,
    evaluate_quality_gate,
    summarize_tracks,
)


def _det(frame_idx, track_id, conf=0.9):
    return Detection(frame_idx=frame_idx, track_id=track_id, bbox=(0, 0, 10, 10), confidence=conf)


def test_summarize_tracks_groups_by_track_id_and_ranks_by_frame_count():
    detections = [_det(i, track_id=1) for i in range(10)] + [_det(i, track_id=2) for i in range(3)]

    summaries = summarize_tracks(detections, fps=30.0)

    assert summaries[0].track_id == 1
    assert summaries[0].frame_count == 10
    assert summaries[1].track_id == 2
    assert summaries[1].frame_count == 3


def test_summarize_tracks_detects_fragmentation():
    # track 1 appears frames 0-4, disappears, reappears 10-14: two fragments
    detections = [_det(i, track_id=1) for i in range(5)] + [_det(i, track_id=1) for i in range(10, 15)]

    summaries = summarize_tracks(detections, fps=30.0)

    assert summaries[0].fragments == 2


def test_compute_lock_quality_on_solo_clip_with_no_gaps():
    total_frames = 100
    detections = [_det(i, track_id=1, conf=0.95) for i in range(total_frames)]

    quality = compute_lock_quality(detections, locked_track_id=1, total_frames=total_frames, fps=30.0)

    assert quality.reliable_frame_pct == 100.0
    assert quality.fragments == 1
    assert quality.person_count == 1
    assert quality.mean_confidence == 0.95


def test_compute_lock_quality_reflects_lost_frames():
    total_frames = 100
    # dancer only tracked for the first 40 frames of a 100-frame clip
    detections = [_det(i, track_id=1) for i in range(40)]

    quality = compute_lock_quality(detections, locked_track_id=1, total_frames=total_frames, fps=30.0)

    assert quality.reliable_frame_pct == 40.0


def test_compute_lock_quality_counts_other_people_toward_person_count():
    detections = [_det(i, track_id=1) for i in range(50)] + [_det(i, track_id=2) for i in range(50)]

    quality = compute_lock_quality(detections, locked_track_id=1, total_frames=50, fps=30.0)

    assert quality.person_count == 2
    assert quality.reliable_frame_pct == 100.0  # the locked track itself has full coverage


def test_quality_gate_passes_a_clean_solo_track():
    quality = compute_lock_quality(
        [_det(i, track_id=1) for i in range(100)], locked_track_id=1, total_frames=100, fps=30.0
    )
    gate = evaluate_quality_gate(quality)
    assert gate.passed is True
    assert gate.reasons == []


def test_quality_gate_rejects_a_mostly_lost_track():
    quality = compute_lock_quality(
        [_det(i, track_id=1) for i in range(20)], locked_track_id=1, total_frames=100, fps=30.0
    )
    gate = evaluate_quality_gate(quality)
    assert gate.passed is False
    assert "lost" in gate.reasons[0]


def test_quality_gate_rejects_heavily_fragmented_track():
    # 10 separate 1-frame appearances scattered through the clip
    detections = [_det(i * 5, track_id=1) for i in range(10)]
    quality = compute_lock_quality(detections, locked_track_id=1, total_frames=100, fps=30.0)
    gate = evaluate_quality_gate(quality, min_reliable_frame_pct=0)
    assert gate.passed is False
    assert any("broke and re-acquired" in reason for reason in gate.reasons)


def test_quality_gate_rejects_no_detections():
    quality = compute_lock_quality([], locked_track_id=1, total_frames=100, fps=30.0)
    gate = evaluate_quality_gate(quality)
    assert gate.passed is False
