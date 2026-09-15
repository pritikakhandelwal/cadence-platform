import cv2
import numpy as np

from modules.pose_detector import PoseDetector
from modules.feature_extractor import extract_keypoints

detector = PoseDetector()

cap = cv2.VideoCapture(0)

while True:

    ret, frame = cap.read()

    if not ret:
        break

    frame, results = detector.detect_pose(frame)

    keypoints = extract_keypoints(results)

    if keypoints is not None:

        print("Number of values:", len(keypoints))
        print(keypoints[:12])  # Show first 12 values

    cv2.imshow("Keypoint Extraction", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()