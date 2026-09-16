"""DTW alignment on normalized joint-angle feature sequences.

Roadmap Phase 3: "DTW/Soft-DTW on the feature sequence for alignment."
This is classic (hard) DTW, not Soft-DTW -- simpler, dependency-free
(a plain O(N*M) numpy DP table), and sufficient for producing a
warping path; Soft-DTW's advantage is a differentiable path for
gradient-based training, which nothing here needs.

Scaling note: this is an O(N*M) time *and* memory implementation --
fine for clips of a few hundred frames (what's been tested), but a
full 5-minute clip at 30fps (9000 frames) would need an 9000x9000
table (~650MB). Not fixed here; the standard fix is a Sakoe-Chiba
band restricting the path to a diagonal corridor. Don't assume this
scales to the platform's MAX_DURATION_SECONDS without adding that.
"""

from __future__ import annotations

import numpy as np


def _impute_nans_with_column_mean(matrix: np.ndarray) -> np.ndarray:
    """Replaces NaN entries with that column's own mean, so a frame
    with one degenerate joint angle doesn't poison every DTW distance
    it participates in. A column that's entirely NaN becomes all
    zeros (no signal, but no crash)."""

    matrix = matrix.copy()
    for col in range(matrix.shape[1]):
        column = matrix[:, col]
        valid = ~np.isnan(column)
        if valid.all():
            continue
        fill = np.mean(column[valid]) if valid.any() else 0.0
        column[~valid] = fill
    return matrix


def dtw_align(seq_a: np.ndarray, seq_b: np.ndarray) -> list[tuple[int, int]]:
    """Classic DTW between two (T, F) feature sequences (Euclidean
    per-frame distance). Returns the warping path as a list of
    (index_in_a, index_in_b) pairs, from (0, 0) to (len(a)-1, len(b)-1),
    monotonically non-decreasing in both indices.
    """

    if len(seq_a) == 0 or len(seq_b) == 0:
        return []

    seq_a = _impute_nans_with_column_mean(seq_a)
    seq_b = _impute_nans_with_column_mean(seq_b)

    n, m = len(seq_a), len(seq_b)
    cost = np.full((n + 1, m + 1), np.inf)
    cost[0, 0] = 0.0

    for i in range(1, n + 1):
        row_i = seq_a[i - 1]
        for j in range(1, m + 1):
            distance = float(np.linalg.norm(row_i - seq_b[j - 1]))
            cost[i, j] = distance + min(cost[i - 1, j], cost[i, j - 1], cost[i - 1, j - 1])

    path: list[tuple[int, int]] = []
    i, j = n, m
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        step = min(cost[i - 1, j - 1], cost[i - 1, j], cost[i, j - 1])
        if step == cost[i - 1, j - 1]:
            i, j = i - 1, j - 1
        elif step == cost[i - 1, j]:
            i -= 1
        else:
            j -= 1
    path.reverse()
    return path
