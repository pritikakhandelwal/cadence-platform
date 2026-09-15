import cv2
from modules.pose_detector import PoseDetector

# Create Pose Detector
detector = PoseDetector()

# Open Webcam
cap = cv2.VideoCapture(0)

while True:

    ret, frame = cap.read()

    if not ret:
        break

    # Detect Pose
    frame, results = detector.detect_pose(frame)

    # Show Output
    cv2.imshow("Pose Detection", frame)

    # Press q to Quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()