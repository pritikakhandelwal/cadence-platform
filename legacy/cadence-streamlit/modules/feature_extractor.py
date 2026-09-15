import os
import cv2
import numpy as np

from modules.pose_detector import PoseDetector

_detector = None


def get_detector() -> PoseDetector:
    global _detector
    if _detector is None:
        _detector = PoseDetector()
    return _detector


def extract_keypoints(results):

    if results is None or getattr(results, "pose_landmarks", None) is None:
        return None

    keypoints = []

    landmarks = results.pose_landmarks
    landmark_list = getattr(landmarks, "landmark", landmarks)

    if not hasattr(landmark_list, "__iter__"):
        return None

    for landmark in landmark_list:
        keypoints.extend([
            getattr(landmark, "x", 0.0),
            getattr(landmark, "y", 0.0),
            getattr(landmark, "z", 0.0)
        ])

    return np.array(keypoints)


def extract_keypoints_from_video(
    video_path,
    output_file,
    skeleton_output=None
):

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if width <= 0:
        width = 640

    if height <= 0:
        height = 480

    # Force every generated skeleton video to 30 FPS
    fps = 30

    writer = None

    if skeleton_output is not None:

        os.makedirs(os.path.dirname(skeleton_output), exist_ok=True)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        writer = cv2.VideoWriter(
            skeleton_output,
            fourcc,
            fps,
            (width, height)
        )

        if not writer.isOpened():
            cap.release()
            raise RuntimeError(f"Cannot create video: {skeleton_output}")

    all_keypoints = []
    detector = get_detector()

    try:
        while True:

            ret, frame = cap.read()

            if not ret:
                break

            frame, results = detector.detect_pose(frame)

            if writer is not None:
                writer.write(frame)

            keypoints = extract_keypoints(results)

            if keypoints is not None:
                all_keypoints.append(keypoints)
    finally:
        cap.release()
        if writer is not None:
            writer.release()

    all_keypoints = np.array(all_keypoints)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    np.save(output_file, all_keypoints)

    return all_keypoints.shape