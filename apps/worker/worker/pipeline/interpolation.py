"""Fill short tracking gaps; leave long ones as real gaps.

Roadmap Phase 2: "Short-gap interpolation; drop track if quality
collapses." A 1-3 frame gap is almost always a missed detection on an
otherwise-present dancer (motion blur, brief occlusion by their own
limb) and linear interpolation is a safe fix. A longer gap usually
means the dancer actually left frame or got occluded by someone else
-- inventing a pose there would be a lie, so it's left missing and the
caller should treat it as a real discontinuity (a fresh smoothing
segment; see pipeline.py).
"""

from __future__ import annotations

import numpy as np


def interpolate_short_gaps(
    frames: dict[int, np.ndarray],
    max_gap: int = 3,
) -> dict[int, np.ndarray]:
    """Given {frame_idx: keypoints} for frames where a track was found
    (sparse -- missing frame_idx values are gaps), linearly interpolate
    across gaps of length <= max_gap. Gaps longer than max_gap are left
    unfilled.
    """

    if not frames:
        return {}

    known_frames = sorted(frames)
    filled = dict(frames)

    for previous, current in zip(known_frames, known_frames[1:]):
        gap = current - previous - 1
        if gap <= 0 or gap > max_gap:
            continue
        start_kp = frames[previous]
        end_kp = frames[current]
        for step in range(1, gap + 1):
            t = step / (gap + 1)
            filled[previous + step] = (1 - t) * start_kp + t * end_kp

    return filled


def split_into_contiguous_segments(frames: dict[int, np.ndarray]) -> list[list[int]]:
    """Group frame indices (after gap-filling) into runs with no missing
    frame in between. Each run should be smoothed independently -- the
    One-Euro filter assumes a continuous time series and shouldn't jump
    across a real discontinuity."""

    if not frames:
        return []

    ordered = sorted(frames)
    segments: list[list[int]] = [[ordered[0]]]
    for previous, current in zip(ordered, ordered[1:]):
        if current == previous + 1:
            segments[-1].append(current)
        else:
            segments.append([current])
    return segments
