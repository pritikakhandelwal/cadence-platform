import cv2
import numpy as np

from modules.pose_detector import PoseDetector
from modules.feature_extractor import extract_keypoints

# Initialize Pose Detector
detector = PoseDetector()

# Load the professional dance video
video_path = "data/professional/professional_dance.mp4"
cap = cv2.VideoCapture(video_path)

# List to store keypoints of every frame
all_keypoints = []

print("Processing video...")

while True:

    ret, frame = cap.read()

    if not ret:
        break

    # Detect pose
    frame, results = detector.detect_pose(frame)

    # Extract keypoints
    keypoints = extract_keypoints(results)

    # Save only if a pose is detected
    if keypoints is not None:
        all_keypoints.append(keypoints)

    # Show video with skeleton
    cv2.imshow("Processing Video", frame)

    # Press q to stop
    if cv2.waitKey(30) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# Convert to NumPy array
all_keypoints = np.array(all_keypoints)

# Save keypoints
np.save(
    "extracted_keypoints/professional.npy",
    all_keypoints
)

print("Done!")
print("Shape:", all_keypoints.shape)
print("Saved to extracted_keypoints/professional.npy")