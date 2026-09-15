from __future__ import annotations

import numpy as np

from worker.pipeline.interpolation import interpolate_short_gaps, split_into_contiguous_segments


def test_fills_a_short_gap_linearly():
    frames = {0: np.array([[0.0, 0.0]]), 4: np.array([[4.0, 4.0]])}
    filled = interpolate_short_gaps(frames, max_gap=3)

    assert set(filled) == {0, 1, 2, 3, 4}
    np.testing.assert_allclose(filled[2], [[2.0, 2.0]])


def test_leaves_a_long_gap_unfilled():
    frames = {0: np.array([[0.0, 0.0]]), 10: np.array([[10.0, 10.0]])}
    filled = interpolate_short_gaps(frames, max_gap=3)

    assert set(filled) == {0, 10}


def test_empty_input_returns_empty():
    assert interpolate_short_gaps({}, max_gap=3) == {}


def test_split_into_contiguous_segments_groups_runs():
    frames = {0: None, 1: None, 2: None, 10: None, 11: None, 20: None}
    segments = split_into_contiguous_segments(frames)
    assert segments == [[0, 1, 2], [10, 11], [20]]


def test_split_into_contiguous_segments_empty():
    assert split_into_contiguous_segments({}) == []
