import cv2
import numpy as np

from modules.pose_detector import PoseDetector
from modules.feature_extractor import extract_keypoints

detector = PoseDetector()

video_path = "data/users/user_dance.mp4"
cap = cv2.VideoCapture(video_path)

all_keypoints = []

print("Processing user video...")

while True:

    ret, frame = cap.read()

    if not ret:
        break

    frame, results = detector.detect_pose(frame)

    keypoints = extract_keypoints(results)

    if keypoints is not None:
        all_keypoints.append(keypoints)

    cv2.imshow("User Video", frame)

    if cv2.waitKey(30) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

all_keypoints = np.array(all_keypoints)

np.save(
    "extracted_keypoints/user.npy",
    all_keypoints
)

print("Done!")
print("Shape:", all_keypoints.shape)
print("Saved to extracted_keypoints/user.npy")