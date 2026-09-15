import cv2

video_path = "data/professional/professional_dance.mp4"

print("Opening:", video_path)

cap = cv2.VideoCapture(video_path)

print("Is Opened:", cap.isOpened())

frame_count = 0

while True:

    ret, frame = cap.read()

    print("Reading frame:", frame_count, "Success:", ret)

    if not ret:
        print("Finished reading video.")
        break

    frame_count += 1

    cv2.imshow("Professional Dance", frame)

    key = cv2.waitKey(30)

    if key == ord('q'):
        print("Q pressed.")
        break

cap.release()
cv2.destroyAllWindows()