import cv2

# Open the default webcam (0 = primary camera)
cap = cv2.VideoCapture(0)

# Check if the webcam opened successfully
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

print("Press 'q' to exit.")

while True:
    # Capture one frame
    ret, frame = cap.read()

    if not ret:
        print("Failed to capture frame.")
        break

    # Display the frame
    cv2.imshow("AI Dance Instructor - Webcam Test", frame)

    # Exit when 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the webcam
cap.release()

# Close all OpenCV windows
cv2.destroyAllWindows()