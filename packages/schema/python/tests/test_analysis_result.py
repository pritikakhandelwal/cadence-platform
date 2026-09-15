from cadence_schema import AnalysisResult, AnalysisStatus, QualityGate, TrackingInfo


def test_minimal_valid_result():
    result = AnalysisResult(
        analysis_id="a1",
        user_id="u1",
        status=AnalysisStatus.queued,
        tracking=TrackingInfo(confidence=0.0, reliable_frame_pct=0.0, person_count=0),
        quality_gate=QualityGate(passed=False, reasons=["not started"]),
    )
    assert result.status is AnalysisStatus.queued
    assert result.segments == []


def test_score_bounds_are_enforced():
    from pydantic import ValidationError

    try:
        TrackingInfo(confidence=1.5, reliable_frame_pct=0, person_count=0)
    except ValidationError:
        return
    raise AssertionError("confidence above 1 should be rejected")
