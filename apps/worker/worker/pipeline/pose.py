"""Pose estimation on a crop, using RTMPose via rtmlib.

Roadmap Phase 2: "Pose on crop only (RTMPose-m default)".

First version of this file fed a pre-cropped image into rtmlib's high-
level `Body` helper, which bundles its *own* internal YOLOX person
detector -- so every frame ran two detectors (our YOLO+ByteTrack one in
detection.py, then Body's YOLOX one again) even though we already knew
exactly where the person was. That's why the first integration run took
~48 minutes for a few seconds of footage (see STATUS.md's Phase 2
section for that history).

Fix: call rtmlib's low-level `RTMPose` model directly with our own
bbox. `RTMPose.__call__(image, bboxes=[bbox])` takes the *full* frame
and does its own affine crop internally per bbox (with sensible
padding) -- it never looks outside that bbox, so "pose on crop only"
still holds, but there's exactly one model doing inference per frame
instead of two. We resolve the actual RTMPose-m onnx weights via
rtmlib's own `Body.MODE` registry rather than hardcoding a model URL
ourselves -- that registry is the thing that knows which checkpoint
goes with which `mode`, and hardcoding our own copy of it would drift
the moment rtmlib updates its model zoo.
"""

from __future__ import annotations

import numpy as np


class PoseEstimator:
    """Wraps rtmlib's RTMPose model directly (no internal detector).
    One instance per process -- the underlying onnxruntime session is
    expensive to create and safe to reuse across frames."""

    def __init__(self, mode: str = "balanced", backend: str = "onnxruntime", device: str = "cpu"):
        from rtmlib import RTMPose
        from rtmlib.tools.solution.body import Body

        pose_url = Body.MODE[mode]["pose"]
        pose_input_size = Body.MODE[mode]["pose_input_size"]
        self._pose_model = RTMPose(
            pose_url,
            model_input_size=pose_input_size,
            to_openpose=False,
            backend=backend,
            device=device,
        )

    def estimate(
        self, frame_bgr: np.ndarray, bbox: tuple[float, float, float, float]
    ) -> tuple[np.ndarray, np.ndarray]:
        """Run pose estimation for the person inside `bbox` (x1, y1, x2,
        y2) of `frame_bgr`. Returns (keypoints, scores) already in the
        original frame's coordinate space -- (num_joints, 2) and
        (num_joints,) -- since RTMPose's own postprocessing maps its
        internal crop-space prediction back to the coordinates of
        whatever image it was given.
        """

        keypoints, scores = self._pose_model(frame_bgr, bboxes=[list(bbox)])
        return keypoints[0].astype(float), scores[0].astype(float)
