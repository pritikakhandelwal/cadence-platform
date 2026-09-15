import os
import urllib.request
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import drawing_utils, PoseLandmarksConnections


class PoseResults:
    """Standardized results container across MediaPipe versions."""

    def __init__(self, pose_landmarks=None):
        self.pose_landmarks = pose_landmarks


class PoseDetector:
    def __init__(self):
        self._landmarker = None
        self._initialized = False

    def _ensure_model_file(self) -> str:
        """Ensure the MediaPipe PoseLandmarker model task file exists locally."""
        model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, "pose_landmarker_full.task")

        if not os.path.exists(model_path) or os.path.getsize(model_path) < 1000:
            url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task"
            try:
                urllib.request.urlretrieve(url, model_path)
            except Exception:
                # Fallback to lite model if full download fails
                lite_path = os.path.join(model_dir, "pose_landmarker_lite.task")
                if not os.path.exists(lite_path):
                    lite_url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
                    urllib.request.urlretrieve(lite_url, lite_path)
                return lite_path

        return model_path

    def _ensure_initialized(self):
        if self._initialized:
            return

        try:
            model_path = self._ensure_model_file()
            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.PoseLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE,
                num_poses=1,
                min_pose_detection_confidence=0.3,
                min_pose_presence_confidence=0.3,
                min_tracking_confidence=0.3,
            )
            self._landmarker = vision.PoseLandmarker.create_from_options(options)
        except Exception:
            self._landmarker = None

        self._initialized = True

    def detect_pose(self, frame):
        """
        Detect 33 pose landmarks on a BGR video frame and draw skeleton connections.
        Returns (annotated_frame, PoseResults).
        """
        self._ensure_initialized()

        if self._landmarker is None or frame is None or frame.size == 0:
            return frame, PoseResults(None)

        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            detection_result = self._landmarker.detect(mp_image)

            if detection_result.pose_landmarks and len(detection_result.pose_landmarks) > 0:
                landmarks = detection_result.pose_landmarks[0]
                # Draw skeleton connections and landmark points onto the frame
                drawing_utils.draw_landmarks(
                    frame,
                    landmarks,
                    PoseLandmarksConnections.POSE_LANDMARKS
                )
                return frame, PoseResults(landmarks)
        except Exception:
            pass

        return frame, PoseResults(None)