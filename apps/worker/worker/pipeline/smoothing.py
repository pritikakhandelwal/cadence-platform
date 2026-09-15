"""One-Euro filtering for keypoint jitter.

Reference algorithm: Casiez, Roussel, Vogel, "1-Euro Filter: A Simple
Speed-based Low-pass Filter for Noisy Input in Interactive Systems"
(CHI 2012). Pose landmarks are noisy frame-to-frame even when tracking
is perfect (roadmap Phase 2: "One-Euro or Savitzky-Golay smoothing --
kill jitter"); we chose One-Euro because it adapts to speed -- it barely
smooths a fast whip turn (where lag would hide real motion) but heavily
smooths a still pose (where jitter is pure noise).
"""

from __future__ import annotations

import math

import numpy as np


class _LowPassFilter:
    def __init__(self, alpha: float):
        self._alpha = alpha
        self._y: float | None = None

    def set_alpha(self, alpha: float) -> None:
        self._alpha = alpha

    def filter(self, value: float) -> float:
        if self._y is None:
            self._y = value
        else:
            self._y = self._alpha * value + (1 - self._alpha) * self._y
        return self._y

    @property
    def last_value(self) -> float | None:
        return self._y


class OneEuroFilter:
    """Filters a single scalar time series."""

    def __init__(self, freq: float, min_cutoff: float = 1.0, beta: float = 0.0, d_cutoff: float = 1.0):
        if freq <= 0:
            raise ValueError("freq must be positive")
        self.freq = freq
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x_filter = _LowPassFilter(self._alpha(min_cutoff))
        self._dx_filter = _LowPassFilter(self._alpha(d_cutoff))
        self._last_time: float | None = None

    def _alpha(self, cutoff: float) -> float:
        te = 1.0 / self.freq
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / te)

    def __call__(self, value: float, timestamp: float | None = None) -> float:
        if timestamp is not None and self._last_time is not None:
            dt = timestamp - self._last_time
            if dt > 0:
                self.freq = 1.0 / dt
        self._last_time = timestamp

        previous = self._x_filter.last_value if self._x_filter.last_value is not None else value
        dx = (value - previous) * self.freq
        edx = self._dx_filter.filter(dx)
        cutoff = self.min_cutoff + self.beta * abs(edx)
        self._x_filter.set_alpha(self._alpha(cutoff))
        return self._x_filter.filter(value)


def smooth_keypoint_sequence(
    keypoints: list[np.ndarray],
    fps: float,
    min_cutoff: float = 1.0,
    beta: float = 0.3,
) -> list[np.ndarray]:
    """Smooth a sequence of (num_joints, 2) keypoint arrays across time.

    One filter per (joint, axis), independent of confidence — callers
    that want confidence-weighted smoothing should mask low-confidence
    points before calling this. Frames are assumed contiguous at a
    constant `fps`; don't feed it a sequence with a lock gap in the
    middle without resetting (create a new filter bank per contiguous
    segment).
    """

    if not keypoints:
        return []

    num_joints = keypoints[0].shape[0]
    filters = [
        [OneEuroFilter(freq=fps, min_cutoff=min_cutoff, beta=beta) for _ in range(2)]
        for _ in range(num_joints)
    ]

    smoothed: list[np.ndarray] = []
    for frame_idx, frame in enumerate(keypoints):
        timestamp = frame_idx / fps
        out = np.empty_like(frame, dtype=float)
        for joint in range(num_joints):
            for axis in range(2):
                out[joint, axis] = filters[joint][axis](float(frame[joint, axis]), timestamp)
        smoothed.append(out)
    return smoothed
