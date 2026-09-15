import cv2
import numpy as np

from modules.pose_detector import PoseDetector
from modules.feature_extractor import extract_keypoints

detector = PoseDetector()

cap = cv2.VideoCapture(0)

all_keypoints = []

print("Recording... Press 'q' to stop.")

while True:

    ret, frame = cap.read()

    if not ret:
        break

    frame, results = detector.detect_pose(frame)

    keypoints = extract_keypoints(results)

    if keypoints is not None:
        all_keypoints.append(keypoints)

    cv2.imshow("Recording Dance", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# Convert list to NumPy array
all_keypoints = np.array(all_keypoints)

print("Shape:", all_keypoints.shape)

# Save keypoints
np.save("extracted_keypoints/user_dance.npy", all_keypoints)

print("Keypoints saved successfully!")