from __future__ import annotations

import numpy as np

from worker.pipeline.alignment import dtw_align


def test_identical_sequences_align_on_the_diagonal():
    seq = np.array([[0.0], [1.0], [2.0], [3.0], [4.0]])
    path = dtw_align(seq, seq)
    assert path == [(i, i) for i in range(5)]


def test_path_spans_both_sequences_start_to_end():
    a = np.random.default_rng(0).normal(size=(10, 3))
    b = np.random.default_rng(1).normal(size=(7, 3))
    path = dtw_align(a, b)
    assert path[0] == (0, 0)
    assert path[-1] == (9, 6)


def test_path_indices_are_monotonically_non_decreasing():
    a = np.random.default_rng(0).normal(size=(12, 2))
    b = np.random.default_rng(1).normal(size=(9, 2))
    path = dtw_align(a, b)
    for (i1, j1), (i2, j2) in zip(path, path[1:]):
        assert i2 >= i1
        assert j2 >= j1


def test_a_stretched_copy_still_aligns_correctly_in_content():
    # b is a's values repeated -- a slower version of the same motion.
    # every frame of a should map to a stretch of matching-valued b frames.
    a = np.array([[0.0], [10.0], [20.0], [30.0]])
    b = np.array([[0.0], [0.0], [10.0], [10.0], [20.0], [20.0], [30.0], [30.0]])
    path = dtw_align(a, b)
    for i, j in path:
        assert abs(a[i, 0] - b[j, 0]) < 1e-9


def test_handles_nan_values_without_crashing():
    a = np.array([[1.0], [np.nan], [3.0]])
    b = np.array([[1.0], [2.0], [3.0]])
    path = dtw_align(a, b)
    assert path[0] == (0, 0)
    assert path[-1] == (2, 2)


def test_empty_sequences_return_empty_path():
    assert dtw_align(np.zeros((0, 3)), np.zeros((5, 3))) == []
    assert dtw_align(np.zeros((5, 3)), np.zeros((0, 3))) == []
