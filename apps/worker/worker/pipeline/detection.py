"""Person detection + multi-object identity tracking.

Roadmap Phase 2: "YOLO / RTMO -- Person detect", "ByteTrack or BoT-SORT
-- Identity across frames". Ultralytics ships both YOLO detection and a
ByteTrack/BoT-SORT tracker together via `model.track()`, so this module
is a thin, deliberately dumb wrapper around that rather than a
hand-rolled tracker -- reimplementing ByteTrack ourselves would be a
research project, not an integration.
"""

from __future__ import annotations

from pathlib import Path

from .quality import Detection

_PERSON_CLASS_ID = 0  # COCO class id for "person"

_model_cache: dict[str, object] = {}


def _get_model(weights: str):
    if weights not in _model_cache:
        from ultralytics import YOLO

        _model_cache[weights] = YOLO(weights)
    return _model_cache[weights]


def detect_and_track(
    video_path: str | Path,
    weights: str = "yolov8n.pt",
    tracker: str = "bytetrack.yaml",
    confidence_threshold: float = 0.3,
) -> tuple[list[Detection], float, int]:
    """Run person detection + tracking over every frame of a video.

    Returns (detections, fps, total_frame_count). `weights` defaults to
    the small YOLOv8 checkpoint (auto-downloaded by ultralytics on
    first use) -- good enough to prove the pipeline; swap for a larger
    checkpoint once accuracy on the real eval clips demands it.
    """

    import cv2

    model = _get_model(weights)

    results = model.track(
        source=str(video_path),
        classes=[_PERSON_CLASS_ID],
        tracker=tracker,
        conf=confidence_threshold,
        stream=True,
        verbose=False,
    )

    detections: list[Detection] = []
    total_frames = 0
    for frame_idx, result in enumerate(results):
        total_frames += 1
        boxes = result.boxes
        if boxes is None or boxes.id is None:
            continue
        for box_idx in range(len(boxes)):
            detections.append(
                Detection(
                    frame_idx=frame_idx,
                    track_id=int(boxes.id[box_idx].item()),
                    bbox=tuple(boxes.xyxy[box_idx].tolist()),
                    confidence=float(boxes.conf[box_idx].item()),
                )
            )

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()

    return detections, fps, total_frames
