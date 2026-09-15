"""Pose estimation on a crop, using RTMPose via rtmlib.

Roadmap Phase 2: "Pose on crop only (RTMPose-m default)". We already
have a person bbox from YOLO+ByteTrack (detection.py); rather than
depend on rtmlib's exact low-level bbox-conditioned API (which we
can't verify offline against docs), we crop the frame to that bbox
ourselves with a plain numpy slice and hand rtmlib *only that crop*.
This still satisfies "pose on crop only" literally -- the pose model
never sees a second person or the background outside the bbox -- while
only depending on rtmlib's simplest, best-documented entry point:
`Body(image) -> (keypoints, scores)`.
"""

from __future__ import annotations

import numpy as np


class PoseEstimator:
    """Wraps rtmlib's Body (RTMDet-person + RTMPose) model. One instance
    per process -- the underlying onnxruntime session is expensive to
    create and safe to reuse across frames."""

    def __init__(self, mode: str = "balanced", backend: str = "onnxruntime", device: str = "cpu"):
        from rtmlib import Body

        self._body = Body(to_openpose=False, mode=mode, backend=backend, device=device)

    def estimate(
        self, frame_bgr: np.ndarray, bbox: tuple[float, float, float, float]
    ) -> tuple[np.ndarray, np.ndarray]:
        """Run pose estimation on the region of `frame_bgr` inside
        `bbox` (x1, y1, x2, y2). Returns (keypoints, scores) in the
        *original frame's* coordinate space -- (num_joints, 2) and
        (num_joints,) -- for the most confident person found in the
        crop (there should only be one, since we cropped to one
        person's bbox already).

        Returns all-zero keypoints/scores if no person is found in the
        crop (e.g. the bbox was mostly motion-blur).
        """

        x1, y1, x2, y2 = (int(round(v)) for v in bbox)
        crop = frame_bgr[y1:y2, x1:x2]
        if crop.size == 0:
            return np.zeros((17, 2)), np.zeros(17)

        keypoints, scores = self._body(crop)
        if keypoints is None or len(keypoints) == 0:
            return np.zeros((17, 2)), np.zeros(17)

        # Body can return multiple detections even inside a single-person
        # crop (e.g. a reflection); keep the one with highest mean score.
        best_idx = int(np.argmax(scores.mean(axis=1)))
        best_keypoints = keypoints[best_idx].astype(float)
        best_scores = scores[best_idx].astype(float)

        best_keypoints[:, 0] += x1
        best_keypoints[:, 1] += y1

        return best_keypoints, best_scores
