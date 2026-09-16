"""Tracking quality metrics and the accept/reject gate.

Roadmap Phase 2 target metrics: reliable-frame % >= 90% on solo clips,
zero false locks on a mirror, time-to-first-lock < 2s. This module
computes what it actually can from a track's raw per-frame detections
-- it does not claim MOTA/IDF1 (those need ground-truth annotated
clips, which is the "film 30 clips yourself" eval work, not something
a single pipeline module can produce on its own).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Detection:
    frame_idx: int
    track_id: int
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2 in pixels
    confidence: float


@dataclass(frozen=True)
class TrackSummary:
    """One row of the "pick your dancer" list."""

    track_id: int
    frame_count: int
    first_frame: int
    last_frame: int
    mean_confidence: float
    fragments: int  # contiguous appearances; >1 means the track was lost and re-acquired


@dataclass(frozen=True)
class LockQuality:
    track_id: int
    total_frames: int
    reliable_frame_pct: float
    mean_confidence: float
    fragments: int
    person_count: int
    time_to_first_detection_seconds: float


def _contiguous_runs(frame_indices: list[int]) -> int:
    if not frame_indices:
        return 0
    ordered = sorted(frame_indices)
    runs = 1
    for previous, current in zip(ordered, ordered[1:]):
        if current != previous + 1:
            runs += 1
    return runs


def summarize_tracks(detections: list[Detection], fps: float) -> list[TrackSummary]:
    """Group raw per-frame detections into one summary per track_id, for
    the multi-person "pick your dancer" UI."""

    by_track: dict[int, list[Detection]] = {}
    for det in detections:
        by_track.setdefault(det.track_id, []).append(det)

    summaries = []
    for track_id, dets in by_track.items():
        frames = [d.frame_idx for d in dets]
        summaries.append(
            TrackSummary(
                track_id=track_id,
                frame_count=len(dets),
                first_frame=min(frames),
                last_frame=max(frames),
                mean_confidence=sum(d.confidence for d in dets) / len(dets),
                fragments=_contiguous_runs(frames),
            )
        )
    return sorted(summaries, key=lambda s: s.frame_count, reverse=True)


def compute_lock_quality(
    detections: list[Detection],
    locked_track_id: int,
    total_frames: int,
    fps: float,
) -> LockQuality:
    """Quality metrics for one locked track across the whole clip."""

    if total_frames <= 0:
        raise ValueError("total_frames must be positive")

    locked = [d for d in detections if d.track_id == locked_track_id]
    frames = [d.frame_idx for d in locked]
    person_count = len({d.track_id for d in detections})

    all_frames_with_any_person = sorted({d.frame_idx for d in detections})
    time_to_first_detection = (
        all_frames_with_any_person[0] / fps if all_frames_with_any_person else float("inf")
    )

    return LockQuality(
        track_id=locked_track_id,
        total_frames=total_frames,
        reliable_frame_pct=100.0 * len(frames) / total_frames,
        mean_confidence=(sum(d.confidence for d in locked) / len(locked)) if locked else 0.0,
        fragments=_contiguous_runs(frames),
        person_count=person_count,
        time_to_first_detection_seconds=time_to_first_detection,
    )


@dataclass(frozen=True)
class QualityGateResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)


def is_lock_ambiguous(tracks: list[TrackSummary], dominance_ratio: float = 0.5) -> bool:
    """True if there's no single clearly-dominant track -- i.e. picking
    the track with the most frames would be a guess, not a confident
    lock.

    Found by testing against a synthetic mirror clip (one dancer +
    their own horizontally-flipped reflection): YOLO+ByteTrack produced
    4 fragmented track IDs for what's really one person + one
    reflection, and naively locking onto "whichever track has the most
    frames" would silently pick one without any signal that the scene
    was ambiguous. This catches that case (and the equally real case
    of two actual people of comparable screen time) by comparing the
    top two tracks' frame counts -- it does not try to guess *which*
    track is the real dancer, it just refuses to guess at all. See
    STATUS.md's Phase 2 section for the actual numbers from that test.
    """

    if len(tracks) <= 1:
        return False
    largest, second = tracks[0].frame_count, tracks[1].frame_count
    if largest == 0:
        return True
    return (second / largest) >= dominance_ratio


def evaluate_quality_gate(
    quality: LockQuality,
    min_reliable_frame_pct: float = 60.0,
    max_fragments: int = 6,
) -> QualityGateResult:
    """Decide whether a locked track is trustworthy enough to score.

    Thresholds are deliberately conservative defaults for v1 -- tune
    against the roadmap's planned 30-clip internal eval set once it
    exists, not against guesses.
    """

    reasons = []
    if quality.reliable_frame_pct < min_reliable_frame_pct:
        lost_pct = 100 - quality.reliable_frame_pct
        reasons.append(f"Dancer lost for {lost_pct:.0f}% of the clip.")
    if quality.fragments > max_fragments:
        reasons.append(
            f"Tracking broke and re-acquired {quality.fragments} times -- likely occlusion or crossing."
        )
    if quality.person_count == 0:
        reasons.append("No person detected in this clip.")

    return QualityGateResult(passed=len(reasons) == 0, reasons=reasons)
