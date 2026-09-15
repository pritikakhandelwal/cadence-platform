from __future__ import annotations

import numpy as np

from worker.pipeline.smoothing import OneEuroFilter, smooth_keypoint_sequence


def test_one_euro_filter_reduces_noise_on_a_stationary_signal():
    rng = np.random.default_rng(42)
    true_value = 10.0
    noisy = [true_value + rng.normal(scale=0.5) for _ in range(100)]

    filt = OneEuroFilter(freq=30.0, min_cutoff=1.0, beta=0.0)
    filtered = [filt(v, timestamp=i / 30.0) for i, v in enumerate(noisy)]

    raw_error = np.mean([(v - true_value) ** 2 for v in noisy[20:]])
    filtered_error = np.mean([(v - true_value) ** 2 for v in filtered[20:]])
    assert filtered_error < raw_error


def test_one_euro_filter_tracks_a_ramp_without_diverging():
    filt = OneEuroFilter(freq=30.0, min_cutoff=1.0, beta=1.0)
    values = [filt(float(i), timestamp=i / 30.0) for i in range(60)]
    # should end up close to the true ramp value, not lagging forever
    assert abs(values[-1] - 59) < 5


def test_smooth_keypoint_sequence_shapes_are_preserved():
    frames = [np.array([[1.0, 2.0], [3.0, 4.0]]) for _ in range(10)]
    smoothed = smooth_keypoint_sequence(frames, fps=30.0)
    assert len(smoothed) == len(frames)
    assert smoothed[0].shape == frames[0].shape


def test_smooth_keypoint_sequence_reduces_jitter():
    rng = np.random.default_rng(0)
    true_pose = np.array([[5.0, 5.0]])
    frames = [true_pose + rng.normal(scale=0.3, size=true_pose.shape) for _ in range(60)]

    smoothed = smooth_keypoint_sequence(frames, fps=30.0)

    raw_variance = np.var([f[0, 0] for f in frames[10:]])
    smoothed_variance = np.var([f[0, 0] for f in smoothed[10:]])
    assert smoothed_variance < raw_variance


def test_empty_sequence_returns_empty():
    assert smooth_keypoint_sequence([], fps=30.0) == []
